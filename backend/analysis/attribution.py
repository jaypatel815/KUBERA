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

from dataclasses import dataclass, field
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
    # T016c: Schwab option fills are per CONTRACT — 100 shares each. Without
    # this, a DB option round trip's P&L would be understated 100x (I020's
    # lesson arriving at the attribution layer). Equity stays 1.
    contract_multiplier: int = 1


def _bucket_key(tag: str | None) -> str:
    return tag if tag is not None else "unattributed"


# T091b — holding-period distribution. "How long do I actually hold?" is a
# discipline question, not a curiosity: an owner whose stated plan is swing
# trades but whose median hold is four hours is describing an intention, not a
# practice. Buckets are calendar days between the ENTRY fill and the exit fill
# that consumed it (FIFO), so a partially-sold lot contributes one record per
# consumed slice — which is correct: each slice really was held that long.
# I020/T105 — the sub-day buckets exist because "intraday" was hiding the owner's
# actual behaviour. His real record is 147 option fills out of 250, and 91 of
# those expire the SAME DAY they were opened. Lumping a 20-minute 0DTE scalp and
# a 7-hour swing into one "intraday" bucket answers the wrong question: for this
# account the interesting split is BELOW a day, not above it.
HOLD_BUCKETS = (
    ("minutes", 0.0, 1.0 / 24.0),          # under an hour
    ("hours", 1.0 / 24.0, 6.5 / 24.0),     # under one trading session
    ("same_day", 6.5 / 24.0, 1.0),         # opened and closed, but held the session
    ("1-3d", 1.0, 4.0),
    ("1-2wk", 4.0, 15.0),
    ("2wk-1mo", 15.0, 31.0),
    ("over_1mo", 31.0, float("inf")),
)

# One option contract controls 100 shares. A fill counted as one share
# understates the position by two orders of magnitude, and 59% of this owner's
# fills are options — so this is not a rounding concern (I020).
OPTION_MULTIPLIER = 100


def contract_multiplier(fill_type: str | None) -> int:
    """100 for an option fill, 1 otherwise. Keyed off the importer's fill_type."""
    return OPTION_MULTIPLIER if (fill_type or "").lower() == "option" else 1


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
    # T069: the raw round trips behind the aggregates. Needed by the risk-tolerance
    # estimator, which asks per-trip questions the summary tables cannot answer
    # ("what did he buy in the 24h AFTER this specific loss?"). Deliberately
    # stripped from the get_attribution payload — it is working data, not a report.
    trips: list[dict] = field(default_factory=list)


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
                          "ts": f.ts_iso,  # T091b: entry clock for holding period
                          "mult": f.contract_multiplier})  # T016c: options are 100x
            continue
        remaining = f.qty
        while remaining > 1e-9 and queue:
            lot = queue[0]
            take = min(remaining, lot["qty"])
            pnl = take * (f.price - lot["price"]) * lot.get("mult", 1)
            total_pnl += pnl
            round_trips += 1
            _credit(by_regime, _bucket_key(lot["regime"]), pnl)
            _credit(by_leg, _bucket_key(lot["sub_strategy"]), pnl)
            _credit(by_bucket, _bucket_key(lot["bucket"]), pnl)
            trips.append({"symbol": f.symbol, "pnl": pnl,
                          "held_days": _held_days(lot.get("ts"), f.ts_iso),
                          "entry_ts": lot.get("ts"), "exit_ts": f.ts_iso,
                          # T091b costs: exit-side notional of this slice, the
                          # base the spread estimate is charged against
                          # (T016c: contract multiplier included for options)
                          "notional": round(take * f.price * lot.get("mult", 1), 6)})
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
         "bucket": lot["bucket"],
         # T117: the TLH scan needs each lot's entry clock (ST/LT line) and
         # the contract multiplier (options exposure) — additive fields.
         "ts": lot.get("ts"), "mult": lot.get("mult", 1)}
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
        trips=trips,
        note=(
            "Realized P&L only, FIFO, credited to the ENTRY's tags. Costs are in "
            "fill prices; 'unattributed' = fills whose order matched no logged "
            "decision (typically manual trades). Attribution needs sample size — "
            "narrate counts alongside every P&L figure."
        ),
    )


def attributed_fills_from_rows(transactions, tags_by_order: dict) -> list[AttributedFill]:
    """Transaction ORM rows (duck-typed) -> AttributedFills, joining each fill's
    order id to the logged decision that placed it. Shared by the attribution
    tool and the weekly review so the two can never disagree (T091b)."""
    out = []
    for f in transactions:
        tag = tags_by_order.get(getattr(f, "order_id", None) or "")
        regime, leg, bucket = tag if tag else (None, None, None)
        # T016c: DB rows carry fill_type; "option" means qty is CONTRACTS.
        out.append(AttributedFill(
            symbol=f.symbol, side=f.side, qty=f.qty, price=f.price,
            ts_iso=f.occurred_at.isoformat(),
            regime=regime, sub_strategy=leg, entry_bucket=bucket,
            contract_multiplier=contract_multiplier(getattr(f, "fill_type", None)),
        ))
    return out


def decompose_costs(trips: list[dict],
                    half_spread_bps_by_symbol: dict[str, float]) -> dict:
    """Estimated round-trip spread cost per symbol (T091b, closing the T090 half).

    Historical spreads were not recorded, so the estimate prices each trip's
    exit-side notional at TODAY's half-spread, twice (entry side + exit side)
    — an approximation labeled as one, never blended into realized P&L.
    Symbols with no usable quote are listed as unpriced rather than silently
    priced at zero.
    """
    by_symbol: dict = {}
    unpriced: list[str] = []
    total = 0.0
    for t in trips:
        sym = t["symbol"]
        notional = t.get("notional")
        if notional is None:
            continue  # pre-T091b trip shape: nothing honest to charge against
        half = half_spread_bps_by_symbol.get(sym)
        if half is None:
            if sym not in unpriced:
                unpriced.append(sym)
            continue
        est = notional * (half / 10_000.0) * 2.0   # entry side + exit side
        slot = by_symbol.setdefault(sym, {"round_trips": 0, "notional": 0.0,
                                          "half_spread_bps": half,
                                          "est_spread_cost": 0.0})
        slot["round_trips"] += 1
        slot["notional"] = round(slot["notional"] + notional, 6)
        slot["est_spread_cost"] = round(slot["est_spread_cost"] + est, 6)
        total += est
    return {
        "by_symbol": by_symbol,
        "total_est_spread_cost": round(total, 6),
        "unpriced_symbols": sorted(unpriced),
        "note": (
            "ESTIMATE: each round trip charged its exit notional at TODAY's "
            "half-spread, twice (both sides). Historical spreads are unrecorded; "
            "commissions are not in the transaction record. Kept separate from "
            "realized P&L — never netted in."
        ),
    }
