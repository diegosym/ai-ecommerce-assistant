import sys

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from scripts.validate_catalog import validate_catalog_file


def seed_catalog() -> None:
    catalog = validate_catalog_file()
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            connection.execute("DELETE FROM product_embeddings")
            connection.execute("DELETE FROM products")
            connection.execute("DELETE FROM categories")
            connection.execute("DELETE FROM catalog_metadata")
            connection.execute(
                """
                INSERT INTO catalog_metadata (catalog_version, provenance)
                VALUES (%s, %s)
                """,
                (catalog.catalogVersion, Jsonb(catalog.provenance.model_dump(mode="json"))),
            )

            for category in catalog.categories:
                connection.execute(
                    """
                    INSERT INTO categories (id, name, description, attribute_definitions)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        category.id,
                        category.name,
                        category.description,
                        Jsonb(
                            [
                                definition.model_dump(mode="json")
                                for definition in category.attributeDefinitions
                            ]
                        ),
                    ),
                )

            for product in catalog.products:
                connection.execute(
                    """
                    INSERT INTO products
                        (id, name, category_id, description,
                         price_minor, price_currency, attributes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        product.id,
                        product.name,
                        product.categoryId,
                        product.description,
                        product.price.amountMinor if product.price else None,
                        product.price.currency if product.price else None,
                        Jsonb(product.attributes),
                    ),
                )

    print("Catalog seed completed.")
    print(f"Catalog version: {catalog.catalogVersion}")
    print(f"Product count: {len(catalog.products)}")
    print(f"Category count: {len(catalog.categories)}")
    print(f"Provenance review status: {catalog.provenance.reviewStatus}")


if __name__ == "__main__":
    try:
        seed_catalog()
    except Exception as error:
        print(f"Catalog seed failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
