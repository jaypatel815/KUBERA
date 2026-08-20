---
description: Connect this Claude session to the KUBERA MCP server (44 read-only analysis tools over your own data).
---

Wire KUBERA's tool registry into this Claude client. The MCP config is
machine-local (it embeds YOUR venv's python path), so it is generated, not
shipped — walk the user through the right path for their client:

**Claude Desktop** — run the existing installer, which locates
`%APPDATA%\Claude\claude_desktop_config.json`, resolves the venv
interpreter absolutely, merges without clobbering other MCP servers, and
backs up the existing file:

    python scripts/install_mcp_config.py

**Claude Code / Cowork (CLI)** — register the server directly, substituting
the absolute repo path:

    claude mcp add kubera -- <repo>\.venv\Scripts\python.exe <repo>\scripts\mcp_server.py

Then verify: ask "what's in my portfolio?" — the reply should cite live
Alpaca paper data with timestamps. The default surface is READ-ONLY
(37 of 44 tools); mutation tools require explicit opt-in and the
confirmation-gated IPS update is never exposed over MCP (I021). Every
tool call opens fresh clients and closes all of them (T106).
