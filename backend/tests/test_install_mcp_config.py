"""T045b — the MCP config installer (D027 self-check made permanent).

These tests exist because a self-review found three real defects in this script
AFTER it had been run once and committed. Running it proved it worked on the
happy path; only trying to break it found the rest. Each test below is one of
those defects.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "install_mcp_config.py"


def _mod():
    spec = importlib.util.spec_from_file_location("install_mcp_config", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reads_a_notepad_written_file_with_a_bom(tmp_path, monkeypatch):
    """THE ONE THAT MATTERED. The owner hand-edits this file in Notepad on
    Windows, which writes a BOM. Reading as plain utf-8 makes json.loads fail,
    so the script written to unblock him would refuse for the likeliest reason
    his file is unusual."""
    m = _mod()
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text('\ufeff{"mcpServers": {"other": {"command": "x"}}}', encoding="utf-8")
    monkeypatch.setattr(m, "config_path", lambda: cfg)
    monkeypatch.setattr(sys, "argv", ["install_mcp_config.py", "--write"])

    assert m.main() == 0
    after = json.loads(cfg.read_text(encoding="utf-8-sig"))
    assert "kubera" in after["mcpServers"]
    assert after["mcpServers"]["other"] == {"command": "x"}   # not clobbered


def test_macos_path_is_chosen_by_platform_not_by_what_exists(monkeypatch):
    """Keying off .exists() meant a Mac without the folder yet got a
    ~/.config path that nothing reads — a correct file in the wrong place."""
    m = _mod()
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert "Library/Application Support/Claude" in m.config_path().as_posix()


def test_windows_path_uses_appdata(monkeypatch):
    """Asserted structurally, not by string: on Linux a Windows path's
    backslashes are ordinary characters, so as_posix() comparisons pass or fail
    for reasons that have nothing to do with the logic under test."""
    m = _mod()
    monkeypatch.setenv("APPDATA", r"C:\Users\someone\AppData\Roaming")
    p = m.config_path()
    assert p.name == "claude_desktop_config.json"
    assert p.parent.name == "Claude"
    assert "Roaming" in str(p.parent.parent)


def test_merge_survives_a_hand_mangled_mcpServers():
    """This file is hand-edited, so it can arrive any shape. A raw ValueError
    would be a worse experience than rebuilding the section."""
    m = _mod()
    for junk in (["oops"], "oops", None, 42):
        out = m.merge({"mcpServers": junk}, {"command": "c", "args": []})
        assert out["mcpServers"]["kubera"] == {"command": "c", "args": []}


def test_merge_preserves_other_servers_and_keys_without_mutating_input():
    m = _mod()
    existing = {"mcpServers": {"other": {"command": "x"}}, "unrelated": 123}
    out = m.merge(existing, {"command": "c", "args": ["s.py"]})
    assert out["mcpServers"]["other"] == {"command": "x"}
    assert out["unrelated"] == 123
    assert "kubera" not in existing["mcpServers"]      # input untouched


def test_records_the_running_interpreter_not_the_string_python():
    """The original hand-written config used 'python', which fails because
    Claude Desktop spawns without activating the venv."""
    m = _mod()
    entry = m.desired_entry()
    assert entry["command"] != "python"
    assert Path(entry["command"]).name.startswith("python")
    assert entry["args"][0].endswith("scripts/mcp_server.py")


def test_refuses_to_overwrite_json_it_cannot_parse(tmp_path, monkeypatch, capsys):
    """Better to stop than to destroy settings that might matter."""
    m = _mod()
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setattr(m, "config_path", lambda: cfg)
    monkeypatch.setattr(sys, "argv", ["install_mcp_config.py", "--write"])

    assert m.main() == 2
    assert "not valid JSON" in capsys.readouterr().out
    assert cfg.read_text(encoding="utf-8") == "{ this is not json"   # untouched


def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    m = _mod()
    cfg = tmp_path / "claude_desktop_config.json"
    monkeypatch.setattr(m, "config_path", lambda: cfg)
    monkeypatch.setattr(sys, "argv", ["install_mcp_config.py"])
    assert m.main() == 0
    assert not cfg.exists()


def test_backup_is_made_before_overwriting(tmp_path, monkeypatch):
    m = _mod()
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text('{"mcpServers": {}}', encoding="utf-8")
    monkeypatch.setattr(m, "config_path", lambda: cfg)
    monkeypatch.setattr(sys, "argv", ["install_mcp_config.py", "--write"])
    m.main()
    assert (tmp_path / "claude_desktop_config.json.bak").exists()


def test_is_idempotent(tmp_path, monkeypatch, capsys):
    m = _mod()
    cfg = tmp_path / "claude_desktop_config.json"
    monkeypatch.setattr(m, "config_path", lambda: cfg)
    monkeypatch.setattr(sys, "argv", ["install_mcp_config.py", "--write"])
    m.main()
    capsys.readouterr()
    assert m.main() == 0
    assert "Already correct" in capsys.readouterr().out


pytest.importorskip("mcp.server.fastmcp",
                    reason="the script refuses to run without it, by design")
