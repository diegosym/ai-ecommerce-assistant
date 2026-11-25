from collections.abc import Callable

from app.features.catalog.repository import CatalogMetadata
from app.lib.telemetry.events import AssistantInteractionEvent


class EmptyCatalogRepository:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def get_metadata(self) -> CatalogMetadata | None:
        if self.fail:
            raise ConnectionError("catalog unavailable")
        return None

    def list_products(self):
        if self.fail:
            raise ConnectionError("catalog unavailable")
        return []

    def list_categories(self):
        return []

    def get_product(self, product_id: str):
        return None


def test_empty_catalog_returns_unavailable_without_fabrication(
    client_factory,
    make_request: Callable[[str], dict],
    telemetry_events: list[AssistantInteractionEvent],
) -> None:
    with client_factory(EmptyCatalogRepository()) as empty_client:
        response = empty_client.post(
            "/api/v1/assistant/interactions",
            json=make_request("Wireless headphones under $150"),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"]["kind"] == "unavailable"
    assert "temporarily unavailable" in body["reply"]["text"]
    assert body["presentations"] == []
    assert body["relaxations"] == []
    assert body["catalogVersion"] is None
    assert len(telemetry_events) == 1
    assert telemetry_events[0].outcome == "unavailable"


def test_catalog_failure_returns_unavailable_and_emits_one_terminal_event(
    client_factory,
    make_request: Callable[[str], dict],
    telemetry_events: list[AssistantInteractionEvent],
) -> None:
    with client_factory(EmptyCatalogRepository(fail=True)) as unavailable_client:
        response = unavailable_client.post(
            "/api/v1/assistant/interactions",
            json=make_request("Wireless headphones under $150"),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"]["kind"] == "unavailable"
    assert body["presentations"] == []
    assert len(telemetry_events) == 1
    assert telemetry_events[0].outcome == "unavailable"
    assert telemetry_events[0].errorCode == "catalog_unavailable"
    assert "catalog unavailable" not in telemetry_events[0].model_dump_json()
