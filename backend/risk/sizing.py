"""Volatility-parity position sizing (T078, D016/D017) — risk a fixed fraction of
equity per trade by sizing inversely to the symbol's volatility.

The arithmetic: if the stop sits `stop_atr_multiple` ATRs away, a full stop-out on
qty shares loses qty × stop_distance dollars. Cap that at equity × risk_frac:

    qty_risk      = (equity × risk_frac) / (stop_atr_multiple × ATR)
    risk_notional = qty_risk × price

The sizer can only SHRINK a requested buy — it never grants more than the strategy
asked for, and it deliberately does NOT replace the RiskEngine's per-symbol cap:
an oversized request that still exceeds the cap after sizing gets REJECTED there,
loudly, exactly as before (the rejection log is a feature, not a bug to smooth over).

Pure logic, no I/O. Bad input raises ValueError — fail closed.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SizingDecision:
    allowed_notional: float    # what the buy may actually be: min(requested, risk)
    requested_notional: float  # what the strategy wanted
    risk_notional: float       # the vol-parity ceiling
    binding: str               # "risk" (sizer shrank it) | "request" (untouched)
    risk_dollars: float        # equity × risk_frac — max loss if the stop is hit
    stop_distance: float       # stop_atr_multiple × ATR, in price units
    atr_value: float


def volatility_parity_notional(
    equity: float,
    price: float,
    atr_value: float,
    requested_notional: float,
    *,
    risk_frac: float,
    stop_atr_multiple: float,
) -> SizingDecision:
    """Bound a requested BUY notional by the volatility-parity risk budget."""
    if equity <= 0:
        raise ValueError(f"equity must be > 0, got {equity}")
    if price <= 0:
        raise ValueError(f"price must be > 0, got {price}")
    if atr_value <= 0:
        raise ValueError(f"atr_value must be > 0, got {atr_value}")
    if requested_notional < 0:
        raise ValueError(f"requested_notional must be >= 0, got {requested_notional}")
    if not 0 < risk_frac < 1:
        raise ValueError(f"risk_frac must be in (0, 1), got {risk_frac}")
    if stop_atr_multiple <= 0:
        raise ValueError(f"stop_atr_multiple must be > 0, got {stop_atr_multiple}")

    risk_dollars = equity * risk_frac
    stop_distance = stop_atr_multiple * atr_value
    risk_notional = (risk_dollars / stop_distance) * price
    allowed = min(requested_notional, risk_notional)
    return SizingDecision(
        allowed_notional=allowed,
        requested_notional=requested_notional,
        risk_notional=risk_notional,
        binding="risk" if risk_notional < requested_notional else "request",
        risk_dollars=risk_dollars,
        stop_distance=stop_distance,
        atr_value=atr_value,
    )
