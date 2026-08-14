"""Liquidity-aware costs (T090, D020) — what does it actually cost to trade this?

Three deterministic pieces:
- spread_bps: the live bid-ask spread in basis points of the mid — crossing the
  spread costs roughly HALF of it per side.
- ADV + participation cap: never be more than MAX_PARTICIPATION of a day's
  volume. Our volumes come from the IEX sample feed (D006), which UNDERSTATES
  consolidated volume — so the cap binds EARLIER than a consolidated cap
  would. That errs conservative and every payload says so.
- estimated per-symbol cost: half-spread with a floor — replaces the flat
  cost-bps assumption when a live quote is available.

Pure functions + a composer; every number hand-tested.
"""

from dataclasses import dataclass

MAX_PARTICIPATION = 0.01   # 1% of ADV — small-account courtesy AND honesty cap
ADV_WINDOW = 20            # trailing sessions for average daily volume
MIN_COST_BPS = 0.5         # even a 1-tick spread isn't free
IEX_NOTE = ("volume from the IEX sample feed — understates consolidated ADV, "
            "so this cap binds early (conservative by design)")


def spread_bps(bid: float, ask: float) -> float:
    """Bid-ask spread in basis points of the mid."""
    if bid <= 0 or ask <= 0:
        raise ValueError("bid and ask must be positive")
    if ask < bid:
        raise ValueError(f"crossed quote: ask {ask} < bid {bid}")
    mid = (bid + ask) / 2
    return (ask - bid) / mid * 10_000


def average_daily_volume(volumes: list[float], window: int = ADV_WINDOW) -> float:
    """Mean volume over the trailing `window` sessions."""
    if not volumes:
        raise ValueError("no volumes")
    if any(v < 0 for v in volumes):
        raise ValueError("volumes must be non-negative")
    tail = volumes[-window:]
    return sum(tail) / len(tail)


def participation_cap_shares(adv_shares: float,
                             max_participation: float = MAX_PARTICIPATION) -> float:
    if adv_shares < 0 or not 0 < max_participation <= 1:
        raise ValueError("bad adv/participation inputs")
    return adv_shares * max_participation


def estimated_cost_bps(spread: float) -> float:
    """Per-side cost estimate: half the spread, floored — the per-symbol number
    that replaces a flat assumption."""
    if spread < 0:
        raise ValueError("spread must be >= 0")
    return max(MIN_COST_BPS, spread / 2)


@dataclass(frozen=True)
class LiquidityProfile:
    symbol: str
    bid: float
    ask: float
    mid: float
    spread_bps: float
    estimated_cost_bps: float      # per side, half-spread floored
    adv_shares: float              # IEX-sample ADV (understated — see note)
    adv_window: int
    max_participation_frac: float
    cap_shares: float              # participation cap in shares
    cap_notional: float            # cap * mid
    quote_age_human: str
    quote_stale: bool
    note: str = IEX_NOTE


def liquidity_profile(symbol: str, bid: float, ask: float, volumes: list[float],
                      quote_age_human: str, quote_stale: bool) -> LiquidityProfile:
    sp = spread_bps(bid, ask)
    adv = average_daily_volume(volumes)
    cap = participation_cap_shares(adv)
    mid = (bid + ask) / 2
    return LiquidityProfile(
        symbol=symbol.upper(), bid=bid, ask=ask, mid=round(mid, 4),
        spread_bps=round(sp, 2), estimated_cost_bps=round(estimated_cost_bps(sp), 2),
        adv_shares=round(adv, 0), adv_window=min(ADV_WINDOW, len(volumes)),
        max_participation_frac=MAX_PARTICIPATION,
        cap_shares=round(cap, 2), cap_notional=round(cap * mid, 2),
        quote_age_human=quote_age_human, quote_stale=quote_stale,
    )
