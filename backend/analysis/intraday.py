"""Intraday session analysis (T052) — VWAP, time-of-day RVOL, VWAP-side reading.

The doctrine (docs/research/regime-trading-notes.md):
- VWAP is the session's rough fair price, weighted by volume; price repeatedly
  crossing VWAP without holding a side = no trend = be selective.
- RVOL is today's volume AT THIS POINT of the day vs the stock's own typical
  volume by the same point — implemented exactly that way: cumulative volume up
  to the last bar's time-of-day, compared with prior sessions' cumulative volume
  up to the same time-of-day.

Definitions (stable contracts):
- Input: chronological bar objects with .ts (tz-aware, UTC ok), .high, .low,
  .close, .volume — duck-typed so the analysis layer stays free of data-layer
  imports; the market client's IntradayBar satisfies it.
- Sessions are grouped by the bar's date in America/New_York (a 20:30 ET
  after-hours bar belongs to that ET day even though it is past midnight UTC).
- rth_only=True (default) keeps bars whose START falls in 09:30 <= t < 16:00 ET.
- Session VWAP = cumulative sum(typical_price * volume) / sum(volume), where
  typical_price = (high + low + close) / 3. None if the session's volume is 0.
- vwap_crossings counts sign flips of (close - running VWAP) across the session;
  a bar exactly on VWAP keeps the previous side. Many crossings = churn.
- D006: volume_feed is REQUIRED; IEX volumes are relative-only and every reading
  says so.

Bad input raises ValueError — fail closed.
"""

from dataclasses import dataclass
from datetime import time
from statistics import mean
from typing import Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
RTH_START = time(9, 30)
RTH_END = time(16, 0)


@dataclass(frozen=True)
class SessionRead:
    session_date: str        # ET date of the session analyzed (the latest one)
    bars_count: int          # bars in that session (after any RTH filter)
    last_ts: str             # ISO timestamp of the last bar analyzed
    last_price: float
    session_vwap: float | None
    above_vwap: bool | None          # None when VWAP is undefined
    vwap_distance_frac: float | None  # (last_price / vwap) - 1
    vwap_crossings: int
    cum_volume: float
    intraday_rvol: float | None      # vs prior sessions by the same time-of-day
    rvol_sessions_used: int
    rth_only: bool
    volume_feed: str
    volume_note: str


def _validate(bars, volume_feed: str) -> None:
    if not bars:
        raise ValueError("no intraday bars provided")
    if not volume_feed.strip():
        raise ValueError("volume_feed is required (D006: label every volume statement)")
    prev = None
    for i, b in enumerate(bars):
        if b.ts.tzinfo is None:
            raise ValueError(f"bar {i}: ts must be tz-aware")
        if prev is not None and b.ts <= prev:
            raise ValueError(f"bar {i}: timestamps must be strictly increasing")
        prev = b.ts
        if b.high <= 0 or b.low <= 0 or b.close <= 0:
            raise ValueError(f"bar {i} ({b.ts.isoformat()}): prices must be > 0")
        if b.low > b.high:
            raise ValueError(f"bar {i} ({b.ts.isoformat()}): low {b.low} > high {b.high}")
        if b.volume < 0:
            raise ValueError(f"bar {i} ({b.ts.isoformat()}): volume must be >= 0")


def _in_rth(b) -> bool:
    t = b.ts.astimezone(ET).time()
    return RTH_START <= t < RTH_END


def group_sessions(bars: Sequence) -> dict[str, list]:
    """Chronological {ET-date-iso: [bars]} (dicts preserve insertion order)."""
    out: dict[str, list] = {}
    for b in bars:
        out.setdefault(b.ts.astimezone(ET).date().isoformat(), []).append(b)
    return out


def session_vwap(bars: Sequence) -> float | None:
    """Cumulative volume-weighted average of typical price; None on zero volume."""
    total_v = sum(b.volume for b in bars)
    if total_v <= 0:
        return None
    weighted = sum((b.high + b.low + b.close) / 3.0 * b.volume for b in bars)
    return weighted / total_v


def build_session_read(
    bars: Sequence,
    *,
    volume_feed: str,
    rvol_sessions: int = 5,
    rth_only: bool = True,
) -> SessionRead:
    """Read the LATEST session in `bars`, with RVOL context from up to
    `rvol_sessions` preceding sessions (fetch ~rvol_sessions+2 calendar days)."""
    if rvol_sessions < 1:
        raise ValueError(f"rvol_sessions must be >= 1, got {rvol_sessions}")
    _validate(bars, volume_feed)
    kept = [b for b in bars if _in_rth(b)] if rth_only else list(bars)
    if not kept:
        raise ValueError(
            "no bars in regular trading hours (09:30-16:00 ET) — pass rth_only=False "
            "to analyze extended hours"
        )
    sessions = group_sessions(kept)
    dates = list(sessions)
    today_bars = sessions[dates[-1]]
    priors = [sessions[d] for d in dates[:-1]][-rvol_sessions:]

    # running VWAP + crossings across today's session
    cum_v = 0.0
    cum_wv = 0.0
    side = 0
    crossings = 0
    for b in today_bars:
        cum_v += b.volume
        cum_wv += (b.high + b.low + b.close) / 3.0 * b.volume
        if cum_v > 0:
            running = cum_wv / cum_v
            new_side = 1 if b.close > running else (-1 if b.close < running else side)
            if side != 0 and new_side != 0 and new_side != side:
                crossings += 1
            side = new_side
    vwap = (cum_wv / cum_v) if cum_v > 0 else None

    # time-of-day RVOL: today's cumulative volume vs priors' by the same ET time
    cutoff = today_bars[-1].ts.astimezone(ET).time()
    prior_cums = [
        sum(b.volume for b in day if b.ts.astimezone(ET).time() <= cutoff)
        for day in priors
    ]
    prior_cums = [c for c in prior_cums if c > 0]
    rvol = (cum_v / mean(prior_cums)) if prior_cums and cum_v >= 0 else None

    last = today_bars[-1]
    return SessionRead(
        session_date=dates[-1],
        bars_count=len(today_bars),
        last_ts=last.ts.isoformat(),
        last_price=last.close,
        session_vwap=vwap,
        above_vwap=(last.close > vwap) if vwap is not None else None,
        vwap_distance_frac=(last.close / vwap - 1.0) if vwap else None,
        vwap_crossings=crossings,
        cum_volume=cum_v,
        intraday_rvol=rvol,
        rvol_sessions_used=len(prior_cums),
        rth_only=rth_only,
        volume_feed=volume_feed,
        volume_note=(
            f"Session VWAP and RVOL are computed from the {volume_feed} feed's own "
            "sample; relative comparisons are valid, absolute volume claims require "
            "the consolidated SIP feed (D006)."
        ),
    )
