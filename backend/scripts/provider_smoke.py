import sys

from app.core.config import Settings, get_settings


def run_provider_smoke(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.ai_provider != "openai":
        raise ValueError(
            "Hosted provider smoke refused: set AI_PROVIDER=openai explicitly. "
            "The deterministic fake journey makes no network calls."
        )
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for the hosted provider smoke")
    try:
        import openai
    except ImportError as error:
        raise RuntimeError(
            "The optional openai package is required only for hosted provider smoke"
        ) from error

    client = openai.OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.provider_timeout_seconds,
    )
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[
            {
                "role": "user",
                "content": "Reply with the single word READY for an opt-in connectivity check.",
            }
        ],
        max_tokens=8,
    )
    usage = response.usage
    print("Hosted provider smoke completed.")
    print(f"Provider: openai; model: {settings.openai_chat_model}")
    print(f"Pricing version: {settings.model_pricing_version}")
    print(
        "Token usage: "
        f"input={getattr(usage, 'prompt_tokens', None)}, "
        f"output={getattr(usage, 'completion_tokens', None)}"
    )


if __name__ == "__main__":
    try:
        run_provider_smoke()
    except Exception as error:
        print(f"Provider smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
