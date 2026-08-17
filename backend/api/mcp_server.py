"""KUBERA Model Context Protocol (MCP) Server (T045, D011).

Exposes KUBERA's deterministic tool registry (T024) over standard MCP (stdio)
so external frontends (Claude Desktop, Antigravity, MCP inspectors) can interact
with KUBERA's research, analysis, and portfolio intelligence.

Safety & Determinism rails:
- Read-only by default. `build_mcp_server()` with no arguments exposes only the
  read-only analysis and portfolio intelligence tools (see READ_ONLY_TOOLS).
- Confirmation-gated tools (update_ips) are excluded from the default set.
  Pass `allow_mutations=True` ONLY when the caller has provided an out-of-band
  confirmation mechanism (never from model output — tools.py:110).
- No direct trade execution or order modification (D011).
- Every financial figure is computed deterministically in tested code.

Integration (add to Claude Desktop config):
    {
      "mcpServers": {
        "kubera": {
          "command": "python",
          "args": ["<path-to-kubera>/scripts/mcp_server.py"]
        }
      }
    }
"""

from __future__ import annotations

import inspect
import logging
from contextlib import contextmanager
from typing import Any, Callable, Iterator

from api.tools import ToolContext, ToolError, registry
from settings import KuberaSettings, get_settings

log = logging.getLogger("kubera.mcp")

# Tools that are safe to expose by default over MCP.
# These are read-only: they fetch, compute, and analyse without writing state.
# Mutation tools (update_ips, record_decision, mark_decision, update_watchlist)
# are excluded by default and must be explicitly opted-in via allow_mutations=True.
# This is the authoritative list — update it when new read-only tools are added.
_READ_ONLY_TOOLS: frozenset[str] = frozenset({
    "compare_benchmark",
    "estimate_risk_tolerance",
    "get_attribution",
    "get_breakouts",
    "get_brief",
    "get_confluence",
    "get_correlation",
    "get_daily_bars",
    "get_execution_quality",
    "get_exit_plan",
    "get_expected_move",
    "get_intraday",
    "get_ips",
    "get_journal",
    "get_latest",
    "get_levels",
    "get_liquidity",
    "get_macro_context",
    "get_news",
    "get_open_excursions",
    "get_portfolio",
    "get_portfolio_risk",
    "get_regime",
    "get_risk_status",
    "get_symbol_briefing",
    "get_trading_autopsy",
    "get_watchlist",
    "goal_math",
    "run_backtest",
    "size_position",
    "triage_position",
})


def make_default_tool_context(
    settings: KuberaSettings | None = None,
    db: Any | None = None,
) -> ToolContext:
    """Build a standard ToolContext from environment settings.

    confirmed is always False here — the MCP protocol has no out-of-band
    confirmation channel, so confirmation-gated tools must not be reached via
    the default context. The default tool_filter already excludes them, but this
    is the defense-in-depth layer: even if a caller bypasses the filter, the
    registry's own gate (tools.py:178) will still reject the call.
    """
    from data.alpaca import AlpacaClient
    from data.db import make_engine, make_session_factory
    from data.market_data import MarketDataClient

    s = settings or get_settings()
    alpaca = AlpacaClient(s) if s.alpaca_configured else None
    market = MarketDataClient(s) if s.alpaca_configured else None
    fred: Any | None = None
    try:
        from data.fred import FredClient
        fred = FredClient(s) if (s.fred_api_key and s.fred_api_key.get_secret_value()) else None
    except Exception:
        fred = None

    if db is None:
        engine = make_engine(s.database_url)
        factory = make_session_factory(engine)
        db = factory()

    return ToolContext(
        alpaca=alpaca,
        market=market,
        fred=fred,
        db=db,
        confirmed=False,  # never True here — no out-of-band confirmation over MCP (I021)
    )


def close_tool_context(ctx: ToolContext) -> None:
    """Close every resource a context owns. Failures are logged, never raised —
    a close() error must not mask the tool's real result or exception (T106).

    Uses getattr rather than isinstance so it works for any client that follows
    the close() convention, including test fakes and future brokers.
    """
    for name in ("alpaca", "market", "fred", "db"):
        resource = getattr(ctx, name, None)
        close = getattr(resource, "close", None)
        if callable(close):
            try:
                close()
            except Exception:                      # noqa: BLE001 — log and continue
                log.warning("close() failed for ToolContext.%s", name, exc_info=True)


@contextmanager
def managed_tool_context(
    factory: Callable[[], ToolContext] | None = None,
) -> Iterator[ToolContext]:
    """The per-call lifecycle (T106): build, yield, ALWAYS close.

    Before this existed, every MCP tool call from a long-lived Claude Desktop
    session opened an Alpaca client, a market-data client, a FRED client and a
    DB session and closed none of them — a socket and file-handle leak that grew
    with every question the owner asked. The context manager makes the close
    unconditional, including on the exception path.
    """
    ctx = (factory or make_default_tool_context)()
    try:
        yield ctx
    finally:
        close_tool_context(ctx)


def build_mcp_server(
    ctx_factory: Callable[[], ToolContext] | None = None,
    name: str = "kubera",
    tool_filter: Callable[[str], bool] | None = None,
    allow_mutations: bool = False,
) -> Any:
    """Construct a FastMCP server populated with tools from KUBERA's registry.

    By default exposes only the read-only tool subset (_READ_ONLY_TOOLS).
    Set allow_mutations=True to additionally expose state-mutating tools
    (record_decision, mark_decision, update_watchlist). The confirmation-gated
    update_ips tool is NEVER exposed over MCP regardless — it requires the owner's
    explicit out-of-band confirmation which MCP cannot provide (I021, tools.py:110).

    If tool_filter is provided it takes precedence over allow_mutations.
    """
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.exceptions import ToolError as MCPToolError

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

    def _default_filter(t_name: str) -> bool:
        if allow_mutations:
            # Mutating tools allowed, but never the confirmation-gated update_ips
            # (requires out-of-band owner confirmation that MCP cannot provide).
            return not registry.requires_confirmation(t_name)
        return t_name in _READ_ONLY_TOOLS

    active_filter = tool_filter if tool_filter is not None else _default_filter

    for tool_name, spec in registry._tools.items():  # noqa: SLF001
        if not active_filter(tool_name):
            continue

        parameters = []
        annotations: dict[str, Any] = {}
        for fname, f in spec.params_model.model_fields.items():
            # A required field's default value is handled by checking is_required(),
            # so the 'is not None' check would pass incorrectly.
            default = (
                inspect.Parameter.empty if f.is_required()
                else f.default
            )
            param = inspect.Parameter(
                fname,
                inspect.Parameter.KEYWORD_ONLY,  # FastMCP calls by keyword; be honest
                default=default,
                annotation=f.annotation,
            )
            parameters.append(param)
            annotations[fname] = f.annotation

        annotations["return"] = dict

        def _make_handler(t_name: str) -> Callable[..., dict]:
            def handler(**kwargs: Any) -> dict:
                # T106: build-per-call is deliberate (a stale shared client would
                # serve yesterday's session to today's question) but it only
                # works if every call CLOSES what it opened — which this now
                # guarantees, on the success and exception paths alike.
                with managed_tool_context(get_ctx) as ctx:
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
