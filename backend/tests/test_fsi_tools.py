"""T117/T118 tool integration — the two FSI-review adoptions, end to end."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from test_paper_loop import db  # noqa: F401

from api.tools import ToolContext, ToolError, registry
from data.models import Transaction

NOW = datetime(2026, 8, 10, 14, 30, tzinfo=timezone.utc)


def _txn(db_, ext, symbol, side, qty, price, when=NOW):  # noqa: ANN001
    db_.add(Transaction(account_id=1, external_id=ext, symbol=symbol,
                        side=side, qty=qty, price=price, occurred_at=when,
                        source="t"))


class _Market:
    def __init__(self, prices):
        self._p = prices

    def get_latest_trade(self, symbol):
        p = self._p.get(symbol)
        if p is None:
            raise RuntimeError(f"no trade for {symbol}")
        return SimpleNamespace(price=p)


def test_tlh_scan_tool_end_to_end(db):  # noqa: F811
    # open lots after FIFO: AAA 10@100 (loss at 90), BBB 5@50 (gain at 60),
    # and a recent AAA rebuy that must trip the wash lookback.
    _txn(db, "e1", "AAA", "buy", 10, 100.0,
         datetime(2026, 6, 1, tzinfo=timezone.utc))
    _txn(db, "e2", "BBB", "buy", 5, 50.0,
         datetime(2026, 5, 1, tzinfo=timezone.utc))
    _txn(db, "e3", "AAA", "buy", 2, 92.0,
         datetime(2026, 8, 5, tzinfo=timezone.utc))   # inside 30d lookback
    db.commit()

    out = registry.execute("get_tlh_scan", {},
                           ToolContext(db=db, market=_Market(
                               {"AAA": 90.0, "BBB": 60.0})))
    assert "NOT TAX ADVICE" in out["limitations"]
    syms = [c["symbol"] for c in out["candidates"]]
    assert "AAA" in syms and "BBB" not in syms          # gains skipped
    aaa = [c for c in out["candidates"] if c["symbol"] == "AAA"]
    # both AAA lots are losses; each carries the wash flag from the 08-05 buy
    assert all(c["wash_lookback_flag"] and "2026-08-05"
               in c["wash_lookback_flag"] for c in aaa)
    # 10*(90-100) + 2*(90-92) = -104
    assert out["total_harvestable_loss"] == pytest.approx(-104.0)
    assert out["n_gains_skipped"] == 1


def test_tlh_scan_refuses_without_fills(db):  # noqa: F811
    with pytest.raises(ToolError, match="no recorded fills"):
        registry.execute("get_tlh_scan", {},
                         ToolContext(db=db, market=_Market({})))


def test_earnings_preview_composes_with_named_absences(db):  # noqa: F811
    from datetime import date, timedelta

    d0 = date(2025, 1, 2)
    dates = [(d0 + timedelta(days=i)).isoformat() for i in range(300)]
    closes = [100.0 * (1 + 0.001 * i) for i in range(300)]
    bars = SimpleNamespace(
        bars=[SimpleNamespace(close=c, date=d, high=c, low=c, volume=1)
              for c, d in zip(closes, dates)],
        asof=datetime(2026, 8, 20, tzinfo=timezone.utc), source="fake")

    market = SimpleNamespace(get_daily_bars=lambda s, days: bars)
    out = registry.execute("get_earnings_preview", {"symbol": "spy"},
                           ToolContext(db=db, market=market))
    assert out["symbol"] == "SPY"
    # no FMP -> the absence is NAMED, never guessed
    assert out["next_report"] is None
    assert "not configured" in out["next_report_note"]
    # no observed events -> base rates degrade to available:false with why
    assert out["base_rates"]["available"] is False
    assert "no observed past earnings" in out["base_rates"]["why"]
    # the distribution lens still answers
    assert out["expected_move_1d"]["horizons"][0]["available"] is True
    assert out["runup_5d_frac"] == pytest.approx(
        closes[-1] / closes[-6] - 1.0)
    assert out["position"] is None                     # no alpaca in ctx
    assert "not options-implied" in out["note"]
