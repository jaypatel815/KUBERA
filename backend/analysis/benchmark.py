"""Benchmark comparison (T021) — pure date-alignment and metric comparison.

Inputs are (date_iso, value) points; this module never fetches anything. The API layer
assembles portfolio history (DB snapshots) and benchmark history (market data) and passes
them in. Comparing misaligned dates would silently produce wrong numbers, so alignment is
an inner join on date and anything below 2 common dates is a hard error.
"""

from dataclasses import dataclass
from typing import Sequence

from analysis.metrics import (
    cumulative_return,
    daily_returns,
    max_drawdown_frac,
    sharpe,
    volatility,
)

Point = tuple[str, float]  # (ISO date "YYYY-MM-DD", value > 0)


@dataclass(frozen=True)
class SeriesMetrics:
    cumulative_return: float
    volatility_ann: float | None  # None when too few points for a stable estimate
    sharpe_ann: float | None
    max_drawdown_frac: float


@dataclass(frozen=True)
class Comparison:
    dates: list[str]
    portfolio_norm: list[float]  # both curves normalized to 1.0 at the first common date
    benchmark_norm: list[float]
    portfolio: SeriesMetrics
    benchmark: SeriesMetrics
    excess_return: float  # portfolio cumulative minus benchmark cumulative


def align_by_date(
    portfolio: Sequence[Point], benchmark: Sequence[Point]
) -> tuple[list[str], list[float], list[float]]:
    """Inner-join both series on date, oldest first. Raises ValueError below 2 overlaps."""
    bench_map = dict(benchmark)
    common = sorted(d for d, _ in portfolio if d in bench_map)
    if len(common) < 2:
        raise ValueError(
            f"only {len(common)} overlapping date(s) between portfolio history and "
            "benchmark — history accumulates as the sync job runs (scripts/sync.py); "
            "try again after more daily snapshots exist"
        )
    port_map = dict(portfolio)
    return common, [port_map[d] for d in common], [bench_map[d] for d in common]


def _series_metrics(values: Sequence[float], periods_per_year: int) -> SeriesMetrics:
    rets = daily_returns(values)
    enough = len(rets) >= 2
    vol = volatility(rets, periods_per_year) if enough else None
    shp = None
    if enough:
        try:
            shp = sharpe(rets, periods_per_year=periods_per_year)
        except ValueError:  # zero volatility — Sharpe undefined, not an error here
            shp = None
    return SeriesMetrics(
        cumulative_return=cumulative_return(values),
        volatility_ann=vol,
        sharpe_ann=shp,
        max_drawdown_frac=max_drawdown_frac(values),
    )


def compare(
    portfolio: Sequence[Point], benchmark: Sequence[Point], periods_per_year: int = 252
) -> Comparison:
    dates, port_vals, bench_vals = align_by_date(portfolio, benchmark)
    p = _series_metrics(port_vals, periods_per_year)
    b = _series_metrics(bench_vals, periods_per_year)
    return Comparison(
        dates=dates,
        portfolio_norm=[v / port_vals[0] for v in port_vals],
        benchmark_norm=[v / bench_vals[0] for v in bench_vals],
        portfolio=p,
        benchmark=b,
        excess_return=p.cumulative_return - b.cumulative_return,
    )
