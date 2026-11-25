import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.lib.telemetry.events import (
    AssistantInteractionEventInput,
    aggregate_estimated_cost_by_conversation,
    create_assistant_interaction_event,
)
from app.lib.telemetry.logger import log_assistant_interaction


def event_input() -> AssistantInteractionEventInput:
    return AssistantInteractionEventInput.model_validate(
        {
            "eventType": "assistant_interaction",
            "interactionId": "6b5a24c4-91a1-4f7f-9f72-c228e2798c01",
            "conversationId": "a17a8a07-20ef-4fc2-93cb-c4c7a41c7f9e",
            "receivedAt": "2026-11-25T12:00:00.000Z",
            "completedAt": "2026-11-25T12:00:00.125Z",
            "catalogVersion": "1.0.0",
            "provider": "fake",
            "modelId": "fake-chat-v1",
            "promptVersion": "fake-prompt-v1",
            "inputTokens": 20,
            "outputTokens": 30,
            "estimatedCostMinor": 0,
            "currency": "USD",
            "pricingVersion": "fake-v1",
            "outcome": "recommendations",
            "errorCode": None,
        }
    )


def test_emits_one_structured_event_with_measured_latency() -> None:
    lines: list[str] = []
    event = create_assistant_interaction_event(event_input())

    log_assistant_interaction(event, lines.append)

    assert event.latencyMs == 125
    assert len(lines) == 1
    assert json.loads(lines[0]) == event.model_dump(mode="json")
    assert "rawMessage" not in lines[0]


def test_aggregates_estimated_cost_by_conversation_id_without_treating_unknown_as_zero() -> None:
    first_conversation = event_input().conversationId
    other_conversation = UUID("76ec1e07-02eb-47f0-a7a7-f6a6ef2a0ce5")
    events = [
        create_assistant_interaction_event(
            event_input().model_copy(update={"estimatedCostMinor": 0.25})
        ),
        create_assistant_interaction_event(
            event_input().model_copy(update={"estimatedCostMinor": 0.75})
        ),
        create_assistant_interaction_event(
            event_input().model_copy(
                update={"conversationId": other_conversation, "estimatedCostMinor": 0.5}
            )
        ),
        create_assistant_interaction_event(
            event_input().model_copy(
                update={"estimatedCostMinor": None, "currency": None, "pricingVersion": None}
            )
        ),
    ]

    totals = aggregate_estimated_cost_by_conversation(events)

    assert totals[first_conversation] == pytest.approx(1.0)
    assert totals[other_conversation] == pytest.approx(0.5)
    assert len(totals) == 2


def test_rejects_raw_message_fields_instead_of_logging_them() -> None:
    event = event_input().model_dump()
    event["latencyMs"] = 125
    event["rawMessage"] = "private customer text"

    with pytest.raises(ValidationError, match="rawMessage"):
        log_assistant_interaction(event, lambda _: None)
