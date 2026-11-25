from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.assistant.interactions import router as assistant_router
from app.api.v1.catalog.categories import router as catalog_categories_router
from app.api.v1.catalog.products import router as catalog_products_router
from app.features.assistant.domain import ErrorResponse
from app.lib.ai.provider import ProviderUnavailableError
from app.lib.telemetry.events import (
    AssistantInteractionEventInput,
    create_assistant_interaction_event,
)
from app.lib.telemetry.logger import log_assistant_interaction


def create_app() -> FastAPI:
    """Create the stateless API application and register bounded public contracts."""
    app = FastAPI(title="Conversational Shopping Assistant API", version="0.1.0")
    app.include_router(assistant_router)
    app.include_router(catalog_categories_router)
    app.include_router(catalog_products_router)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, _error: RequestValidationError) -> JSONResponse:
        if request.url.path == "/api/v1/assistant/interactions":
            conversation_id = uuid4()
            try:
                body = await request.json()
                candidate = body.get("conversation", {}).get("conversationId")
                if candidate:
                    conversation_id = UUID(candidate)
            except (ValueError, TypeError, AttributeError):
                pass
            received_at = datetime.now(UTC)
            event = create_assistant_interaction_event(
                AssistantInteractionEventInput(
                    eventType="assistant_interaction",
                    interactionId=uuid4(),
                    conversationId=conversation_id,
                    receivedAt=received_at,
                    completedAt=datetime.now(UTC),
                    catalogVersion=None,
                    outcome="error",
                    errorCode="invalid_request",
                )
            )
            log_assistant_interaction(event)
        error = ErrorResponse(
            error={
                "code": "invalid_request",
                "message": "The request or conversation state is invalid or oversized.",
                "retryable": False,
            },
            interactionId=None,
        )
        return JSONResponse(status_code=400, content=error.model_dump(mode="json"))

    @app.exception_handler(ProviderUnavailableError)
    async def provider_unavailable(
        _request: Request, error: ProviderUnavailableError
    ) -> JSONResponse:
        response = ErrorResponse(
            error={
                "code": "provider_unavailable",
                "message": "The language model provider is temporarily unavailable.",
                "retryable": True,
            },
            interactionId=error.interaction_id,
        )
        return JSONResponse(status_code=503, content=response.model_dump(mode="json"))

    return app


app = create_app()
