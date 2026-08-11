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

from data.alpaca import AlpacaClient  # noqa: E402
from data.db import make_engine, make_session_factory  # noqa: E402
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
            print(f"synced {r.positions} positions, equity {r.equity:.2f}, asof {r.asof:%H:%M:%S}")
        if not args.loop:
            return 0
        time.sleep(args.loop)


if __name__ == "__main__":
    sys.exit(main())
