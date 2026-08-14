"""T036 — fills sync (dedup proven), broker clock, market-hours guard, and the
entry delay ("never the open print") with sells exempt."""


import httpx
import pytest
from sqlalchemy import select
from test_alpaca import paper_settings
from test_paper_loop import BARS_JSON, FakeBroker, account_json, db, position_json  # noqa: F401

from backtest.paper_loop import run_paper_cycle
from data.alpaca import AlpacaClient
from data.fills import sync_fills
from data.market_data import MarketDataClient
from data.models import SignalLog, Transaction
from risk.engine import RiskEngine

FILLS_JSON = [
    {"id": "act-1", "activity_type": "FILL", "transaction_time": "2026-08-13T14:32:01.5Z",
     "type": "fill", "price": "179.05", "qty": "10", "side": "buy", "symbol": "SPY",
     "order_id": "ord-1"},
    {"id": "act-2", "activity_type": "FILL", "transaction_time": "2026-08-13T15:10:00Z",
     "type": "partial_fill", "price": "180.10", "qty": "5", "side": "sell",
     "symbol": "SPY", "order_id": "ord-2"},
]


def clock_json(is_open, ts="2026-08-13T13:40:00-04:00"):
    return {"timestamp": ts, "is_open": is_open,
            "next_open": "2026-08-14T09:30:00-04:00",
            "next_close": "2026-08-13T16:00:00-04:00"}


def alpaca_with(handler) -> AlpacaClient:
    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


# --- client parsing -----------------------------------------------------------

def test_get_fills_and_clock_parse():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/activities/FILL" in request.url.path:
            assert request.url.params["direction"] == "asc"
            return httpx.Response(200, json=FILLS_JSON)
        if "/v2/clock" in request.url.path:
            return httpx.Response(200, json=clock_json(True))
        return httpx.Response(200, json=account_json())

    with alpaca_with(handler) as a:
        fills = a.get_fills()
        clock = a.get_clock()
    assert len(fills) == 2
    assert fills[0].price == pytest.approx(179.05) and fills[0].qty == 10.0
    assert fills[0].occurred_at.tzinfo is not None
    assert fills[1].fill_type == "partial_fill" and fills[1].side == "sell"
    assert clock.is_open is True and clock.next_open.tzinfo is not None


# --- fills sync: dedup proven --------------------------------------------------

def test_sync_fills_inserts_then_dedups(db):  # noqa: F811
    def handler(request: httpx.Request) -> httpx.Response:
        if "/activities/FILL" in request.url.path:
            return httpx.Response(200, json=FILLS_JSON)
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=account_json())
        return httpx.Response(200, json=[])

    with alpaca_with(handler) as a:
        first = sync_fills(db, a)
        second = sync_fills(db, a)
    assert (first.inserted, first.skipped) == (2, 0)
    assert (second.inserted, second.skipped) == (0, 2)  # re-running is always safe
    rows = db.execute(select(Transaction)).scalars().all()
    assert len(rows) == 2
    assert {r.external_id for r in rows} == {"act-1", "act-2"}
    assert rows[0].occurred_at.tzinfo is not None


# --- market-hours guard + entry delay ------------------------------------------

class ClockBroker(FakeBroker):
    def __init__(self, is_open, ts="2026-08-13T13:40:00-04:00", **kw):
        super().__init__(**kw)
        self._clock = clock_json(is_open, ts)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if "/v2/clock" in request.url.path:
            return httpx.Response(200, json=self._clock)
        return super().__call__(request)


def run_hours_cycle(db, broker, strategy=None, **kwargs):  # noqa: F811
    strategy = strategy or (lambda closes: 1.0)
    strategy.__name__ = getattr(strategy, "__name__", "always_long")
    transport = httpx.MockTransport(broker)
    with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
         MarketDataClient(settings=paper_settings(), transport=transport) as market:
        return run_paper_cycle(db, alpaca, market, RiskEngine(), strategy, "SPY",
                               allocation_frac=0.15, enforce_market_hours=True,
                               **kwargs)


def test_closed_market_places_nothing(db):  # noqa: F811
    broker = ClockBroker(is_open=False)
    r = run_hours_cycle(db, broker)
    assert r.action == "no_action"
    assert "market closed" in r.detail and "queue for the open" in r.detail
    assert broker.order_posts == []
    row = db.execute(select(SignalLog)).scalar_one()
    assert row.source == "alpaca-clock"


def test_entry_delay_blocks_the_open_print(db):  # noqa: F811
    # broker clock 09:40 ET, delay 30 -> inside the window: buys are a no_trade
    broker = ClockBroker(is_open=True, ts="2026-08-13T09:40:00-04:00")
    r = run_hours_cycle(db, broker, entry_delay_minutes=30)
    assert r.action == "no_trade"
    assert "never the open print" in r.detail
    assert broker.order_posts == []


def test_after_the_delay_buys_proceed(db):  # noqa: F811
    broker = ClockBroker(is_open=True, ts="2026-08-13T10:31:00-04:00")
    r = run_hours_cycle(db, broker, entry_delay_minutes=30)
    assert r.action == "ordered"
    assert len(broker.order_posts) == 1


def test_sells_ignore_the_entry_delay(db):  # noqa: F811
    broker = ClockBroker(is_open=True, ts="2026-08-13T09:35:00-04:00",
                         positions=[position_json(qty=10.0, market_value=1790.0)])
    flat = lambda closes: 0.0  # noqa: E731
    flat.__name__ = "always_flat"
    r = run_hours_cycle(db, broker, strategy=flat, entry_delay_minutes=30)
    assert r.action == "ordered" and broker.order_posts[0]["side"] == "sell"


def test_entry_delay_validation(db):  # noqa: F811
    with pytest.raises(ValueError, match="entry_delay_minutes"):
        run_hours_cycle(db, ClockBroker(is_open=True), entry_delay_minutes=999)
