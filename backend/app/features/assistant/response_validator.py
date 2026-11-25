from uuid import UUID

from app.core.validation import Product
from app.features.assistant.conversation_state import assign_presented_references
from app.features.assistant.domain import (
    GroundingReference,
    PresentedProductReference,
    ProductPresentation,
    RankedCandidate,
)
from app.lib.ai.provider import ResponseSelection


class GroundingValidationError(ValueError):
    """Raised when provider output is not completely supported by catalog evidence."""


def validate_and_hydrate(
    selection: ResponseSelection,
    *,
    candidates: list[RankedCandidate],
    products: list[Product],
    existing_references: list[PresentedProductReference],
    assistant_turn_id: UUID,
) -> tuple[list[ProductPresentation], list[PresentedProductReference]]:
    """Reject untrusted IDs/claims, then hydrate every display value from the catalog."""
    evidence = {product.id: product for product in products}
    candidate_ids = [candidate.productId for candidate in candidates]
    try:
        selected_ids = _validate_selection(selection, candidate_ids=candidate_ids, evidence=evidence)
    except GroundingValidationError:
        selected_ids = candidate_ids

    all_references = assign_presented_references(
        existing_references, selected_ids, assistant_turn_id=assistant_turn_id
    )
    references = {reference.productId: reference for reference in all_references}
    matched_attributes = {
        candidate.productId: candidate.matchedAttributes for candidate in candidates
    }
    presentations = [
        _hydrate_presentation(
            evidence[product_id],
            reference=references[product_id],
            matched_attributes=matched_attributes[product_id],
        )
        for product_id in selected_ids
    ]
    return presentations, all_references


def _validate_selection(
    selection: ResponseSelection,
    *,
    candidate_ids: list[str],
    evidence: dict[str, Product],
) -> list[str]:
    if not selection.productIds or len(selection.productIds) != len(set(selection.productIds)):
        raise GroundingValidationError("Response selection must contain unique product IDs")
    if any(product_id not in candidate_ids or product_id not in evidence for product_id in selection.productIds):
        raise GroundingValidationError("Provider selected a product outside the evidence bundle")
    for claim in selection.claims:
        if claim.productId not in selection.productIds:
            raise GroundingValidationError("Claim references an unselected product")
        if not _claim_matches_catalog(claim.productId, claim.field, claim.value, evidence):
            raise GroundingValidationError("Provider claim is not supported by the catalog")
    return selection.productIds


def _claim_matches_catalog(
    product_id: str,
    field: str,
    value: object,
    evidence: dict[str, Product],
) -> bool:
    product = evidence[product_id]
    if field in {"id", "name", "categoryId", "description"}:
        return getattr(product, field) == value
    if field == "price":
        expected = product.price.model_dump(mode="json") if product.price is not None else None
        return expected == value
    if field.startswith("attributes."):
        key = field.removeprefix("attributes.")
        return key in product.attributes and product.attributes[key] == value
    return False


def hydrate_answer_presentation(
    product: Product,
    *,
    reference: PresentedProductReference,
    attribute: str,
) -> ProductPresentation:
    """Build a product-specific answer card from the asked catalog field only."""
    if attribute == "price":
        available = product.price is not None
        grounding_fields = ["id", "name", "price"]
        matched_attributes = []
        unavailable_fields = [] if available else ["price"]
    else:
        available = product.attributes.get(attribute) is not None
        grounding_fields = ["id", "name"]
        if attribute in product.attributes:
            grounding_fields.append(f"attributes.{attribute}")
        matched_attributes = [attribute] if available else []
        unavailable_fields = [] if available else [attribute]
    return ProductPresentation(
        reference=reference,
        product=product,
        matchedAttributes=matched_attributes,
        unavailableFields=unavailable_fields,
        grounding=[GroundingReference(productId=product.id, fields=grounding_fields)],
    )


def _hydrate_presentation(
    product: Product,
    *,
    reference: PresentedProductReference,
    matched_attributes: list[str],
) -> ProductPresentation:
    unavailable_fields = []
    if product.price is None:
        unavailable_fields.append("price")
    unavailable_fields.extend(
        key for key, value in product.attributes.items() if value is None
    )
    grounding_fields = ["id", "name", "categoryId", "description", "price"]
    grounding_fields.extend(f"attributes.{key}" for key in matched_attributes)
    return ProductPresentation(
        reference=reference,
        product=product,
        matchedAttributes=matched_attributes,
        unavailableFields=unavailable_fields,
        grounding=[GroundingReference(productId=product.id, fields=grounding_fields)],
    )
