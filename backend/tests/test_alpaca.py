"""Unit tests for the Alpaca client — no network; httpx.MockTransport only."""

import httpx
import pytest

from data.alpaca import PAPER_BASE_URL, AlpacaClient, AlpacaError
from settings import ConfigError, KuberaSettings

ACCOUNT_JSON = {
    "account_number": "PA1TEST23",
    "status": "ACTIVE",
    "currency": "USD",
    "cash": "25000.50",
    "equity": "100000.75",
    "buying_power": "200001.50",
}

POSITIONS_JSON = [
    {
        "symbol": "AAPL",
        "qty": "10",
        "avg_entry_price": "150.25",
        "current_price": "165.10",
        "market_value": "1651.00",
        "cost_basis": "1502.50",
        "unrealized_pl": "148.50",
        "unrealized_plpc": "0.0988",
    }
]


def paper_settings(**overrides) -> KuberaSettings:
    values = {
        "alpaca_api_key_id": "PKTEST123",
        "alpaca_api_secret_key": "testsecret",
        "alpaca_paper": True,
        **overrides,
    }
    return KuberaSettings(_env_file=None, **values)


def make_client(handler) -> AlpacaClient:
    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_get_account_parses_and_timestamps():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{PAPER_BASE_URL}/v2/account"
        assert request.headers["APCA-API-KEY-ID"] == "PKTEST123"
        return httpx.Response(200, json=ACCOUNT_JSON)

    with make_client(handler) as c:
        acct = c.get_account()
    assert acct.equity == pytest.approx(100000.75)
    assert acct.cash == pytest.approx(25000.50)
    assert acct.status == "ACTIVE"
    assert acct.external_id == "PA1TEST23"
    assert acct.source == "alpaca-paper"
    assert acct.asof.tzinfo is not None


def test_get_positions_parses():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=POSITIONS_JSON)

    with make_client(handler) as c:
        positions = c.get_positions()
    assert len(positions) == 1
    p = positions[0]
    assert p.symbol == "AAPL"
    assert p.qty == 10
    assert p.unrealized_pl == pytest.approx(148.50)
    assert p.asof.tzinfo is not None


def test_401_gives_actionable_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "unauthorized"})

    with make_client(handler) as c, pytest.raises(AlpacaError) as exc:
        c.get_account()
    assert "401" in str(exc.value)
    assert ".env" in str(exc.value)


def test_live_endpoint_is_refused_by_code():
    """The §7.4 rail: no code path to real capital exists."""
    with pytest.raises(ConfigError) as exc:
        AlpacaClient(settings=paper_settings(alpaca_paper=False))
    assert "7.4" in str(exc.value)


def test_missing_keys_fail_fast():
    unconfig = KuberaSettings(_env_file=None, alpaca_api_key_id=None, alpaca_api_secret_key=None)
    with pytest.raises(ConfigError):
        AlpacaClient(settings=unconfig)


def test_place_order_posts_and_parses():
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/orders" and request.method == "POST":
            import json
            posts.append(json.loads(request.content))
            return httpx.Response(200, json={"id": "abc-1", "symbol": "SPY", "qty": "5",
                                             "side": "buy", "status": "accepted"})
        return httpx.Response(404, json={})

    with make_client(handler) as c:
        result = c.place_order("spy", "buy", 5)
    assert posts[0] == {"symbol": "SPY", "qty": "5", "side": "buy",
                        "type": "market", "time_in_force": "day"}
    assert result.external_id == "abc-1"
    assert result.status == "accepted"
    assert result.asof.tzinfo is not None


def test_place_order_validates_inputs():
    with make_client(lambda r: httpx.Response(200, json={})) as c:
        with pytest.raises(ValueError):
            c.place_order("SPY", "hold", 5)
        with pytest.raises(ValueError):
            c.place_order("SPY", "buy", 0)
