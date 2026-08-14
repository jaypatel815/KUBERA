"""Correlation & overlap guard (T079, D016) — "am I holding the same bet three times?"

Deterministic answers from daily closes, no external deps:
- pairwise Pearson correlation of daily log returns (aligned, shared window)
- per-symbol beta vs a benchmark (SPY), portfolio beta from position weights
- flags: highly-correlated pairs and candidate-symbol overlap with the book

SPY + QQQ + AAPL feels like three positions; in drawdowns it's roughly one.
This module is the engine behind the pre-trade concentration warning (T066) and
the portfolio-risk summary (T093 extends it). Pure functions, hand-tested.
"""

import math
from dataclasses import dataclass, field

HIGH_CORR = 0.80          # a pair above this is flagged as one bet in two wrappers
MIN_OVERLAP = 20          # fewer shared return observations -> refuse, don't guess


def log_returns(closes: list[float]) -> list[float]:
    """Daily log returns; positive prices required."""
    if any(c <= 0 for c in closes):
        raise ValueError("closes must be positive")
    return [math.log(b / a) for a, b in zip(closes, closes[1:])]


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys):
        raise ValueError("series lengths differ")
    n = len(xs)
    if n < 2:
        raise ValueError("need at least 2 observations")
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0            # a flat series correlates with nothing (honest zero)
    return cov / math.sqrt(vx * vy)


def beta(asset_returns: list[float], bench_returns: list[float]) -> float:
    """OLS beta: cov(asset, bench) / var(bench)."""
    if len(asset_returns) != len(bench_returns):
        raise ValueError("series lengths differ")
    n = len(asset_returns)
    if n < 2:
        raise ValueError("need at least 2 observations")
    ma = sum(asset_returns) / n
    mb = sum(bench_returns) / n
    var_b = sum((b_ - mb) ** 2 for b_ in bench_returns)
    if var_b == 0:
        raise ValueError("benchmark variance is zero — cannot compute beta")
    cov = sum((a - ma) * (b_ - mb) for a, b_ in zip(asset_returns, bench_returns))
    return cov / var_b


def _aligned_returns(closes_by_symbol: dict[str, list[float]],
                     a: str, b: str) -> tuple[list[float], list[float]]:
    """Align two return series on their shared trailing window (closes are
    assumed chronological; the overlap is the min length, taken from the end)."""
    ra, rb = log_returns(closes_by_symbol[a]), log_returns(closes_by_symbol[b])
    n = min(len(ra), len(rb))
    return ra[-n:], rb[-n:]


@dataclass(frozen=True)
class OverlapReport:
    symbols: list[str]
    window_obs: dict          # pair "A/B" -> shared observation count
    matrix: dict              # sym -> sym -> corr (symmetric, 1.0 diagonal)
    high_corr_pairs: list     # [{a, b, corr}] above HIGH_CORR
    betas: dict               # sym -> beta vs benchmark (present symbols only)
    portfolio_beta: float | None
    benchmark: str
    candidate: str | None
    candidate_max_corr: dict | None   # {"with": sym, "corr": x} | None
    warnings: list = field(default_factory=list)


def overlap_report(
    closes_by_symbol: dict[str, list[float]],
    benchmark_closes: list[float],
    weights: dict[str, float] | None = None,
    candidate: str | None = None,
    benchmark: str = "SPY",
) -> OverlapReport:
    """The full guard. `closes_by_symbol` includes holdings (and the candidate,
    if any); `weights` are portfolio weight fractions for held symbols."""
    symbols = sorted(closes_by_symbol)
    if len(symbols) < 1:
        raise ValueError("need at least one symbol")
    if candidate is not None and candidate not in closes_by_symbol:
        raise ValueError(f"candidate {candidate} missing from closes_by_symbol")

    matrix: dict = {s: {} for s in symbols}
    window_obs: dict = {}
    pairs = []
    warnings: list[str] = []
    for i, a in enumerate(symbols):
        matrix[a][a] = 1.0
        for b in symbols[i + 1:]:
            ra, rb = _aligned_returns(closes_by_symbol, a, b)
            window_obs[f"{a}/{b}"] = len(ra)
            if len(ra) < MIN_OVERLAP:
                matrix[a][b] = matrix[b][a] = None
                warnings.append(
                    f"{a}/{b}: only {len(ra)} shared observations "
                    f"(<{MIN_OVERLAP}) — correlation not computed"
                )
                continue
            c = round(pearson(ra, rb), 4)
            matrix[a][b] = matrix[b][a] = c
            if c >= HIGH_CORR:
                pairs.append({"a": a, "b": b, "corr": c})

    bench_r = log_returns(benchmark_closes)
    betas: dict = {}
    for s in symbols:
        rs = log_returns(closes_by_symbol[s])
        n = min(len(rs), len(bench_r))
        if n < MIN_OVERLAP:
            warnings.append(f"{s}: too little overlap with {benchmark} for beta")
            continue
        betas[s] = round(beta(rs[-n:], bench_r[-n:]), 4)

    portfolio_beta = None
    if weights:
        covered = [s for s in weights if s in betas]
        wsum = sum(weights[s] for s in covered)
        if covered and wsum > 0:
            portfolio_beta = round(
                sum(weights[s] * betas[s] for s in covered) / wsum, 4
            )
            if wsum < 0.99:
                warnings.append(
                    f"portfolio beta covers {wsum:.0%} of weights — "
                    "some holdings lacked usable history"
                )

    candidate_max = None
    if candidate is not None:
        best = None
        for s in symbols:
            if s == candidate:
                continue
            c = matrix[candidate].get(s)
            if c is not None and (best is None or c > best["corr"]):
                best = {"with": s, "corr": c}
        candidate_max = best
        if best and best["corr"] >= HIGH_CORR:
            warnings.append(
                f"candidate {candidate} correlates {best['corr']:.2f} with held "
                f"{best['with']} — this adds exposure, not diversification"
            )

    pairs.sort(key=lambda p: -p["corr"])
    return OverlapReport(
        symbols=symbols, window_obs=window_obs, matrix=matrix,
        high_corr_pairs=pairs, betas=betas, portfolio_beta=portfolio_beta,
        benchmark=benchmark, candidate=candidate,
        candidate_max_corr=candidate_max, warnings=warnings,
    )
