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
from data.sync import sync_once  # noqa: E402


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
        if not args.loop:
            return 0
        time.sleep(args.loop)


if __name__ == "__main__":
    sys.exit(main())
