import time
from collections.abc import Callable

from app.lib.ai.fake_provider import FakeLanguageModelProvider
from app.lib.telemetry.events import AssistantInteractionEvent


class SlowProvider(FakeLanguageModelProvider):
    def extract_preferences(self, *, message: str):
        time.sleep(0.2)
        return super().extract_preferences(message=message)


def test_provider_timeout_returns_typed_error_without_partial_content(
    client_factory,
    catalog_repository,
    make_request: Callable[[str], dict],
    telemetry_events: list[AssistantInteractionEvent],
) -> None:
    started = time.perf_counter()
    with client_factory(catalog_repository, SlowProvider()) as slow_client:
        response = slow_client.post(
            "/api/v1/assistant/interactions",
            json=make_request("Wireless headphones under $150"),
        )
    elapsed = time.perf_counter() - started

    assert elapsed < 0.15
    assert response.status_code == 503, response.text
    assert response.json() == {
        "error": {
            "code": "provider_unavailable",
            "message": "The language model provider is temporarily unavailable.",
            "retryable": True,
        },
        "interactionId": response.json()["interactionId"],
    }
    assert response.json()["interactionId"] is not None
    assert "presentations" not in response.json()
    assert len(telemetry_events) == 1
    event = telemetry_events[0]
    assert event.outcome == "error"
    assert event.errorCode == "provider_unavailable"
    assert str(event.interactionId) == response.json()["interactionId"]
    assert "Wireless headphones" not in event.model_dump_json()
