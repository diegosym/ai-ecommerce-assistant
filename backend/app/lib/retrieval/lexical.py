import re
from collections.abc import Iterable

from app.core.validation import Product
from app.features.assistant.domain import CustomerPreference, RankedCandidate, RetrievalQuery

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a",
    "and",
    "any",
    "budget",
    "for",
    "i",
    "in",
    "me",
    "my",
    "need",
    "of",
    "show",
    "the",
    "under",
    "with",
}


def eligible_products(
    products: Iterable[Product], requirements: list[CustomerPreference]
) -> list[Product]:
    return [product for product in products if _matches_all(product, requirements)]


def matched_attributes(
    product: Product, requirements: list[CustomerPreference]
) -> list[str]:
    return _matched_attributes(product, requirements)


def rank_products(products: Iterable[Product], query: RetrievalQuery) -> list[RankedCandidate]:
    eligible = eligible_products(products, query.requirements)
    query_tokens = set(TOKEN_PATTERN.findall(query.text.lower())) - STOP_WORDS
    ranked = sorted(
        eligible,
        key=lambda product: (
            -_lexical_score(product, query_tokens),
            product.price.amountMinor if product.price is not None else 2**63,
            product.id,
        ),
    )
    return [
        RankedCandidate(
            productId=product.id,
            lexicalRank=index,
            hybridRank=index,
            matchedAttributes=_matched_attributes(product, query.requirements),
        )
        for index, product in enumerate(ranked[: query.limit], start=1)
    ]


def count_matching_products(
    products: Iterable[Product],
    requirements: list[CustomerPreference],
    *,
    excluded_preference_id: object,
) -> int:
    remaining = [
        requirement
        for requirement in requirements
        if requirement.preferenceId != excluded_preference_id
    ]
    return sum(1 for product in products if _matches_all(product, remaining))


def _matches_all(product: Product, requirements: list[CustomerPreference]) -> bool:
    return all(
        _matches_requirement(product, requirement)
        for requirement in requirements
        if requirement.nature == "requirement" and requirement.status == "active"
    )


def _matches_requirement(product: Product, requirement: CustomerPreference) -> bool:
    if requirement.slot == "category":
        return product.categoryId == requirement.value.get("id")
    if requirement.slot == "budget":
        return (
            product.price is not None
            and product.price.currency == requirement.value.get("currency")
            and product.price.amountMinor <= requirement.value.get("amountMinor", -1)
        )
    if requirement.slot != "characteristic":
        return True

    key = requirement.value.get("key")
    if key not in product.attributes:
        return False
    actual = product.attributes[key]
    if actual is None:
        return False
    expected = requirement.value.get("value")
    if requirement.value.get("operator") == "min":
        return type(actual) in (int, float) and actual >= expected
    if key == "connectivity" and isinstance(expected, str):
        actual_text = str(actual).lower()
        if expected.lower() == "wireless":
            return any(value in actual_text for value in ("bluetooth", "wi-fi"))
        return expected.lower() in actual_text
    return actual == expected


def _matched_attributes(
    product: Product, requirements: list[CustomerPreference]
) -> list[str]:
    return list(
        dict.fromkeys(
            requirement.value["key"]
            for requirement in requirements
            if requirement.slot == "characteristic"
            and requirement.status == "active"
            and requirement.value.get("key") in product.attributes
        )
    )


def _lexical_score(product: Product, query_tokens: set[str]) -> int:
    attribute_text = " ".join(f"{key} {value}" for key, value in product.attributes.items())
    product_tokens = set(
        TOKEN_PATTERN.findall(
            f"{product.name} {product.categoryId} {product.description} {attribute_text}".lower()
        )
    )
    return len(query_tokens & product_tokens)
