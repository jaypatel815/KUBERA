"""T062c — the scheduled-brief CLI, importlib-by-path (T106 precedent)."""

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "brief.py"


def _mod():
    spec = importlib.util.spec_from_file_location("brief_cli_t062c", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_composes_and_saves(tmp_path, monkeypatch, capsys):
    """Full path with everything faked: composes morning, prints JSON,
    saves under private/briefs/<type>-<date>.json."""
    mod = _mod()
    payload = {"type": "morning", "generated_at": "t", "account": {}}

    class FakeCM:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): ...
        def close(self): ...

    monkeypatch.setattr(mod, "AlpacaClient", FakeCM)
    monkeypatch.setattr(mod, "MarketDataClient", FakeCM)
    monkeypatch.setattr(mod, "compose_morning_brief",
                        lambda *a, **k: payload)
    monkeypatch.setattr(mod, "_optional_clients", lambda: (None, None))
    monkeypatch.setattr(mod, "make_engine", lambda url: None)

    class FakeFactory:
        def __call__(self): return FakeCM()

    monkeypatch.setattr(mod, "make_session_factory", lambda e: FakeFactory())

    class OkSettings:
        database_url = "sqlite://"
        def require_alpaca(self): return self

    monkeypatch.setattr(mod, "get_settings", lambda: OkSettings())
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["brief.py"])

    assert mod.main() == 0
    out = capsys.readouterr().out
    assert json.loads(out)["type"] == "morning"
    saved = list((tmp_path / "private" / "briefs").glob("morning-*.json"))
    assert len(saved) == 1
    assert json.loads(saved[0].read_text(encoding="utf-8")) == payload


def test_cli_not_configured_is_actionable(monkeypatch, capsys):
    mod = _mod()

    class BadSettings:
        def require_alpaca(self):
            from settings import ConfigError
            raise ConfigError("ALPACA keys missing — add them to .env")

    monkeypatch.setattr(mod, "get_settings", lambda: BadSettings())
    monkeypatch.setattr("sys.argv", ["brief.py"])
    assert mod.main() == 2
    assert "NOT CONFIGURED" in capsys.readouterr().out
