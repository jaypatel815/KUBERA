"""Unit tests for KUBERA MCP Server (T045, D011).

Guard: all tests require mcp.server.fastmcp (pinned mcp>=1.29,<2 in requirements.txt).
If the optional dep is absent the whole module is skipped — keeps CI green on a bare
checkout before `pip install -r backend/requirements.txt` (I022).
"""

import asyncio
import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings
from test_market_data import BARS_JSON, QUOTE_JSON, TRADE_JSON

# I022: guard module-level import so CI does not abort collection when mcp is absent.
fastmcp = pytest.importorskip("mcp.server.fastmcp", reason="mcp>=1.29,<2 not installed")
MCPToolError = pytest.importorskip(
    "mcp.server.fastmcp.exceptions", reason="mcp>=1.29,<2 not installed"
).ToolError

from api.mcp_server import (  # noqa: E402
    _READ_ONLY_TOOLS,
    build_mcp_server,
    make_default_tool_context,
)
from api.tools import ToolContext, registry  # noqa: E402
from data.alpaca import AlpacaClient  # noqa: E402
from data.market_data import MarketDataClient  # noqa: E402
from data.models import Base  # noqa: E402


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sm = sessionmaker(bind=engine, expire_on_commit=False)
    session = sm()
    try:
        yield session
    finally:
        session.close()


def alpaca_fake() -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        if "/v2/positions" in request.url.path:
            return httpx.Response(200, json=POSITIONS_JSON)
        if "/v2/clock" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "is_open": True,
                    "next_open": "2026-08-17T09:30:00-04:00",
                    "next_close": "2026-08-17T16:00:00-04:00",
                    "timestamp": "2026-08-16T12:00:00-04:00",
                },
            )
        return httpx.Response(200, json={})

    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def market_fake() -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "trades/latest" in request.url.path:
            return httpx.Response(200, json=TRADE_JSON)
        if "quotes/latest" in request.url.path:
            return httpx.Response(200, json=QUOTE_JSON)
        if "bars" in request.url.path:
            return httpx.Response(200, json=BARS_JSON)
        return httpx.Response(200, json={})

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_server_registers_all_read_only_tools_by_default():
    """By default the server exposes the read-only subset, not the full registry (I021)."""
    async def run():
        server = build_mcp_server()
        tools = await server.list_tools()
        registered_names = {t.name for t in tools}

        # Must be exactly the read-only set
        assert registered_names == _READ_ONLY_TOOLS
        # Confirmation-gated tools must not appear
        assert "update_ips" not in registered_names
        # State-mutating tools excluded by default
        assert "record_decision" not in registered_names
        assert "mark_decision" not in registered_names
        assert "update_watchlist" not in registered_names

    asyncio.run(run())


def test_allow_mutations_excludes_gated_tools():
    """allow_mutations=True adds record/mark/watchlist but never the gated update_ips."""
    async def run():
        server = build_mcp_server(allow_mutations=True)
        tools = await server.list_tools()
        registered_names = {t.name for t in tools}

        # The confirmation-gated tool must still be absent
        assert "update_ips" not in registered_names
        # Mutating but non-gated tools should now appear
        assert "record_decision" in registered_names
        assert "mark_decision" in registered_names
        assert "update_watchlist" in registered_names

    asyncio.run(run())


def test_explicit_tool_filter_overrides_defaults():
    """When tool_filter is provided it overrides the allow_mutations default."""
    async def run():
        server = build_mcp_server(tool_filter=lambda n: n in {"get_latest", "goal_math"})
        tools = await server.list_tools()
        assert {t.name for t in tools} == {"get_latest", "goal_math"}

    asyncio.run(run())


def test_server_tool_metadata():
    async def run():
        server = build_mcp_server()
        tools = await server.list_tools()
        latest_tool = next(t for t in tools if t.name == "get_latest")

        assert latest_tool.description == registry._tools["get_latest"].description
        assert "symbol" in latest_tool.inputSchema["properties"]
        assert "symbol" in latest_tool.inputSchema["required"]

    asyncio.run(run())


def test_execute_goal_math_pure():
    async def run():
        server = build_mcp_server()
        res = await server.call_tool(
            "goal_math",
            {
                "start": 10000.0,
                "target": 25000.0,
                "monthly_contribution": 500.0,
                "annual_return_frac": 0.08,
            },
        )
        assert len(res) == 1
        data = json.loads(res[0].text)
        assert "scenarios" in data
        assert data["scenarios"]["start"] == 10000.0
        assert data["scenarios"]["target"] == 25000.0

    asyncio.run(run())


def test_execute_with_custom_context(memory_db):
    async def run():
        fake_ctx = ToolContext(
            alpaca=alpaca_fake(),
            market=market_fake(),
            db=memory_db,
            confirmed=False,  # confirmed=False — read-only tools do not need it (I021)
        )
        server = build_mcp_server(ctx_factory=lambda: fake_ctx)

        # Test get_latest
        latest_res = await server.call_tool("get_latest", {"symbol": "AAPL"})
        latest_data = json.loads(latest_res[0].text)
        assert latest_data["trade"]["symbol"] == "AAPL"
        assert latest_data["trade"]["price"] == 229.83

        # Test get_portfolio
        port_res = await server.call_tool("get_portfolio", {})
        port_data = json.loads(port_res[0].text)
        assert port_data["account"]["equity"] == 100000.75
        assert port_data["positions"][0]["symbol"] == "AAPL"

        # Test get_daily_bars
        bars_res = await server.call_tool("get_daily_bars", {"symbol": "AAPL", "days": 5})
        bars_data = json.loads(bars_res[0].text)
        assert bars_data["symbol"] == "AAPL"
        assert len(bars_data["bars"]) == 2

    asyncio.run(run())


def test_tool_error_surfaced_cleanly():
    async def run():
        server = build_mcp_server()
        with pytest.raises(MCPToolError) as exc_info:
            # get_latest without broker/context raises ToolError
            await server.call_tool("get_latest", {"symbol": "INVALID"})
        err_msg = str(exc_info.value).lower()
        assert "market data feed not configured" in err_msg or "error" in err_msg

    asyncio.run(run())


def test_make_default_tool_context_has_confirmed_false(memory_db):
    """I021: the default context must never hardcode confirmed=True."""
    ctx = make_default_tool_context(db=memory_db)
    assert ctx.db is memory_db
    assert ctx.confirmed is False, (
        "confirmed must remain False in the default context — the MCP protocol "
        "has no out-of-band confirmation channel (I021, tools.py:110)"
    )
