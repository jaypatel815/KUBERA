"""Unit tests for KUBERA MCP Server (T045, D011)."""

import asyncio
import json

import httpx
import pytest
from mcp.server.fastmcp.exceptions import ToolError as MCPToolError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings
from test_market_data import BARS_JSON, QUOTE_JSON, TRADE_JSON

from api.mcp_server import build_mcp_server, make_default_tool_context
from api.tools import ToolContext, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import Base


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


def test_server_registers_all_registry_tools():
    async def run():
        server = build_mcp_server()
        tools = await server.list_tools()
        registered_names = {t.name for t in tools}
        expected_names = set(registry.names())

        assert registered_names == expected_names
        assert len(registered_names) >= 30

    asyncio.run(run())


def test_server_tool_filter():
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
            confirmed=True,
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


def test_make_default_tool_context(memory_db):
    ctx = make_default_tool_context(db=memory_db)
    assert ctx.db is memory_db
    assert ctx.confirmed is True
