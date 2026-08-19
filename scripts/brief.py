"""T062c — generate a brief on a schedule, no server required.

    python scripts/brief.py                    # morning brief, printed + saved
    python scripts/brief.py --type eod
    python scripts/brief.py --type weekly --no-save

WINDOWS TASK SCHEDULER (weekdays; from an admin-less prompt, one line each —
substitute your repo path; VENV = <repo>\\.venv\\Scripts\\python.exe):
    schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 09:00 ^
      /TN "KUBERA morning brief" /TR "<VENV> <repo>\\scripts\\brief.py"
    schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:15 ^
      /TN "KUBERA eod report" /TR "<VENV> <repo>\\scripts\\brief.py --type eod"

Composes DIRECTLY via api/brief.py — the same deterministic composition the
chat tool narrates — so the schedule works whether or not the server is up.
Output: full JSON to stdout (pipe-friendly) and, unless --no-save, to
private/briefs/<type>-<market-date>.json (gitignored with the rest of
private/; briefs contain holdings and P&L). Optional clients (FRED/FMP/
EDGAR-fed sections) construct best-effort exactly like the endpoint.

This closes T062b's last open item (scheduled auto-generation). The other
T062b leftovers stay where they were dispositioned: PWA push is Phase 5;
ET-aware windows landed with T111.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import httpx  # noqa: E402

from analysis.market_time import market_today  # noqa: E402
from api.brief import (  # noqa: E402
    compose_eod_report,
    compose_morning_brief,
    compose_weekly_review,
)
from data.alpaca import AlpacaClient, AlpacaError  # noqa: E402
from data.db import make_engine, make_session_factory  # noqa: E402
from data.market_data import MarketDataClient  # noqa: E402
from settings import ConfigError, get_settings  # noqa: E402


def _optional_clients():
    """FRED/FMP best-effort, mirroring the /api/brief endpoint."""
    fred = fmp = None
    try:
        from data.fred import FredClient
        fred = FredClient(settings=get_settings())
    except ConfigError:
        pass
    try:
        from data.fmp import FmpClient
        fmp = FmpClient(settings=get_settings())
    except ConfigError:
        pass
    return fred, fmp


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a KUBERA brief (T062c).")
    ap.add_argument("--type", default="morning",
                    choices=("morning", "eod", "weekly"))
    ap.add_argument("--no-save", action="store_true",
                    help="print only; skip writing private/briefs/")
    args = ap.parse_args()

    try:
        get_settings().require_alpaca()
    except ConfigError as e:
        print(f"NOT CONFIGURED\n  {e}")
        return 2

    engine = make_engine(get_settings().database_url)
    factory = make_session_factory(engine)
    fred, fmp = _optional_clients()
    try:
        with AlpacaClient() as alpaca, factory() as session:
            if args.type == "morning":
                with MarketDataClient() as market:
                    payload = compose_morning_brief(session, alpaca, market,
                                                    fred=fred, fmp=fmp)
            elif args.type == "eod":
                payload = compose_eod_report(session, alpaca)
            else:
                with MarketDataClient() as market:
                    payload = compose_weekly_review(session, alpaca, market)
    except (AlpacaError, httpx.HTTPError) as e:
        print(f"BROKER/DATA UNREACHABLE — no brief composed\n  {type(e).__name__}: {e}")
        return 2
    finally:
        for c in (fred, fmp):
            if c is not None:
                c.close()

    text = json.dumps(payload, indent=2, default=str)
    print(text)

    if not args.no_save:
        out_dir = ROOT / "private" / "briefs"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{args.type}-{market_today().isoformat()}.json"
        out.write_text(text, encoding="utf-8")
        print(f"\nsaved: {out.relative_to(ROOT)}  (private/ — gitignored)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
