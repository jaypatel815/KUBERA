"""Typed, fail-fast configuration (T010).

All environment/config access goes through this module — no bare os.getenv() calls
scattered around the codebase. Secrets are SecretStr so they can never leak via repr/logs.

The app boots without Alpaca keys (so agents can develop and CI can run cold), but any
code path that actually needs the broker calls `require_alpaca()` and fails immediately
with a precise, actionable message instead of a mysterious HTTP 401 later.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]


class ConfigError(RuntimeError):
    """Raised when required configuration is missing. Message says exactly what and how to fix."""


class KuberaSettings(BaseSettings):
    """Loaded from environment variables, then repo-root .env (env vars win)."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    alpaca_api_key_id: str | None = None
    alpaca_api_secret_key: SecretStr | None = None
    alpaca_paper: bool = True

    def require_alpaca(self) -> "KuberaSettings":
        """Return self if Alpaca credentials are present; raise ConfigError otherwise."""
        missing = []
        if not self.alpaca_api_key_id:
            missing.append("ALPACA_API_KEY_ID")
        if not self.alpaca_api_secret_key or not self.alpaca_api_secret_key.get_secret_value():
            missing.append("ALPACA_API_SECRET_KEY")
        if missing:
            raise ConfigError(
                f"Missing required config: {', '.join(missing)}. "
                "Copy .env.example to .env at the repo root and fill in your Alpaca PAPER keys "
                "(owner task T006 in /project-memory/TASKS.md). Never commit .env."
            )
        return self

    @property
    def alpaca_configured(self) -> bool:
        try:
            self.require_alpaca()
            return True
        except ConfigError:
            return False


@lru_cache
def get_settings() -> KuberaSettings:
    """Process-wide settings singleton. Tests construct KuberaSettings() directly instead."""
    return KuberaSettings()
