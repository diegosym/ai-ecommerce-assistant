import pytest

from app.core.config import Settings
from scripts.provider_smoke import run_provider_smoke


def test_provider_smoke_refuses_fake_without_credentials_or_network() -> None:
    settings = Settings(_env_file=None, AI_PROVIDER="fake")

    with pytest.raises(ValueError, match="Hosted provider smoke refused"):
        run_provider_smoke(settings)
