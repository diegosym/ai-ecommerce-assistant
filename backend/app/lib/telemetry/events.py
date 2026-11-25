from collections.abc import Iterable
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.validation import Currency, SemanticVersion


class AssistantInteractionEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventType: Literal["assistant_interaction"]
    interactionId: UUID
    conversationId: UUID
    receivedAt: datetime
    completedAt: datetime
    catalogVersion: SemanticVersion | None
    provider: str | None = Field(default=None, min_length=1)
    modelId: str | None = Field(default=None, min_length=1)
    promptVersion: str | None = Field(default=None, min_length=1)
    inputTokens: int | None = Field(default=None, ge=0)
    outputTokens: int | None = Field(default=None, ge=0)
    estimatedCostMinor: float | None = Field(default=None, ge=0)
    currency: Currency | None = None
    pricingVersion: str | None = Field(default=None, min_length=1)
    outcome: Literal[
        "recommendations",
        "answer",
        "clarification",
        "no_match",
        "out_of_scope",
        "unavailable",
        "error",
    ]
    errorCode: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_timing_and_cost(self) -> "AssistantInteractionEventInput":
        if self.completedAt < self.receivedAt:
            raise ValueError("completedAt must not precede receivedAt")
        if self.estimatedCostMinor is not None:
            if self.pricingVersion is None:
                raise ValueError("pricingVersion is required with estimatedCostMinor")
            if self.currency is None:
                raise ValueError("currency is required with estimatedCostMinor")
        return self


class AssistantInteractionEvent(AssistantInteractionEventInput):
    latencyMs: int = Field(ge=0)


def aggregate_estimated_cost_by_conversation(
    events: Iterable[AssistantInteractionEvent],
) -> dict[UUID, float]:
    """Aggregate known estimates only; unknown costs are never coerced to zero."""
    totals: dict[UUID, float] = {}
    for event in events:
        if event.estimatedCostMinor is not None:
            totals[event.conversationId] = (
                totals.get(event.conversationId, 0) + event.estimatedCostMinor
            )
    return totals


def create_assistant_interaction_event(
    event_input: AssistantInteractionEventInput,
) -> AssistantInteractionEvent:
    latency_ms = int((event_input.completedAt - event_input.receivedAt).total_seconds() * 1000)
    return AssistantInteractionEvent.model_validate(
        {**event_input.model_dump(), "latencyMs": latency_ms}
    )
