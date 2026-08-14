"""Backtest rigor (T064): per-trade statistics, Calmar, anchored walk-forward.

Per-trade extraction works on the engine's contract: long-only 0/1 weights where
weights[i] earns bar i's return. A TRADE is a contiguous run of weight 1.0 from
index a to b; its return is equity[b] / equity[a-1] - 1 (equity[-1] treated as
the 1.0 starting base). A position still open at the end is closed at the last
equity mark and flagged via `open_at_end`.

Anchored walk-forward: our templates carry NO tunable parameters, so classic
train/test splits have nothing to fit — what CAN be tested honestly is
robustness across periods. We run ONCE over the full history (the engine is
no-lookahead by construction) and score each contiguous segment of the equity
curve separately. PASS = overall return > 0 AND at least half the segments are
non-negative. This is a consistency screen, not proof of future returns — and
the promotion gate (D016/D018) requires it before the paper loop will run a
template.
"""

from dataclasses import dataclass
from math import ceil
from typing import Sequence

from analysis.metrics import cagr, max_drawdown_frac


@dataclass(frozen=True)
class TradeStats:
    n_trades: int
    win_rate: float | None       # None when no trades
    profit_factor: float | None  # gross gains / gross losses; None if no losses
    avg_return_frac: float | None
    best_return_frac: float | None
    worst_return_frac: float | None
    open_at_end: bool
    trade_returns: list[float]


def trade_stats(weights: Sequence[float], equity_curve: Sequence[float]) -> TradeStats:
    if len(weights) != len(equity_curve):
        raise ValueError("weights and equity_curve must be equal length")
    if any(w not in (0.0, 1.0) for w in weights):
        raise ValueError("trade extraction requires 0/1 weights (long-only contract)")

    trades: list[float] = []
    open_at_end = False
    i, n = 0, len(weights)
    while i < n:
        if weights[i] == 1.0:
            a = i
            while i < n and weights[i] == 1.0:
                i += 1
            b = i - 1
            base = equity_curve[a - 1] if a > 0 else 1.0
            if base <= 0:
                raise ValueError("equity must be > 0")
            trades.append(equity_curve[b] / base - 1.0)
            if b == n - 1:
                open_at_end = True
        else:
            i += 1

    if not trades:
        return TradeStats(0, None, None, None, None, None, False, [])
    gains = [t for t in trades if t > 0]
    losses = [-t for t in trades if t < 0]
    return TradeStats(
        n_trades=len(trades),
        win_rate=len(gains) / len(trades),
        profit_factor=(sum(gains) / sum(losses)) if losses else None,
        avg_return_frac=sum(trades) / len(trades),
        best_return_frac=max(trades),
        worst_return_frac=min(trades),
        open_at_end=open_at_end,
        trade_returns=trades,
    )


def calmar(equity_curve: Sequence[float], periods_per_year: int = 252) -> float | None:
    """CAGR / max drawdown; None when the curve never drew down (undefined)."""
    dd = max_drawdown_frac(equity_curve)
    if dd == 0:
        return None
    return cagr(equity_curve, periods_per_year=periods_per_year) / dd


@dataclass(frozen=True)
class WalkForwardResult:
    n_segments: int
    segment_returns: list[float]
    non_negative_segments: int
    overall_return: float
    passed: bool
    criteria: str


def walk_forward(equity_curve: Sequence[float], n_segments: int = 4) -> WalkForwardResult:
    """Score contiguous segments of a single no-lookahead equity curve."""
    if n_segments < 2:
        raise ValueError(f"n_segments must be >= 2, got {n_segments}")
    n = len(equity_curve)
    if n < n_segments * 2:
        raise ValueError(f"need at least {n_segments * 2} bars for {n_segments} segments")
    bounds = [round(k * n / n_segments) for k in range(n_segments + 1)]
    seg_returns = []
    for k in range(n_segments):
        a, b = bounds[k], bounds[k + 1] - 1
        base = equity_curve[a - 1] if a > 0 else 1.0
        seg_returns.append(equity_curve[b] / base - 1.0)
    non_neg = sum(1 for r in seg_returns if r >= 0)
    overall = equity_curve[-1] / 1.0 - 1.0
    need = ceil(n_segments / 2)
    passed = overall > 0 and non_neg >= need
    return WalkForwardResult(
        n_segments=n_segments,
        segment_returns=seg_returns,
        non_negative_segments=non_neg,
        overall_return=overall,
        passed=passed,
        criteria=(f"overall return > 0 AND >= {need} of {n_segments} segments "
                  "non-negative — a consistency screen, not a promise"),
    )
