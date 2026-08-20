"""T065 — disable/enable symbols for NEW BUYS. Sells are never blocked.

    python scripts/risk_symbols.py --list
    python scripts/risk_symbols.py --disable TSLA GME
    python scripts/risk_symbols.py --enable TSLA

A deliberate, typed act — like the breaker reset (T035). No chat tool can
reach this: changing a rail through conversation is the failure mode the
tiers exist to prevent. State persists in risk_state and the loop's
pre-trade gate refuses disabled buys with a named reason.

Order-frequency limits are NOT here: T055's max_trades_per_day already
enforces them in the loop. Cancel-all is NOT here either: the paper loop
places market orders only — nothing rests to cancel; the day resting
orders exist, that control gets built with them.
"""

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from data.db import make_engine, make_session_factory  # noqa: E402
from risk.engine import RiskEngine, RiskLimits  # noqa: E402
from risk.persistence import persist_risk_state, restore_risk_state  # noqa: E402
from settings import get_settings  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Disable/enable symbols for new buys (T065).")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--disable", nargs="+", default=[], metavar="SYMBOL")
    ap.add_argument("--enable", nargs="+", default=[], metavar="SYMBOL")
    args = ap.parse_args()

    engine = make_engine(get_settings().database_url)
    factory = make_session_factory(engine)
    with factory() as session:
        risk = RiskEngine(limits=RiskLimits.from_settings(get_settings()))
        restore_risk_state(session, risk)
        current = set(risk.disabled_symbols)
        before = sorted(current)

        current |= {s.upper() for s in args.disable}
        current -= {s.upper() for s in args.enable}
        if args.disable or args.enable:
            risk.set_disabled_symbols(current)
            persist_risk_state(session, risk)

        after = sorted(risk.disabled_symbols)
        if args.list or not (args.disable or args.enable):
            print(f"disabled for new buys: {', '.join(after) or '(none)'}")
        else:
            print(f"before: {', '.join(before) or '(none)'}")
            print(f"after:  {', '.join(after) or '(none)'}")
            print("Sells were never blocked — reducing risk is always allowed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
