"""Manually reset KUBERA's circuit breaker — the ONLY way a trip clears (spec §8).

Usage:
    python scripts/risk_reset.py                          # show current risk state
    python scripts/risk_reset.py --note "reviewed the drawdown, re-enabling"

The note is required and is written to the log: future-you deserves to know why.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from data.db import make_engine, make_session_factory  # noqa: E402
from risk.engine import LockoutActiveError, RiskEngine  # noqa: E402
from risk.persistence import persist_risk_state, restore_risk_state  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Show or reset KUBERA's risk state")
    parser.add_argument("--note", help="why you are resetting (required to reset)")
    args = parser.parse_args()

    engine = make_engine()
    factory = make_session_factory(engine)
    risk = RiskEngine()
    with factory() as db:
        existed = restore_risk_state(db, risk)
        if not existed:
            print("No saved risk state yet — nothing to show or reset.")
            return 0
        print(f"day={risk.day}  day_start_equity={risk.day_start_equity}  "
              f"tripped={risk.tripped}")
        if risk.tripped:
            print(f"trip reason: {risk.trip_reason}")

        if not args.note:
            if risk.tripped:
                print('\nTo reset: python scripts/risk_reset.py --note "your reason"')
            return 0
        if not risk.tripped:
            print("Breaker is not tripped — nothing to reset.")
            return 0

        confirm = input("Type RESET to confirm re-enabling trading: ").strip()
        if confirm != "RESET":
            print("Not confirmed — breaker stays tripped.")
            return 1
        try:
            risk.reset(args.note)
        except LockoutActiveError as e:
            print(f"\nRESET REFUSED: {e}")
            print("There is no override flag. That is the feature.")
            return 1
        persist_risk_state(db, risk)
        print("Breaker reset and persisted. Trading may resume next cycle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
