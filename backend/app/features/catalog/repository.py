from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.core.validation import CatalogProvenance, Category, Product


@dataclass(frozen=True)
class CatalogMetadata:
    catalogVersion: str
    provenance: CatalogProvenance
    seededAt: datetime


class CatalogRepository(Protocol):
    """Narrow read port; PostgreSQL remains behind this boundary."""

    def get_metadata(self) -> CatalogMetadata | None: ...

    def list_categories(self) -> list[Category]: ...

    def list_products(self) -> list[Product]: ...

    def get_product(self, product_id: str) -> Product | None: ...
