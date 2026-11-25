import pytest
from pydantic import ValidationError

from app.core.config import Settings

ENVIRONMENT_KEYS = (
    "AI_PROVIDER",
    "AI_RETRIEVAL",
    "DATABASE_URL",
    "LOG_RAW_CONTENT",
    "OPENAI_API_KEY",
    "OPENAI_CHAT_MODEL",
    "OPENAI_EMBEDDING_MODEL",
    "MODEL_PRICING_VERSION",
)


def test_defaults_are_local_and_do_not_log_raw_content(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)

    assert settings.ai_provider == "fake"
    assert settings.ai_retrieval == "lexical"
    assert settings.database_url == "postgresql://assistant:assistant@localhost:55434/assistant_dev"
    assert settings.log_raw_content is False


def test_openai_provider_requires_server_side_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError, match="OPENAI_API_KEY is required"):
        Settings(_env_file=None, AI_PROVIDER="openai")
