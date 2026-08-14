"""I014 postmortem: .env said claude-sdk, the running server used openai.
Mechanism: real env vars beat .env (pydantic-settings precedence). These tests
pin the detection helper and the startup mismatch warning."""

import logging

from fastapi.testclient import TestClient

from api.main import app
from settings import KuberaSettings, env_file_llm_provider


def test_env_file_provider_parses_variants(tmp_path):
    p = tmp_path / ".env"
    p.write_text("FOO=1\nLLM_PROVIDER=claude-sdk\nBAR=2\n")
    assert env_file_llm_provider(p) == "claude-sdk"
    p.write_text('KUBERA_LLM_PROVIDER="openai"  # comment\n')
    assert env_file_llm_provider(p) == "openai"
    p.write_text("  LLM_PROVIDER = anthropic\n")
    assert env_file_llm_provider(p) == "anthropic"


def test_env_file_provider_absent(tmp_path):
    assert env_file_llm_provider(tmp_path / "nope.env") is None
    empty = tmp_path / ".env"
    empty.write_text("ALPACA_PAPER=true\n")
    assert env_file_llm_provider(empty) is None


def test_os_env_beats_env_file(monkeypatch, tmp_path):
    """The exact I014 mechanism, reproduced: .env says claude-sdk, an OS var
    says openai — the OS var wins. This is pydantic-settings' documented
    precedence; the test exists so nobody 'fixes' it by accident or argues
    with the owner about what their .env says."""
    envfile = tmp_path / ".env"
    envfile.write_text("LLM_PROVIDER=claude-sdk\n")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    s = KuberaSettings(_env_file=str(envfile))
    assert s.llm_provider == "openai"  # OS env overrode the file
    monkeypatch.delenv("LLM_PROVIDER")
    s2 = KuberaSettings(_env_file=str(envfile))
    assert s2.llm_provider == "claude-sdk"  # file honored once the var is gone


def test_startup_announces_brain_and_warns_on_mismatch(monkeypatch, caplog):
    """Lifespan logs the resolved provider; if .env intent differs, it WARNS
    with a pointer to brain_check.py."""
    import api.main as main_mod

    monkeypatch.setattr(main_mod, "env_file_llm_provider", lambda: "claude-sdk")

    class FakeSettings:
        llm_provider = "openai"

    monkeypatch.setattr(main_mod, "get_settings", lambda: FakeSettings())
    with caplog.at_level(logging.INFO, logger="kubera.api"):
        with TestClient(app):  # context manager runs the lifespan
            pass
    text = caplog.text
    assert "llm_provider=openai" in text
    assert "PROVIDER MISMATCH" in text
    assert "brain_check.py" in text


def test_startup_quiet_when_aligned(monkeypatch, caplog):
    import api.main as main_mod

    monkeypatch.setattr(main_mod, "env_file_llm_provider", lambda: "claude-sdk")

    class FakeSettings:
        llm_provider = "claude-sdk"

    monkeypatch.setattr(main_mod, "get_settings", lambda: FakeSettings())
    with caplog.at_level(logging.INFO, logger="kubera.api"):
        with TestClient(app):
            pass
    assert "PROVIDER MISMATCH" not in caplog.text
    assert "llm_provider=claude-sdk" in caplog.text
