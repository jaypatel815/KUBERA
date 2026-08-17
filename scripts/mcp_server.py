"""CLI entrypoint for KUBERA Model Context Protocol (MCP) server (T045, D011).

Usage:
  python scripts/mcp_server.py

Configuring with Claude Desktop (`claude_desktop_config.json`):
  {
    "mcpServers": {
      "kubera": {
        "command": "python",
        "args": ["<path-to-repo>/scripts/mcp_server.py"],
        "cwd": "<path-to-repo>"
      }
    }
  }
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
