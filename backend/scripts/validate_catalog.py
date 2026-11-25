import json
import sys
from pathlib import Path

from app.core.validation import CatalogDocument, validate_catalog

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPOSITORY_ROOT / "data/catalog/catalog.json"


def validate_catalog_file(path: Path = CATALOG_PATH) -> CatalogDocument:
    input_value: object = json.loads(path.read_text(encoding="utf-8"))
    return validate_catalog(input_value)


def main() -> None:
    catalog = validate_catalog_file()
    print("Catalog validation passed.")
    print(f"Catalog version: {catalog.catalogVersion}")
    print(f"Product count: {len(catalog.products)}")
    print(f"Category count: {len(catalog.categories)}")
    print(f"Provenance source: {catalog.provenance.sourceType}")
    print(f"Provenance review status: {catalog.provenance.reviewStatus}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Catalog validation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
