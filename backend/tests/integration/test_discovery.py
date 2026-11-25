from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.features.catalog.postgres_repository import PostgresCatalogRepository
from app.lib.ai.fake_provider import FakeLanguageModelProvider
from app.lib.ai.provider import ProductClaim, ResponseSelection
from app.lib.telemetry.events import AssistantInteractionEvent

DISCOVERY_MESSAGE = (
    "I need wireless headphones for working, with noise cancellation and a budget of $150."
)


def test_discovery_returns_only_catalog_products_matching_every_requirement(
    client: TestClient,
    catalog_repository: PostgresCatalogRepository,
    make_request: Callable[[str], dict],
    telemetry_events: list[AssistantInteractionEvent],
) -> None:
    response = client.post("/api/v1/assistant/interactions", json=make_request(DISCOVERY_MESSAGE))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"]["kind"] == "recommendations"
    assert body["catalogVersion"] == "1.0.0"
    assert body["relaxations"] == []
    assert 1 <= len(body["presentations"]) <= 10

    for presentation in body["presentations"]:
        product = presentation["product"]
        catalog_product = catalog_repository.get_product(product["id"])
        assert catalog_product is not None
        assert product == catalog_product.model_dump(mode="json")
        assert product["categoryId"] == "headphones"
        assert product["price"]["amountMinor"] <= 15000
        assert product["attributes"]["noise-cancellation"] is True
        assert any(
            wireless in product["attributes"]["connectivity"].lower()
            for wireless in ("bluetooth", "wi-fi")
        )
        assert presentation["grounding"][0]["productId"] == product["id"]
        assert "name" in presentation["grounding"][0]["fields"]
        assert "price" in presentation["grounding"][0]["fields"]

    assert len(body["conversation"]["turns"]) == 2
    assert body["conversation"]["turns"][0]["text"] == DISCOVERY_MESSAGE
    assert body["conversation"]["turns"][1]["interactionId"] == body["measurements"][
        "interactionId"
    ]
    assert len(telemetry_events) == 1
    assert telemetry_events[0].outcome == "recommendations"
    assert telemetry_events[0].provider == "fake"
    assert DISCOVERY_MESSAGE not in telemetry_events[0].model_dump_json()


def test_missing_budget_is_an_explicit_assumption(
    client: TestClient,
    make_request: Callable[[str], dict],
) -> None:
    response = client.post(
        "/api/v1/assistant/interactions",
        json=make_request("Show me noise-cancelling headphones"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"]["kind"] == "recommendations"
    assert "No budget was stated" in body["reply"]["text"]
    assert body["presentations"]


def test_quickstart_for_budget_phrase_is_applied_without_missing_budget_assumption(
    client: TestClient,
    make_request: Callable[[str], dict],
) -> None:
    response = client.post(
        "/api/v1/assistant/interactions",
        json=make_request("I need wireless headphones with noise cancellation for $150."),
    )

    assert response.status_code == 200
    body = response.json()
    assert "No budget was stated" not in body["reply"]["text"]
    budget = next(
        preference
        for preference in body["conversation"]["preferences"]
        if preference["slot"] == "budget"
    )
    assert budget["value"]["amountMinor"] == 15000
    assert all(
        presentation["product"]["price"]["amountMinor"] <= 15000
        for presentation in body["presentations"]
    )


def test_gibberish_gets_clarification_without_products(
    client: TestClient,
    make_request: Callable[[str], dict],
) -> None:
    response = client.post(
        "/api/v1/assistant/interactions",
        json=make_request("flarble zqx 123 !!!!"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"]["kind"] == "clarification"
    assert body["presentations"] == []
    assert body["relaxations"] == []


class InvalidGroundingProvider(FakeLanguageModelProvider):
    def __init__(self, unknown_product: bool) -> None:
        self.unknown_product = unknown_product

    def select_response(self, *, message, candidates, products) -> ResponseSelection:
        selected_id = "not-in-catalog" if self.unknown_product else candidates[0].productId
        return ResponseSelection(
            productIds=[selected_id],
            claims=[
                ProductClaim(
                    productId=selected_id,
                    field="price",
                    value={"amountMinor": 1, "currency": "USD"},
                )
            ],
        )


@pytest.mark.parametrize("unknown_product", [True, False])
def test_invalid_provider_output_falls_back_to_grounded_deterministic_response(
    client_factory,
    catalog_repository: PostgresCatalogRepository,
    make_request: Callable[[str], dict],
    unknown_product: bool,
) -> None:
    with client_factory(
        catalog_repository, InvalidGroundingProvider(unknown_product=unknown_product)
    ) as invalid_client:
        response = invalid_client.post(
            "/api/v1/assistant/interactions", json=make_request(DISCOVERY_MESSAGE)
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"]["kind"] == "recommendations"
    assert "0.01" not in body["reply"]["text"]
    for presentation in body["presentations"]:
        assert presentation["product"]["id"] != "not-in-catalog"
        assert presentation["product"] == catalog_repository.get_product(
            presentation["product"]["id"]
        ).model_dump(mode="json")
