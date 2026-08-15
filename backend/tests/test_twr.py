"""T060 time-weighted returns — the deposit that must not look like skill.

The headline hand computation:
  Day1 1000 -> Day2 1100 (+10%), then +500 deposited on Day3 and the account
  ends Day3 at 1760.
    simple: 1760/1000 - 1 = +76%          <- a lie: 500 of that was a transfer
    TWR:    (1100/1000) * (1760/(1100+500)) - 1
          = 1.10 * 1.10 - 1 = +21%        <- what the strategy actually did
"""

from datetime import datetime, timezone

import httpx
import pytest
from test_alpaca import ACCOUNT_JSON, paper_settings

from analysis.twr import time_weighted_return
from api.tools import ToolContext, registry
from data.alpaca import AlpacaClient
from data.db import make_engine, make_session_factory
from data.flows import flow_history, sync_cash_flows
from data.market_data import MarketDataClient
from data.models import AccountSnapshot, Base, BrokerAccount, CashFlow

VALUES = [("2026-01-01", 1000.0), ("2026-01-02", 1100.0), ("2026-01-03", 1760.0)]


# --- pure math ----------------------------------------------------------------

def test_deposit_is_not_performance():
    r = time_weighted_return(VALUES, [("2026-01-03", 500.0)])
    assert r.simple_return_frac == pytest.approx(0.76)
    assert r.twr_frac == pytest.approx(0.21)          # 1.10 * 1.10 - 1
    assert r.net_flows == 500.0 and r.n_flows == 1
    assert "inflated" in r.note
    assert len(r.sub_periods) == 2
    assert r.sub_periods[1].flow == 500.0


def test_withdrawal_is_not_a_loss():
    # 1000 -> 1100 (+10%), withdraw 600, end 500 -> second leg 500/500 = 0%
    r = time_weighted_return(
        [("d1", 1000.0), ("d2", 1100.0), ("d3", 500.0)], [("d3", -600.0)])
    assert r.twr_frac == pytest.approx(0.10)
    assert r.simple_return_frac == pytest.approx(-0.50)  # the naive lie
    assert r.net_flows == -600.0


def test_no_flows_equals_simple_return():
    r = time_weighted_return([("d1", 1000.0), ("d2", 1200.0)])
    assert r.twr_frac == pytest.approx(r.simple_return_frac) == pytest.approx(0.2)
    assert "no external flows" in r.note
    assert r.n_flows == 0


def test_flows_outside_the_window_are_ignored_and_noted():
    r = time_weighted_return(VALUES, [("2025-12-01", 999.0), ("2030-01-01", 5.0)])
    assert r.n_flows == 0
    assert "outside the window ignored" in r.note


def test_flow_on_the_first_date_is_not_double_counted():
    # money already in the opening balance must not be subtracted again
    r = time_weighted_return(VALUES, [("2026-01-01", 250.0)])
    assert r.n_flows == 0
    assert r.twr_frac == pytest.approx(r.simple_return_frac)


def test_input_validation():
    with pytest.raises(ValueError):
        time_weighted_return([("d1", 100.0)])                     # too short
    with pytest.raises(ValueError):
        time_weighted_return([("d2", 100.0), ("d1", 90.0)])       # out of order
    with pytest.raises(ValueError):
        time_weighted_return([("d1", 0.0), ("d2", 10.0)])         # non-positive
    with pytest.raises(ValueError):  # withdrawal empties the base
        time_weighted_return([("d1", 100.0), ("d2", 50.0)], [("d2", -100.0)])


# --- client + sync ------------------------------------------------------------

CSD = [{"id": "dep1", "net_amount": "500", "date": "2026-01-03"}]
CSW = [{"id": "wd1", "net_amount": "-200", "date": "2026-01-05"}]


def alpaca_fake(seen: list | None = None) -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if seen is not None:
            seen.append(p)
        if "/activities/CSD" in p:
            return httpx.Response(200, json=CSD)
        if "/activities/CSW" in p:
            return httpx.Response(200, json=CSW)
        if "/v2/account" in p:
            return httpx.Response(200, json=ACCOUNT_JSON)
        return httpx.Response(200, json=[])
    return AlpacaClient(settings=paper_settings(),
                        transport=httpx.MockTransport(handler))


def test_cash_activities_normalize_signs():
    with alpaca_fake() as a:
        acts = a.get_cash_activities()
    by_kind = {x.kind: x for x in acts}
    assert by_kind["deposit"].amount == 500.0
    assert by_kind["withdrawal"].amount == -200.0     # always negative out
    assert acts[0].occurred_at < acts[1].occurred_at  # sorted


def test_sync_is_idempotent():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db, alpaca_fake() as a:
        first = sync_cash_flows(db, a)
        second = sync_cash_flows(db, a)
        assert first.inserted == 2 and first.skipped == 0
        assert second.inserted == 0 and second.skipped == 2   # dedup holds
        hist = flow_history(db)
        assert hist == [("2026-01-03", 500.0), ("2026-01-05", -200.0)]
    engine.dispose()


# --- the tool surfaces it -----------------------------------------------------

BARS = {"symbol": "SPY", "next_page_token": None,
        "bars": [{"t": f"2026-01-0{d}T04:00:00Z", "o": 1, "h": 1, "l": 1,
                  "c": c, "v": 1}
                 for d, c in ((1, 500.0), (2, 505.0), (3, 510.0))]}


def test_compare_benchmark_reports_twr_after_a_deposit():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    market = MarketDataClient(
        settings=paper_settings(),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=BARS)))
    with make_session_factory(engine)() as db, market:
        acct = BrokerAccount(broker="alpaca-paper", external_id="A1")
        db.add(acct)
        db.flush()
        for day, equity in ((1, 1000.0), (2, 1100.0), (3, 1760.0)):
            db.add(AccountSnapshot(
                account_id=acct.id, equity=equity, cash=0.0, buying_power=0.0,
                asof=datetime(2026, 1, day, 16, 0, tzinfo=timezone.utc),
                source="alpaca-paper"))
        db.add(CashFlow(account_id=acct.id, external_id="dep1", kind="deposit",
                        amount=500.0,
                        occurred_at=datetime(2026, 1, 3, 12, 0, tzinfo=timezone.utc),
                        source="alpaca-paper"))
        db.commit()
        out = registry.execute("compare_benchmark", {"symbol": "SPY", "days": 30},
                               ToolContext(db=db, market=market))
    tw = out["time_weighted"]
    assert tw["twr_frac"] == pytest.approx(0.21)
    assert tw["simple_return_frac"] == pytest.approx(0.76)
    assert tw["n_flows"] == 1 and tw["net_flows"] == 500.0
    # SPY 500 -> 510 = +2%; honest excess is 21% - 2%, not 76% - 2%
    assert tw["excess_vs_benchmark"] == pytest.approx(0.19, abs=1e-6)
    assert out["excess_return"] != pytest.approx(tw["excess_vs_benchmark"])
    engine.dispose()
