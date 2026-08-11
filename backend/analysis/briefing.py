"""Symbol briefing composer (T025) — the evidence pack behind "should I buy X?".

Deterministic facts only: no opinions, no predictions, no LLM. The Phase 4 conversation
layer narrates this structure and must state data recency (`last_close_date`, `asof`)
and coverage (`bars_count`) — both are always present here.

Unlike analysis.metrics (which raises on thin input), a briefing DEGRADES GRACEFULLY:
fields that need more history than exists are None rather than errors, because "this
ticker only has 90 trading days of data" is itself information the user should see.
Windows are in TRADING DAYS (bars), not calendar days.
"""

from dataclasses import dataclass
from typing import Sequence

from analysis.metrics import daily_returns, max_drawdown_frac, sma, volatility


@dataclass(frozen=True)
class PositionContext:
    qty: float
    market_value: float
    unrealized_pl: float
    portfolio_weight_frac: float | None  # None when total portfolio value unknown


@dataclass(frozen=True)
class SymbolBriefing:
    symbol: str
    last_close: float
    last_close_date: str
    bars_count: int
    return_20d: float | None
    return_60d: float | None
    return_252d: float | None
    volatility_ann_60d: float | None
    max_drawdown_252d: float | None
    pct_from_52w_high: float | None  # -0.12 == 12% below the 52-week high
    pct_from_52w_low: float | None   # +0.30 == 30% above the 52-week low
    sma_50: float | None
    sma_200: float | None
    sma50_above_sma200: bool | None  # long-term trend context; None if insufficient data
    position: PositionContext | None  # None when the user holds no position


def _trailing_return(closes: Sequence[float], bars: int) -> float | None:
    if len(closes) <= bars:
        return None
    past = closes[-(bars + 1)]
    return closes[-1] / past - 1.0 if past > 0 else None


def build_briefing(
    symbol: str,
    closes: Sequence[float],
    dates: Sequence[str],
    position: PositionContext | None = None,
) -> SymbolBriefing:
    """Compose the evidence pack from daily closes (oldest first) and their ISO dates."""
    if not closes or len(closes) != len(dates):
        raise ValueError("closes and dates must be equal-length and non-empty")
    n = len(closes)

    vol_60 = None
    if n >= 61:
        vol_60 = volatility(daily_returns(closes[-61:]), periods_per_year=252)

    dd_252 = max_drawdown_frac(closes[-252:]) if n >= 2 else None

    year = closes[-min(n, 252):]
    high, low = max(year), min(year)
    last = closes[-1]

    sma50 = sma(closes, 50) if n >= 50 else None
    sma200 = sma(closes, 200) if n >= 200 else None

    return SymbolBriefing(
        symbol=symbol.upper(),
        last_close=last,
        last_close_date=dates[-1],
        bars_count=n,
        return_20d=_trailing_return(closes, 20),
        return_60d=_trailing_return(closes, 60),
        return_252d=_trailing_return(closes, 252),
        volatility_ann_60d=vol_60,
        max_drawdown_252d=dd_252,
        pct_from_52w_high=(last / high - 1.0) if high > 0 else None,
        pct_from_52w_low=(last / low - 1.0) if low > 0 else None,
        sma_50=sma50,
        sma_200=sma200,
        sma50_above_sma200=(sma50 > sma200) if (sma50 and sma200) else None,
        position=position,
    )
