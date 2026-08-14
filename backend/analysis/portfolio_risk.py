"""Portfolio-level risk (T093, D020/D021) — what does the BOOK risk, jointly?

Position-level rails (per-trade risk, per-symbol caps) can all pass while the
portfolio quietly becomes one bet. Three deterministic measures fix that:

- portfolio volatility: sigma_p = sqrt(w' C w) with C_ij = vol_i vol_j corr_ij —
  correlations either amplify (rho→1) or cancel (rho→-1) individual vols.
- marginal risk contributions (Euler): how much of sigma_p each position is
  responsible for; the contributions sum EXACTLY to sigma_p, so "SPY is 62% of
  your risk" is arithmetic, not opinion.
- effective bets: 1 / sum(w_i^2) on normalized weights — 3 equal positions of
  the same thing is still measured here as 3 (concentration of WEIGHTS);
  pair with correlations for the full "one bet in three wrappers" story.

Pure functions; weights are market-value fractions; vols are annualized.
"""

import math
from dataclasses import dataclass


def portfolio_volatility(weights: list[float], vols: list[float],
                         corr: list[list[float]]) -> float:
    """sqrt(w' C w); inputs validated, correlation diagonal must be 1."""
    n = len(weights)
    if not (n == len(vols) == len(corr)):
        raise ValueError("weights, vols, corr must have matching lengths")
    if n == 0:
        raise ValueError("empty portfolio")
    if any(v < 0 for v in vols):
        raise ValueError("volatilities must be non-negative")
    var = 0.0
    for i in range(n):
        if len(corr[i]) != n:
            raise ValueError("corr must be square")
        if abs(corr[i][i] - 1.0) > 1e-9:
            raise ValueError("corr diagonal must be 1.0")
        for j in range(n):
            if abs(corr[i][j] - corr[j][i]) > 1e-9:
                raise ValueError("corr must be symmetric")
            var += weights[i] * weights[j] * vols[i] * vols[j] * corr[i][j]
    return math.sqrt(max(0.0, var))  # -1 corr can drive tiny negatives via fp


def marginal_contributions(weights: list[float], vols: list[float],
                           corr: list[list[float]]) -> list[float]:
    """Euler decomposition: MC_i = w_i * (C w)_i / sigma_p; sums to sigma_p.
    A zero-vol portfolio has zero contributions."""
    sigma_p = portfolio_volatility(weights, vols, corr)
    n = len(weights)
    if sigma_p == 0:
        return [0.0] * n
    out = []
    for i in range(n):
        cw = sum(vols[i] * vols[j] * corr[i][j] * weights[j] for j in range(n))
        out.append(weights[i] * cw / sigma_p)
    return out


def effective_bets(weights: list[float]) -> float:
    """1 / sum(w^2) on weights normalized to sum 1. Equal N-way split -> N;
    everything in one name -> 1."""
    total = sum(weights)
    if total <= 0:
        raise ValueError("weights must sum to a positive number")
    norm = [w / total for w in weights]
    return 1.0 / sum(w * w for w in norm)


@dataclass(frozen=True)
class PortfolioRisk:
    symbols: list[str]
    weights: dict            # symbol -> weight frac
    vols_ann: dict           # symbol -> annualized vol
    portfolio_vol_ann: float
    contributions: dict      # symbol -> risk contribution (sums to portfolio vol)
    contribution_fracs: dict # symbol -> share of total risk (sums to 1)
    effective_bets: float
    diversification_ratio: float  # weighted-avg vol / portfolio vol (>=1; 1 = none)
    warnings: list


def portfolio_risk(symbols: list[str], weights: list[float], vols: list[float],
                   corr: list[list[float]]) -> PortfolioRisk:
    sigma_p = portfolio_volatility(weights, vols, corr)
    mc = marginal_contributions(weights, vols, corr)
    warnings = []
    top = max(range(len(symbols)), key=lambda i: mc[i]) if symbols else None
    fracs = [c / sigma_p if sigma_p > 0 else 0.0 for c in mc]
    if top is not None and fracs[top] >= 0.6 and len(symbols) > 1:
        warnings.append(
            f"{symbols[top]} carries {fracs[top]:.0%} of total portfolio risk — "
            "the book is effectively one bet"
        )
    wavg_vol = (sum(w * v for w, v in zip(weights, vols)) / sum(weights)
                if sum(weights) > 0 else 0.0)
    div_ratio = wavg_vol / sigma_p if sigma_p > 0 else 1.0
    return PortfolioRisk(
        symbols=list(symbols),
        weights={s: round(w, 4) for s, w in zip(symbols, weights)},
        vols_ann={s: round(v, 4) for s, v in zip(symbols, vols)},
        portfolio_vol_ann=round(sigma_p, 4),
        contributions={s: round(c, 4) for s, c in zip(symbols, mc)},
        contribution_fracs={s: round(f, 4) for s, f in zip(symbols, fracs)},
        effective_bets=round(effective_bets(weights), 2),
        diversification_ratio=round(div_ratio, 3),
        warnings=warnings,
    )
