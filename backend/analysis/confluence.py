"""Multi-timeframe regime confluence (T075, D016) — do the timeframes agree?

The doctrine's day-typing gets stronger when independent views line up: the daily
regime (T050), the intraday regime (same classifier on hourly bars), and which
side of session VWAP price is holding (T052). This module only ADJUSTS the daily
confidence — it never flips the regime call itself.

Adjustment rules (deterministic, hand-computable; argue in DECISIONS.md):
- direction: trending_up = +1, trending_down = -1, range_bound/breakout_watch = 0
- intraday regime agrees (same nonzero direction)      +0.05
- intraday regime conflicts (opposite nonzero)         -0.10
- VWAP side aligned with the daily direction           +0.05
- VWAP side against the daily direction                -0.05
- VWAP churn (>= 4 crossings — no side held)           -0.05
- either view neutral/absent: no adjustment from it
Result clamped to [0.05, 0.90] — confluence can strengthen a read, never make it
certain. HONESTY (D006): agreement uses regime structure + VWAP side only; true
volume-delta confirmation needs the SIP feed and is deliberately absent.
"""

from dataclasses import dataclass

REGIMES = ("trending_up", "trending_down", "range_bound", "breakout_watch")
_DIRECTION = {"trending_up": 1, "trending_down": -1,
              "range_bound": 0, "breakout_watch": 0}
CHURN_CROSSINGS = 4
CONF_FLOOR, CONF_CAP = 0.05, 0.90


@dataclass(frozen=True)
class ConfluenceReading:
    daily_regime: str
    daily_confidence: float
    intraday_regime: str | None
    intraday_confidence: float | None
    above_vwap: bool | None
    vwap_crossings: int | None
    churn: bool
    regime_agreement: str  # "agree" | "conflict" | "neutral"
    vwap_alignment: str    # "aligned" | "conflict" | "neutral"
    adjusted_confidence: float
    adjustments: list[str]
    note: str


def assess_confluence(
    daily_regime: str,
    daily_confidence: float,
    *,
    intraday_regime: str | None = None,
    intraday_confidence: float | None = None,
    above_vwap: bool | None = None,
    vwap_crossings: int | None = None,
) -> ConfluenceReading:
    if daily_regime not in REGIMES:
        raise ValueError(f"daily_regime must be one of {REGIMES}, got {daily_regime!r}")
    if intraday_regime is not None and intraday_regime not in REGIMES:
        raise ValueError(f"intraday_regime must be one of {REGIMES} or None")
    if not 0 <= daily_confidence <= 1:
        raise ValueError("daily_confidence must be in [0, 1]")

    daily_dir = _DIRECTION[daily_regime]
    intra_dir = _DIRECTION.get(intraday_regime) if intraday_regime else None

    adjustments: list[str] = []
    adjusted = daily_confidence

    if intra_dir is None or daily_dir == 0 or intra_dir == 0:
        agreement = "neutral"
    elif intra_dir == daily_dir:
        agreement = "agree"
        adjusted += 0.05
        adjustments.append(f"intraday regime {intraday_regime} agrees: +0.05")
    else:
        agreement = "conflict"
        adjusted -= 0.10
        adjustments.append(f"intraday regime {intraday_regime} conflicts: -0.10")

    if above_vwap is None or daily_dir == 0:
        vwap_alignment = "neutral"
    elif (above_vwap and daily_dir > 0) or (not above_vwap and daily_dir < 0):
        vwap_alignment = "aligned"
        adjusted += 0.05
        adjustments.append(
            f"price holding {'above' if above_vwap else 'below'} session VWAP "
            "with the trend: +0.05"
        )
    else:
        vwap_alignment = "conflict"
        adjusted -= 0.05
        adjustments.append(
            f"price {'above' if above_vwap else 'below'} session VWAP against "
            "the trend: -0.05"
        )

    churn = vwap_crossings is not None and vwap_crossings >= CHURN_CROSSINGS
    if churn:
        adjusted -= 0.05
        adjustments.append(
            f"VWAP churn ({vwap_crossings} crossings — no side held): -0.05"
        )

    adjusted = min(CONF_CAP, max(CONF_FLOOR, adjusted))
    return ConfluenceReading(
        daily_regime=daily_regime,
        daily_confidence=daily_confidence,
        intraday_regime=intraday_regime,
        intraday_confidence=intraday_confidence,
        above_vwap=above_vwap,
        vwap_crossings=vwap_crossings,
        churn=churn,
        regime_agreement=agreement,
        vwap_alignment=vwap_alignment,
        adjusted_confidence=adjusted,
        adjustments=adjustments,
        note=(
            "Confluence adjusts confidence in the DAILY read; it never flips the "
            "regime. Uses regime structure + VWAP side only — volume-delta "
            "confirmation needs the SIP feed and is deliberately absent (D006). "
            f"Clamped to [{CONF_FLOOR}, {CONF_CAP}]."
        ),
    )
