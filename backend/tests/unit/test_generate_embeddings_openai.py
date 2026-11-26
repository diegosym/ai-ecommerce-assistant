from types import SimpleNamespace

from app.core.config import Settings
from scripts.generate_embeddings import (
    generate_embeddings,
    normalized_product_text,
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


class MockEmbeddings:
    def __init__(self) -> None:
        self.calls = []

    def create(self, *, model, input):
        self.calls.append({"model": model, "input": input})
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.001] * 1536)]
        )


class MockOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = MockEmbeddings()


def test_openai_generation_uses_normalized_text_and_upserts_real_metadata(
    monkeypatch,
) -> None:
    connection = FakeConnection()
    client = MockOpenAIClient()
    settings = Settings(
        _env_file=None,
        AI_PROVIDER="openai",
        OPENAI_API_KEY="test-only",
        OPENAI_EMBEDDING_MODEL="text-embedding-3-small",
    )
    monkeypatch.setattr(
        "scripts.generate_embeddings.psycopg.connect", lambda _url: connection
    )

    generate_embeddings(settings=settings, openai_client=client)

    catalog = validate_catalog_file()
    assert len(client.embeddings.calls) == len(catalog.products) == 120
    assert client.embeddings.calls[0] == {
        "model": "text-embedding-3-small",
        "input": normalized_product_text(catalog.products[0]),
    }
    upserts = [call for call in connection.calls if "ON CONFLICT" in call[0]]
    assert len(upserts) == 120
    parameters = upserts[0][1]
    assert parameters[0] == catalog.products[0].id
    assert parameters[2:] == (
        "1.0.0",
        "openai",
        "text-embedding-3-small",
        product_content_digest(catalog.products[0]),
        1536,
    )
