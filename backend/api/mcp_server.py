"""KUBERA Model Context Protocol (MCP) Server (T045, D011).

Exposes KUBERA's deterministic tool registry (T024) over standard MCP (stdio)
so external frontends (Claude Desktop, Antigravity, MCP inspectors) can interact
with KUBERA's research, analysis, and portfolio intelligence.

Safety & Determinism rails:
- Read-only analysis & portfolio intelligence by default.
- No direct trade execution or order modification (D011).
- Every financial figure is computed deterministically in tested code.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError as MCPToolError

from api.tools import ToolContext, ToolError, registry
from data.alpaca import AlpacaClient
from data.db import make_engine, make_session_factory
from data.fred import FredClient
from data.market_data import MarketDataClient
from settings import KuberaSettings, get_settings

log = logging.getLogger("kubera.mcp")


def make_default_tool_context(
    settings: KuberaSettings | None = None,
    db: Any | None = None,
) -> ToolContext:
    """Build a standard ToolContext from environment settings."""
    s = settings or get_settings()
    alpaca = AlpacaClient(s) if s.alpaca_configured else None
    market = MarketDataClient(s) if s.alpaca_configured else None
    fred = FredClient(s) if (s.fred_api_key and s.fred_api_key.get_secret_value()) else None

    if db is None:
        engine = make_engine(s.database_url)
        factory = make_session_factory(engine)
        db = factory()

    return ToolContext(
        alpaca=alpaca,
        market=market,
        fred=fred,
        db=db,
        confirmed=True,
    )


def build_mcp_server(
    ctx_factory: Callable[[], ToolContext] | None = None,
    name: str = "kubera",
    tool_filter: Callable[[str], bool] | None = None,
) -> FastMCP:
    """Construct a FastMCP server populated with tools from KUBERA's registry."""
    server = FastMCP(
        name=name,
        instructions=(
            "KUBERA is a personal financial research and portfolio-analysis assistant. "
            "All financial figures (returns, metrics, drawdowns, risk budgets) are computed "
            "by tested, deterministic backend code. Use the provided tools to fetch real data "
            "and market analysis."
        ),
    )

    get_ctx = ctx_factory or make_default_tool_context

    for tool_name, spec in registry._tools.items():
        if tool_filter and not tool_filter(tool_name):
            continue

        parameters = []
        annotations = {}
        for fname, f in spec.params_model.model_fields.items():
            default = (
                f.default
                if f.default is not None and f.default is not ...
                else (inspect.Parameter.empty if f.is_required() else None)
            )
            param = inspect.Parameter(
                fname,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=f.annotation,
            )
            parameters.append(param)
            annotations[fname] = f.annotation

        annotations["return"] = dict

        def _make_handler(t_name: str) -> Callable[..., dict]:
            def handler(*args: Any, **kwargs: Any) -> dict:
                ctx = get_ctx()
                try:
                    return registry.execute(t_name, kwargs, ctx)
                except ToolError as e:
                    raise MCPToolError(str(e)) from e
                except Exception as e:
                    log.exception("Unexpected error executing MCP tool %s", t_name)
                    raise MCPToolError(f"Internal error executing '{t_name}': {e}") from e

            return handler

        fn = _make_handler(tool_name)
        fn.__signature__ = inspect.Signature(parameters, return_annotation=dict)
        fn.__annotations__ = annotations
        fn.__name__ = tool_name
        fn.__doc__ = spec.description

        server.add_tool(fn, name=tool_name, description=spec.description)

    return server
