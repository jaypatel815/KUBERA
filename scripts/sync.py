"""Run a snapshot sync against the paper account.

One-shot (default):   python scripts/sync.py
Continuous:           python scripts/sync.py --loop 300      (every 5 minutes, Ctrl+C to stop)

The database schema must exist first:  alembic -c backend/alembic.ini upgrade head
"""

import argparse
import logging
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from data.alpaca import AlpacaClient, AlpacaError  # noqa: E402
from data.db import make_engine, make_session_factory  # noqa: E402
from data.fills import sync_fills  # noqa: E402
from data.flows import sync_cash_flows  # noqa: E402
from data.schwab import SchwabClient, SchwabError  # noqa: E402
from data.schwab_sync import sync_schwab_fills  # noqa: E402
from data.sync import sync_once  # noqa: E402
from settings import ConfigError, get_settings  # noqa: E402


def _sync_schwab(factory) -> str:
    """T016c: the owner's REAL fills, best-effort. Two conditions are EXPECTED
    and must never kill the sync: no Schwab config (skip with a note) and the
    ~weekly token lapse (name the fix, carry on). Anything else raises."""
    try:
        get_settings().require_schwab()
    except ConfigError:
        return "schwab: not configured (optional)"
    try:
        with SchwabClient() as client, factory() as session:
            s = sync_schwab_fills(session, client)
        return s.summary()
    except SchwabError as e:
        # Best-effort: the Alpaca half already synced; a Schwab transport
        # failure must not kill the run. Token lapse gets its named fix.
        if "expire roughly weekly" in str(e):
            return ("schwab: token refresh failed — the ~weekly token lapsed, "
                    "run `python scripts\\schwab_auth.py --write` (not a bug)")
        return f"schwab: skipped ({type(e).__name__}: {e})"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="KUBERA snapshot sync (paper account)")
    parser.add_argument("--loop", type=int, metavar="SECONDS", default=0,
                        help="repeat every N seconds (default: run once)")
    args = parser.parse_args()

    engine = make_engine()
    factory = make_session_factory(engine)
    while True:
        with AlpacaClient() as client, factory() as session:
            r = sync_once(session, client)
            f = sync_fills(session, client)
            try:
                cf = sync_cash_flows(session, client)
                flows_note = f"flows +{cf.inserted}/{cf.skipped} known"
            except AlpacaError as e:  # activities endpoint unavailable: never fatal
                flows_note = f"flows skipped ({type(e).__name__})"
            print(f"synced {r.positions} positions, equity {r.equity:.2f}, "
                  f"fills +{f.inserted}/{f.skipped} known, {flows_note}, "
                  f"asof {r.asof:%H:%M:%S}")
        print(_sync_schwab(factory))
        if not args.loop:
            return 0
        time.sleep(args.loop)


if __name__ == "__main__":
    sys.exit(main())
