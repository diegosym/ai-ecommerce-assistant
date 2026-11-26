import hashlib
import json
import sys
from typing import Any

import psycopg
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.validation import Product
from scripts.validate_catalog import validate_catalog_file

DIMENSIONS = 1536
FAKE_MODEL_ID = "fake-embedding-1536-v1"
OPENAI_KEY_ERROR = "OPENAI_API_KEY is required when AI_PROVIDER=openai"


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


def resolve_settings(settings: Settings | None) -> Settings:
    """Resolve process settings; report configuration problems without pydantic dumps."""
    if settings is not None:
        return settings
    try:
        return get_settings()
    except ValidationError as error:
        details = "; ".join(configuration_error_details(error))
        raise ValueError(f"Invalid embedding configuration: {details}") from None


def configuration_error_details(error: ValidationError) -> list[str]:
    """Keep the original validator message; drop pydantic's wrapper and input dump."""
    details = []
    for item in error.errors():
        original = item.get("ctx", {}).get("error")
        details.append(str(original) if isinstance(original, Exception) else str(item["msg"]))
    return details


def build_openai_client(settings: Settings) -> Any:
    if not settings.openai_api_key:
        raise ValueError(OPENAI_KEY_ERROR)
    try:
        import openai
    except ImportError as error:
        raise RuntimeError(
            "The optional openai package is required for hosted embedding generation"
        ) from error
    return openai.OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.provider_timeout_seconds,
    )


def openai_embedding(client: Any, model_id: str, content_text: str) -> list[float]:
    """One hosted vector per product, validated against the stored schema width."""
    response = client.embeddings.create(model=model_id, input=content_text)
    rows = response.data
    if not rows:
        raise ValueError(f"Embeddings API returned no vector for model {model_id}.")
    values = [float(value) for value in rows[0].embedding]
    if len(values) != DIMENSIONS:
        raise ValueError(
            f"Embeddings API returned {len(values)} dimensions for model {model_id}; "
            f"product_embeddings requires vector({DIMENSIONS})."
        )
    return values


def generate_embeddings(
    settings: Settings | None = None,
    openai_client: Any | None = None,
) -> None:
    settings = resolve_settings(settings)
    hosted = settings.ai_provider == "openai"
    provider = "openai" if hosted else "fake"
    model_id = FAKE_MODEL_ID
    dimensions = DIMENSIONS
    if hosted:
        if not settings.openai_api_key:
            raise ValueError(OPENAI_KEY_ERROR)
        if openai_client is None:
            openai_client = build_openai_client(settings)
        model_id = settings.openai_embedding_model

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
                if hosted:
                    values = openai_embedding(
                        openai_client, model_id, normalized_product_text(product)
                    )
                    embedding = json.dumps(values)
                    dimensions = len(values)
                else:
                    embedding = fake_embedding(content_digest)
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
                        embedding,
                        catalog.catalogVersion,
                        provider,
                        model_id,
                        content_digest,
                        dimensions,
                    ),
                )

    print(f"Embedding generation completed for {len(catalog.products)} products.")
    print(f"Catalog version: {catalog.catalogVersion}")
    print(f"Provider: {provider}; model: {model_id}; dimensions: {dimensions}")


if __name__ == "__main__":
    try:
        generate_embeddings()
    except Exception as error:
        print(f"Embedding generation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
