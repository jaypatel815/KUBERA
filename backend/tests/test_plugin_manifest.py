"""T120 — the plugin package: manifests parse, names are immutable, the
commands exist and carry frontmatter. File-based contract, pinned."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_plugin_manifest_parses_with_required_keys():
    p = json.loads((ROOT / ".claude-plugin" / "plugin.json")
                   .read_text(encoding="utf-8"))
    # the name is an IMMUTABLE slug (claude-plugins-official convention):
    # renaming breaks installs — this pin makes a rename a deliberate act.
    assert p["name"] == "kubera"
    assert p["version"] and p["description"]
    assert "tested code computes" in p["description"]   # doctrine travels


def test_marketplace_lists_the_root_plugin():
    m = json.loads((ROOT / ".claude-plugin" / "marketplace.json")
                   .read_text(encoding="utf-8"))
    assert m["name"] == "kubera"
    assert [pl["name"] for pl in m["plugins"]] == ["kubera"]
    assert m["plugins"][0]["source"] == "."


def test_commands_exist_with_frontmatter_and_no_machine_paths():
    for name in ("kubera.md", "kubera-connect.md"):
        text = (ROOT / "commands" / name).read_text(encoding="utf-8")
        assert text.startswith("---\ndescription:")
        # machine-local paths must NEVER ship in the plugin — the connect
        # command instructs generating them (install_mcp_config.py / a
        # substituted claude mcp add), it does not hardcode one.
        assert "C:\\Users" not in text and "/sessions/" not in text
    connect = (ROOT / "commands" / "kubera-connect.md").read_text(
        encoding="utf-8")
    assert "install_mcp_config.py" in connect
    assert "READ-ONLY" in connect
