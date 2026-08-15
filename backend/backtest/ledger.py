"""Backtest results ledger (T034): every run recorded, comparable, and auditable.

The §7.4 promotion checklist will read from here: a strategy earns paper (and one day,
with the owner's explicit approval, live) status by accumulating evidence in this table.
"""

import json
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backtest.engine import BacktestResult, Strategy, run_backtest
from backtest.stats import WalkForwardResult, walk_forward
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


def promote_template(
    session: Session,
    market: MarketDataClient,
    strategy: Strategy,
    template: str,
    symbol: str,
    days: int = 730,
    n_segments: int = 4,
    cost_bps: float = 5.0,
) -> tuple[WalkForwardResult, BacktestRun]:
    """The T064 promotion gate: run the anchored walk-forward on real history and
    record the verdict. The paper loop (require_promotion) honors ONLY runs whose
    promotion_status is 'passed_walk_forward' for this (template, symbol) pair."""
    result, row = run_and_record(
        session, market, strategy,
        {"template": template, "walk_forward_segments": n_segments},
        symbol, days=days, cost_bps=cost_bps,
    )
    wf = walk_forward(result.equity_curve, n_segments=n_segments)
    row.promotion_status = "passed_walk_forward" if wf.passed else "failed_walk_forward"
    params = json.loads(row.params_json)
    params["segment_returns"] = [round(r, 6) for r in wf.segment_returns]
    params["walk_forward_criteria"] = wf.criteria
    row.params_json = json.dumps(params, sort_keys=True)
    session.commit()
    return wf, row


def attach_stability(session: Session, template: str, symbol: str,
                     report: dict) -> int:
    """T092: record a StabilityReport (as dict) on the LATEST run for this
    (template, symbol) — the stability evidence lives beside the promotion.
    Returns the run id; raises if no run exists to attach to."""
    rows = session.execute(
        select(BacktestRun).where(BacktestRun.symbol == symbol.upper())
        .order_by(BacktestRun.ts.desc())
    ).scalars().all()
    for r in rows:
        try:
            if json.loads(r.params_json).get("template") == template:
                r.stability_json = json.dumps(report, sort_keys=True)
                session.commit()
                return r.id
        except (TypeError, ValueError):
            continue
    raise ValueError(
        f"no recorded run for template={template} symbol={symbol.upper()} — "
        "run a backtest (or promote) first, then attach stability"
    )


PROMOTION_MAX_AGE_DAYS = 180  # T064b: a pass is evidence, not a lifetime badge


def is_promoted(session: Session, template: str, symbol: str,
                max_age_days: int = PROMOTION_MAX_AGE_DAYS) -> bool:
    """Any recorded run for this (template, symbol) that passed the walk-forward
    AND is younger than `max_age_days`? Markets drift; a promotion earned on
    year-old history no longer speaks for today (T064b expiry). Re-promote to
    refresh the badge."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    rows = session.execute(
        select(BacktestRun).where(
            BacktestRun.symbol == symbol.upper(),
            BacktestRun.promotion_status == "passed_walk_forward",
        )
    ).scalars().all()
    for r in rows:
        ts = r.ts if r.ts.tzinfo else r.ts.replace(tzinfo=timezone.utc)
        if ts < cutoff:
            continue  # stale pass: does not count
        try:
            if json.loads(r.params_json).get("template") == template:
                return True
        except (TypeError, ValueError):
            continue
    return False


def latest_stability(session: Session, template: str, symbol: str) -> dict | None:
    """Most recent StabilityReport recorded for this pair (T092), or None."""
    rows = session.execute(
        select(BacktestRun).where(BacktestRun.symbol == symbol.upper())
        .order_by(BacktestRun.ts.desc())
    ).scalars().all()
    for r in rows:
        if not r.stability_json:
            continue
        try:
            if json.loads(r.params_json).get("template") == template:
                return json.loads(r.stability_json)
        except (TypeError, ValueError):
            continue
    return None
