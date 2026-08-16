"""Live MAE/MFE on OPEN positions (T089, D020 gap 3).

The backtest version (backtest/stats.trade_excursions) measures closed trades
on closes only. This measures what a position the owner is holding RIGHT NOW
has already put him through, using daily HIGHS and LOWS:

- MAE (maximum adverse excursion): the worst the position went against him
- MFE (maximum favourable excursion): the best it ever showed him
- give-back: how much of the MFE he has handed back — the number behind
  "it was up 8% and I watched it round-trip"
- heat remaining: how far MAE sits from a 2xATR stop, so "you've already taken
  most of the pain this trade is allowed" is arithmetic

The calibration question this feeds: if winners routinely dip 3% before
working, a 2% stop is manufacturing losses.

HONEST LIMITS, carried in every payload: daily bars, so intraday spikes
between the high and low are invisible; and the basis is the broker's AVERAGE
entry price, so an averaged-in position reports excursions against the blend,
not any single fill.
"""

from dataclasses import dataclass, field

DAILY_BARS_NOTE = ("daily high/low only — an intraday spike beyond these is "
                   "invisible; basis is the broker's AVERAGE entry price")


@dataclass(frozen=True)
class PositionExcursion:
    symbol: str
    entry_price: float
    current_price: float
    bars_held: int
    mae_frac: float          # <= 0 (worst drawdown from entry)
    mfe_frac: float          # >= 0 (best run-up from entry)
    current_frac: float
    give_back_frac: float | None   # fraction of MFE surrendered; None if MFE 0
    mae_price: float
    mfe_price: float
    stop_price: float | None
    heat_used_frac: float | None   # MAE as a share of entry->stop distance
    verdict: str
    note: str = DAILY_BARS_NOTE


def position_excursion(symbol: str, entry_price: float, highs: list[float],
                       lows: list[float], closes: list[float],
                       stop_price: float | None = None) -> PositionExcursion:
    """Excursions since entry. `highs/lows/closes` cover the holding period
    (oldest first) and must be the same length."""
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    n = len(highs)
    if not (n == len(lows) == len(closes)) or n == 0:
        raise ValueError("highs, lows, closes must be non-empty and equal length")
    if any(h <= 0 for h in highs) or any(low <= 0 for low in lows):
        raise ValueError("prices must be positive")
    if any(h < low for h, low in zip(highs, lows)):
        raise ValueError("a high below its low is corrupt data")

    worst = min(lows)
    best = max(highs)
    current = closes[-1]
    mae = worst / entry_price - 1.0
    mfe = best / entry_price - 1.0
    cur = current / entry_price - 1.0
    give_back = None
    if mfe > 0:
        give_back = max(0.0, (mfe - cur) / mfe)

    heat = None
    if stop_price is not None:
        if stop_price <= 0 or stop_price >= entry_price:
            raise ValueError("stop_price must be positive and below entry")
        allowed = (entry_price - stop_price) / entry_price      # positive frac
        heat = min(1.0, abs(mae) / allowed) if allowed > 0 else None

    if heat is not None and heat >= 0.9:
        verdict = ("this trade has used nearly all the pain its stop allows — "
                   "another move against you triggers the exit")
    elif give_back is not None and give_back >= 0.6 and mfe >= 0.03:
        verdict = (f"gave back {give_back:.0%} of a {mfe:.1%} run-up — the exit "
                   "plan's review clock exists for exactly this")
    elif mae >= -0.005:
        verdict = "barely tested — this position has not been under real pressure"
    else:
        verdict = "within normal excursion for a held position"

    return PositionExcursion(
        symbol=symbol.upper(), entry_price=round(entry_price, 4),
        current_price=round(current, 4), bars_held=n,
        mae_frac=round(mae, 6), mfe_frac=round(mfe, 6), current_frac=round(cur, 6),
        give_back_frac=None if give_back is None else round(give_back, 4),
        mae_price=round(worst, 4), mfe_price=round(best, 4),
        stop_price=None if stop_price is None else round(stop_price, 4),
        heat_used_frac=None if heat is None else round(heat, 4),
        verdict=verdict,
    )


@dataclass(frozen=True)
class ExcursionBook:
    positions: list
    worst_mae: dict | None       # the position that has hurt most
    biggest_give_back: dict | None
    warnings: list = field(default_factory=list)
    note: str = DAILY_BARS_NOTE


def excursion_book(rows: list[PositionExcursion],
                   warnings: list[str] | None = None) -> ExcursionBook:
    if not rows:
        return ExcursionBook(positions=[], worst_mae=None, biggest_give_back=None,
                             warnings=warnings or ["no open positions"])
    worst = min(rows, key=lambda r: r.mae_frac)
    gb = [r for r in rows if r.give_back_frac is not None]
    biggest = max(gb, key=lambda r: r.give_back_frac) if gb else None
    return ExcursionBook(
        positions=rows,
        worst_mae={"symbol": worst.symbol, "mae_frac": worst.mae_frac},
        biggest_give_back=(None if biggest is None else
                           {"symbol": biggest.symbol,
                            "give_back_frac": biggest.give_back_frac}),
        warnings=warnings or [],
    )
