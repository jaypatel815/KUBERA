"""T093 — portfolio risk + CUSUM decay, every number hand-verified.

Hand computations:
- two assets, w=[.5,.5], vol=[.2,.2]:
    rho= 1 -> sigma_p = .2 ;  rho= 0 -> .2/sqrt(2) = .141421 ;  rho=-1 -> 0
- contributions with rho=0: each = .5*.2*.2*.5/.141421 = .01/.141421 = .070711
  (they sum to sigma_p exactly)
- effective bets: [.5,.5] -> 2 ; [1] -> 1 ; [.6,.2,.2] -> 1/(0.36+.04+.04)=2.2727
- CUSUM: mu=.001, slack=.0005, live returns all 0 -> S grows .0005/day;
  threshold .01 crossed on day 20 (0-indexed 19)
"""

import math

import httpx
import pytest
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings
from test_correlation import BASE_R, closes_from_returns

from analysis.portfolio_risk import (
    effective_bets,
    marginal_contributions,
    portfolio_risk,
    portfolio_volatility,
)
from api.tools import ToolContext, ToolError, registry
from backtest.decay import cusum_shortfall, demote, expected_daily_return
from backtest.ledger import is_promoted, promote_template
from backtest.strategies import build_strategy
from data.alpaca import AlpacaClient
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import Base

# --- portfolio vol ------------------------------------------------------------

W2, V2 = [0.5, 0.5], [0.2, 0.2]


def corr2(rho):
    return [[1.0, rho], [rho, 1.0]]


def test_vol_correlation_extremes():
    assert portfolio_volatility(W2, V2, corr2(1.0)) == pytest.approx(0.2)
    assert portfolio_volatility(W2, V2, corr2(0.0)) == pytest.approx(0.2 / math.sqrt(2))
    assert portfolio_volatility(W2, V2, corr2(-1.0)) == pytest.approx(0.0, abs=1e-9)


def test_vol_input_validation():
    with pytest.raises(ValueError):
        portfolio_volatility([0.5], V2, corr2(0))          # length mismatch
    with pytest.raises(ValueError):
        portfolio_volatility(W2, V2, [[1.0, 0.5], [0.4, 1.0]])  # asymmetric
    with pytest.raises(ValueError):
        portfolio_volatility(W2, V2, [[0.9, 0], [0, 1.0]])      # bad diagonal


def test_contributions_sum_to_portfolio_vol():
    mc = marginal_contributions(W2, V2, corr2(0.0))
    sigma = portfolio_volatility(W2, V2, corr2(0.0))
    assert mc[0] == pytest.approx(0.070711, rel=1e-4)
    assert sum(mc) == pytest.approx(sigma)
    # rho=1: each contributes half of 0.2
    mc1 = marginal_contributions(W2, V2, corr2(1.0))
    assert mc1 == pytest.approx([0.1, 0.1])


def test_effective_bets_hand_cases():
    assert effective_bets([0.5, 0.5]) == pytest.approx(2.0)
    assert effective_bets([1.0]) == pytest.approx(1.0)
    assert effective_bets([0.6, 0.2, 0.2]) == pytest.approx(2.2727, rel=1e-4)
    with pytest.raises(ValueError):
        effective_bets([0.0, 0.0])


def test_composer_flags_the_dominant_position():
    rep = portfolio_risk(["AAA", "BBB"], [0.9, 0.1], [0.3, 0.1], corr2(0.2))
    assert rep.contribution_fracs["AAA"] > 0.9
    assert any("one bet" in w for w in rep.warnings)
    assert rep.effective_bets == pytest.approx(1.22, abs=0.01)
    # perfectly diversifying book: no warning
    rep2 = portfolio_risk(["A", "B"], W2, V2, corr2(0.0))
    assert rep2.warnings == []
    assert rep2.diversification_ratio == pytest.approx(math.sqrt(2), rel=1e-3)


# --- CUSUM decay --------------------------------------------------------------

def test_expected_daily_return_hand_case():
    # +10% over 101 bars -> (1.1)^(1/100) - 1
    assert expected_daily_return(0.10, 101) == pytest.approx(1.1 ** 0.01 - 1)
    with pytest.raises(ValueError):
        expected_daily_return(0.1, 1)


def test_cusum_meeting_expectation_never_alarms():
    res = cusum_shortfall([0.001] * 60, mu_expected=0.001, slack=0.0005,
                          threshold=0.01)
    assert not res.alarm and res.stat == 0.0


def test_cusum_flat_reality_crosses_on_day_twenty():
    # shortfall accrues (0.001 - 0 - 0.0005) = 0.0005/day. Threshold 0.0102 sits
    # unambiguously between day-20's S=0.0100 and day-21's S=0.0105 (a threshold
    # exactly ON an accumulation boundary is fp-untestable — 20*0.0005 lands at
    # 0.010000000000000002).
    res = cusum_shortfall([0.0] * 25, mu_expected=0.001, slack=0.0005,
                          threshold=0.0102)
    assert res.alarm
    assert res.crossed_at == 20          # S=0.0105 on index 20 (21st day)
    assert res.series[19] == pytest.approx(0.01)   # below threshold: no alarm yet
    assert res.peak == pytest.approx(0.0125)


def test_cusum_recovery_resets_the_clock():
    # 10 bad days then strong days: statistic drains back to 0, no alarm
    live = [0.0] * 10 + [0.01] * 10
    res = cusum_shortfall(live, mu_expected=0.001, slack=0.0005, threshold=0.01)
    assert not res.alarm and res.stat == 0.0


def test_demote_flips_promotion_and_gate_refuses():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    closes = closes_from_returns([0.004] * 260)  # steady uptrend: promotable
    bars = {"symbol": "SPY", "next_page_token": None,
            "bars": [{"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
                      "o": 1, "h": 1, "l": 1, "c": c, "v": 1}
                     for i, c in enumerate(closes)]}
    market = MarketDataClient(
        settings=paper_settings(),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=bars)),
    )
    with make_session_factory(engine)() as db, market:
        wf, row = promote_template(db, market, build_strategy("momentum"),
                                   "momentum", "SPY", days=260)
        assert wf.passed and is_promoted(db, "momentum", "SPY")
        n = demote(db, "momentum", "SPY", "test decay alarm")
        assert n == 1
        assert not is_promoted(db, "momentum", "SPY")   # the gate now refuses
        with pytest.raises(ValueError):
            demote(db, "momentum", "SPY", "again")      # nothing left to demote
    engine.dispose()


# --- the tool -----------------------------------------------------------------

def test_portfolio_risk_tool_identical_holdings_are_one_bet():
    # every symbol gets the SAME closes -> corr 1.0 -> effective one bet
    closes = closes_from_returns(BASE_R * 4)  # 96 returns, plenty of history
    bars = {"symbol": "X", "next_page_token": None,
            "bars": [{"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
                      "o": 1, "h": 1, "l": 1, "c": c, "v": 1}
                     for i, c in enumerate(closes)]}

    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        if "/v2/positions" in request.url.path:
            return httpx.Response(200, json=POSITIONS_JSON)
        return httpx.Response(200, json=bars)

    transport = httpx.MockTransport(handler)
    with AlpacaClient(settings=paper_settings(), transport=transport) as a, \
         MarketDataClient(settings=paper_settings(), transport=transport) as m:
        out = registry.execute("get_portfolio_risk", {},
                               ToolContext(alpaca=a, market=m))
    n = len(out["symbols"])
    if n >= 2:
        # identical series: portfolio vol == weighted avg vol, div ratio ~1
        assert out["diversification_ratio"] == pytest.approx(1.0, abs=0.01)
    assert sum(out["contributions"].values()) == pytest.approx(
        out["portfolio_vol_ann"], rel=1e-3)
    assert out["asof"] and out["source"]


def test_portfolio_risk_tool_requires_positions():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        return httpx.Response(200, json=[])  # no positions

    transport = httpx.MockTransport(handler)
    with AlpacaClient(settings=paper_settings(), transport=transport) as a, \
         MarketDataClient(settings=paper_settings(), transport=transport) as m:
        with pytest.raises(ToolError) as exc:
            registry.execute("get_portfolio_risk", {},
                             ToolContext(alpaca=a, market=m))
    assert "empty book" in str(exc.value)
