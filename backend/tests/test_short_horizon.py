"""T116 — the short-horizon leading lens: packaging pinned against the
already-tested T077 engine; refusals named; the persona carries the rule."""

from datetime import date, timedelta

from analysis.expected_move import expected_move
from analysis.short_horizon import one_line, short_horizon_read
from api.persona import SHORT_HORIZON_RULE, build_system_prompt
from api.tools import ToolContext, registry


def _series(n=300):
    d0 = date(2025, 1, 2)
    dates = [(d0 + timedelta(days=i)).isoformat() for i in range(n)]
    closes = [100.0 * (1.0 + 0.001 * i) * (1.0 + (0.01 if i % 7 == 0 else
                                                  -0.004 if i % 3 == 0 else
                                                  0.002))
              for i in range(n)]
    return dates, closes


def test_read_packages_the_t077_engine_faithfully():
    dates, closes = _series()
    read = short_horizon_read("spy", closes, dates)
    assert read.symbol == "SPY" and read.last_close == closes[-1]
    assert [h.horizon_days for h in read.horizons] == [1, 3]
    h1 = read.horizons[0]
    assert h1.available and h1.why is None
    # the numbers must be EXACTLY the engine's numbers for the same basis
    em = expected_move(closes, dates, horizon_days=1)
    bands = em.conditioned if (em.conditioned is not None and
                               em.current_vol_tercile is not None) \
        else em.unconditional
    assert h1.up_odds == bands.up_frac
    assert h1.p05_frac == bands.percentiles["p05"]
    assert h1.p95_price == bands.band_prices["p95"]
    assert h1.samples == bands.samples
    assert h1.basis.startswith(("vol-conditioned", "unconditional"))
    assert "never point predictions" in read.note


def test_thin_history_refuses_by_horizon_and_empty_is_named():
    dates, closes = _series(10)
    read = short_horizon_read("SPY", closes, dates)
    assert all(not h.available and "insufficient history" in h.why
               for h in read.horizons)
    empty = short_horizon_read("SPY", [], [])
    assert empty.last_close is None
    assert all(h.why == "no price history" for h in empty.horizons)


def test_one_line_leads_with_shortest_available_and_names_refusal():
    dates, closes = _series()
    line = one_line(short_horizon_read("SPY", closes, dates))
    assert line.startswith("next 1d usually ")
    assert "up-odds" in line and "odds, not a prediction" in line
    assert ("vol-conditioned" in line) or ("unconditional" in line)

    none_line = one_line(short_horizon_read("SPY", [], []))
    assert none_line.startswith("next-days read unavailable:")


def test_tool_returns_the_leading_lens(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace

    dates, closes = _series()
    bars = SimpleNamespace(
        bars=[SimpleNamespace(close=c, date=d) for c, d in zip(closes, dates)],
        asof=datetime(2026, 8, 20, tzinfo=timezone.utc), source="fake")
    market = SimpleNamespace(get_daily_bars=lambda s, days: bars)
    out = registry.execute("get_short_horizon", {"symbol": "spy"},
                           ToolContext(market=market))
    assert out["symbol"] == "SPY" and len(out["horizons"]) == 2
    assert out["horizons"][0]["available"] is True
    assert out["source"] == "fake" and out["asof"]


def test_persona_carries_the_d035_rule():
    assert "confidence trick" in SHORT_HORIZON_RULE
    assert "get_short_horizon" in SHORT_HORIZON_RULE
    prompt = build_system_prompt("2026-08-20T12:00:00Z", ["get_short_horizon"])
    assert SHORT_HORIZON_RULE in prompt          # wired, not just defined
    assert "weeks-to-months lens" in prompt      # I033 language reaches chat
