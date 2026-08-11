"""Deterministic portfolio aggregation (T015). The LLM narrates these numbers; it never
computes them (AGENTS.md Determinism rule).

Inputs are duck-typed: any objects with symbol/qty/market_value/cost_basis/unrealized_pl
attributes (e.g. data.alpaca.Position) — analysis stays decoupled from broker clients.
"""

from dataclasses import dataclass
from typing import Iterable, Protocol


class PositionLike(Protocol):
    symbol: str
    qty: float
    market_value: float
    cost_basis: float
    unrealized_pl: float


@dataclass(frozen=True)
class PositionView:
    symbol: str
    qty: float
    market_value: float
    cost_basis: float
    unrealized_pl: float
    return_frac: float | None  # None when cost basis is 0 (e.g. free shares)
    weight_frac: float  # share of total market value, 0..1


@dataclass(frozen=True)
class PortfolioSummary:
    total_market_value: float
    total_cost_basis: float
    total_unrealized_pl: float
    total_return_frac: float | None
    positions: list[PositionView]


@dataclass(frozen=True)
class WinLossBreakdown:
    """Green vs red across open positions, by unrealized P&L. Natural signs throughout:
    total_gain >= 0 is the sum over winners, total_loss <= 0 the sum over losers."""

    winners: int
    losers: int
    flat: int
    total_gain: float
    total_loss: float
    net: float
    best_symbol: str | None
    best_pl: float | None
    worst_symbol: str | None
    worst_pl: float | None


def win_loss(positions: Iterable[PositionLike]) -> WinLossBreakdown:
    """Count and size winners vs losers among open positions."""
    items = list(positions)
    winners = [p for p in items if p.unrealized_pl > 0]
    losers = [p for p in items if p.unrealized_pl < 0]
    total_gain = sum(p.unrealized_pl for p in winners)
    total_loss = sum(p.unrealized_pl for p in losers)
    best = max(items, key=lambda p: p.unrealized_pl) if items else None
    worst = min(items, key=lambda p: p.unrealized_pl) if items else None
    return WinLossBreakdown(
        winners=len(winners),
        losers=len(losers),
        flat=len(items) - len(winners) - len(losers),
        total_gain=total_gain,
        total_loss=total_loss,
        net=total_gain + total_loss,
        best_symbol=best.symbol if best else None,
        best_pl=best.unrealized_pl if best else None,
        worst_symbol=worst.symbol if worst else None,
        worst_pl=worst.unrealized_pl if worst else None,
    )


def summarize(positions: Iterable[PositionLike]) -> PortfolioSummary:
    """Aggregate holdings into totals, per-position returns, and portfolio weights."""
    items = list(positions)
    total_mv = sum(p.market_value for p in items)
    total_cb = sum(p.cost_basis for p in items)
    total_pl = sum(p.unrealized_pl for p in items)

    views = [
        PositionView(
            symbol=p.symbol,
            qty=p.qty,
            market_value=p.market_value,
            cost_basis=p.cost_basis,
            unrealized_pl=p.unrealized_pl,
            return_frac=(p.unrealized_pl / p.cost_basis) if p.cost_basis > 0 else None,
            weight_frac=(p.market_value / total_mv) if total_mv > 0 else 0.0,
        )
        for p in items
    ]
    views.sort(key=lambda v: v.market_value, reverse=True)

    return PortfolioSummary(
        total_market_value=total_mv,
        total_cost_basis=total_cb,
        total_unrealized_pl=total_pl,
        total_return_frac=(total_pl / total_cb) if total_cb > 0 else None,
        positions=views,
    )
