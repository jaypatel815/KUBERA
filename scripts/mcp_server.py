"""CLI entrypoint for KUBERA Model Context Protocol (MCP) server (T045, D011).

Usage:
  python scripts/mcp_server.py

Configuring with Claude Desktop (`claude_desktop_config.json`):
  {
    "mcpServers": {
      "kubera": {
        "command": "C:/Users/<you>/Projects/KUBERA/.venv/Scripts/python.exe",
        "args": ["C:/Users/<you>/Projects/KUBERA/scripts/mcp_server.py"]
      }
    }
  }

THREE THINGS THAT GO WRONG HERE, all of them found the first time the owner
tried it, and two of them caused by an earlier version of this very docstring:

1. THE FILE GOES IN %APPDATA%\Claude\, NOT IN THE REPO. Claude Desktop reads
   C:\Users\<you>\AppData\Roaming\Claude\claude_desktop_config.json. A
   correct config sitting in the project folder does nothing at all.

2. USE THE ABSOLUTE PATH TO .venv\Scripts\python.exe, NOT bare "python".
   Claude Desktop spawns this process directly — it does not open a shell and
   does not activate your virtualenv. Bare "python" resolves to whatever the
   system default is, which is not where `mcp` is installed, so the server dies
   at import with ModuleNotFoundError and Claude Desktop reports only that the
   server failed to start.

3. DELETE THE ANGLE BRACKETS. `<path-to-repo>` is a placeholder. Leaving
   "<C:/Users/...>" in the JSON produces a literal path with angle brackets in
   it, which resolves to nothing.

`cwd` is not needed: the script resolves its own repo root from __file__.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from api.mcp_server import build_mcp_server  # noqa: E402


def main() -> None:
    server = build_mcp_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
