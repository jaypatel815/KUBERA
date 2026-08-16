"""Performance attribution (T091, D020 priority #2) — WHY is the money moving?

FIFO round-trip attribution: buy fills open lots (each lot carries the
attribution tags of its ENTRY decision — regime, router leg, session bucket,
joined via order_id upstream); sell fills consume lots first-in-first-out, and
each consumed slice's realized P&L is credited to the ENTRY lot's tags. That is
the honest convention: a trade's outcome belongs to the conditions under which
it was OPENED.

Fills whose order_id matches no signal_log row get tags=None and land in the
"unattributed" bucket — typically the owner's manual trades; visible, never
silently dropped.

Answers, once fills accumulate: "is the regime classifier adding value?"
(P&L by regime), "which router leg earns?" (by sub-strategy), and "do
mid-session entries beat the open?" (by bucket). Pure function; the tool joins
DB rows and feeds it. Fail closed on bad input.
"""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class AttributedFill:
    """One fill + the entry tags its order maps to (None tags = unattributed)."""

    symbol: str
    side: str            # "buy" | "sell"
    qty: float
    price: float
    ts_iso: str          # for ordering within a symbol (ISO sorts correctly)
    regime: str | None = None
    sub_strategy: str | None = None
    entry_bucket: str | None = None


def _bucket_key(tag: str | None) -> str:
    return tag if tag is not None else "unattributed"


# T091b — holding-period distribution. "How long do I actually hold?" is a
# discipline question, not a curiosity: an owner whose stated plan is swing
# trades but whose median hold is four hours is describing an intention, not a
# practice. Buckets are calendar days between the ENTRY fill and the exit fill
# that consumed it (FIFO), so a partially-sold lot contributes one record per
# consumed slice — which is correct: each slice really was held that long.
HOLD_BUCKETS = (
    ("intraday", 0.0, 1.0),
    ("1-3d", 1.0, 4.0),
    ("1-2wk", 4.0, 15.0),
    ("2wk-1mo", 15.0, 31.0),
    ("over_1mo", 31.0, float("inf")),
)


def _held_days(entry_ts: str | None, exit_ts: str) -> float | None:
    """Calendar days between two ISO timestamps; None if the entry predates
    KUBERA's records (older lots have no stored clock)."""
    if not entry_ts:
        return None
    from datetime import datetime
    try:
        a = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
        b = datetime.fromisoformat(exit_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if a.tzinfo is None or b.tzinfo is None:      # compare like with like
        a, b = a.replace(tzinfo=None), b.replace(tzinfo=None)
    delta = (b - a).total_seconds() / 86400.0
    return round(delta, 6) if delta >= 0 else None   # exit before entry = corrupt


def hold_bucket(days: float | None) -> str:
    if days is None:
        return "unknown"
    for name, lo, hi in HOLD_BUCKETS:
        if lo <= days < hi:
            return name
    return "over_1mo"


def holding_period_distribution(trips: list[dict]) -> dict:
    """Per-bucket count / win rate / realized P&L, plus median and mean days.
    Describes what HAPPENED — never a target, never a recommendation."""
    dated = [t for t in trips if t.get("held_days") is not None]
    table: dict = {}
    for t in trips:
        key = hold_bucket(t.get("held_days"))
        slot = table.setdefault(key, {"round_trips": 0, "wins": 0,
                                      "realized_pnl": 0.0})
        slot["round_trips"] += 1
        slot["realized_pnl"] = round(slot["realized_pnl"] + t["pnl"], 6)
        if t["pnl"] > 0:
            slot["wins"] += 1
    for slot in table.values():
        slot["win_rate"] = (round(slot["wins"] / slot["round_trips"], 4)
                            if slot["round_trips"] else None)
    days = sorted(t["held_days"] for t in dated)
    n = len(days)
    median = None
    if n:
        median = days[n // 2] if n % 2 else (days[n // 2 - 1] + days[n // 2]) / 2
    return {
        "by_bucket": table,
        "n_dated_round_trips": n,
        "n_undated_round_trips": len(trips) - n,
        "median_days": None if median is None else round(median, 4),
        "mean_days": None if not n else round(sum(days) / n, 4),
        "shortest_days": days[0] if n else None,
        "longest_days": days[-1] if n else None,
        "note": ("calendar days from the entry fill to the exit that consumed it "
                 "(FIFO, one record per consumed slice). Describes what happened; "
                 "it is not a target. 'unknown' = lots opened before KUBERA "
                 "recorded fill timestamps."),
    }


def _credit(table: dict, key: str, pnl: float) -> None:
    slot = table.setdefault(key, {"realized_pnl": 0.0, "round_trips": 0, "wins": 0})
    slot["realized_pnl"] += pnl
    slot["round_trips"] += 1
    if pnl > 0:
        slot["wins"] += 1


@dataclass(frozen=True)
class AttributionReport:
    round_trips: int
    realized_pnl: float
    by_regime: dict
    by_sub_strategy: dict
    by_entry_bucket: dict
    open_lots: list[dict]
    oversold: list[dict]  # sells with no matching lots (external history) — shown, not hidden
    note: str
    # T091b (default keeps older constructions valid)
    holding_periods: dict | None = None


def fifo_attribution(fills: Sequence[AttributedFill]) -> AttributionReport:
    for f in fills:
        if f.side not in ("buy", "sell"):
            raise ValueError(f"side must be buy/sell, got {f.side!r}")
        if f.qty <= 0 or f.price <= 0:
            raise ValueError("qty and price must be > 0")

    by_regime: dict = {}
    by_leg: dict = {}
    by_bucket: dict = {}
    total_pnl = 0.0
    round_trips = 0
    oversold: list[dict] = []
    trips: list[dict] = []  # T091b: one record per FIFO round trip, with its clock
    lots: dict[str, list[dict]] = {}  # symbol -> FIFO queue of open lots

    for f in sorted(fills, key=lambda x: (x.symbol, x.ts_iso)):
        queue = lots.setdefault(f.symbol, [])
        if f.side == "buy":
            queue.append({"qty": f.qty, "price": f.price, "regime": f.regime,
                          "sub_strategy": f.sub_strategy, "bucket": f.entry_bucket,
                          "ts": f.ts_iso})  # T091b: entry clock for holding period
            continue
        remaining = f.qty
        while remaining > 1e-9 and queue:
            lot = queue[0]
            take = min(remaining, lot["qty"])
            pnl = take * (f.price - lot["price"])
            total_pnl += pnl
            round_trips += 1
            _credit(by_regime, _bucket_key(lot["regime"]), pnl)
            _credit(by_leg, _bucket_key(lot["sub_strategy"]), pnl)
            _credit(by_bucket, _bucket_key(lot["bucket"]), pnl)
            trips.append({"symbol": f.symbol, "pnl": pnl,
                          "held_days": _held_days(lot.get("ts"), f.ts_iso),
                          "entry_ts": lot.get("ts"), "exit_ts": f.ts_iso})
            lot["qty"] -= take
            remaining -= take
            if lot["qty"] <= 1e-9:
                queue.pop(0)
        if remaining > 1e-9:
            oversold.append({"symbol": f.symbol, "qty": remaining, "price": f.price,
                             "why": "sell without a recorded buy lot (pre-KUBERA "
                                    "history or unsynced fills)"})

    for table in (by_regime, by_leg, by_bucket):
        for slot in table.values():
            slot["win_rate"] = (slot["wins"] / slot["round_trips"]
                                if slot["round_trips"] else None)

    open_lots = [
        {"symbol": sym, "qty": lot["qty"], "price": lot["price"],
         "regime": lot["regime"], "sub_strategy": lot["sub_strategy"],
         "bucket": lot["bucket"]}
        for sym, queue in lots.items() for lot in queue
    ]
    return AttributionReport(
        round_trips=round_trips,
        realized_pnl=total_pnl,
        by_regime=by_regime,
        by_sub_strategy=by_leg,
        by_entry_bucket=by_bucket,
        open_lots=open_lots,
        oversold=oversold,
        holding_periods=holding_period_distribution(trips),
        note=(
            "Realized P&L only, FIFO, credited to the ENTRY's tags. Costs are in "
            "fill prices; 'unattributed' = fills whose order matched no logged "
            "decision (typically manual trades). Attribution needs sample size — "
            "narrate counts alongside every P&L figure."
        ),
    )
