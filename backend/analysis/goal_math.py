"""Goal math (I012) — the deterministic answers behind "$1,000 → $1,000,000".

Born from a real owner brief: required annualized returns per horizon, future
value with monthly contributions, years-to-target, and the daily-compounding
reality check that shows why "2–5% per trading day" is not a plan. Money math
lives in tested code, never in the LLM — this module is why KUBERA can answer
those questions with numbers instead of vibes.

Every function is pure and hand-testable. Nothing here is a forecast: these are
arithmetic consequences of ASSUMED returns, and the assumption is the fragile
part — the narration must say so.
"""

from dataclasses import dataclass

MAX_YEARS = 100


def required_cagr(start: float, target: float, years: float) -> float:
    """The annualized return that turns `start` into `target` in `years`."""
    if start <= 0 or target <= 0 or years <= 0:
        raise ValueError("start, target, years must all be > 0")
    return (target / start) ** (1.0 / years) - 1.0


def future_value(start: float, monthly: float, years: float,
                 annual_return: float) -> float:
    """FV with monthly compounding; contributions land at each month's end."""
    if start < 0 or monthly < 0 or years <= 0:
        raise ValueError("start/monthly must be >= 0, years > 0")
    if annual_return <= -1:
        raise ValueError("annual_return must be > -100%")
    r = (1.0 + annual_return) ** (1.0 / 12.0) - 1.0
    n = round(years * 12)
    fv = start * (1.0 + r) ** n
    if monthly > 0:
        fv += monthly * (((1.0 + r) ** n - 1.0) / r if r != 0 else n)
    return fv


def years_to_target(start: float, monthly: float, annual_return: float,
                    target: float) -> float | None:
    """Months iterated until `target`; None if 100 years isn't enough — an honest
    'not with these numbers' instead of a fantasy decimal."""
    if start < 0 or monthly < 0 or target <= 0:
        raise ValueError("start/monthly >= 0, target > 0")
    if start >= target:
        return 0.0
    if annual_return <= -1:
        raise ValueError("annual_return must be > -100%")
    r = (1.0 + annual_return) ** (1.0 / 12.0) - 1.0
    balance = start
    for month in range(1, MAX_YEARS * 12 + 1):
        balance = balance * (1.0 + r) + monthly
        if balance >= target:
            return round(month / 12.0, 1)
    return None


def daily_return_reality(daily_return_frac: float,
                         trading_days: int = 252) -> dict:
    """What 'X% per trading day' compounds to in a year — the number that ends
    the conversation. 2%/day is a 147x year; nobody does that."""
    if daily_return_frac <= -1:
        raise ValueError("daily_return_frac must be > -100%")
    annual_multiple = (1.0 + daily_return_frac) ** trading_days
    return {
        "daily_return_frac": daily_return_frac,
        "trading_days": trading_days,
        "annual_multiple": annual_multiple,
        "annualized_return_frac": annual_multiple - 1.0,
        "note": (
            "compounding X% per trading day for a year multiplies the account "
            f"by {annual_multiple:,.1f}x — sustained daily-return targets at "
            "this level have no documented precedent; treat any plan built on "
            "them as broken arithmetic, not ambition"
        ),
    }


@dataclass(frozen=True)
class GoalScenarios:
    start: float
    target: float
    required_cagr_by_years: dict[str, float]
    fv_table: dict          # monthly -> return -> {years: fv}
    years_to_target_table: dict  # monthly -> return -> years | None
    daily_reality: list[dict]
    note: str


def goal_scenarios(
    start: float,
    target: float,
    years_options: tuple = (10, 15, 20, 25, 30),
    monthly_options: tuple = (0, 50, 100, 250, 500),
    return_options: tuple = (0.05, 0.08, 0.10, 0.15, 0.20),
    daily_checks: tuple = (0.02, 0.05),
) -> GoalScenarios:
    if start <= 0 or target <= start:
        raise ValueError("need start > 0 and target > start")
    req = {str(y): required_cagr(start, target, y) for y in years_options}
    fv_table = {
        str(m): {
            f"{r:.0%}": {str(y): future_value(start, m, y, r)
                         for y in (10, 20, 30)}
            for r in return_options
        }
        for m in monthly_options
    }
    ytt = {
        str(m): {f"{r:.0%}": years_to_target(start, m, r, target)
                 for r in return_options}
        for m in monthly_options
    }
    return GoalScenarios(
        start=start,
        target=target,
        required_cagr_by_years=req,
        fv_table=fv_table,
        years_to_target_table=ytt,
        daily_reality=[daily_return_reality(d) for d in daily_checks],
        note=(
            "Arithmetic consequences of ASSUMED returns — the assumptions are "
            "the fragile part. null in years-to-target means 'not within 100 "
            "years at that return'. Contributions usually dominate returns at "
            "small account sizes; the tables show it rather than assert it."
        ),
    )
