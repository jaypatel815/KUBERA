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
    alpaca_data_base_url: str = Field(
        default="https://data.alpaca.markets",
        validation_alias=AliasChoices("ALPACA_DATA_BASE_URL", "KUBERA_ALPACA_DATA_BASE_URL"),
    )

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
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com",
        validation_alias=AliasChoices("ANTHROPIC_BASE_URL", "KUBERA_ANTHROPIC_BASE_URL"),
    )
    openai_model: str = Field(
        default="gpt-5", validation_alias=AliasChoices("OPENAI_MODEL",)
    )
    # Any OpenAI-compatible endpoint: Ollama (http://localhost:11434/v1), Groq,
    # Gemini's compat endpoint, etc. Default = the real OpenAI.
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("OPENAI_BASE_URL", "KUBERA_OPENAI_BASE_URL"),
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
    fred_base_url: str = Field(
        default="https://api.stlouisfed.org",
        validation_alias=AliasChoices("FRED_BASE_URL", "KUBERA_FRED_BASE_URL"),
    )

    # FMP (T023, D030) — FREE tier, probe-verified 2026-08-17: the /stable
    # earnings calendar and 5-year statements answer; news/transcripts are
    # paywalled (news comes from Alpaca instead). 250 requests/day.
    fmp_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("FMP_API_KEY", "KUBERA_FMP_API_KEY"),
    )
    fmp_base_url: str = Field(
        default="https://financialmodelingprep.com",
        validation_alias=AliasChoices("FMP_BASE_URL", "KUBERA_FMP_BASE_URL"),
    )

    # Risk limits (T115 — the T033 promise "owner tunes via config later").
    # These are RAILS: raising one is a decision, not a tweak. Values are
    # validated by RiskLimits itself at engine construction — a bad .env
    # value fails LOUDLY at startup with the allowed range, never silently
    # clamped. Defaults here MUST mirror risk/engine.RiskLimits defaults
    # (pinned by test so they cannot drift apart).
    risk_daily_loss_limit_frac: float = Field(
        default=0.03,
        validation_alias=AliasChoices("KUBERA_DAILY_LOSS_LIMIT_FRAC"),
    )
    risk_max_position_frac: float = Field(
        default=0.20,
        validation_alias=AliasChoices("KUBERA_MAX_POSITION_FRAC"),
    )
    risk_cooldown_hours: float = Field(
        default=20.0,
        validation_alias=AliasChoices("KUBERA_COOLDOWN_HOURS"),
    )
    risk_per_trade_frac: float = Field(
        default=0.01,
        validation_alias=AliasChoices("KUBERA_RISK_PER_TRADE_FRAC"),
    )
    risk_stop_atr_multiple: float = Field(
        default=2.0,
        validation_alias=AliasChoices("KUBERA_STOP_ATR_MULTIPLE"),
    )
    risk_max_buys_per_day: int = Field(
        default=5,
        validation_alias=AliasChoices("KUBERA_MAX_BUYS_PER_DAY"),
    )

    # Finnhub (T121, D030/D037) — OWNER-PROBED 2026-08-20 from his machine:
    # free tier answers quote, company-news (244 articles/31d observed),
    # /stock/earnings surprises (4 quarters actual-vs-estimate — the prize:
    # real beat/miss splits for T083 base rates), stock/metric (133
    # metrics); news-sentiment PAYWALLED (403). 60 calls/min free ceiling.
    finnhub_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("FINNHUB_API_KEY",
                                      "KUBERA_FINNHUB_API_KEY"),
    )
    finnhub_base_url: str = Field(
        default="https://finnhub.io/api/v1",
        validation_alias=AliasChoices("FINNHUB_BASE_URL",
                                      "KUBERA_FINNHUB_BASE_URL"),
    )

    # SEC EDGAR (T083b, D030/D034) — free and keyless, probe-verified
    # 2026-08-18 (46 earnings 8-Ks for the probe symbol, 46/46 with
    # acceptance timestamps). The SEC requires a CONTACT ADDRESS in the
    # User-Agent and blocks anonymous clients; the contact is the owner's —
    # SecretStr so it is never logged, and never committed (repo is public).
    edgar_contact: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("EDGAR_CONTACT", "KUBERA_EDGAR_CONTACT"),
    )
    edgar_base_url: str = Field(
        default="https://data.sec.gov",
        validation_alias=AliasChoices("EDGAR_BASE_URL", "KUBERA_EDGAR_BASE_URL"),
    )
    edgar_www_url: str = Field(
        default="https://www.sec.gov",
        validation_alias=AliasChoices("EDGAR_WWW_URL", "KUBERA_EDGAR_WWW_URL"),
    )

    # Schwab Trader API (T016, D026) — READ-ONLY. OAuth, not a key pair: the app
    # key/secret identify the APPLICATION, the refresh token identifies the LOGIN,
    # and the account number is neither — it only picks which account, and Schwab
    # addresses accounts by an encrypted hash anyway.
    schwab_app_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SCHWAB_APP_KEY", "KUBERA_SCHWAB_APP_KEY"),
    )
    schwab_app_secret: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SCHWAB_APP_SECRET", "KUBERA_SCHWAB_APP_SECRET"),
    )
    schwab_refresh_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SCHWAB_REFRESH_TOKEN", "KUBERA_SCHWAB_REFRESH_TOKEN"),
    )
    schwab_base_url: str = Field(
        default="https://api.schwabapi.com",
        validation_alias=AliasChoices("SCHWAB_BASE_URL", "KUBERA_SCHWAB_BASE_URL"),
    )
    schwab_auth_url: str = Field(
        default="https://api.schwabapi.com/v1/oauth/authorize",
        validation_alias=AliasChoices("SCHWAB_AUTH_URL", "KUBERA_SCHWAB_AUTH_URL"),
    )
    schwab_token_url: str = Field(
        default="https://api.schwabapi.com/v1/oauth/token",
        validation_alias=AliasChoices("SCHWAB_TOKEN_URL", "KUBERA_SCHWAB_TOKEN_URL"),
    )
    # Must EXACTLY match the callback registered on the app at developer.schwab.com —
    # Schwab compares it byte for byte, and it must be https even for localhost.
    schwab_callback_url: str = Field(
        default="https://127.0.0.1",
        validation_alias=AliasChoices("SCHWAB_CALLBACK_URL", "KUBERA_SCHWAB_CALLBACK_URL"),
    )
    schwab_account_number: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SCHWAB_ACCOUNT_NUMBER", "KUBERA_SCHWAB_ACCOUNT_NUMBER"),
    )

    def require_schwab(self) -> "KuberaSettings":
        """Return self if Schwab OAuth config is present; raise ConfigError otherwise."""
        missing = []
        if not self.schwab_app_key:
            missing.append("SCHWAB_APP_KEY")
        if not self.schwab_app_secret or not self.schwab_app_secret.get_secret_value():
            missing.append("SCHWAB_APP_SECRET")
        if not self.schwab_refresh_token or not self.schwab_refresh_token.get_secret_value():
            missing.append("SCHWAB_REFRESH_TOKEN")
        if missing:
            raise ConfigError(
                f"Missing required config: {', '.join(missing)}. The app key and secret come "
                "from your approved app at developer.schwab.com; the refresh token comes from "
                "a one-time browser authorisation (python scripts/schwab_auth.py) and expires "
                "roughly weekly. Schwab access is READ-ONLY (D026). Never commit .env."
            )
        return self

    @property
    def schwab_configured(self) -> bool:
        try:
            self.require_schwab()
            return True
        except ConfigError:
            return False

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
