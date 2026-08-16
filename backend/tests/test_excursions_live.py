"""T089 live MAE/MFE — hand-computed excursions on open positions.

Headline hand case (entry 100):
  lows reach 94  -> MAE = 94/100 - 1 = -6%
  highs reach 112 -> MFE = 112/100 - 1 = +12%
  last close 103 -> current = +3%
  give-back = (12% - 3%) / 12% = 75% of the run-up handed back
  stop at 96 -> allowed pain 4%; MAE 6% -> heat capped at 100%
"""

import httpx
import pytest
from test_alpaca import ACCOUNT_JSON, paper_settings

from analysis.excursions_live import (
    excursion_book,
    position_excursion,
)
from api.tools import ToolContext, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient

HIGHS = [104.0, 108.0, 112.0, 106.0, 103.5]
LOWS = [99.0, 101.0, 105.0, 94.0, 102.0]
CLOSES = [102.0, 107.0, 110.0, 99.0, 103.0]


# --- pure math ----------------------------------------------------------------

def test_headline_hand_case():
    r = position_excursion("spy", 100.0, HIGHS, LOWS, CLOSES)
    assert r.symbol == "SPY"
    assert r.mae_frac == pytest.approx(-0.06)
    assert r.mfe_frac == pytest.approx(0.12)
    assert r.current_frac == pytest.approx(0.03)
    assert r.give_back_frac == pytest.approx(0.75)
    assert r.mae_price == 94.0 and r.mfe_price == 112.0
    assert r.bars_held == 5
    assert "gave back" in r.verdict and "review clock" in r.verdict
    assert "daily high/low" in r.note and "AVERAGE entry" in r.note


def test_heat_against_a_stop_is_capped_at_one():
    r = position_excursion("SPY", 100.0, HIGHS, LOWS, CLOSES, stop_price=96.0)
    # allowed 4%, MAE 6% -> would be 1.5, capped to 1.0 (the stop would have hit)
    assert r.heat_used_frac == 1.0
    assert "nearly all the pain" in r.verdict


def test_partial_heat():
    r = position_excursion("SPY", 100.0, [101.0], [98.0], [100.5],
                           stop_price=94.0)
    # MAE 2% of an allowed 6% -> one third of the heat used
    assert r.heat_used_frac == pytest.approx(1 / 3, abs=1e-3)
    assert "within normal excursion" in r.verdict


def test_untested_position_says_so():
    r = position_excursion("SPY", 100.0, [100.4], [99.8], [100.2])
    assert r.mae_frac == pytest.approx(-0.002)
    assert "not been under real pressure" in r.verdict


def test_no_run_up_means_no_give_back():
    r = position_excursion("SPY", 100.0, [99.0], [95.0], [96.0])
    assert r.mfe_frac < 0
    assert r.give_back_frac is None      # can't give back what never existed


def test_validation():
    with pytest.raises(ValueError):
        position_excursion("SPY", 0, HIGHS, LOWS, CLOSES)
    with pytest.raises(ValueError):
        position_excursion("SPY", 100.0, HIGHS, LOWS[:2], CLOSES)
    with pytest.raises(ValueError):
        position_excursion("SPY", 100.0, [], [], [])
    with pytest.raises(ValueError):          # high below low = corrupt
        position_excursion("SPY", 100.0, [95.0], [99.0], [97.0])
    with pytest.raises(ValueError):          # stop above entry is nonsense
        position_excursion("SPY", 100.0, HIGHS, LOWS, CLOSES, stop_price=105.0)


def test_book_picks_the_worst_and_the_biggest_giveback():
    a = position_excursion("AAA", 100.0, HIGHS, LOWS, CLOSES)       # MAE -6%, gave back 75%
    # BBB never traded above entry, so it has NO run-up to give back — it only
    # hurts. (Fixture lesson: a 1% pop fully surrendered scores 100% give-back.)
    b = position_excursion("BBB", 100.0, [99.0], [90.0], [95.0])    # MAE -10%
    book = excursion_book([a, b])
    assert book.worst_mae == {"symbol": "BBB", "mae_frac": pytest.approx(-0.10)}
    assert b.give_back_frac is None
    assert book.biggest_give_back["symbol"] == "AAA"
    empty = excursion_book([])
    assert empty.positions == [] and "no open positions" in empty.warnings[0]


# --- the tool -----------------------------------------------------------------

POSITIONS = [{
    "symbol": "SPY", "qty": "10", "avg_entry_price": "100.0",
    "current_price": "103.0", "market_value": "1030", "cost_basis": "1000",
    "unrealized_pl": "30", "unrealized_plpc": "0.03",
}]
BARS = {"symbol": "SPY", "next_page_token": None,
        "bars": [{"t": f"2026-08-{i + 1:02d}T04:00:00Z", "o": c, "h": h, "l": low,
                  "c": c, "v": 1_000_000}
                 for i, (h, low, c) in enumerate(zip(HIGHS, LOWS, CLOSES))]}


def clients(positions=POSITIONS, bars=BARS):
    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if "/v2/account" in p:
            return httpx.Response(200, json=ACCOUNT_JSON)
        if "/v2/positions" in p:
            return httpx.Response(200, json=positions)
        return httpx.Response(200, json=bars)
    t = httpx.MockTransport(handler)
    return (AlpacaClient(settings=paper_settings(), transport=t),
            MarketDataClient(settings=paper_settings(), transport=t))


def test_tool_reports_open_position_excursions():
    a, m = clients()
    with a, m:
        out = registry.execute("get_open_excursions", {"days": 60},
                               ToolContext(alpaca=a, market=m))
    pos = out["positions"][0]
    assert pos["symbol"] == "SPY"
    assert pos["mae_frac"] == pytest.approx(-0.06)
    assert pos["mfe_frac"] == pytest.approx(0.12)
    assert out["worst_mae"]["symbol"] == "SPY"
    assert out["asof"] and "alpaca" in out["source"]
    # too little history for ATR -> no stop context, but excursions still land
    assert pos["stop_price"] is None


def test_tool_empty_book_is_calm():
    a, m = clients(positions=[])
    with a, m:
        out = registry.execute("get_open_excursions", {}, ToolContext(alpaca=a, market=m))
    assert out["positions"] == []
    assert "no open positions" in out["warnings"][0]
