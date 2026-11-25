from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.features.catalog.postgres_repository import PostgresCatalogRepository
from app.lib.telemetry.events import AssistantInteractionEvent


@pytest.mark.parametrize("budget", [50, 1])
def test_no_match_computes_real_relaxations_and_invents_no_products(
    client: TestClient,
    catalog_repository: PostgresCatalogRepository,
    make_request: Callable[[str], dict],
    telemetry_events: list[AssistantInteractionEvent],
    budget: int,
) -> None:
    message = f"I need wireless headphones with noise cancellation under ${budget}."
    response = client.post("/api/v1/assistant/interactions", json=make_request(message))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"]["kind"] == "no_match"
    assert "No catalog products match" in body["reply"]["text"]
    assert body["presentations"] == []
    assert body["relaxations"]

    active_preference_ids = {
        preference["preferenceId"]
        for preference in body["conversation"]["preferences"]
        if preference["status"] == "active"
    }
    for relaxation in body["relaxations"]:
        assert relaxation["preferenceId"] in active_preference_ids
        assert relaxation["resultCount"] > 0

    budget_relaxation = next(
        relaxation
        for relaxation in body["relaxations"]
        if "budget" in relaxation["label"].lower()
    )
    expected_without_budget = [
        product
        for product in catalog_repository.list_products()
        if product.categoryId == "headphones"
        and product.attributes.get("noise-cancellation") is True
        and product.attributes.get("connectivity") is not None
        and any(
            value in str(product.attributes["connectivity"]).lower()
            for value in ("bluetooth", "wi-fi")
        )
    ]
    assert budget_relaxation["resultCount"] == len(expected_without_budget)
    assert str(budget) in budget_relaxation["label"]
    assert len(telemetry_events) == 1
    assert telemetry_events[0].outcome == "no_match"
