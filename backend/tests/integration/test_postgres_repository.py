import psycopg

from app.core.config import get_settings
from app.features.catalog.postgres_repository import PostgresCatalogRepository


def test_reads_seeded_catalog_through_repository_port() -> None:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        repository = PostgresCatalogRepository(connection)

        metadata = repository.get_metadata()
        categories = repository.list_categories()
        products = repository.list_products()

        assert metadata is not None
        assert metadata.catalogVersion == "1.0.0"
        assert metadata.provenance.sourceType == "synthetic"
        assert len(categories) == 5
        assert len(products) == 120
        assert repository.get_product(products[0].id) == products[0]
        assert repository.get_product("not-in-catalog") is None
