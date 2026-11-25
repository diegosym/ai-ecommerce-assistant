from collections.abc import Callable, Iterator
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api.v1.assistant.interactions import (
    get_catalog_repository,
    get_interaction_logger,
    get_interaction_service,
    get_language_model_provider,
)
from app.core.config import get_settings
from app.features.assistant.interaction_service import InteractionService
from app.features.catalog.postgres_repository import PostgresCatalogRepository
from app.features.catalog.repository import CatalogRepository
from app.lib.ai.fake_provider import FakeLanguageModelProvider
from app.lib.ai.provider import LanguageModelProvider
from app.lib.telemetry.events import AssistantInteractionEvent
from app.main import create_app


@pytest.fixture
def telemetry_events() -> list[AssistantInteractionEvent]:
    return []


@pytest.fixture
def catalog_repository() -> Iterator[PostgresCatalogRepository]:
    with psycopg.connect(get_settings().database_url) as connection:
        yield PostgresCatalogRepository(connection)


@pytest.fixture
def client_factory(
    telemetry_events: list[AssistantInteractionEvent],
) -> Callable[
    [CatalogRepository, LanguageModelProvider | None],
    TestClient,
]:
    def build(
        repository: CatalogRepository,
        provider: LanguageModelProvider | None = None,
    ) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_catalog_repository] = lambda: repository
        app.dependency_overrides[get_language_model_provider] = (
            lambda: provider or FakeLanguageModelProvider()
        )
        app.dependency_overrides[get_interaction_logger] = lambda: telemetry_events.append
        app.dependency_overrides[get_interaction_service] = lambda: InteractionService(
            repository=repository,
            provider=provider or FakeLanguageModelProvider(),
            emit_event=telemetry_events.append,
            provider_timeout_seconds=0.05,
        )
        return TestClient(app)

    return build


@pytest.fixture
def client(
    client_factory: Callable[
        [CatalogRepository, LanguageModelProvider | None],
        TestClient,
    ],
    catalog_repository: PostgresCatalogRepository,
) -> Iterator[TestClient]:
    with client_factory(catalog_repository) as test_client:
        yield test_client


@pytest.fixture
def make_request() -> Callable[[str], dict]:
    def build(message: str) -> dict:
        return {
            "conversation": {
                "conversationId": str(uuid4()),
                "createdAt": "2026-11-25T12:00:00Z",
                "turns": [],
                "preferences": [],
                "presentedProducts": [],
            },
            "message": message,
        }

    return build
