"""Backtest rigor + promotion gate (T064) — trade stats, Calmar, walk-forward all
hand-computed; promotion recorded in the ledger; the loop refuses unpromoted buys."""

import json
from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select
from test_alpaca import paper_settings
from test_paper_loop import BARS_JSON, FakeBroker, db, position_json  # noqa: F401
from test_strategies import CHOP, DATES

from backtest.engine import run_backtest
from backtest.ledger import is_promoted, promote_template
from backtest.paper_loop import run_paper_cycle
from backtest.stats import calmar, trade_excursions, trade_stats, walk_forward
from backtest.strategies import make_momentum, make_regime_router
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import BacktestRun, SignalLog

# --- trade stats: hand-computed -----------------------------------------------

def test_trade_stats_hand():
    weights = [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0]
    equity = [1.0, 1.0, 1.1, 1.21, 1.21, 1.21, 1.089]
    s = trade_stats(weights, equity)
    # trade 1: bars 2-3 -> 1.21/1.0 - 1 = +21%; trade 2: bar 6 -> 1.089/1.21 = -10%
    assert s.n_trades == 2
    assert s.trade_returns == [pytest.approx(0.21), pytest.approx(-0.10)]
    assert s.win_rate == pytest.approx(0.5)
    assert s.profit_factor == pytest.approx(2.1)  # 0.21 / 0.10
    assert s.avg_return_frac == pytest.approx(0.055)
    assert s.best_return_frac == pytest.approx(0.21)
    assert s.worst_return_frac == pytest.approx(-0.10)
    assert s.open_at_end is True  # the last trade never closed


def test_trade_stats_edges():
    empty = trade_stats([0.0, 0.0], [1.0, 1.0])
    assert empty.n_trades == 0 and empty.win_rate is None
    all_win = trade_stats([0.0, 1.0], [1.0, 1.1])
    assert all_win.profit_factor is None  # no losses to divide by
    with pytest.raises(ValueError, match="0/1"):
        trade_stats([0.5], [1.0])
    with pytest.raises(ValueError, match="equal length"):
        trade_stats([0.0], [1.0, 1.0])


def test_trade_excursions_hand():
    # one trade over bars 1-3: entry basis closes[0]=100; path [100, 95, 110]
    # MAE = 95/100-1 = -5%; MFE = +10%; return = +10% (a winner that dipped 5%)
    ex = trade_excursions([0.0, 1.0, 1.0, 1.0, 0.0],
                          [100.0, 100.0, 95.0, 110.0, 100.0])
    assert ex.n_trades == 1
    assert ex.per_trade[0]["mae"] == pytest.approx(-0.05)
    assert ex.per_trade[0]["mfe"] == pytest.approx(0.10)
    assert ex.per_trade[0]["return"] == pytest.approx(0.10)
    assert ex.winners_avg_mae_frac == pytest.approx(-0.05)  # the stop-calibration number
    assert "T036" in ex.note  # honesty: close-to-close until fills exist


def test_trade_excursions_no_trades_and_validation():
    assert trade_excursions([0.0, 0.0], [100.0, 100.0]).n_trades == 0
    with pytest.raises(ValueError, match="0/1"):
        trade_excursions([0.5], [100.0])


def test_sortino_and_omega_hand():
    from analysis.metrics import omega, sortino

    returns = [0.1, -0.05, 0.02, -0.01]
    # downside dev (target 0, full sample): sqrt((0.0025 + 0.0001)/4) = 0.0254951
    # mean 0.015 -> sortino (ppy=1) = 0.015/0.0254951 = 0.58835
    assert sortino(returns, periods_per_year=1) == pytest.approx(0.58835, abs=1e-4)
    # omega(0): gains 0.12 / shortfalls 0.06 = 2.0
    assert omega(returns) == pytest.approx(2.0)
    assert omega([0.1, 0.2]) is None  # no shortfalls: undefined, not infinite skill
    with pytest.raises(ValueError, match="no downside"):
        sortino([0.1, 0.2])


def test_calmar_hand():
    # cagr over 3 periods at ppy=3 = 21%; max DD = 1 - 0.99/1.1 = 10% -> 2.1
    assert calmar([1.0, 1.1, 0.99, 1.21], periods_per_year=3) == pytest.approx(2.1)
    assert calmar([1.0, 1.1, 1.2]) is None  # never drew down: undefined


# --- walk-forward: hand-computed + regime properties --------------------------

def test_walk_forward_hand():
    equity = [1.0, 1.1, 1.2, 1.3, 1.2, 1.3, 1.4, 1.5]
    wf = walk_forward(equity, n_segments=2)
    assert wf.segment_returns[0] == pytest.approx(0.3)          # 1.3/1.0 - 1
    assert wf.segment_returns[1] == pytest.approx(1.5 / 1.3 - 1)
    assert wf.non_negative_segments == 2
    assert wf.overall_return == pytest.approx(0.5)
    assert wf.passed is True


def test_walk_forward_fails_flat_and_losing_curves():
    flat = walk_forward([1.0] * 20, n_segments=4)
    assert flat.passed is False  # overall 0 is NOT > 0 — no free promotions
    losing = walk_forward([1.0 - 0.01 * i for i in range(20)], n_segments=4)
    assert losing.passed is False
    with pytest.raises(ValueError, match="segments"):
        walk_forward([1.0] * 20, n_segments=1)


def test_walk_forward_momentum_fails_on_chop_router_passes():
    mom = make_momentum(lookback=60)
    r_mom = run_backtest(CHOP, DATES, mom, mom.__name__)
    assert walk_forward(r_mom.equity_curve).passed is False  # flat: nothing earned

    router = make_regime_router(lookback=40, momentum_lookback=60)
    r_router = run_backtest(CHOP, DATES, router, router.__name__)
    assert walk_forward(r_router.equity_curve).passed is True


# --- promotion in the ledger --------------------------------------------------

def market_fake(bars_json: dict) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bars_json)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def _chop_json():
    return {"symbol": "SPY", "next_page_token": None, "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": c, "h": c + 0.5, "l": c - 0.5, "c": c, "v": 1}
        for i, c in enumerate(CHOP)
    ]}


def test_promote_template_records_verdicts(db):  # noqa: F811
    with market_fake(_chop_json()) as m:
        router = make_regime_router(lookback=40, momentum_lookback=60)
        wf, row = promote_template(db, m, router, "regime_router", "SPY")
        assert wf.passed and row.promotion_status == "passed_walk_forward"
        assert "segment_returns" in json.loads(row.params_json)

        mom = make_momentum(lookback=60)
        wf2, row2 = promote_template(db, m, mom, "momentum", "SPY")
        assert not wf2.passed and row2.promotion_status == "failed_walk_forward"

    assert is_promoted(db, "regime_router", "SPY") is True
    assert is_promoted(db, "momentum", "SPY") is False       # failed run
    assert is_promoted(db, "regime_router", "AAPL") is False  # promotion is per pair


# --- the loop enforces the gate -----------------------------------------------

def run_gated_cycle(db, broker, template, promoted_first=False):  # noqa: F811
    if promoted_first:
        db.add(BacktestRun(
            strategy=template, params_json=json.dumps({"template": template}),
            symbol="SPY", start_date="2026-01-01", end_date="2026-06-01",
            bars_count=100, cost_bps=5.0, cumulative_return=0.1,
            max_drawdown_frac=0.05, n_rebalances=4, total_cost_frac=0.001,
            source="test", promotion_status="passed_walk_forward",
            ts=datetime.now(timezone.utc),
        ))
        db.commit()
    strategy = lambda closes: 1.0  # noqa: E731
    strategy.__name__ = template
    transport = httpx.MockTransport(broker)
    from risk.engine import RiskEngine
    with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
         MarketDataClient(settings=paper_settings(), transport=transport) as market:
        return run_paper_cycle(db, alpaca, market, RiskEngine(), strategy, "SPY",
                               allocation_frac=0.15, require_promotion=True,
                               template=template)


def test_gate_refuses_unpromoted_buys(db):  # noqa: F811
    broker = FakeBroker()
    r = run_gated_cycle(db, broker, "always_long", promoted_first=False)
    assert r.action == "no_trade"
    assert "promotion gate" in r.detail and "promote.py" in r.detail
    assert broker.order_posts == []
    assert db.execute(select(SignalLog)).scalars().all()[-1].action == "no_trade"


def test_gate_admits_promoted_buys(db):  # noqa: F811
    broker = FakeBroker()
    r = run_gated_cycle(db, broker, "always_long", promoted_first=True)
    assert r.action == "ordered"
    assert len(broker.order_posts) == 1


def test_gate_never_blocks_sells(db):  # noqa: F811
    broker = FakeBroker(positions=[position_json(qty=10.0, market_value=1790.0)])
    flat = lambda closes: 0.0  # noqa: E731
    flat.__name__ = "always_flat"
    transport = httpx.MockTransport(broker)
    from risk.engine import RiskEngine
    with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
         MarketDataClient(settings=paper_settings(), transport=transport) as market:
        r = run_paper_cycle(db, alpaca, market, RiskEngine(), flat, "SPY",
                            require_promotion=True, template="always_flat")
    assert r.action == "ordered" and broker.order_posts[0]["side"] == "sell"
