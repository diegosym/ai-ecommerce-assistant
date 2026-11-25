import hashlib
import json
import sys

import psycopg

from app.core.config import get_settings
from app.core.validation import Product
from scripts.validate_catalog import validate_catalog_file

DIMENSIONS = 1536
FAKE_MODEL_ID = "fake-embedding-1536-v1"


def normalized_product_text(product: Product) -> str:
    attributes = json.dumps(product.attributes, sort_keys=True, separators=(",", ":"))
    return f"{product.name}\n{product.description}\n{attributes}"


def product_content_digest(product: Product) -> str:
    return hashlib.sha256(normalized_product_text(product).encode()).hexdigest()


def fake_embedding(content_digest: str) -> str:
    values: list[float] = []
    block = 0
    while len(values) < DIMENSIONS:
        digest = hashlib.sha256(f"{content_digest}:{block}".encode()).digest()
        for offset in range(0, len(digest), 4):
            if len(values) == DIMENSIONS:
                break
            integer = int.from_bytes(digest[offset : offset + 4], signed=True)
            values.append(integer / 2_147_483_648)
        block += 1

    magnitude = sum(value * value for value in values) ** 0.5
    return f"[{','.join(f'{value / magnitude:.8f}' for value in values)}]"


def generate_embeddings() -> None:
    settings = get_settings()
    if settings.ai_provider != "fake":
        raise ValueError(
            "This foundational command supports only AI_PROVIDER=fake; "
            "no hosted network calls are made."
        )

    catalog = validate_catalog_file()
    with psycopg.connect(settings.database_url) as connection:
        row = connection.execute(
            "SELECT catalog_version FROM catalog_metadata "
            "ORDER BY seeded_at DESC, catalog_version DESC LIMIT 1"
        ).fetchone()
        if row is None or row[0] != catalog.catalogVersion:
            raise ValueError("Catalog version mismatch: run seed_catalog before generating embeddings.")

        with connection.transaction():
            for product in catalog.products:
                content_digest = product_content_digest(product)
                connection.execute(
                    """
                    INSERT INTO product_embeddings
                        (product_id, embedding, catalog_version, provider,
                         model_id, content_digest, dimensions)
                    VALUES (%s, %s::vector, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        catalog_version = EXCLUDED.catalog_version,
                        provider = EXCLUDED.provider,
                        model_id = EXCLUDED.model_id,
                        content_digest = EXCLUDED.content_digest,
                        dimensions = EXCLUDED.dimensions,
                        indexed_at = now()
                    """,
                    (
                        product.id,
                        fake_embedding(content_digest),
                        catalog.catalogVersion,
                        "fake",
                        FAKE_MODEL_ID,
                        content_digest,
                        DIMENSIONS,
                    ),
                )

    print(f"Embedding generation completed for {len(catalog.products)} products.")
    print(f"Catalog version: {catalog.catalogVersion}")
    print(f"Provider: fake; model: {FAKE_MODEL_ID}; dimensions: {DIMENSIONS}")


if __name__ == "__main__":
    try:
        generate_embeddings()
    except Exception as error:
        print(f"Embedding generation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
