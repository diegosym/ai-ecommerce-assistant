from fastapi.testclient import TestClient

from app.features.catalog.postgres_repository import PostgresCatalogRepository
from tests.integration.test_qa import discovered_conversation, interact


def test_customer_price_belief_does_not_override_verified_catalog_price(
    client: TestClient,
    catalog_repository: PostgresCatalogRepository,
) -> None:
    conversation = discovered_conversation(client)
    product_id = conversation["presentedProducts"][0]["productId"]
    verified = catalog_repository.get_product(product_id)
    assert verified is not None and verified.price is not None

    answer = interact(
        client,
        "I thought the first one was $99. What is its actual price?",
        conversation,
    )

    assert answer["reply"]["kind"] == "answer"
    assert "$99.00" in answer["reply"]["text"]
    assert "verified catalog price" in answer["reply"]["text"].lower()
    assert "$94.00" in answer["reply"]["text"]
    presentation = answer["presentations"][0]
    assert presentation["product"] == verified.model_dump(mode="json")
    assert "price" in presentation["grounding"][0]["fields"]
    belief = next(
        preference
        for preference in answer["conversation"]["preferences"]
        if preference["sourceTurnId"] == answer["conversation"]["turns"][-2]["turnId"]
    )
    assert belief["nature"] == "belief"
    assert belief["value"]["amountMinor"] == 9900
