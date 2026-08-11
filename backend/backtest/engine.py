"""Backtest engine v1 (T030) — minimal, deterministic, hand-verifiable (D010).

Execution model (single asset, daily bars, long-only, fractional exposure 0..1):
- The strategy sees ONLY closes up to and including day t (the engine enforces this by
  passing a prefix slice) and returns a target weight for day t+1.
- That weight is applied to day t+1's return: no lookahead, by construction.
- Changing weight costs `cost_bps` of the equity being shifted (|Δw| × equity × bps).
- Equity starts at 1.0; the curve is unitless and comparable across runs.

This engine IS money math: every behavior above has a hand-computed known-answer test.
Framework adoption criteria are recorded in DECISIONS.md D010.
"""

from dataclasses import dataclass
from typing import Callable, Sequence

from analysis.metrics import (
    cumulative_return,
    daily_returns,
    max_drawdown_frac,
    sharpe,
    volatility,
)

# A strategy maps the closes seen so far (oldest first, through "today") to the target
# exposure [0..1] to hold for the NEXT bar.
Strategy = Callable[[Sequence[float]], float]


@dataclass(frozen=True)
class BacktestResult:
    strategy_name: str
    dates: list[str]
    equity_curve: list[float]  # aligned with dates; starts at 1.0
    weights: list[float]  # weight in force on each bar (first bar: 0.0)
    n_rebalances: int  # number of weight changes
    total_cost_frac: float  # total transaction cost paid, as fraction of equity
    cumulative_return: float
    volatility_ann: float | None
    sharpe_ann: float | None
    max_drawdown_frac: float


def run_backtest(
    closes: Sequence[float],
    dates: Sequence[str],
    strategy: Strategy,
    strategy_name: str = "unnamed",
    cost_bps: float = 0.0,
) -> BacktestResult:
    """Run `strategy` over the series. Raises ValueError on malformed input."""
    if len(closes) != len(dates):
        raise ValueError("closes and dates must be equal length")
    if len(closes) < 2:
        raise ValueError("need at least 2 bars to backtest")
    if any(c <= 0 for c in closes):
        raise ValueError("all closes must be > 0")
    if not 0 <= cost_bps < 10_000:
        raise ValueError(f"cost_bps must be in [0, 10000), got {cost_bps}")

    rets = daily_returns(closes)  # rets[i] is the return from bar i to bar i+1

    equity = 1.0
    weight = 0.0  # exposure in force during the first bar (nothing bought yet)
    equity_curve = [equity]
    weights = [weight]
    n_rebalances = 0
    total_cost = 0.0

    for t in range(len(rets)):
        # Strategy decides at the close of bar t, seeing bars [0..t] ONLY.
        target = strategy(closes[: t + 1])
        if not 0.0 <= target <= 1.0:
            raise ValueError(
                f"strategy '{strategy_name}' returned weight {target} at bar {t}; "
                "must be within [0, 1]"
            )
        if target != weight:
            cost = abs(target - weight) * equity * (cost_bps / 10_000.0)
            equity -= cost
            total_cost += cost
            n_rebalances += 1
            weight = target
        # The chosen weight rides bar t -> t+1.
        equity *= 1.0 + weight * rets[t]
        equity_curve.append(equity)
        weights.append(weight)

    strat_rets = daily_returns(equity_curve) if len(equity_curve) >= 2 else []
    vol = volatility(strat_rets, 252) if len(strat_rets) >= 2 else None
    shp = None
    if len(strat_rets) >= 2:
        try:
            shp = sharpe(strat_rets, periods_per_year=252)
        except ValueError:  # zero volatility (e.g. never invested) — undefined, not an error
            shp = None

    return BacktestResult(
        strategy_name=strategy_name,
        dates=list(dates),
        equity_curve=equity_curve,
        weights=weights,
        n_rebalances=n_rebalances,
        total_cost_frac=total_cost,
        cumulative_return=cumulative_return(equity_curve),
        volatility_ann=vol,
        sharpe_ann=shp,
        max_drawdown_frac=max_drawdown_frac(equity_curve),
    )
