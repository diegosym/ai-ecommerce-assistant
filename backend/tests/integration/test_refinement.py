from collections.abc import Callable

from fastapi.testclient import TestClient


def active_by_slot(preferences: list[dict], slot: str, key: str | None = None) -> dict:
    return next(
        preference
        for preference in preferences
        if preference["status"] == "active"
        and preference["slot"] == slot
        and preference.get("key") == key
    )


def refine(client: TestClient, conversation: dict, message: str) -> dict:
    response = client.post(
        "/api/v1/assistant/interactions",
        json={"conversation": conversation, "message": message},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_new_characteristic_preserves_category_budget_and_connectivity(
    client: TestClient,
    make_request: Callable[[str], dict],
) -> None:
    first_response = client.post(
        "/api/v1/assistant/interactions",
        json=make_request("Wireless headphones under $150"),
    )
    assert first_response.status_code == 200
    first = first_response.json()

    second = refine(client, first["conversation"], "Also add noise cancellation")

    first_preferences = first["conversation"]["preferences"]
    second_preferences = second["conversation"]["preferences"]
    for slot, key in (("category", None), ("budget", None), ("characteristic", "connectivity")):
        before = active_by_slot(first_preferences, slot, key)
        after = active_by_slot(second_preferences, slot, key)
        assert after["preferenceId"] == before["preferenceId"]
        assert after["value"] == before["value"]
        assert after["sourceTurnId"] == before["sourceTurnId"]

    noise = active_by_slot(second_preferences, "characteristic", "noise-cancellation")
    assert noise["sourceTurnId"] == second["conversation"]["turns"][-2]["turnId"]
    assert second["reply"]["kind"] == "recommendations"
    assert second["presentations"]
    for presentation in second["presentations"]:
        product = presentation["product"]
        assert product["categoryId"] == "headphones"
        assert product["price"]["amountMinor"] <= 15000
        assert product["attributes"]["noise-cancellation"] is True
        assert any(
            value in product["attributes"]["connectivity"].lower()
            for value in ("bluetooth", "wi-fi")
        )


def test_budget_replacement_recomputes_results_without_changing_other_preferences(
    client: TestClient,
    make_request: Callable[[str], dict],
) -> None:
    first_response = client.post(
        "/api/v1/assistant/interactions",
        json=make_request("Wireless headphones with noise cancellation under $150"),
    )
    assert first_response.status_code == 200
    first = first_response.json()
    first_ids = {presentation["product"]["id"] for presentation in first["presentations"]}
    assert "headphones-004" in first_ids

    second = refine(client, first["conversation"], "Actually my budget is $120")

    first_preferences = first["conversation"]["preferences"]
    second_preferences = second["conversation"]["preferences"]
    old_budget = active_by_slot(first_preferences, "budget")
    replaced_budget = next(
        preference
        for preference in second_preferences
        if preference["preferenceId"] == old_budget["preferenceId"]
    )
    new_budget = active_by_slot(second_preferences, "budget")
    assert replaced_budget["status"] == "replaced"
    assert replaced_budget["value"]["amountMinor"] == 15000
    assert new_budget["preferenceId"] != old_budget["preferenceId"]
    assert new_budget["value"] == {"amountMinor": 12000, "currency": "USD"}
    assert new_budget["sourceTurnId"] == second["conversation"]["turns"][-2]["turnId"]

    for slot, key in (
        ("category", None),
        ("characteristic", "connectivity"),
        ("characteristic", "noise-cancellation"),
    ):
        assert active_by_slot(second_preferences, slot, key)["preferenceId"] == active_by_slot(
            first_preferences, slot, key
        )["preferenceId"]

    second_ids = {presentation["product"]["id"] for presentation in second["presentations"]}
    assert second_ids == {"headphones-002"}
    assert "headphones-004" not in second_ids
    assert all(
        presentation["product"]["price"]["amountMinor"] <= 12000
        for presentation in second["presentations"]
    )
