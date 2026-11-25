from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any, Literal, Protocol, TypeVar
from uuid import UUID

from pydantic import Field

from app.core.validation import Product, StrictSchema
from app.features.assistant.domain import RankedCandidate


class ExtractedPreference(StrictSchema):
    slot: Literal["category", "characteristic", "budget", "other"]
    key: str | None = Field(default=None, max_length=100)
    value: dict[str, Any]


class QuestionExtraction(StrictSchema):
    attribute: str
    ordinal: int | None = Field(default=None, ge=1)
    productId: str | None = None
    comparative: bool = False


class PreferenceExtraction(StrictSchema):
    intent: Literal["discovery", "product_question", "out_of_scope"] = "discovery"
    preferences: list[ExtractedPreference] = Field(default_factory=list, max_length=10)
    beliefs: list[ExtractedPreference] = Field(default_factory=list, max_length=10)
    question: QuestionExtraction | None = None
    assumptions: list[str] = Field(default_factory=list)


class ProductClaim(StrictSchema):
    productId: str
    field: str
    value: Any


class ResponseSelection(StrictSchema):
    productIds: list[str] = Field(max_length=10)
    claims: list[ProductClaim] = Field(default_factory=list)


T = TypeVar("T")
_PROVIDER_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="assistant-provider")


class ProviderTimeoutError(TimeoutError):
    """Raised when a provider operation exceeds its configured deadline."""


class ProviderUnavailableError(Exception):
    """Carries the already-emitted interaction ID to the public error handler."""

    def __init__(self, interaction_id: UUID) -> None:
        super().__init__("Provider unavailable")
        self.interaction_id = interaction_id


def call_with_timeout[T](operation: Callable[[], T], timeout_seconds: float) -> T:
    future = _PROVIDER_EXECUTOR.submit(operation)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as error:
        future.cancel()
        raise ProviderTimeoutError from error


class LanguageModelProvider(Protocol):
    """Only preference extraction and evidence-bound response selection are permitted."""

    provider_name: str
    model_id: str
    prompt_version: str

    def extract_preferences(self, *, message: str) -> PreferenceExtraction: ...

    def select_response(
        self,
        *,
        message: str,
        candidates: list[RankedCandidate],
        products: list[Product],
    ) -> ResponseSelection: ...
