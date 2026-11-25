from collections.abc import Callable, Iterator
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.features.assistant.domain import (
    AssistantInteractionRequest,
    AssistantInteractionResponse,
    ErrorResponse,
)
from app.features.assistant.interaction_service import InteractionService
from app.features.catalog.postgres_repository import PostgresCatalogRepository
from app.features.catalog.repository import CatalogRepository
from app.lib.ai.fake_provider import FakeLanguageModelProvider
from app.lib.ai.provider import LanguageModelProvider
from app.lib.telemetry.events import AssistantInteractionEvent
from app.lib.telemetry.logger import log_assistant_interaction

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


def get_catalog_repository() -> Iterator[CatalogRepository]:
    with psycopg.connect(get_settings().database_url) as connection:
        yield PostgresCatalogRepository(connection)


def get_language_model_provider() -> LanguageModelProvider:
    if get_settings().ai_provider != "fake":
        raise RuntimeError("Only the deterministic fake provider is available in this story")
    return FakeLanguageModelProvider()


def get_interaction_logger() -> Callable[[AssistantInteractionEvent], None]:
    return log_assistant_interaction


def get_interaction_service(
    repository: Annotated[CatalogRepository, Depends(get_catalog_repository)],
    provider: Annotated[LanguageModelProvider, Depends(get_language_model_provider)],
    emit_event: Annotated[
        Callable[[AssistantInteractionEvent], None], Depends(get_interaction_logger)
    ],
) -> InteractionService:
    return InteractionService(
        repository=repository,
        provider=provider,
        emit_event=emit_event,
    )


@router.post(
    "/interactions",
    response_model=AssistantInteractionResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def create_assistant_interaction(
    request: AssistantInteractionRequest,
    service: Annotated[InteractionService, Depends(get_interaction_service)],
) -> AssistantInteractionResponse:
    return service.handle(request)
