r"""T045b — write the Claude Desktop MCP config for KUBERA, correctly, on this machine.

    python scripts/install_mcp_config.py           # show what would change
    python scripts/install_mcp_config.py --write   # do it (backs up first)

WHY THIS EXISTS RATHER THAN INSTRUCTIONS. Getting this config in by hand failed
three times in a row, and every failure was a path problem, not a judgement one:

  * the file was written into the repo instead of %APPDATA%\Claude\, where it
    does nothing at all;
  * "<path-to-repo>" placeholders kept their angle brackets, producing a literal
    unresolvable path;
  * "command": "python" was used, but Claude Desktop spawns the process directly
    — no shell, no activated virtualenv — so bare "python" finds the system
    interpreter, which does not have `mcp`, and the server dies at import.

None of that is worth a human's attention twice. This script resolves all three
from the machine it runs on: it locates %APPDATA%\Claude, uses THIS interpreter's
absolute path, and points at this repo's own script.

IT MERGES, IT DOES NOT CLOBBER. If you already have other MCP servers configured,
they are preserved; only the "kubera" entry is added or updated, and the previous
file is copied to claude_desktop_config.json.bak first.
"""

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "scripts" / "mcp_server.py"


def config_path() -> Path:
    """%APPDATA%\\Claude\\claude_desktop_config.json, without anyone typing it."""
    appdata = os.environ.get("APPDATA")
    if appdata:                                   # Windows
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    home = Path.home()
    mac = home / "Library" / "Application Support" / "Claude"
    if mac.exists():                              # macOS
        return mac / "claude_desktop_config.json"
    return home / ".config" / "Claude" / "claude_desktop_config.json"


def interpreter() -> str:
    """The interpreter running this script — which is the one that has the deps.

    Using sys.executable rather than the string "python" is the whole point: it
    is correct by construction on whatever machine this runs on, venv or not.
    """
    return str(Path(sys.executable).resolve()).replace("\\", "/")


def desired_entry() -> dict:
    return {
        "command": interpreter(),
        "args": [str(SERVER_SCRIPT).replace("\\", "/")],
    }


def merge(existing: dict, entry: dict) -> dict:
    out = dict(existing)
    servers = dict(out.get("mcpServers") or {})
    servers["kubera"] = entry
    out["mcpServers"] = servers
    return out


def main() -> int:
    write = "--write" in sys.argv
    path = config_path()
    entry = desired_entry()

    print(f"config file : {path}")
    print(f"exists      : {path.exists()}")
    print(f"interpreter : {entry['command']}")
    print(f"server      : {entry['args'][0]}")

    if not SERVER_SCRIPT.exists():
        print(f"\nERROR: {SERVER_SCRIPT} does not exist. Wrong repo root?")
        return 2

    # Fail early and clearly rather than writing a config that cannot work.
    try:
        import mcp.server.fastmcp  # noqa: F401
    except ImportError:
        print("\nERROR: this interpreter cannot import mcp.server.fastmcp.")
        print("  Run:  pip install -r backend/requirements.txt")
        print("  (and run THIS script with the same interpreter, so the config")
        print("   records the one that actually has the dependency.)")
        return 2
    print("mcp import  : OK")

    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as e:
            print(f"\nERROR: the existing config is not valid JSON ({e}).")
            print("  Fix or delete it first — refusing to overwrite something")
            print("  that might contain settings worth keeping.")
            return 2

    other = [k for k in (existing.get("mcpServers") or {}) if k != "kubera"]
    if other:
        print(f"preserving  : {', '.join(other)}")

    merged = merge(existing, entry)
    rendered = json.dumps(merged, indent=2)

    if existing.get("mcpServers", {}).get("kubera") == entry:
        print("\nAlready correct — nothing to change.")
        return 0

    if not write:
        print("\n--- would write ---")
        print(rendered)
        print("\nRe-run with --write to apply.")
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(".json.bak")
        shutil.copy2(path, backup)
        print(f"backup      : {backup}")
    path.write_text(rendered + "\n", encoding="utf-8")
    print('\nWritten. Restart Claude Desktop, then ask it: '
          '"what does my portfolio look like?"')
    print("KUBERA exposes 30 read-only tools; the four that write are withheld,")
    print("and update_ips cannot be reached over MCP at all (D026, I021).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
