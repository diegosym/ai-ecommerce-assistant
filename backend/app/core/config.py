from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Process-local settings; secrets never belong in client-prefixed variables."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env.local",
        env_prefix="",
        case_sensitive=True,
        extra="ignore",
    )

    ai_provider: Literal["fake", "openai"] = Field(default="fake", validation_alias="AI_PROVIDER")
    ai_retrieval: Literal["lexical", "hybrid"] = Field(
        default="lexical", validation_alias="AI_RETRIEVAL"
    )
    database_url: str = Field(
        default="postgresql://assistant:assistant@localhost:55434/assistant_dev",
        validation_alias="DATABASE_URL",
        min_length=1,
    )
    log_raw_content: bool = Field(default=False, validation_alias="LOG_RAW_CONTENT")
    provider_timeout_seconds: float = Field(
        default=5.0, validation_alias="PROVIDER_TIMEOUT_SECONDS", gt=0, le=60
    )
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(
        default="gpt-4o-mini", validation_alias="OPENAI_CHAT_MODEL", min_length=1
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="OPENAI_EMBEDDING_MODEL",
        min_length=1,
    )
    model_pricing_version: str = Field(
        default="not-configured", validation_alias="MODEL_PRICING_VERSION", min_length=1
    )

    @model_validator(mode="after")
    def require_hosted_credentials_only_for_openai(self) -> "Settings":
        if self.ai_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
