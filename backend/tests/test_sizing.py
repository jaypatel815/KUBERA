"""ATR + vol-parity sizing (T078) — every number hand-computed, plus the paper loop
shrinking a buy in a volatile market and refusing to size a buy on thin history."""

import httpx
import pytest
from sqlalchemy import select
from test_alpaca import paper_settings
from test_paper_loop import FakeBroker, db  # noqa: F401  (fixture reuse)

from analysis.metrics import atr, true_ranges
from backtest.paper_loop import run_paper_cycle
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import SignalLog
from risk.engine import RiskEngine, RiskLimits
from risk.sizing import volatility_parity_notional

# --- true range / ATR: hand-computed -----------------------------------------

HIGHS = [101.0, 103.0, 102.0, 104.0, 105.0]
LOWS = [99.0, 100.0, 100.0, 102.0, 103.0]
CLOSES = [100.0, 102.0, 101.0, 103.0, 104.0]


def test_true_ranges_hand():
    # i1: max(103-100, |103-100|, |100-100|) = 3
    # i2: max(102-100, |102-102|, |100-102|) = 2
    # i3: max(104-102, |104-101|,  |102-101|) = 3
    # i4: max(105-103, |105-103|, |103-103|) = 2
    assert true_ranges(HIGHS, LOWS, CLOSES) == [3.0, 2.0, 3.0, 2.0]


def test_atr_wilder_hand():
    # seed = mean(3,2,3) = 8/3; next = (8/3 * 2 + 2) / 3 = 22/9
    assert atr(HIGHS, LOWS, CLOSES, window=3) == pytest.approx(22 / 9)


def test_atr_constant_tr_is_that_tr():
    closes = [100.0 + i for i in range(20)]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    assert atr(highs, lows, closes, window=14) == pytest.approx(2.0)


@pytest.mark.parametrize(
    "highs, lows, closes, match",
    [
        (HIGHS[:4], LOWS, CLOSES, "equal length"),
        (HIGHS[:2], LOWS[:2], CLOSES[:2], "at least 4 bars|need at least"),
        ([101.0, 90.0], [99.0, 100.0], [100.0, 95.0], "low"),
        ([101.0, -1.0], [99.0, -2.0], [100.0, 95.0], "> 0"),
    ],
)
def test_atr_bad_input(highs, lows, closes, match):
    with pytest.raises(ValueError, match=match):
        atr(highs, lows, closes, window=3)


# --- vol-parity arithmetic: hand-computed ------------------------------------

def test_sizer_binds_when_volatility_is_high():
    # risk$ = 100k * 1% = 1000; stop = 2 * ATR 4 = 8; qty_risk = 125; @100 -> 12,500
    s = volatility_parity_notional(
        100_000.0, 100.0, 4.0, 20_000.0, risk_frac=0.01, stop_atr_multiple=2.0
    )
    assert s.risk_dollars == pytest.approx(1_000.0)
    assert s.stop_distance == pytest.approx(8.0)
    assert s.risk_notional == pytest.approx(12_500.0)
    assert s.allowed_notional == pytest.approx(12_500.0)
    assert s.binding == "risk"


def test_sizer_leaves_small_requests_alone():
    s = volatility_parity_notional(
        100_000.0, 100.0, 4.0, 10_000.0, risk_frac=0.01, stop_atr_multiple=2.0
    )
    assert s.allowed_notional == pytest.approx(10_000.0)
    assert s.binding == "request"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"equity": 0.0}, {"price": -1.0}, {"atr_value": 0.0},
        {"requested_notional": -1.0}, {"risk_frac": 0.0}, {"risk_frac": 1.0},
        {"stop_atr_multiple": 0.0},
    ],
)
def test_sizer_bad_input(kwargs):
    base = dict(equity=100_000.0, price=100.0, atr_value=4.0,
                requested_notional=10_000.0, risk_frac=0.01, stop_atr_multiple=2.0)
    base.update(kwargs)
    with pytest.raises(ValueError):
        volatility_parity_notional(
            base["equity"], base["price"], base["atr_value"],
            base["requested_notional"], risk_frac=base["risk_frac"],
            stop_atr_multiple=base["stop_atr_multiple"],
        )


@pytest.mark.parametrize(
    "bad", [{"risk_per_trade_frac": 0.0}, {"risk_per_trade_frac": 0.06},
            {"stop_atr_multiple": 0.0}, {"stop_atr_multiple": 11.0}]
)
def test_risk_limits_sizing_band(bad):
    with pytest.raises(ValueError):
        RiskLimits(**bad)


# --- the loop actually shrinks a volatile buy --------------------------------

# closes whipsaw 159/199 (prev-close jumps of 40, H/L margins ±1) -> TR = 41 every
# bar -> Wilder ATR = 41 exactly. risk$ 1000 / stop 82 = 12.195 shares; the series
# ends on the 199 leg (odd final index) so last_price = 199; strategy asks 15,000.
VOLATILE_BARS = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": c, "h": c + 1.0, "l": c - 1.0, "c": c, "v": 1}
        for i in range(80)
        for c in [199.0 if i % 2 == 1 else 159.0]
    ],
}
assert VOLATILE_BARS["bars"][-1]["c"] == 199.0  # final index 79 is odd: the high leg

THIN_BARS = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        {"t": f"2026-01-{i + 1:02d}T04:00:00Z",
         "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "v": 1}
        for i in range(10)  # < ATR_WINDOW + 1 = 15
    ],
}


def run_cycle_with_bars(db, bars_json, allocation=0.15):  # noqa: F811
    broker = FakeBroker()
    always_long = lambda closes: 1.0  # noqa: E731
    always_long.__name__ = "always_long"

    def handler(request: httpx.Request) -> httpx.Response:
        if "/bars" in request.url.path:
            return httpx.Response(200, json=bars_json)
        return broker(request)

    transport = httpx.MockTransport(handler)
    with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
         MarketDataClient(settings=paper_settings(), transport=transport) as market:
        result = run_paper_cycle(db, alpaca, market, RiskEngine(), always_long, "SPY",
                                 allocation_frac=allocation)
    return result, broker


def test_loop_shrinks_buy_in_volatile_market(db):  # noqa: F811
    r, broker = run_cycle_with_bars(db, VOLATILE_BARS)
    assert r.action == "ordered"
    # target stays 15,000 (what the strategy WANTED)…
    assert r.target_value == pytest.approx(15_000.0)
    # …but the order is the vol-parity qty: 1000 / (2*41) = 12.195
    assert float(broker.order_posts[0]["qty"]) == pytest.approx(1000 / 82, abs=1e-3)
    assert "vol-parity sizing bound the buy" in r.detail
    row = db.execute(select(SignalLog)).scalar_one()
    assert row.action == "ordered"
    assert "vol-parity" in (row.reasons or "")


def test_loop_refuses_buy_on_thin_history(db):  # noqa: F811
    r, broker = run_cycle_with_bars(db, THIN_BARS)
    assert r.action == "no_action"
    assert "insufficient history for ATR" in r.detail
    assert broker.order_posts == []  # fail closed: nothing reached the broker
