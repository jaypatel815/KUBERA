"""T087a — open-trade monitor v1 (the owner's Q&A ticket, advisory half).

"I'm IN trades — tell me when one needs my eyes DURING the session."
Four checks per held position, each a NAMED alert with its numbers:

- rvol_collapse  (ALERT): the daily read is breakout-watch but session RVOL
  has collapsed — a break without volume is the fakeout setup the doctrine
  warns about. Fires ONLY under a breakout-ish daily regime: low volume on
  a range-bound day is normal, not news.
- vwap_churn     (WATCH): price keeps crossing session VWAP — chop, not
  conviction; the T052 churn detector applied to an open position.
- invalidation_hit / invalidation_near (ALERT/WATCH): the live price traded
  through the exit plan's invalidation level, or sits within half an ATR of
  it — the plan the owner already ratified is speaking, not a new opinion.
- event_window   (WATCH): a scheduled-event entry-guard window is open
  (FOMC/CPI/NFP…) — held risk into a binary print is a decision, so it is
  surfaced, never auto-acted on.

ADVISORY ONLY: this module never places, cancels, or resizes anything —
execution stays inside the paper loop's rails. Voice barge-in and the Orb
surface stay with T074/T087 by design. Missing inputs (no intraday bars,
no plan) become NOTES on the check, never crashes — a monitor that dies
mid-session is worse than one that says what it couldn't see.

Pure composition: the caller (scripts/monitor.py) fetches; this file only
judges. Thresholds are module constants, commented, owner-tunable later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RVOL_COLLAPSE_BELOW = 0.7    # session RVOL under 70% of usual = no fuel
CHURN_CROSSINGS = 4          # same line T052 uses for "churn, not trend"
NEAR_INVALIDATION_ATR = 0.5  # within half an ATR of the level = eyes on it
BREAKOUTISH_REGIMES = ("breakout_watch",)


@dataclass(frozen=True)
class MonitorAlert:
    symbol: str
    severity: str            # "alert" (needs eyes now) | "watch" (context)
    kind: str
    detail: str


@dataclass(frozen=True)
class PositionCheck:
    symbol: str
    price: float | None
    regime: str | None
    alerts: list[MonitorAlert] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)   # named blind spots


def check_position(
    symbol: str,
    price: float | None,
    *,
    daily_regime: str | None,
    session_rvol: float | None,
    rvol_sessions_used: int,
    vwap_crossings: int | None,
    invalidation_level: float | None,
    invalidation_reason: str,
    atr_value: float | None,
    open_event_windows: list[str],
) -> PositionCheck:
    """Judge one held position from prepared readings. Long-thesis v1 —
    the exit-plan module is long-oriented by doctrine; shorts arrive with
    the D021 revisit, and pretending otherwise here would judge them with
    the wrong sign."""
    symbol = symbol.upper()
    alerts: list[MonitorAlert] = []
    notes: list[str] = []

    # 1. RVOL collapse — only meaningful under a breakout-ish daily read.
    if daily_regime in BREAKOUTISH_REGIMES:
        if session_rvol is None:
            notes.append("session RVOL unavailable — the breakout-fuel check "
                         "could not run")
        elif session_rvol < RVOL_COLLAPSE_BELOW:
            alerts.append(MonitorAlert(
                symbol, "alert", "rvol_collapse",
                f"breakout thesis without fuel: session RVOL "
                f"{session_rvol:.2f}x vs {rvol_sessions_used} prior sessions "
                f"(collapse line {RVOL_COLLAPSE_BELOW:.2f}) — breaks that "
                "hold are made of volume"))

    # 2. VWAP churn — chop while holding.
    if vwap_crossings is None:
        notes.append("no session VWAP read — the churn check could not run")
    elif vwap_crossings >= CHURN_CROSSINGS:
        alerts.append(MonitorAlert(
            symbol, "watch", "vwap_churn",
            f"price crossed session VWAP {vwap_crossings}x "
            f"(churn line {CHURN_CROSSINGS}) — chop, not conviction"))

    # 3. The exit plan speaking: through the level, or within half an ATR.
    if invalidation_level is None:
        notes.append("no invalidation level in the exit plan — the "
                     "plan check could not run")
    elif price is None:
        notes.append("no live price — invalidation distance unknown")
    elif price <= invalidation_level:
        alerts.append(MonitorAlert(
            symbol, "alert", "invalidation_hit",
            f"price {price:.2f} is AT/THROUGH the invalidation level "
            f"{invalidation_level:.2f} ({invalidation_reason}) — the plan "
            "you ratified says the thesis is dead; deciding to stay is a "
            "NEW decision, journal it"))
    elif atr_value and atr_value > 0 and \
            (price - invalidation_level) <= NEAR_INVALIDATION_ATR * atr_value:
        dist = (price - invalidation_level) / atr_value
        alerts.append(MonitorAlert(
            symbol, "watch", "invalidation_near",
            f"price {price:.2f} is {dist:.2f} ATR above the invalidation "
            f"level {invalidation_level:.2f} (eyes-on line "
            f"{NEAR_INVALIDATION_ATR:g} ATR) — {invalidation_reason}"))

    # 4. Scheduled-event windows currently open.
    for why in open_event_windows:
        alerts.append(MonitorAlert(
            symbol, "watch", "event_window",
            f"{why} — held risk into a binary print is a decision; "
            "this is a surface, not an instruction"))

    return PositionCheck(symbol=symbol, price=price, regime=daily_regime,
                         alerts=alerts, notes=notes)


@dataclass(frozen=True)
class MonitorSummary:
    positions: int
    alerts: int              # severity == "alert"
    watches: int             # severity == "watch"
    blind_spots: int         # notes across positions
    exit_code: int           # 1 when anything needs eyes NOW, else 0
    note: str = ("advisory only — nothing was placed, cancelled, or "
                 "resized; execution stays inside the loop's rails")


def summarize(checks: list[PositionCheck]) -> MonitorSummary:
    alerts = sum(1 for c in checks for a in c.alerts if a.severity == "alert")
    watches = sum(1 for c in checks for a in c.alerts if a.severity == "watch")
    return MonitorSummary(
        positions=len(checks),
        alerts=alerts,
        watches=watches,
        blind_spots=sum(len(c.notes) for c in checks),
        exit_code=1 if alerts else 0,
    )
