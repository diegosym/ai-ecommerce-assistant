from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.api.v1.catalog.schemas import CategoryListResponse, ProductListResponse
from app.features.assistant.domain import ErrorResponse

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs/001-conversational-shopping-assistant/contracts/openapi.yaml"
)


def test_catalog_contract_has_only_deterministic_structured_product_filters(
    client: TestClient,
) -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    catalog_contract = contract.split("  /api/v1/catalog/categories:", 1)[1].split(
        "  /api/v1/assistant/interactions:", 1
    )[0]
    for forbidden in ("name: search", "name: query", "name: q", "name: text"):
        assert forbidden not in catalog_contract

    paths = client.app.openapi()["paths"]
    list_operation = paths["/api/v1/catalog/products"]["get"]
    parameter_names = {parameter["name"] for parameter in list_operation["parameters"]}
    assert parameter_names == {
        "categoryId",
        "minPriceMinor",
        "maxPriceMinor",
        "currency",
        "page",
        "pageSize",
    }
    assert paths["/api/v1/catalog/categories"]["get"]["responses"]["200"]
    assert paths["/api/v1/catalog/products/{productId}"]["get"]["responses"]["404"]


def test_category_and_product_list_responses_match_openapi_schemas(
    client: TestClient,
) -> None:
    categories = client.get("/api/v1/catalog/categories")
    products = client.get("/api/v1/catalog/products", params={"pageSize": 5})

    assert categories.status_code == 200, categories.text
    category_body = TypeAdapter(CategoryListResponse).validate_json(categories.text)
    assert len(category_body.items) == 5
    assert category_body.catalogVersion == "1.0.0"

    assert products.status_code == 200, products.text
    product_body = TypeAdapter(ProductListResponse).validate_json(products.text)
    assert len(product_body.items) == 5
    assert product_body.page == 1
    assert product_body.pageSize == 5
    assert product_body.total == 120


def test_empty_filter_result_is_successful_empty_list_not_an_error(client: TestClient) -> None:
    response = client.get(
        "/api/v1/catalog/products",
        params={"categoryId": "headphones", "minPriceMinor": 1, "maxPriceMinor": 0},
    )

    assert response.status_code == 200, response.text
    body = TypeAdapter(ProductListResponse).validate_json(response.text)
    assert body.items == []
    assert body.total == 0


def test_unknown_product_returns_typed_not_found_error(client: TestClient) -> None:
    response = client.get("/api/v1/catalog/products/not-in-catalog")

    assert response.status_code == 404, response.text
    error = TypeAdapter(ErrorResponse).validate_json(response.text)
    assert error.error.code == "not_found"
    assert error.error.retryable is False
    assert error.interactionId is None
