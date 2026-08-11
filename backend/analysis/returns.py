"""Return calculations — pure, tested, deterministic (AGENTS.md: Determinism rule).

Every function here takes explicit inputs and returns raw floats. Formatting,
rounding, and narration belong to callers; money math belongs here.
"""


def simple_return(cost_basis: float, current_value: float) -> float:
    """Fractional return on a position: 0.10 means +10%.

    Raises ValueError if cost_basis is not positive — a zero/negative cost basis
    signals bad upstream data and must never be silently absorbed.
    """
    if cost_basis <= 0:
        raise ValueError(f"cost_basis must be > 0, got {cost_basis}")
    return (current_value - cost_basis) / cost_basis


def total_pnl(cost_basis: float, current_value: float) -> float:
    """Absolute profit/loss in account currency."""
    if cost_basis <= 0:
        raise ValueError(f"cost_basis must be > 0, got {cost_basis}")
    return current_value - cost_basis
