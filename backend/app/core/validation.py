import math
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    StringConstraints,
    model_validator,
)

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SEMANTIC_VERSION_PATTERN = (
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

Slug = Annotated[str, StringConstraints(pattern=SLUG_PATTERN)]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SemanticVersion = Annotated[str, StringConstraints(pattern=SEMANTIC_VERSION_PATTERN)]
Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
AttributeValue = StrictStr | StrictInt | StrictFloat | StrictBool | None


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Money(StrictSchema):
    amountMinor: int = Field(ge=0)
    currency: Currency


class AttributeDefinition(StrictSchema):
    key: Slug
    label: NonEmptyString
    valueType: Literal["string", "number", "boolean"]
    unit: NonEmptyString | None = None
    filterable: bool


class Category(StrictSchema):
    id: Slug
    name: NonEmptyString
    description: str
    attributeDefinitions: list[AttributeDefinition]

    @model_validator(mode="after")
    def reject_duplicate_attribute_definitions(self) -> Self:
        keys = [definition.key for definition in self.attributeDefinitions]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate attribute definition key")
        return self


class Product(StrictSchema):
    id: Slug
    name: NonEmptyString
    categoryId: Slug
    description: NonEmptyString
    price: Money | None
    attributes: dict[str, AttributeValue]


class CatalogProvenance(StrictSchema):
    sourceType: Literal["synthetic"]
    method: NonEmptyString
    reviewStatus: Literal["draft", "reviewed", "approved"]
    notes: NonEmptyString


class CatalogDocument(StrictSchema):
    catalogVersion: SemanticVersion
    generatedAt: datetime
    provenance: CatalogProvenance
    categories: list[Category] = Field(min_length=4, max_length=6)
    products: list[Product] = Field(min_length=100, max_length=200)

    @model_validator(mode="after")
    def validate_references_and_provenance_shape(self) -> Self:
        if self.generatedAt.utcoffset() is None:
            raise ValueError("generatedAt must include a timezone offset")

        definitions_by_category: dict[str, dict[str, AttributeDefinition]] = {}
        for category in self.categories:
            if category.id in definitions_by_category:
                raise ValueError(f"Duplicate category id: {category.id}")
            definitions_by_category[category.id] = {
                definition.key: definition for definition in category.attributeDefinitions
            }

        product_ids: set[str] = set()
        for product in self.products:
            if product.id in product_ids:
                raise ValueError(f"Duplicate product id: {product.id}")
            product_ids.add(product.id)

            definitions = definitions_by_category.get(product.categoryId)
            if definitions is None:
                raise ValueError(f"Unknown category id: {product.categoryId}")

            for key, value in product.attributes.items():
                definition = definitions.get(key)
                if definition is None:
                    raise ValueError(
                        f"Attribute {key} is not defined for category {product.categoryId}"
                    )
                if not _matches_attribute_type(value, definition.valueType):
                    raise ValueError(
                        f"Attribute {key} must be {definition.valueType} or null"
                    )
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError(f"Attribute {key} must be a finite number or null")
        return self


def _matches_attribute_type(value: AttributeValue, value_type: str) -> bool:
    if value is None:
        return True
    if value_type == "string":
        return type(value) is str
    if value_type == "boolean":
        return type(value) is bool
    return type(value) in (int, float)


def validate_catalog(input_value: object) -> CatalogDocument:
    """Validate untrusted JSON through the single catalog schema used by CLI and seed."""
    return CatalogDocument.model_validate(input_value)
