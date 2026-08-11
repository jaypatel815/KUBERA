"""Backtest results ledger (T034): every run recorded, comparable, and auditable.

The §7.4 promotion checklist will read from here: a strategy earns paper (and one day,
with the owner's explicit approval, live) status by accumulating evidence in this table.
"""

import json
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backtest.engine import BacktestResult, Strategy, run_backtest
from data.market_data import MarketDataClient
from data.models import BacktestRun


def record_run(
    session: Session,
    result: BacktestResult,
    symbol: str,
    params: dict,
    cost_bps: float,
    source: str,
) -> BacktestRun:
    row = BacktestRun(
        strategy=result.strategy_name,
        params_json=json.dumps(params, sort_keys=True),
        symbol=symbol.upper(),
        start_date=result.dates[0],
        end_date=result.dates[-1],
        bars_count=len(result.dates),
        cost_bps=cost_bps,
        cumulative_return=result.cumulative_return,
        volatility_ann=result.volatility_ann,
        sharpe_ann=result.sharpe_ann,
        max_drawdown_frac=result.max_drawdown_frac,
        n_rebalances=result.n_rebalances,
        total_cost_frac=result.total_cost_frac,
        source=source,
    )
    session.add(row)
    session.commit()
    return row


def list_runs(
    session: Session,
    strategy: str | None = None,
    symbol: str | None = None,
    limit: int = 50,
) -> Sequence[BacktestRun]:
    if not 1 <= limit <= 500:
        raise ValueError(f"limit must be 1..500, got {limit}")
    q = select(BacktestRun).order_by(BacktestRun.ts.desc()).limit(limit)
    if strategy:
        q = q.where(BacktestRun.strategy == strategy)
    if symbol:
        q = q.where(BacktestRun.symbol == symbol.upper())
    return session.execute(q).scalars().all()


def run_and_record(
    session: Session,
    market: MarketDataClient,
    strategy: Strategy,
    strategy_params: dict,
    symbol: str,
    days: int = 730,
    cost_bps: float = 5.0,
) -> tuple[BacktestResult, BacktestRun]:
    """Backtest on real history and persist the evidence in one step."""
    bars = market.get_daily_bars(symbol, days=days)
    if len(bars.bars) < 2:
        raise ValueError(f"insufficient history for {symbol!r}")
    result = run_backtest(
        [b.close for b in bars.bars],
        [b.date for b in bars.bars],
        strategy,
        getattr(strategy, "__name__", "strategy"),
        cost_bps=cost_bps,
    )
    row = record_run(session, result, symbol, strategy_params, cost_bps, bars.source)
    return result, row
