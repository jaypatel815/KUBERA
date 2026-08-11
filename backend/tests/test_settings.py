import pytest

from settings import ConfigError, KuberaSettings


def clean_settings(monkeypatch, **env) -> KuberaSettings:
    """Settings from a controlled environment: no ambient vars, no .env file."""
    for var in (
        "ALPACA_API_KEY_ID",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER",
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
