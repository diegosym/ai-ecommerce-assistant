from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.core.validation import Currency, Product, SemanticVersion, Slug, StrictSchema


class ConversationTurn(StrictSchema):
    turnId: UUID
    role: Literal["customer", "assistant"]
    text: str = Field(max_length=12000)
    createdAt: datetime
    interactionId: UUID | None = None

    @model_validator(mode="after")
    def require_timezone(self) -> "ConversationTurn":
        if self.createdAt.utcoffset() is None:
            raise ValueError("createdAt must include a timezone offset")
        return self


class CustomerPreference(StrictSchema):
    preferenceId: UUID
    slot: Literal["category", "characteristic", "budget", "other"]
    key: str | None = Field(default=None, max_length=100)
    nature: Literal["requirement", "belief"]
    value: Any
    sourceTurnId: UUID
    status: Literal["active", "replaced"]


class PresentedProductReference(StrictSchema):
    ordinal: int = Field(ge=1)
    productId: Slug
    firstPresentedTurnId: UUID


class ConversationState(StrictSchema):
    conversationId: UUID
    createdAt: datetime
    turns: list[ConversationTurn] = Field(max_length=50)
    preferences: list[CustomerPreference] = Field(max_length=30)
    presentedProducts: list[PresentedProductReference] = Field(max_length=50)

    @model_validator(mode="after")
    def validate_internal_references(self) -> "ConversationState":
        if self.createdAt.utcoffset() is None:
            raise ValueError("createdAt must include a timezone offset")
        turn_ids = [turn.turnId for turn in self.turns]
        if len(turn_ids) != len(set(turn_ids)):
            raise ValueError("turnId values must be unique")
        known_turn_ids = set(turn_ids)
        for preference in self.preferences:
            if preference.sourceTurnId not in known_turn_ids:
                raise ValueError("Preference sourceTurnId must reference a conversation turn")
        ordinals = [reference.ordinal for reference in self.presentedProducts]
        if len(ordinals) != len(set(ordinals)) or ordinals != sorted(ordinals):
            raise ValueError("Presented product ordinals must be unique and increasing")
        for reference in self.presentedProducts:
            if reference.firstPresentedTurnId not in known_turn_ids:
                raise ValueError("firstPresentedTurnId must reference a conversation turn")
        return self


class AssistantInteractionRequest(StrictSchema):
    conversation: ConversationState
    message: str = Field(min_length=1, max_length=4000)


class AssistantReply(StrictSchema):
    kind: Literal[
        "recommendations",
        "answer",
        "clarification",
        "no_match",
        "out_of_scope",
        "unavailable",
    ]
    text: str = Field(max_length=12000)


class GroundingReference(StrictSchema):
    productId: Slug
    fields: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_fields(self) -> "GroundingReference":
        if len(self.fields) != len(set(self.fields)):
            raise ValueError("Grounding fields must be unique")
        return self


class ProductPresentation(StrictSchema):
    reference: PresentedProductReference
    product: Product
    matchedAttributes: list[str]
    unavailableFields: list[str]
    grounding: list[GroundingReference] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_field_lists(self) -> "ProductPresentation":
        if len(self.matchedAttributes) != len(set(self.matchedAttributes)):
            raise ValueError("matchedAttributes must be unique")
        if len(self.unavailableFields) != len(set(self.unavailableFields)):
            raise ValueError("unavailableFields must be unique")
        return self


class RelaxationSuggestion(StrictSchema):
    preferenceId: UUID
    label: str
    resultCount: int = Field(ge=0)


class InteractionMeasurements(StrictSchema):
    interactionId: UUID
    latencyMs: int = Field(ge=0)
    inputTokens: int | None = Field(default=None, ge=0)
    outputTokens: int | None = Field(default=None, ge=0)
    estimatedCostMinor: float | None = Field(default=None, ge=0)
    currency: Currency | None = None
    pricingVersion: str | None = None


class AssistantInteractionResponse(StrictSchema):
    conversation: ConversationState
    reply: AssistantReply
    presentations: list[ProductPresentation] = Field(max_length=10)
    relaxations: list[RelaxationSuggestion] = Field(max_length=5)
    measurements: InteractionMeasurements
    catalogVersion: SemanticVersion | None


class RetrievalQuery(StrictSchema):
    text: str = Field(min_length=1, max_length=4000)
    requirements: list[CustomerPreference] = Field(max_length=30)
    limit: int = Field(default=3, ge=1, le=10)


class RankedCandidate(StrictSchema):
    productId: Slug
    lexicalRank: int | None = Field(default=None, ge=1)
    semanticRank: int | None = Field(default=None, ge=1)
    hybridRank: int = Field(ge=1)
    matchedAttributes: list[str]


class Recommendation(StrictSchema):
    recommendationId: UUID
    requestTurnId: UUID
    candidates: list[RankedCandidate] = Field(max_length=10)
    grounding: list[GroundingReference] = Field(min_length=1)
    relaxedCriteria: list[RelaxationSuggestion] = Field(default_factory=list, max_length=5)


class ErrorDetail(StrictSchema):
    code: Literal[
        "invalid_request",
        "invalid_state",
        "not_found",
        "catalog_unavailable",
        "provider_unavailable",
        "response_validation_failed",
        "internal_error",
    ]
    message: str
    retryable: bool


class ErrorResponse(StrictSchema):
    error: ErrorDetail
    interactionId: UUID | None
