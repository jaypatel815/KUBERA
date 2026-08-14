"""T093 — strategy decay check: is the promoted strategy still earning its badge?

Compares ACCOUNT-level daily returns (from account_snapshots) against the
promoted backtest's implicit daily expectation with a one-sided CUSUM. On a
sustained shortfall it can DEMOTE the (template, symbol) pair — the paper
loop's require_promotion gate then refuses new buys automatically.

HONEST LIMITATION printed with every run: account returns are a fair proxy
only while ONE strategy trades this account.

Usage (owner machine):
    python scripts\\decay_check.py regime_router SPY
    python scripts\\decay_check.py regime_router SPY --demote   # act on alarm
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from backtest.decay import (  # noqa: E402
    ACCOUNT_PROXY_NOTE,
    cusum_shortfall,
    demote,
    expected_daily_return,
)
from data.db import make_engine, make_session_factory  # noqa: E402
from data.models import AccountSnapshot, BacktestRun  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("template")
    ap.add_argument("symbol")
    ap.add_argument("--days", type=int, default=30,
                    help="trailing snapshot days to evaluate")
    ap.add_argument("--demote", action="store_true",
                    help="on alarm, flip the promotion to 'demoted'")
    args = ap.parse_args()

    engine = make_engine()
    with make_session_factory(engine)() as db:
        promoted = None
        for r in db.execute(
            select(BacktestRun).where(
                BacktestRun.symbol == args.symbol.upper(),
                BacktestRun.promotion_status == "passed_walk_forward",
            ).order_by(BacktestRun.ts.desc())
        ).scalars():
            if json.loads(r.params_json).get("template") == args.template:
                promoted = r
                break
        if promoted is None:
            print(f"no promoted run for {args.template}/{args.symbol.upper()} — "
                  "nothing to check")
            return 1

        snaps = db.execute(
            select(AccountSnapshot).order_by(AccountSnapshot.asof.desc())
            .limit(args.days + 1)
        ).scalars().all()[::-1]
        if len(snaps) < 8:
            print(f"only {len(snaps)} account snapshots — need ~8+ days of "
                  "sync history (run scripts/sync.py daily)")
            return 1
        equities = [s.equity for s in snaps]
        live = [equities[i] / equities[i - 1] - 1.0
                for i in range(1, len(equities))]

        mu = expected_daily_return(promoted.cumulative_return,
                                   promoted.bars_count)
        res = cusum_shortfall(live, mu)
        print(f"{args.template}/{args.symbol.upper()}: expectation "
              f"{mu * 10000:.1f} bps/day (run #{promoted.id}), "
              f"{res.n_days} live days")
        print(f"CUSUM {res.stat:.4f} (peak {res.peak:.4f}, "
              f"threshold {res.threshold}) -> "
              f"{'ALARM' if res.alarm else 'ok'}")
        print(f"note: {ACCOUNT_PROXY_NOTE}")
        if res.alarm:
            print(f"sustained shortfall since day {res.crossed_at}")
            if args.demote:
                n = demote(db, args.template, args.symbol,
                           f"CUSUM decay alarm: stat {res.stat:.4f} > "
                           f"{res.threshold} over {res.n_days}d")
                print(f"DEMOTED {n} run(s) — the paper loop will refuse new "
                      "buys until re-promoted")
            else:
                print("run again with --demote to act on it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
