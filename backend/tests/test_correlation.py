"""Correlation & overlap guard (T079) — every statistic hand-verified.

Key hand computations:
- pearson of y=2x is exactly 1.0; of y=-x is exactly -1.0
- xs=[.01,-.01,.02,-.02] vs ys=[.01,.01,-.01,-.01]: both means 0, cov terms
  (+.0001, -.0001, -.0002, +.0002) sum to 0 -> corr exactly 0.0
- asset returns = 2 * bench returns -> beta exactly 2.0
"""

import math

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings

from analysis.correlation import (
    HIGH_CORR,
    MIN_OVERLAP,
    beta,
    log_returns,
    overlap_report,
    pearson,
)
from api.main import app, get_alpaca_client, get_market_client
from api.tools import ToolContext, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient

client = TestClient(app)


def closes_from_returns(returns, start=100.0):
    closes = [start]
    for r in returns:
        closes.append(closes[-1] * math.exp(r))
    return closes


# --- primitives ---------------------------------------------------------------

def test_pearson_perfect_and_inverse():
    assert pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert pearson([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_pearson_hand_computed_zero():
    assert pearson([0.01, -0.01, 0.02, -0.02],
                   [0.01, 0.01, -0.01, -0.01]) == pytest.approx(0.0)


def test_pearson_flat_series_is_honest_zero():
    assert pearson([1, 1, 1], [1, 2, 3]) == 0.0


def test_pearson_input_validation():
    with pytest.raises(ValueError):
        pearson([1, 2], [1, 2, 3])
    with pytest.raises(ValueError):
        pearson([1], [1])


def test_beta_doubling_is_two():
    bench = [0.01, -0.02, 0.015, 0.005, -0.01]
    asset = [2 * r for r in bench]
    assert beta(asset, bench) == pytest.approx(2.0)
    assert beta(bench, bench) == pytest.approx(1.0)


def test_beta_flat_benchmark_rejected():
    with pytest.raises(ValueError):
        beta([0.01, 0.02], [0.0, 0.0])


def test_log_returns_rejects_nonpositive():
    with pytest.raises(ValueError):
        log_returns([100, 0, 50])


# --- overlap_report -----------------------------------------------------------

BASE_R = [0.01, -0.01] * 12                    # 24 obs, > MIN_OVERLAP
INDEP_R = [0.01, 0.01, -0.01, -0.01] * 6       # corr 0 vs BASE_R (hand-computed)


def test_report_flags_the_duplicate_bet():
    closes = {
        "AAA": closes_from_returns(BASE_R),
        "BBB": closes_from_returns(BASE_R, start=50),   # same returns = same bet
        "CCC": closes_from_returns(INDEP_R),
    }
    rep = overlap_report(closes, closes_from_returns(BASE_R, start=400),
                         weights={"AAA": 0.5, "BBB": 0.5})
    assert rep.matrix["AAA"]["BBB"] == pytest.approx(1.0)
    assert rep.matrix["AAA"]["CCC"] == pytest.approx(0.0, abs=1e-9)
    assert rep.high_corr_pairs == [{"a": "AAA", "b": "BBB", "corr": 1.0}]
    # AAA/BBB move identically to the benchmark -> betas 1.0, portfolio 1.0
    assert rep.betas["AAA"] == pytest.approx(1.0)
    assert rep.portfolio_beta == pytest.approx(1.0)
    assert rep.matrix["AAA"]["AAA"] == 1.0


def test_candidate_overlap_warning():
    closes = {
        "AAA": closes_from_returns(BASE_R),
        "NEW": closes_from_returns(BASE_R, start=20),
    }
    rep = overlap_report(closes, closes_from_returns(BASE_R),
                         weights={"AAA": 1.0}, candidate="NEW")
    assert rep.candidate_max_corr == {"with": "AAA", "corr": 1.0}
    assert any("adds exposure, not diversification" in w for w in rep.warnings)


def test_candidate_low_overlap_no_warning():
    closes = {
        "AAA": closes_from_returns(BASE_R),
        "NEW": closes_from_returns(INDEP_R),
    }
    rep = overlap_report(closes, closes_from_returns(BASE_R),
                         weights={"AAA": 1.0}, candidate="NEW")
    assert rep.candidate_max_corr["corr"] == pytest.approx(0.0, abs=1e-9)
    assert not any("adds exposure" in w for w in rep.warnings)


def test_short_history_refused_not_guessed():
    closes = {
        "AAA": closes_from_returns(BASE_R),
        "TINY": closes_from_returns([0.01] * 5),   # 5 obs < MIN_OVERLAP
    }
    rep = overlap_report(closes, closes_from_returns(BASE_R))
    assert rep.matrix["AAA"]["TINY"] is None
    assert any("shared observations" in w for w in rep.warnings)
    assert rep.window_obs["AAA/TINY"] == 5
    assert MIN_OVERLAP == 20  # doc anchor: the refusal threshold is deliberate


def test_report_requires_candidate_closes():
    with pytest.raises(ValueError):
        overlap_report({"AAA": closes_from_returns(BASE_R)},
                       closes_from_returns(BASE_R), candidate="GHOST")


# --- tool + endpoint (identical closes for every symbol -> corr 1.0 pairs) ----

BARS_JSON = {
    "symbol": "X", "next_page_token": None,
    "bars": [
        {"t": f"2026-07-{d:02d}T04:00:00Z", "o": 1, "h": 1, "l": 1,
         "c": 100.0 * math.exp(sum(BASE_R[:i])), "v": 1}
        for i, d in enumerate(range(1, 26))
    ],
}


def alpaca_fake() -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        return httpx.Response(200, json=POSITIONS_JSON)
    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def market_fake() -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BARS_JSON)
    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_tool_executes_and_flags_identical_holdings():
    with alpaca_fake() as a, market_fake() as m:
        out = registry.execute("get_correlation", {},
                               ToolContext(alpaca=a, market=m))
    assert len(out["symbols"]) >= 1
    for s in out["symbols"]:
        assert out["matrix"][s][s] == 1.0
        assert out["betas"][s] == pytest.approx(1.0)   # same series as benchmark
    if len(out["symbols"]) >= 2:                        # identical closes -> flagged
        assert out["high_corr_pairs"][0]["corr"] == pytest.approx(1.0)
        assert out["high_corr_pairs"][0]["corr"] >= HIGH_CORR
    assert out["portfolio_beta"] == pytest.approx(1.0)
    assert out["asof"] and out["source"]


def test_endpoint_with_candidate():
    def alpaca_override():
        a = alpaca_fake()
        try:
            yield a
        finally:
            a.close()

    def market_override():
        m = market_fake()
        try:
            yield m
        finally:
            m.close()

    app.dependency_overrides[get_alpaca_client] = alpaca_override
    app.dependency_overrides[get_market_client] = market_override
    try:
        r = client.get("/api/correlation?candidate=qqq")
        assert r.status_code == 200
        body = r.json()
        assert body["candidate"] == "QQQ"
        assert body["candidate_max_corr"]["corr"] == pytest.approx(1.0)
        assert any("adds exposure" in w for w in body["warnings"])
        assert client.get("/api/correlation?days=5").status_code == 422
    finally:
        app.dependency_overrides.clear()
