from collections.abc import Sequence
from typing import Any

import psycopg

from app.core.config import get_settings
from app.core.validation import CatalogProvenance, Category, Product
from app.features.catalog.repository import CatalogMetadata, CatalogRepository


class PostgresCatalogRepository(CatalogRepository):
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    @classmethod
    def from_environment(cls) -> "PostgresCatalogRepository":
        return cls(psycopg.connect(get_settings().database_url))

    def get_metadata(self) -> CatalogMetadata | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT catalog_version, provenance, seeded_at
                FROM catalog_metadata
                ORDER BY seeded_at DESC, catalog_version DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return CatalogMetadata(
            catalogVersion=row[0],
            provenance=CatalogProvenance.model_validate(row[1]),
            seededAt=row[2],
        )

    def list_categories(self) -> list[Category]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, description, attribute_definitions
                FROM categories
                ORDER BY id
                """
            )
            rows = cursor.fetchall()
        return [
            Category.model_validate(
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "attributeDefinitions": row[3],
                }
            )
            for row in rows
        ]

    def list_products(self) -> list[Product]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, category_id, description,
                       price_minor, price_currency, attributes
                FROM products
                ORDER BY id
                """
            )
            rows = cursor.fetchall()
        return [_parse_product_row(row) for row in rows]

    def get_product(self, product_id: str) -> Product | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, category_id, description,
                       price_minor, price_currency, attributes
                FROM products
                WHERE id = %s
                """,
                (product_id,),
            )
            row = cursor.fetchone()
        return _parse_product_row(row) if row is not None else None


def _parse_product_row(row: Sequence[Any]) -> Product:
    return Product.model_validate(
        {
            "id": row[0],
            "name": row[1],
            "categoryId": row[2],
            "description": row[3],
            "price": (
                None
                if row[4] is None
                else {"amountMinor": row[4], "currency": row[5]}
            ),
            "attributes": row[6],
        }
    )
