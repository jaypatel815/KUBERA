import importlib.util
from pathlib import Path

import httpx
import pytest

from analysis.attribution import OPTION_MULTIPLIER
from api.llm import AnthropicProvider
from data.alpaca import PAPER_BASE_URL
from data.fred import FredClient
from data.market_data import MarketDataClient
from data.schwab import SchwabClient
from settings import ConfigError, KuberaSettings


def _auth_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "schwab_auth.py"
    spec = importlib.util.spec_from_file_location("schwab_auth", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean_settings(monkeypatch, **env) -> KuberaSettings:
    """Settings from a controlled environment: no ambient vars, no .env file."""
    for var in (
        "ALPACA_API_KEY_ID",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER",
        "ALPACA_DATA_BASE_URL",
        "ANTHROPIC_BASE_URL",
        "OPENAI_BASE_URL",
        "FRED_BASE_URL",
        "SCHWAB_BASE_URL",
        "SCHWAB_AUTH_URL",
        "SCHWAB_TOKEN_URL",
    ):
        monkeypatch.delenv(var, raising=False)
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    return KuberaSettings(_env_file=None)


def test_boots_without_keys(monkeypatch):
    s = clean_settings(monkeypatch)
    assert s.alpaca_configured is False
    assert s.alpaca_paper is True  # paper trading is the default, always (D003)


def test_require_alpaca_lists_exact_missing_vars(monkeypatch):
    s = clean_settings(monkeypatch, ALPACA_API_KEY_ID="PKTEST123")
    with pytest.raises(ConfigError) as exc:
        s.require_alpaca()
    msg = str(exc.value)
    assert "ALPACA_API_SECRET_KEY" in msg
    assert "ALPACA_API_KEY_ID" not in msg.split("Missing required config:")[1].split(".")[0]
    assert "T006" in msg  # points the owner at the fix


def test_require_alpaca_passes_when_configured(monkeypatch):
    s = clean_settings(
        monkeypatch, ALPACA_API_KEY_ID="PKTEST123", ALPACA_API_SECRET_KEY="supersecret"
    )
    assert s.require_alpaca() is s
    assert s.alpaca_configured is True


def test_secret_never_leaks_in_repr(monkeypatch):
    s = clean_settings(
        monkeypatch, ALPACA_API_KEY_ID="PKTEST123", ALPACA_API_SECRET_KEY="supersecret"
    )
    assert "supersecret" not in repr(s)
    assert "supersecret" not in str(s)
    assert s.alpaca_api_secret_key is not None
    assert s.alpaca_api_secret_key.get_secret_value() == "supersecret"


def test_alias_names_accepted(monkeypatch):
    """The owner's .env uses ALPACA_API_KEY — both spellings must work."""
    s = clean_settings(
        monkeypatch, ALPACA_API_KEY="PKTEST123", ALPACA_API_SECRET_KEY="supersecret"
    )
    assert s.alpaca_configured is True


def test_paper_flag_parses_from_env(monkeypatch):
    s = clean_settings(
        monkeypatch,
        ALPACA_API_KEY_ID="PKTEST123",
        ALPACA_API_SECRET_KEY="supersecret",
        ALPACA_PAPER="false",
    )
    assert s.alpaca_paper is False


# ---------------------------------------------------------------- T107 Base URLs


def test_base_url_defaults(monkeypatch):
    """Default endpoints match standard production hosts (T107)."""
    s = clean_settings(monkeypatch)
    assert s.anthropic_base_url == "https://api.anthropic.com"
    assert s.openai_base_url == "https://api.openai.com/v1"
    assert s.alpaca_data_base_url == "https://data.alpaca.markets"
    assert s.fred_base_url == "https://api.stlouisfed.org"
    assert s.schwab_base_url == "https://api.schwabapi.com"
    assert s.schwab_auth_url == "https://api.schwabapi.com/v1/oauth/authorize"
    assert s.schwab_token_url == "https://api.schwabapi.com/v1/oauth/token"


def test_base_url_env_overrides(monkeypatch):
    """Base URLs can be overridden via env vars for sandbox/mock/proxy use (T107, D028)."""
    s = clean_settings(
        monkeypatch,
        ANTHROPIC_BASE_URL="http://mock-anthropic:8000",
        OPENAI_BASE_URL="http://localhost:11434/v1",
        ALPACA_DATA_BASE_URL="http://mock-alpaca-data:8000",
        FRED_BASE_URL="http://mock-fred:8000",
        SCHWAB_BASE_URL="http://mock-schwab:8000",
        SCHWAB_AUTH_URL="http://mock-schwab:8000/authorize",
        SCHWAB_TOKEN_URL="http://mock-schwab:8000/token",
    )
    assert s.anthropic_base_url == "http://mock-anthropic:8000"
    assert s.openai_base_url == "http://localhost:11434/v1"
    assert s.alpaca_data_base_url == "http://mock-alpaca-data:8000"
    assert s.fred_base_url == "http://mock-fred:8000"
    assert s.schwab_base_url == "http://mock-schwab:8000"
    assert s.schwab_auth_url == "http://mock-schwab:8000/authorize"
    assert s.schwab_token_url == "http://mock-schwab:8000/token"


def test_clients_honor_base_url_settings(monkeypatch):
    """Clients configure their httpx base URLs from settings (T107)."""
    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if "messages" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": "hello"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            )
        if "quotes" in str(request.url):
            return httpx.Response(
                200,
                json={"quotes": {"SPY": {"ap": 500.0, "as": 100, "t": "2026-03-02T10:00:00Z"}}},
            )
        if "series" in str(request.url):
            return httpx.Response(
                200,
                json={"observations": [{"date": "2026-03-02", "value": "15.5"}]},
            )
        if "token" in str(request.url):
            return httpx.Response(
                200,
                json={"access_token": "mock-token", "expires_in": 1800},
            )
        if "accountNumbers" in str(request.url):
            return httpx.Response(
                200,
                json=[{"accountNumber": "12345678", "hashValue": "hash123"}],
            )
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(mock_handler)

    # 1. Anthropic provider with custom base_url
    provider = AnthropicProvider("test-key", "claude-sonnet-5", transport,
                                 base_url="http://mock-anthropic:8000")
    provider.complete("system", [{"role": "user", "content": "hi"}], [])
    assert captured_requests[-1].url.scheme == "http"
    assert captured_requests[-1].url.host == "mock-anthropic"
    assert captured_requests[-1].url.path == "/v1/messages"

    # 2. MarketDataClient with custom base_url
    m_settings = clean_settings(
        monkeypatch,
        ALPACA_API_KEY_ID="PKTEST",
        ALPACA_API_SECRET_KEY="secret",
        ALPACA_DATA_BASE_URL="http://mock-alpaca-data:8000",
    )
    with MarketDataClient(settings=m_settings, transport=transport) as client:
        assert str(client._http.base_url) == "http://mock-alpaca-data:8000"

    # 3. FredClient with custom base_url
    f_settings = clean_settings(
        monkeypatch,
        FRED_API_KEY="test-fred",
        FRED_BASE_URL="http://mock-fred:8000",
    )
    with FredClient(settings=f_settings, transport=transport) as client:
        assert str(client._http.base_url) == "http://mock-fred:8000"

    # 4. SchwabClient with custom base_url
    s_settings = clean_settings(
        monkeypatch,
        SCHWAB_APP_KEY="app-key",
        SCHWAB_APP_SECRET="app-secret",
        SCHWAB_REFRESH_TOKEN="refresh-token",
        SCHWAB_BASE_URL="http://mock-schwab:8000",
        SCHWAB_TOKEN_URL="http://mock-schwab:8000/custom-token",
        SCHWAB_AUTH_URL="http://mock-schwab:8000/custom-auth",
    )
    with SchwabClient(settings=s_settings, transport=transport) as client:
        assert str(client._http.base_url) == "http://mock-schwab:8000"
        accounts = client.list_accounts()
        assert len(accounts) == 1
        assert accounts[0].hash_value == "hash123"

    # 5. Schwab auth script URL builder
    auth_url = _auth_module().build_auth_url("app-key", "https://127.0.0.1", settings=s_settings)
    assert auth_url.startswith("http://mock-schwab:8000/custom-auth?")


def test_safety_rails_stay_hardcoded():
    """Alpaca paper URL and Option multiplier must stay hardcoded per D028."""
    # Safety rail 1: Alpaca paper endpoint cannot be pointed at live money
    assert PAPER_BASE_URL == "https://paper-api.alpaca.markets"
    # Safety rail 2: Option contract multiplier is fixed by the market
    assert OPTION_MULTIPLIER == 100
