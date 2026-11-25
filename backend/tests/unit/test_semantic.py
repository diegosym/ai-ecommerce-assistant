import pytest

from app.core.validation import Product
from app.lib.retrieval.semantic import EmbeddingCompatibilityError, validate_embedding_rows
from scripts.generate_embeddings import product_content_digest


def product() -> Product:
    return Product(
        id="headphones-001",
        name="Catalog headphone",
        categoryId="headphones",
        description="Synthetic catalog product",
        price={"amountMinor": 7900, "currency": "USD"},
        attributes={"connectivity": "Bluetooth 5.3"},
    )


def test_embedding_validation_rejects_content_digest_mismatch() -> None:
    item = product()
    rows = [
        {
            "productId": item.id,
            "catalogVersion": "1.0.0",
            "contentDigest": "0" * 64,
            "dimensions": 1536,
            "distance": 0.1,
        }
    ]

    with pytest.raises(EmbeddingCompatibilityError, match="content digest"):
        validate_embedding_rows(rows, [item], "1.0.0")


def test_embedding_validation_rejects_missing_product_vectors() -> None:
    with pytest.raises(EmbeddingCompatibilityError, match="Missing embeddings"):
        validate_embedding_rows([], [product()], "1.0.0")


def test_embedding_validation_accepts_current_catalog_artifact() -> None:
    item = product()
    rows = [
        {
            "productId": item.id,
            "catalogVersion": "1.0.0",
            "contentDigest": product_content_digest(item),
            "dimensions": 1536,
            "distance": 0.1,
        }
    ]

    assert validate_embedding_rows(rows, [item], "1.0.0") == {item.id: 0.1}
