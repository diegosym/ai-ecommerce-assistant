from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import get_settings
from app.core.validation import Product
from app.features.assistant.conversation_state import (
    active_requirements,
    append_interaction,
    assign_presented_references,
    new_assistant_turn,
    new_customer_turn,
    replace_same_slot_preferences,
    resolve_presented_reference,
)
from app.features.assistant.domain import (
    AssistantInteractionRequest,
    AssistantInteractionResponse,
    AssistantReply,
    CustomerPreference,
    InteractionMeasurements,
    ProductPresentation,
    RelaxationSuggestion,
    RetrievalQuery,
)
from app.features.assistant.response_validator import (
    hydrate_answer_presentation,
    validate_and_hydrate,
)
from app.features.catalog.repository import CatalogRepository
from app.lib.ai.prompts.boundaries import OUT_OF_SCOPE_REPLY
from app.lib.ai.provider import (
    LanguageModelProvider,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QuestionExtraction,
    call_with_timeout,
)
from app.lib.retrieval.hybrid import fuse_rankings
from app.lib.retrieval.lexical import count_matching_products, rank_products
from app.lib.retrieval.semantic import rank_semantic_candidates
from app.lib.telemetry.events import (
    AssistantInteractionEvent,
    AssistantInteractionEventInput,
    create_assistant_interaction_event,
)

UNAVAILABLE_TEXT = "Product information is temporarily unavailable. Please try again later."


class InteractionService:
    def __init__(
        self,
        *,
        repository: CatalogRepository,
        provider: LanguageModelProvider,
        emit_event: Callable[[AssistantInteractionEvent], None],
        retrieval: str | None = None,
        provider_timeout_seconds: float | None = None,
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.emit_event = emit_event
        self.retrieval = retrieval or get_settings().ai_retrieval
        self.provider_timeout_seconds = (
            provider_timeout_seconds or get_settings().provider_timeout_seconds
        )

    def handle(self, request: AssistantInteractionRequest) -> AssistantInteractionResponse:
        received_at = datetime.now(UTC)
        interaction_id = uuid4()
        customer_turn_id = uuid4()
        assistant_turn_id = uuid4()
        customer_turn = new_customer_turn(
            request.message, turn_id=customer_turn_id, created_at=received_at
        )
        new_preferences: list[CustomerPreference] = []
        presentations: list[ProductPresentation] = []
        presented_references = list(request.conversation.presentedProducts)
        relaxations: list[RelaxationSuggestion] = []
        catalog_version = None
        outcome = "unavailable"
        error_code = None
        stage = "catalog"
        reply_text = UNAVAILABLE_TEXT
        assumptions: list[str] = []
        provider_failure = False

        try:
            metadata = self.repository.get_metadata()
            catalog_version = metadata.catalogVersion if metadata is not None else None
            products = self.repository.list_products()
            if not products:
                reply_text = UNAVAILABLE_TEXT
                outcome = "unavailable"
            else:
                stage = "provider"
                extraction = self._call_provider(
                    self.provider.extract_preferences, message=request.message
                )
                assumptions = extraction.assumptions
                new_preferences = [
                    CustomerPreference(
                        preferenceId=uuid4(),
                        slot=preference.slot,
                        key=preference.key,
                        nature="requirement",
                        value=preference.value,
                        sourceTurnId=customer_turn_id,
                        status="active",
                    )
                    for preference in extraction.preferences
                ] + [
                    CustomerPreference(
                        preferenceId=uuid4(),
                        slot=preference.slot,
                        key=preference.key,
                        nature="belief",
                        value=preference.value,
                        sourceTurnId=customer_turn_id,
                        status="active",
                    )
                    for preference in extraction.beliefs
                ]
                if extraction.intent == "out_of_scope":
                    reply_text = OUT_OF_SCOPE_REPLY
                    outcome = "out_of_scope"
                elif extraction.intent == "product_question":
                    stage = "response"
                    if extraction.question is None:
                        reply_text = "Which catalog product would you like to ask about?"
                        outcome = "clarification"
                    else:
                        (
                            reply_text,
                            outcome,
                            presentations,
                            presented_references,
                        ) = self._answer_question(
                            extraction.question,
                            products=products,
                            existing_references=request.conversation.presentedProducts,
                            assistant_turn_id=assistant_turn_id,
                            beliefs=new_preferences,
                        )
                elif not new_preferences:
                    reply_text = (
                        "I can help you discover catalog products. Please tell me a product "
                        "category, characteristics, or budget."
                    )
                    outcome = "clarification"
                else:
                    stage = "response"
                    merged_preferences = replace_same_slot_preferences(
                        request.conversation.preferences, new_preferences
                    )
                    requirements = active_requirements(merged_preferences)
                    if any(requirement.slot == "budget" for requirement in requirements):
                        assumptions = [
                            assumption
                            for assumption in assumptions
                            if not assumption.startswith("No budget was stated")
                        ]
                    query = RetrievalQuery(
                        text=request.message, requirements=requirements, limit=3
                    )
                    candidates = self._rank_candidates(products, query)
                    if not candidates:
                        relaxations = self._compute_relaxations(products, requirements)
                        reply_text = (
                            "No catalog products match all of your stated requirements. "
                            "You can relax one of the criteria below."
                        )
                        outcome = "no_match"
                    else:
                        candidate_ids = {candidate.productId for candidate in candidates}
                        evidence = [product for product in products if product.id in candidate_ids]
                        selection = self._call_provider(
                            self.provider.select_response,
                            message=request.message,
                            candidates=candidates,
                            products=evidence,
                        )
                        presentations, presented_references = validate_and_hydrate(
                            selection,
                            candidates=candidates,
                            products=evidence,
                            existing_references=request.conversation.presentedProducts,
                            assistant_turn_id=assistant_turn_id,
                        )
                        reply_text = self._recommendation_text(assumptions)
                        outcome = "recommendations"
        except ProviderTimeoutError:
            presentations = []
            relaxations = []
            presented_references = list(request.conversation.presentedProducts)
            reply_text = UNAVAILABLE_TEXT
            outcome = "error"
            error_code = "provider_unavailable"
            provider_failure = True
        except Exception:
            presentations = []
            relaxations = []
            presented_references = list(request.conversation.presentedProducts)
            reply_text = UNAVAILABLE_TEXT
            outcome = "unavailable"
            error_code = {
                "catalog": "catalog_unavailable",
                "provider": "provider_unavailable",
                "response": "response_validation_failed",
            }[stage]

        completed_at = datetime.now(UTC)
        assistant_turn = new_assistant_turn(
            reply_text,
            turn_id=assistant_turn_id,
            interaction_id=interaction_id,
            created_at=completed_at,
        )
        conversation = append_interaction(
            request.conversation,
            customer_turn=customer_turn,
            assistant_turn=assistant_turn,
            new_preferences=new_preferences,
            presentations=presented_references,
        )
        event = create_assistant_interaction_event(
            AssistantInteractionEventInput(
                eventType="assistant_interaction",
                interactionId=interaction_id,
                conversationId=request.conversation.conversationId,
                receivedAt=received_at,
                completedAt=completed_at,
                catalogVersion=catalog_version,
                provider=self.provider.provider_name,
                modelId=self.provider.model_id,
                promptVersion=self.provider.prompt_version,
                outcome=outcome,
                errorCode=error_code,
            )
        )
        self.emit_event(event)
        if provider_failure:
            raise ProviderUnavailableError(interaction_id)
        return AssistantInteractionResponse(
            conversation=conversation,
            reply=AssistantReply(kind=outcome, text=reply_text),
            presentations=presentations,
            relaxations=relaxations,
            measurements=InteractionMeasurements(
                interactionId=interaction_id,
                latencyMs=event.latencyMs,
            ),
            catalogVersion=catalog_version,
        )

    def _call_provider(self, operation, **kwargs):
        return call_with_timeout(
            lambda: operation(**kwargs), self.provider_timeout_seconds
        )

    def _rank_candidates(
        self, products: list[Product], query: RetrievalQuery
    ) -> list:
        lexical_query = query.model_copy(update={"limit": 10})
        lexical = rank_products(products, lexical_query)
        if self.retrieval == "lexical":
            return lexical[: query.limit]
        semantic = rank_semantic_candidates(self.repository, products, lexical_query)
        return fuse_rankings(lexical, semantic, limit=query.limit)

    def _answer_question(
        self,
        question: QuestionExtraction,
        *,
        products: list[Product],
        existing_references,
        assistant_turn_id,
        beliefs: list[CustomerPreference],
    ) -> tuple[str, str, list[ProductPresentation], list]:
        products_by_id = {product.id: product for product in products}
        if question.comparative:
            return self._answer_comparison(
                question,
                products_by_id=products_by_id,
                existing_references=existing_references,
            )

        if question.productId is not None:
            product = products_by_id.get(question.productId)
            if product is None:
                return self._unverified_product(existing_references)
            references = assign_presented_references(
                existing_references,
                [product.id],
                assistant_turn_id=assistant_turn_id,
            )
            reference = next(ref for ref in references if ref.productId == product.id)
        else:
            ordinal = question.ordinal or 1
            reference = resolve_presented_reference(existing_references, ordinal)
            if reference is None:
                if existing_references:
                    return (
                        "I can’t verify that product reference in this conversation.",
                        "unavailable",
                        [],
                        existing_references,
                    )
                return (
                    "Which catalog product would you like to ask about?",
                    "clarification",
                    [],
                    existing_references,
                )
            product = products_by_id.get(reference.productId)
            if product is None:
                return (
                    "I can no longer verify that product in the current catalog.",
                    "unavailable",
                    [],
                    existing_references,
                )
            references = existing_references

        presentation = hydrate_answer_presentation(
            product,
            reference=reference,
            attribute=question.attribute,
        )
        if presentation.unavailableFields:
            label = question.attribute.replace("-", " ")
            return (
                f"{label.capitalize()} information is not available in the catalog "
                f"for {product.name}.",
                "unavailable",
                [presentation],
                references,
            )
        return (
            self._answer_text(product, question.attribute, beliefs),
            "answer",
            [presentation],
            references,
        )

    def _answer_comparison(
        self,
        question: QuestionExtraction,
        *,
        products_by_id: dict[str, Product],
        existing_references,
    ) -> tuple[str, str, list[ProductPresentation], list]:
        if not existing_references:
            return (
                "Which catalog products would you like me to compare?",
                "clarification",
                [],
                existing_references,
            )
        compared = []
        for reference in existing_references:
            product = products_by_id.get(reference.productId)
            if product is None:
                return (
                    "I can no longer verify one of those products in the current catalog.",
                    "unavailable",
                    [],
                    existing_references,
                )
            weight = product.attributes.get(question.attribute)
            if type(weight) not in (int, float):
                presentation = hydrate_answer_presentation(
                    product, reference=reference, attribute=question.attribute
                )
                return (
                    f"Weight information is not available in the catalog for {product.name}.",
                    "unavailable",
                    [presentation],
                    existing_references,
                )
            compared.append((weight, product.id, product, reference))
        weight, _product_id, product, reference = min(compared)
        presentation = hydrate_answer_presentation(
            product, reference=reference, attribute=question.attribute
        )
        return (
            f"Among the presented products, {product.name} is the lightest at {weight} g.",
            "answer",
            [presentation],
            existing_references,
        )

    @staticmethod
    def _unverified_product(existing_references) -> tuple[str, str, list, list]:
        return (
            "I can’t verify that product in the current catalog.",
            "unavailable",
            [],
            existing_references,
        )

    @staticmethod
    def _answer_text(
        product: Product,
        attribute: str,
        beliefs: list[CustomerPreference],
    ) -> str:
        if attribute == "price":
            assert product.price is not None
            price = f"${product.price.amountMinor / 100:.2f}"
            belief = next((item for item in beliefs if item.nature == "belief"), None)
            belief_text = ""
            if belief is not None and belief.value["amountMinor"] != product.price.amountMinor:
                belief_text = (
                    f"Your stated belief was ${belief.value['amountMinor'] / 100:.2f}. "
                )
            return (
                f"{belief_text}The verified catalog price for {product.name} is {price}."
            )
        value = product.attributes[attribute]
        label = attribute.replace("-", " ")
        if attribute == "battery-life":
            return f"{product.name} has a catalog-listed battery life of {value} hours."
        if attribute == "weight":
            return f"{product.name} has a catalog-listed weight of {value} g."
        if type(value) is bool:
            answer = "Yes" if value else "No"
            verb = "has" if value else "does not have"
            return f"{answer}. {product.name} {verb} {label}, according to the catalog."
        return f"{product.name} has {label} of {value}, according to the catalog."

    def _compute_relaxations(
        self, products, requirements: list[CustomerPreference]
    ) -> list[RelaxationSuggestion]:
        suggestions = []
        for requirement in requirements:
            result_count = count_matching_products(
                products,
                requirements,
                excluded_preference_id=requirement.preferenceId,
            )
            if result_count > 0:
                suggestions.append(
                    RelaxationSuggestion(
                        preferenceId=requirement.preferenceId,
                        label=self._relaxation_label(requirement),
                        resultCount=result_count,
                    )
                )
        return suggestions[:5]

    @staticmethod
    def _relaxation_label(requirement: CustomerPreference) -> str:
        if requirement.slot == "budget":
            amount = requirement.value["amountMinor"] / 100
            return f"Increase the ${amount:.2f} budget"
        if requirement.slot == "category":
            return f"Broaden the {requirement.value['id']} category"
        return f"Remove the {requirement.value.get('key', requirement.key)} requirement"

    @staticmethod
    def _recommendation_text(assumptions: list[str]) -> str:
        recommendation = "Here are catalog-grounded recommendations matching your stated requirements."
        return f"{' '.join(assumptions)} {recommendation}".strip()
