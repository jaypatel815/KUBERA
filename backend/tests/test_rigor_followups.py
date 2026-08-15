"""T064b — promotion expiry, stability surfacing, richer run_backtest output."""

import json
import math
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from test_alpaca import paper_settings

from api.tools import ToolContext, registry
from backtest.ledger import (
    PROMOTION_MAX_AGE_DAYS,
    attach_stability,
    is_promoted,
    latest_stability,
    promote_template,
)
from backtest.stability import run_sweep
from backtest.strategies import build_strategy
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import BacktestRun, Base


def rising_closes(n=260, drift=0.004):
    closes = [100.0]
    for _ in range(n - 1):
        closes.append(closes[-1] * math.exp(drift))
    return closes


def bars_json(closes):
    return {"symbol": "SPY", "next_page_token": None,
            "bars": [{"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
                      "o": 1, "h": 1, "l": 1, "c": c, "v": 1}
                     for i, c in enumerate(closes)]}


def market_fake(closes) -> MarketDataClient:
    body = bars_json(closes)
    return MarketDataClient(
        settings=paper_settings(),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)),
    )


@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def _promote(db, market):
    wf, row = promote_template(db, market, build_strategy("momentum"),
                               "momentum", "SPY", days=260)
    assert wf.passed
    return row


def test_promotion_expires(db):
    with market_fake(rising_closes()) as m:
        row = _promote(db, m)
    assert is_promoted(db, "momentum", "SPY")
    # backdate the pass beyond the expiry window
    row.ts = datetime.now(timezone.utc) - timedelta(days=PROMOTION_MAX_AGE_DAYS + 1)
    db.commit()
    assert not is_promoted(db, "momentum", "SPY")          # stale badge revoked
    assert is_promoted(db, "momentum", "SPY", max_age_days=10_000)  # explicit long leash
    assert PROMOTION_MAX_AGE_DAYS == 180


def test_latest_stability_roundtrip(db):
    with market_fake(rising_closes()) as m:
        _promote(db, m)
    assert latest_stability(db, "momentum", "SPY") is None  # none recorded yet
    closes = rising_closes()
    rep = run_sweep(closes, [f"d{i}" for i in range(len(closes))],
                    "momentum", values=[20, 40, 60])
    from dataclasses import asdict
    attach_stability(db, "momentum", "SPY", asdict(rep))
    stored = latest_stability(db, "momentum", "SPY")
    assert stored is not None and stored["verdict"] == rep.verdict
    assert latest_stability(db, "range", "SPY") is None     # other template: none


def test_run_backtest_tool_surfaces_rigor(db):
    with market_fake(rising_closes()) as m:
        out = registry.execute(
            "run_backtest", {"strategy": "buy_and_hold", "symbol": "SPY"},
            ToolContext(db=db, market=m),
        )
    t = out["trades"]
    assert t["n_trades"] >= 1
    assert t["win_rate"] is None or 0 <= t["win_rate"] <= 1
    assert out["calmar"] is None or out["calmar"] > 0      # monotone uptrend
    promo = out["promotion"]
    assert promo["is_promoted"] is False                   # no walk-forward run yet
    assert promo["stability"] is None
    assert "EXPIRES" in promo["note"] and "sweep.py" in promo["note"]
    # the ledger row exists with pending status
    row = db.get(BacktestRun, out["run_id"])
    assert row.promotion_status == "pending"
    assert json.loads(row.params_json)["template"] == "buy_and_hold"
