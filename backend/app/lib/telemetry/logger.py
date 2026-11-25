import sys
from collections.abc import Callable, Mapping

from app.lib.telemetry.events import AssistantInteractionEvent


def log_assistant_interaction(
    event: AssistantInteractionEvent | Mapping[str, object],
    write: Callable[[str], object] | None = None,
) -> None:
    """Validate and emit exactly one JSON line; unknown content fields are forbidden."""
    validated = AssistantInteractionEvent.model_validate(event)
    writer = write if write is not None else sys.stdout.write
    writer(f"{validated.model_dump_json()}\n")
