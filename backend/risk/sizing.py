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


# ------------------------------------------------------------------ T085b

KELLY_MIN_SAMPLES = 30      # below this the view refuses — thin history lies
KELLY_FRACTION = 0.25       # quarter-Kelly: full Kelly assumes the estimates
                            # are TRUE; they are estimates, so bet a quarter
KELLY_ADVISORY_CAP = 0.10   # even great numbers never advise >10% of equity


@dataclass(frozen=True)
class KellyView:
    """ADVISORY ONLY (D017): a fractional-Kelly reading from T077's
    DISTRIBUTION of past h-day moves (win rate + payoff ratio over N
    samples) — never a per-trade probability, never autopilot. The actual
    sizing (ATR risk-parity + caps) is unchanged by this view existing."""

    available: bool
    why: str | None
    win_rate: float | None
    payoff_ratio: float | None
    n_samples: int | None
    full_kelly_frac: float | None       # w - (1-w)/R; can be negative
    advisory_frac: float | None         # quarter-Kelly, floored 0, capped
    note: str


_KELLY_NOTE = ("advisory view only (D017): fractional Kelly from the "
               "distribution of past moves — the actual sized qty above is "
               "unchanged; quarter-Kelly because win rate and payoff are "
               "ESTIMATES, capped at "
               f"{KELLY_ADVISORY_CAP:.0%} of equity regardless")


def fractional_kelly_view(win_rate: float | None,
                          payoff_ratio: float | None,
                          n_samples: int | None) -> KellyView:
    """Pure math with named refusals. full Kelly f* = w - (1-w)/R.
    A non-positive f* is REPORTED (the distribution argues for no
    position at this payoff), not floored away silently — the advisory
    fraction floors at 0 but the full number stays visible."""
    if n_samples is None or n_samples < KELLY_MIN_SAMPLES:
        return KellyView(False,
                         f"only {n_samples or 0} samples "
                         f"(need {KELLY_MIN_SAMPLES}) — thin history lies",
                         win_rate, payoff_ratio, n_samples, None, None,
                         _KELLY_NOTE)
    if payoff_ratio is None or payoff_ratio <= 0:
        return KellyView(False, "no payoff ratio (one-sided sample window)",
                         win_rate, payoff_ratio, n_samples, None, None,
                         _KELLY_NOTE)
    if win_rate is None or not 0.0 < win_rate < 1.0:
        return KellyView(False, f"win rate {win_rate!r} outside (0, 1)",
                         win_rate, payoff_ratio, n_samples, None, None,
                         _KELLY_NOTE)
    full = win_rate - (1.0 - win_rate) / payoff_ratio
    advisory = min(max(0.0, full * KELLY_FRACTION), KELLY_ADVISORY_CAP)
    return KellyView(True, None, win_rate, payoff_ratio, n_samples,
                     full, advisory, _KELLY_NOTE)
