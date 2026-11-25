import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.validation import validate_catalog

CATALOG_PATH = Path(__file__).resolve().parents[3] / "data/catalog/catalog.json"


@pytest.fixture
def catalog_input() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_accepts_retained_catalog_and_preserves_unavailable_fields(catalog_input: dict) -> None:
    catalog = validate_catalog(catalog_input)

    assert catalog.catalogVersion == "1.0.0"
    assert len(catalog.products) == 120
    assert len(catalog.categories) == 5
    assert any(product.price is None for product in catalog.products)
    assert any(
        value is None for product in catalog.products for value in product.attributes.values()
    )


def test_rejects_duplicate_product_id(catalog_input: dict) -> None:
    invalid = copy.deepcopy(catalog_input)
    invalid["products"][1]["id"] = invalid["products"][0]["id"]

    with pytest.raises(ValidationError, match="Duplicate product id"):
        validate_catalog(invalid)


def test_rejects_missing_provenance(catalog_input: dict) -> None:
    invalid = copy.deepcopy(catalog_input)
    del invalid["provenance"]

    with pytest.raises(ValidationError, match="provenance"):
        validate_catalog(invalid)


def test_rejects_attribute_value_with_wrong_runtime_type(catalog_input: dict) -> None:
    invalid = copy.deepcopy(catalog_input)
    product = next(
        product for product in invalid["products"] if "battery-life" in product["attributes"]
    )
    product["attributes"]["battery-life"] = "not-a-number"

    with pytest.raises(ValidationError, match="Attribute battery-life must be number or null"):
        validate_catalog(invalid)
