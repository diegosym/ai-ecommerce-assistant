from fastapi.testclient import TestClient

from app.features.catalog.postgres_repository import PostgresCatalogRepository


def test_category_and_price_filters_return_only_matching_catalog_products(
    client: TestClient,
    catalog_repository: PostgresCatalogRepository,
) -> None:
    response = client.get(
        "/api/v1/catalog/products",
        params={
            "categoryId": "headphones",
            "minPriceMinor": 10000,
            "maxPriceMinor": 15000,
            "currency": "USD",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    assert [product["id"] for product in body["items"]] == [
        "headphones-003",
        "headphones-004",
        "headphones-005",
    ]
    for product in body["items"]:
        assert product["categoryId"] == "headphones"
        assert 10000 <= product["price"]["amountMinor"] <= 15000
        assert product["price"]["currency"] == "USD"
        assert product == catalog_repository.get_product(product["id"]).model_dump(mode="json")


def test_impossible_price_range_returns_empty_success(client: TestClient) -> None:
    response = client.get(
        "/api/v1/catalog/products",
        params={"minPriceMinor": 20000, "maxPriceMinor": 10000},
    )

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_price_filter_excludes_unavailable_prices(client: TestClient) -> None:
    response = client.get(
        "/api/v1/catalog/products",
        params={"categoryId": "headphones", "minPriceMinor": 0, "pageSize": 50},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 23
    assert all(product["price"] is not None for product in body["items"])
    assert "headphones-013" not in {product["id"] for product in body["items"]}


def test_pagination_is_deterministic_over_filtered_results(client: TestClient) -> None:
    params = {"categoryId": "headphones", "minPriceMinor": 10000, "maxPriceMinor": 15000}
    first = client.get("/api/v1/catalog/products", params={**params, "page": 1, "pageSize": 2})
    second = client.get("/api/v1/catalog/products", params={**params, "page": 2, "pageSize": 2})

    assert first.status_code == second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["total"] == second_body["total"] == 3
    assert [product["id"] for product in first_body["items"]] == [
        "headphones-003",
        "headphones-004",
    ]
    assert [product["id"] for product in second_body["items"]] == ["headphones-005"]
    assert second_body["page"] == 2
