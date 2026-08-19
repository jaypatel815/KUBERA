"""T065 — sector exposure measurement + disable-symbol control."""

import pytest
from test_paper_loop import db  # noqa: F401

from analysis.sector_exposure import sector_exposure
from risk.engine import OrderRequest, RiskEngine
from risk.persistence import persist_risk_state, restore_risk_state

# ------------------------------------------------------ sector exposure


def test_sector_weights_hand_computed_with_warning():
    """60k tech / 30k energy / 10k unknown of 100k: tech 60% >= 40% warns;
    the unknown symbol is grouped and NAMED, never guessed."""
    positions = [("AAPL", 40_000.0), ("MSFT", 20_000.0),
                 ("XLE", 30_000.0), ("MYSTERY", 10_000.0)]
    sectors = {"AAPL": "Technology", "MSFT": "Technology",
               "XLE": "Energy", "MYSTERY": None}
    r = sector_exposure(positions, sectors)
    assert r.by_sector["Technology"] == pytest.approx(0.60)
    assert r.by_sector["Energy"] == pytest.approx(0.30)
    assert r.by_sector["unknown"] == pytest.approx(0.10)
    assert r.top_sector == "Technology" and r.top_frac == pytest.approx(0.60)
    assert any("Technology" in w and "bad day" in w for w in r.warnings)
    assert r.unknown_symbols == ["MYSTERY"]
    assert "measurement only" in r.note


def test_sector_below_warn_line_is_quiet_and_unknown_never_warns_as_top():
    """39% top sector: no concentration warning (line is 40%). An 'unknown'
    top sector must not trigger the concentration warning — it is a data gap,
    not a measured concentration."""
    r = sector_exposure([("A", 39.0), ("B", 31.0), ("C", 30.0)],
                        {"A": "Tech", "B": "Energy", "C": "Health"})
    assert not any("bad day" in w for w in r.warnings)
    r2 = sector_exposure([("A", 90.0), ("B", 10.0)], {"A": None, "B": "Tech"})
    assert r2.top_sector == "unknown"
    assert not any("bad day" in w for w in r2.warnings)
    assert any("no sector data" in w for w in r2.warnings)


def test_sector_empty_book():
    r = sector_exposure([], {})
    assert r.by_sector == {} and "no positive market value" in r.warnings[0]


# ------------------------------------------------- disable-symbol control


def eng(equity: float = 100_000.0) -> RiskEngine:
    e = RiskEngine()
    e.start_day(equity, "2026-08-19")
    return e


def test_disabled_symbol_refuses_buys_sells_exempt():
    e = eng()
    e.set_disabled_symbols(["tsla"])                 # case-normalised
    buy = e.pre_trade_check(OrderRequest(symbol="TSLA", side="buy", qty=10,
                                         est_price=100.0), 100_000.0, 0.0)
    assert not buy.approved
    assert any("DISABLED" in r for r in buy.reasons)
    sell = e.pre_trade_check(OrderRequest(symbol="TSLA", side="sell", qty=10,
                                          est_price=100.0), 100_000.0, 5_000.0)
    assert sell.approved                             # reducing risk: always
    other = e.pre_trade_check(OrderRequest(symbol="AAPL", side="buy", qty=1,
                                           est_price=100.0), 100_000.0, 0.0)
    assert other.approved


def test_disabled_symbols_survive_restart(db):  # noqa: F811
    """The T035 property extended: a restart must not forget the disable list."""
    e = eng()
    e.set_disabled_symbols(["GME", "TSLA"])
    persist_risk_state(db, e)

    fresh = RiskEngine()
    assert restore_risk_state(db, fresh) is True
    assert fresh.disabled_symbols == frozenset({"GME", "TSLA"})
    fresh.start_day(100_000.0, "2026-08-20")
    blocked = fresh.pre_trade_check(OrderRequest(symbol="GME", side="buy",
                                                 qty=1, est_price=20.0),
                                    100_000.0, 0.0)
    assert not blocked.approved


def test_corrupt_disabled_json_degrades_to_empty(db):  # noqa: F811
    e = eng()
    persist_risk_state(db, e)
    from data.models import RiskState
    row = db.get(RiskState, 1)
    row.disabled_symbols_json = "{not json"
    db.commit()
    fresh = RiskEngine()
    assert restore_risk_state(db, fresh) is True
    assert fresh.disabled_symbols == frozenset()     # empty, never a crash
