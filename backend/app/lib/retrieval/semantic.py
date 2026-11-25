import hashlib
import math
from collections.abc import Sequence
from typing import Any

from app.core.validation import Product
from app.features.assistant.domain import RankedCandidate, RetrievalQuery
from app.features.catalog.repository import CatalogRepository
from app.lib.retrieval.lexical import eligible_products, matched_attributes
from scripts.generate_embeddings import DIMENSIONS, fake_embedding, product_content_digest


class EmbeddingCompatibilityError(ValueError):
    """Raised when derived vectors do not match the current catalog artifact."""


def validate_embedding_rows(
    rows: Sequence[dict[str, Any]],
    products: list[Product],
    catalog_version: str,
) -> dict[str, float]:
    products_by_id = {product.id: product for product in products}
    product_ids = [row["productId"] for row in rows]
    if len(product_ids) != len(set(product_ids)):
        raise EmbeddingCompatibilityError("Duplicate product embeddings")
    missing = set(products_by_id) - set(product_ids)
    if missing:
        raise EmbeddingCompatibilityError(f"Missing embeddings for {sorted(missing)}")

    distances: dict[str, float] = {}
    for row in rows:
        product_id = row["productId"]
        product = products_by_id.get(product_id)
        if product is None:
            raise EmbeddingCompatibilityError(f"Embedding references unknown product {product_id}")
        if row["catalogVersion"] != catalog_version:
            raise EmbeddingCompatibilityError("Embedding catalog version mismatch")
        if row["contentDigest"] != product_content_digest(product):
            raise EmbeddingCompatibilityError(f"Embedding content digest mismatch for {product_id}")
        if row["dimensions"] != DIMENSIONS:
            raise EmbeddingCompatibilityError(f"Embedding dimensions mismatch for {product_id}")
        distance = float(row["distance"])
        if not math.isfinite(distance):
            raise EmbeddingCompatibilityError(f"Invalid embedding distance for {product_id}")
        distances[product_id] = distance
    return distances


def rank_semantic_candidates(
    repository: CatalogRepository,
    products: list[Product],
    query: RetrievalQuery,
) -> list[RankedCandidate]:
    metadata = repository.get_metadata()
    connection = getattr(repository, "connection", None)
    if metadata is None or connection is None:
        raise EmbeddingCompatibilityError("PostgreSQL catalog metadata and connection are required")

    query_digest = hashlib.sha256(query.text.encode()).hexdigest()
    query_vector = fake_embedding(query_digest)
    rows = connection.execute(
        """
        SELECT product_id, catalog_version, content_digest, dimensions,
               embedding <=> %s::vector AS distance
        FROM product_embeddings
        """,
        (query_vector,),
    ).fetchall()
    distances = validate_embedding_rows(
        [
            {
                "productId": row[0],
                "catalogVersion": row[1],
                "contentDigest": row[2],
                "dimensions": row[3],
                "distance": row[4],
            }
            for row in rows
        ],
        products,
        metadata.catalogVersion,
    )
    eligible = eligible_products(products, query.requirements)
    ranked = sorted(eligible, key=lambda product: (distances[product.id], product.id))
    return [
        RankedCandidate(
            productId=product.id,
            semanticRank=index,
            hybridRank=index,
            matchedAttributes=matched_attributes(product, query.requirements),
        )
        for index, product in enumerate(ranked[: query.limit], start=1)
    ]
