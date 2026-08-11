"""Briefing composer — hand-computed on a synthetic linear series, plus degradation."""

import pytest

from analysis.briefing import PositionContext, build_briefing

# 300 trading days, closes 100, 101, ..., 399 (strictly rising)
CLOSES = [float(100 + i) for i in range(300)]
DATES = [f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(300)]


def test_linear_series_hand_computed():
    b = build_briefing("aapl", CLOSES, DATES)
    assert b.symbol == "AAPL"
    assert b.last_close == 399.0
    assert b.bars_count == 300
    # trailing returns: 399/379 - 1 and 399/339 - 1; 252d needs 253 bars -> present
    assert b.return_20d == pytest.approx(399 / 379 - 1)
    assert b.return_60d == pytest.approx(399 / 339 - 1)
    assert b.return_252d == pytest.approx(399 / 147 - 1)
    # SMA50 = mean(350..399) = 374.5 ; SMA200 = mean(200..399) = 299.5
    assert b.sma_50 == pytest.approx(374.5)
    assert b.sma_200 == pytest.approx(299.5)
    assert b.sma50_above_sma200 is True
    # monotonic rise: at the 52w high, no drawdown; low of last 252 bars = 148
    assert b.pct_from_52w_high == pytest.approx(0.0)
    assert b.pct_from_52w_low == pytest.approx(399 / 148 - 1)
    assert b.max_drawdown_252d == pytest.approx(0.0)
    assert b.volatility_ann_60d is not None and b.volatility_ann_60d > 0
    assert b.position is None


def test_thin_history_degrades_to_none_not_errors():
    b = build_briefing("NEW", CLOSES[:30], DATES[:30])
    assert b.bars_count == 30
    assert b.return_20d is not None
    assert b.return_60d is None
    assert b.return_252d is None
    assert b.volatility_ann_60d is None  # needs 61 bars
    assert b.sma_50 is None
    assert b.sma50_above_sma200 is None
    assert b.max_drawdown_252d is not None  # only needs 2


def test_position_context_passthrough():
    pos = PositionContext(qty=10, market_value=3990.0, unrealized_pl=100.0,
                          portfolio_weight_frac=0.25)
    b = build_briefing("AAPL", CLOSES, DATES, position=pos)
    assert b.position == pos


@pytest.mark.parametrize("closes,dates", [([], []), ([1.0, 2.0], ["a"])])
def test_bad_input_rejected(closes, dates):
    with pytest.raises(ValueError):
        build_briefing("X", closes, dates)
