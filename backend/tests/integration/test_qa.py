import pytest
from fastapi.testclient import TestClient

from app.features.catalog.postgres_repository import PostgresCatalogRepository


def interact(client: TestClient, message: str, conversation: dict | None = None) -> dict:
    if conversation is None:
        from uuid import uuid4

        conversation = {
            "conversationId": str(uuid4()),
            "createdAt": "2026-11-25T12:00:00Z",
            "turns": [],
            "preferences": [],
            "presentedProducts": [],
        }
    response = client.post(
        "/api/v1/assistant/interactions",
        json={"conversation": conversation, "message": message},
    )
    assert response.status_code == 200, response.text
    return response.json()


def discovered_conversation(client: TestClient) -> dict:
    return interact(client, "Wireless headphones with noise cancellation under $150")[
        "conversation"
    ]


def test_presented_product_answers_use_catalog_attributes_and_grounding(
    client: TestClient,
    catalog_repository: PostgresCatalogRepository,
) -> None:
    conversation = discovered_conversation(client)
    first_product_id = conversation["presentedProducts"][0]["productId"]

    answer = interact(client, "Does the first one have noise cancellation?", conversation)

    assert answer["reply"]["kind"] == "answer"
    assert "Auralis Air 02" in answer["reply"]["text"]
    assert "noise cancellation" in answer["reply"]["text"].lower()
    presentation = answer["presentations"][0]
    assert presentation["product"]["id"] == first_product_id
    assert presentation["product"] == catalog_repository.get_product(
        first_product_id
    ).model_dump(mode="json")
    assert presentation["grounding"][0]["productId"] == first_product_id
    assert "attributes.noise-cancellation" in presentation["grounding"][0]["fields"]
    assert presentation["matchedAttributes"] == ["noise-cancellation"]


def test_battery_answer_uses_the_catalog_number(
    client: TestClient,
) -> None:
    conversation = discovered_conversation(client)

    answer = interact(client, "What is the battery life of the first product?", conversation)

    assert answer["reply"]["kind"] == "answer"
    assert "12 hours" in answer["reply"]["text"]
    assert answer["presentations"][0]["product"]["attributes"]["battery-life"] == 12
    assert "attributes.battery-life" in answer["presentations"][0]["grounding"][0]["fields"]


def test_missing_attribute_is_explicitly_unavailable_without_fabrication(
    client: TestClient,
) -> None:
    conversation = discovered_conversation(client)

    answer = interact(client, "Is there a warranty on the first product?", conversation)

    assert answer["reply"]["kind"] == "unavailable"
    assert "not available" in answer["reply"]["text"].lower()
    assert answer["presentations"][0]["unavailableFields"] == ["warranty"]
    assert "warranty" not in answer["presentations"][0]["product"]["attributes"]


def test_nonexistent_product_cannot_be_answered(client: TestClient) -> None:
    answer = interact(client, "Does product not-in-catalog have noise cancellation?")

    assert answer["reply"]["kind"] == "unavailable"
    assert "can’t verify" in answer["reply"]["text"]
    assert answer["presentations"] == []


def test_existing_product_can_be_answered_even_if_not_previously_presented(
    client: TestClient,
) -> None:
    answer = interact(client, "Does headphones-004 have noise cancellation?")

    assert answer["reply"]["kind"] == "answer"
    assert answer["presentations"][0]["product"]["id"] == "headphones-004"
    assert answer["presentations"][0]["product"]["attributes"]["noise-cancellation"] is True
    assert answer["presentations"][0]["reference"]["ordinal"] == 1


@pytest.mark.parametrize(
    "message",
    [
        "What is the status of my order?",
        "Can I pay for the first product now?",
        "What is your store warranty policy?",
    ],
)
def test_out_of_scope_questions_get_transparent_decline(
    client: TestClient,
    message: str,
) -> None:
    answer = interact(client, message)

    assert answer["reply"]["kind"] == "out_of_scope"
    assert "can’t help" in answer["reply"]["text"]
    assert answer["presentations"] == []
