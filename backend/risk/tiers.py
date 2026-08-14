"""Graduated risk tiers (T067, D016/D018) — the ladder BEFORE the breaker.

The owner's documented failure mode: set a limit, hit it, keep trading. The
T033/T035 breaker is the hard stop at 100% of the daily loss budget; these tiers
add friction on the way there, ENFORCED in the paper loop (advisory in chat):

    tier 0  < 25% of budget   normal
    tier 1  >= 25%            entry thresholds tightened (2x cost floor + RVOL floor)
    tier 2  >= 50%            max new-buy size HALVED
    tier 3  >= 75%            new entries paused (no_trade)
    tier 4  >= 100%           the circuit breaker — owned by RiskEngine, unchanged,
                              time-locked, no override (this module never trips it)

Sells are exempt at every tier: reducing risk is always allowed. Pure logic.
"""

from dataclasses import dataclass

_TIERS = (
    (0, "normal", "no restrictions"),
    (1, "caution", "entry thresholds tightened (2x cost floor and RVOL floor)"),
    (2, "half_size", "maximum new-buy size halved"),
    (3, "entries_paused", "new entries paused — sells only"),
    (4, "breaker", "daily loss limit reached — RiskEngine circuit breaker territory"),
)


@dataclass(frozen=True)
class RiskTier:
    level: int
    name: str
    effect: str
    budget_consumed_frac: float  # share of the daily loss budget used (can exceed 1)
    loss_frac: float             # raw loss from day start (0 when flat/up)


def current_tier(
    day_start_equity: float, equity: float, daily_loss_limit_frac: float
) -> RiskTier:
    """Where are we on the ladder right now? Fail closed on bad inputs."""
    if day_start_equity <= 0 or equity <= 0:
        raise ValueError("equities must be > 0")
    if not 0 < daily_loss_limit_frac < 1:
        raise ValueError(f"daily_loss_limit_frac must be in (0,1), got {daily_loss_limit_frac}")
    loss_frac = max(0.0, (day_start_equity - equity) / day_start_equity)
    consumed = loss_frac / daily_loss_limit_frac
    if consumed >= 1.0:
        level = 4
    elif consumed >= 0.75:
        level = 3
    elif consumed >= 0.50:
        level = 2
    elif consumed >= 0.25:
        level = 1
    else:
        level = 0
    _, name, effect = _TIERS[level][0], _TIERS[level][1], _TIERS[level][2]
    return RiskTier(level=level, name=name, effect=effect,
                    budget_consumed_frac=consumed, loss_frac=loss_frac)
