from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse

from app.api.v1.assistant.interactions import get_catalog_repository
from app.api.v1.catalog.schemas import ProductListResponse, ProductResponse
from app.core.validation import SLUG_PATTERN, Product
from app.features.assistant.domain import ErrorResponse
from app.features.catalog.repository import CatalogRepository

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get(
    "/products",
    response_model=ProductListResponse,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def list_products(
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
    categoryId: Annotated[str | None, Query(pattern=SLUG_PATTERN)] = None,
    minPriceMinor: Annotated[int | None, Query(ge=0)] = None,
    maxPriceMinor: Annotated[int | None, Query(ge=0)] = None,
    currency: Annotated[str, Query(pattern=r"^[A-Z]{3}$")] = "USD",
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ProductListResponse | JSONResponse:
    metadata = repository.get_metadata()
    if metadata is None:
        return _error_response(
            503, "catalog_unavailable", "Product information is temporarily unavailable.", True
        )
    filtered = [
        product
        for product in repository.list_products()
        if _matches_filters(product, categoryId, minPriceMinor, maxPriceMinor, currency)
    ]
    offset = (page - 1) * pageSize
    return ProductListResponse(
        catalogVersion=metadata.catalogVersion,
        items=filtered[offset : offset + pageSize],
        page=page,
        pageSize=pageSize,
        total=len(filtered),
    )


@router.get(
    "/products/{productId}",
    response_model=ProductResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_product(
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
    productId: Annotated[str, Path(pattern=SLUG_PATTERN)],
) -> ProductResponse | JSONResponse:
    metadata = repository.get_metadata()
    if metadata is None:
        return _error_response(
            503, "catalog_unavailable", "Product information is temporarily unavailable.", True
        )
    product = repository.get_product(productId)
    if product is None:
        return _error_response(404, "not_found", "The requested product was not found.", False)
    return ProductResponse(catalogVersion=metadata.catalogVersion, product=product)


def _matches_filters(
    product: Product,
    category_id: str | None,
    minimum: int | None,
    maximum: int | None,
    currency: str,
) -> bool:
    if category_id is not None and product.categoryId != category_id:
        return False
    if product.price is None:
        return minimum is None and maximum is None
    return (
        product.price.currency == currency
        and (minimum is None or product.price.amountMinor >= minimum)
        and (maximum is None or product.price.amountMinor <= maximum)
    )


def _error_response(status: int, code: str, message: str, retryable: bool) -> JSONResponse:
    error = ErrorResponse(
        error={"code": code, "message": message, "retryable": retryable},
        interactionId=None,
    )
    return JSONResponse(status_code=status, content=error.model_dump(mode="json"))
