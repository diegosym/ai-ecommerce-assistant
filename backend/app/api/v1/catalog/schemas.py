from pydantic import Field

from app.core.validation import Category, Product, SemanticVersion, StrictSchema


class CategoryListResponse(StrictSchema):
    catalogVersion: SemanticVersion
    items: list[Category]


class ProductListResponse(StrictSchema):
    catalogVersion: SemanticVersion
    items: list[Product]
    page: int = Field(ge=1)
    pageSize: int = Field(ge=1, le=50)
    total: int = Field(ge=0)


class ProductResponse(StrictSchema):
    catalogVersion: SemanticVersion
    product: Product
