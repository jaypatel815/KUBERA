"""Execution quality (T088, D020) — the gap between the trade you designed and
the trade you got.

The doctrine says "never buy the open print". This module turns that from a
belief into a measurement: every order carries the price the DECISION was made
on; the fill carries what was actually paid. The difference is implementation
shortfall, and grouping it by time-of-day bucket says — with the owner's own
money — whether the open really is expensive for him.

Sign convention (stated because it inverts by side):
  BUY  — paying MORE than the decision price is a cost -> positive bps
  SELL — receiving LESS than the decision price is a cost -> positive bps
So positive slippage_bps ALWAYS means "this execution cost you".

Pure functions; hand-tested.
"""

from dataclasses import dataclass, field
from statistics import median


def slippage_bps(decision_price: float, fill_price: float, side: str) -> float:
    """Signed execution cost in basis points of the decision price."""
    if decision_price <= 0 or fill_price <= 0:
        raise ValueError("prices must be positive")
    s = side.strip().lower()
    if s not in ("buy", "sell"):
        raise ValueError(f"side must be buy or sell, got {side!r}")
    diff = fill_price - decision_price
    if s == "sell":
        diff = -diff
    return diff / decision_price * 10_000


@dataclass(frozen=True)
class ExecutionFill:
    symbol: str
    side: str
    qty: float
    decision_price: float
    fill_price: float
    bucket: str | None       # T091 entry bucket: pre / first_hour / midday / ...
    occurred_at: str


@dataclass(frozen=True)
class ExecutionReport:
    n_fills: int
    total_notional: float
    total_cost_dollars: float      # sum(slippage_frac * notional)
    avg_slippage_bps: float | None
    median_slippage_bps: float | None
    worst: dict | None             # the single most expensive execution
    by_bucket: dict                # bucket -> {n, avg_bps, cost_dollars}
    by_side: dict
    verdict: str
    warnings: list = field(default_factory=list)


MIN_BUCKET_SAMPLE = 5  # below this, a bucket's average is anecdote, not evidence


def execution_report(fills: list[ExecutionFill]) -> ExecutionReport:
    if not fills:
        return ExecutionReport(
            n_fills=0, total_notional=0.0, total_cost_dollars=0.0,
            avg_slippage_bps=None, median_slippage_bps=None, worst=None,
            by_bucket={}, by_side={},
            verdict="no matched fills yet — run scripts/sync.py after trading; "
                    "execution quality needs real fills, not estimates",
        )
    rows = []
    for f in fills:
        bps = slippage_bps(f.decision_price, f.fill_price, f.side)
        notional = f.qty * f.fill_price
        rows.append({
            "symbol": f.symbol, "side": f.side, "qty": f.qty,
            "decision_price": f.decision_price, "fill_price": f.fill_price,
            "slippage_bps": round(bps, 2),
            "cost_dollars": round(bps / 10_000 * notional, 4),
            "notional": round(notional, 2),
            "bucket": f.bucket, "occurred_at": f.occurred_at,
        })
    all_bps = [r["slippage_bps"] for r in rows]
    total_notional = sum(r["notional"] for r in rows)
    total_cost = sum(r["cost_dollars"] for r in rows)

    def group(key: str) -> dict:
        out: dict = {}
        for r in rows:
            k = r[key] or "unknown"
            g = out.setdefault(k, {"n": 0, "bps": [], "cost_dollars": 0.0})
            g["n"] += 1
            g["bps"].append(r["slippage_bps"])
            g["cost_dollars"] = round(g["cost_dollars"] + r["cost_dollars"], 4)
        for k, g in out.items():
            g["avg_bps"] = round(sum(g["bps"]) / len(g["bps"]), 2)
            g["thin_sample"] = g["n"] < MIN_BUCKET_SAMPLE
            del g["bps"]
        return out

    by_bucket = group("bucket")
    warnings = []
    thin = [k for k, g in by_bucket.items() if g["thin_sample"]]
    if thin:
        warnings.append(
            f"thin samples ({', '.join(sorted(thin))}): fewer than "
            f"{MIN_BUCKET_SAMPLE} fills — read these as anecdotes, not evidence")
    avg = sum(all_bps) / len(all_bps)
    verdict = (
        "executions are costing you on average — check order timing and spreads"
        if avg > 5 else
        "execution cost is small on average; the sample is what matters next"
        if avg > 0 else
        "average execution is at or better than the decision price")
    worst = max(rows, key=lambda r: r["slippage_bps"])
    return ExecutionReport(
        n_fills=len(rows),
        total_notional=round(total_notional, 2),
        total_cost_dollars=round(total_cost, 4),
        avg_slippage_bps=round(avg, 2),
        median_slippage_bps=round(median(all_bps), 2),
        worst=worst,
        by_bucket=by_bucket,
        by_side=group("side"),
        verdict=verdict,
        warnings=warnings,
    )
