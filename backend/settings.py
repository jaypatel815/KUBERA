"""Typed, fail-fast configuration (T010).

All environment/config access goes through this module — no bare os.getenv() calls
scattered around the codebase. Secrets are SecretStr so they can never leak via repr/logs.

The app boots without Alpaca keys (so agents can develop and CI can run cold), but any
code path that actually needs the broker calls `require_alpaca()` and fails immediately
with a precise, actionable message instead of a mysterious HTTP 401 later.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]


class ConfigError(RuntimeError):
    """Raised when required configuration is missing. Message says exactly what and how to fix."""


def env_file_llm_provider(env_path: Path | None = None) -> str | None:
    """What repo .env SAYS for LLM_PROVIDER — the owner's intent, which real
    environment variables silently override (pydantic-settings precedence).
    Used to detect and WARN about that mismatch (I014 postmortem)."""
    import re  # local: keep module import surface unchanged

    path = env_path if env_path is not None else REPO_ROOT / ".env"
    if not path.exists():
        return None
    m = re.search(
        r"^\s*(?:KUBERA_)?LLM_PROVIDER\s*=\s*([^\s#]+)",
        path.read_text(encoding="utf-8", errors="replace"),
        re.MULTILINE,
    )
    return m.group(1).strip().strip('"').strip("'") if m else None


class KuberaSettings(BaseSettings):
    """Loaded from environment variables, then repo-root .env (env vars win)."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Accepts both our canonical name and the common short form (owner's .env uses the latter).
    alpaca_api_key_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ALPACA_API_KEY_ID", "ALPACA_API_KEY"),
    )
    alpaca_api_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ALPACA_API_SECRET_KEY", "ALPACA_SECRET_KEY"),
    )
    alpaca_paper: bool = True

    # Conversation layer (Phase 4). Provider picked here; keys never leave SecretStr.
    llm_provider: str = Field(
        default="anthropic",
        validation_alias=AliasChoices("KUBERA_LLM_PROVIDER", "LLM_PROVIDER"),
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("ANTHROPIC_API_KEY",)
    )
    openai_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("OPENAI_API_KEY",)
    )
    # T046: Claude Agent SDK provider — runs chat on the owner's Claude subscription.
    # Personal use only (D012). Token from `claude setup-token`.
    claude_code_oauth_token: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("CLAUDE_CODE_OAUTH_TOKEN",)
    )
    claude_sdk_max_turns: int = Field(
        default=8, ge=1, le=24, validation_alias=AliasChoices("CLAUDE_SDK_MAX_TURNS",)
    )

    # Verify current model names when configuring; override via env any time.
    anthropic_model: str = Field(
        default="claude-sonnet-5", validation_alias=AliasChoices("ANTHROPIC_MODEL",)
    )
    openai_model: str = Field(
        default="gpt-5", validation_alias=AliasChoices("OPENAI_MODEL",)
    )
    # Any OpenAI-compatible endpoint: Ollama (http://localhost:11434/v1), Groq,
    # Gemini's compat endpoint, etc. Default = the real OpenAI.
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("OPENAI_BASE_URL",),
    )

    # T044: how much conversation history (in characters, ~4 chars/token) the chat
    # loop replays to the LLM each round.
    context_budget_chars: int = Field(
        default=24_000, ge=1_000,
        validation_alias=AliasChoices("KUBERA_CONTEXT_BUDGET_CHARS",),
    )

    # T096: which slice of the registry a brain is offered. "auto" curates a
    # core set for local/compat endpoints (I008: small models drown in 31
    # tools) and offers everything to strong brains; "full"/"core" force it.
    tool_profile: str = Field(
        default="auto",
        validation_alias=AliasChoices("KUBERA_TOOL_PROFILE", "TOOL_PROFILE"),
    )

    # How long one LLM call may take. Local models (Ollama) chewing a long IPS
    # brief blew through the old hard-coded 120s (I014); default is generous and
    # env-tunable rather than guessed.
    llm_timeout_seconds: float = Field(
        default=300.0, ge=10, le=1800,
        validation_alias=AliasChoices("KUBERA_LLM_TIMEOUT_SECONDS",
                                      "LLM_TIMEOUT_SECONDS"),
    )

    # D007: SQLite now, Postgres+pgvector at Phase 3 — switching is a URL change.
    database_url: str = Field(
        default=f"sqlite:///{(REPO_ROOT / 'kubera.sqlite3').as_posix()}",
        validation_alias=AliasChoices("DATABASE_URL", "KUBERA_DATABASE_URL"),
    )

    # Macro context (T080). Owner already holds a FRED key (D009).
    fred_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("FRED_API_KEY", "KUBERA_FRED_API_KEY"),
    )

    def require_fred(self) -> "KuberaSettings":
        """Return self if the FRED key is present; raise ConfigError otherwise."""
        if not self.fred_api_key or not self.fred_api_key.get_secret_value():
            raise ConfigError(
                "Missing required config: FRED_API_KEY. Get a free key at "
                "https://fred.stlouisfed.org/docs/api/api_key.html and add it to .env "
                "at the repo root. Never commit .env."
            )
        return self

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
