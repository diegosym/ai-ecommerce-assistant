import pytest
from pydantic import ValidationError

from app.core.config import Settings
from scripts.generate_embeddings import (
    FAKE_MODEL_ID,
    fake_embedding,
    generate_embeddings,
    product_content_digest,
)
from scripts.validate_catalog import validate_catalog_file


class FakeResult:
    def __init__(self, row=None) -> None:
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self) -> None:
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def transaction(self):
        return self

    def execute(self, sql, parameters=None):
        self.calls.append((sql, parameters))
        if "SELECT catalog_version FROM catalog_metadata" in sql:
            return FakeResult(("1.0.0",))
        return FakeResult()


def test_fake_path_stays_deterministic_and_network_free(monkeypatch) -> None:
    connection = FakeConnection()
    monkeypatch.setattr("scripts.generate_embeddings.psycopg.connect", lambda _url: connection)
    settings = Settings(_env_file=None, AI_PROVIDER="fake")

    generate_embeddings(settings=settings, openai_client=None)

    catalog = validate_catalog_file()
    upserts = [call for call in connection.calls if "ON CONFLICT" in call[0]]
    assert len(upserts) == len(catalog.products) == 120
    parameters = upserts[0][1]
    digest = product_content_digest(catalog.products[0])
    assert parameters[1] == fake_embedding(digest)
    assert parameters[2:] == (catalog.catalogVersion, "fake", FAKE_MODEL_ID, digest, 1536)


def test_hosted_path_fails_closed_without_api_key() -> None:
    settings = Settings(_env_file=None, AI_PROVIDER="openai", OPENAI_API_KEY="test-only")
    settings = settings.model_copy(update={"openai_api_key": None})

    with pytest.raises(ValueError, match="OPENAI_API_KEY is required when AI_PROVIDER=openai"):
        generate_embeddings(settings=settings, openai_client=None)


def test_settings_errors_surface_as_clean_configuration_message(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError) as captured:
        Settings(_env_file=None, AI_PROVIDER="openai")
    configuration_error = captured.value

    def raise_configuration_error() -> Settings:
        raise configuration_error

    monkeypatch.setattr("scripts.generate_embeddings.get_settings", raise_configuration_error)

    with pytest.raises(
        ValueError, match="Invalid embedding configuration: OPENAI_API_KEY is required"
    ):
        generate_embeddings()
