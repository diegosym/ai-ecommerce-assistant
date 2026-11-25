from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.v1.assistant.interactions import get_catalog_repository
from app.api.v1.catalog.schemas import CategoryListResponse
from app.features.assistant.domain import ErrorResponse
from app.features.catalog.repository import CatalogRepository

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get(
    "/categories",
    response_model=CategoryListResponse,
    responses={503: {"model": ErrorResponse}},
)
def list_categories(
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
) -> CategoryListResponse | JSONResponse:
    metadata = repository.get_metadata()
    if metadata is None:
        error = ErrorResponse(
            error={
                "code": "catalog_unavailable",
                "message": "Product information is temporarily unavailable.",
                "retryable": True,
            },
            interactionId=None,
        )
        return JSONResponse(status_code=503, content=error.model_dump(mode="json"))
    return CategoryListResponse(
        catalogVersion=metadata.catalogVersion,
        items=repository.list_categories(),
    )
