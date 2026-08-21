"""T137 — backfill EDGAR earnings history into the store, once per symbol.

The probe that seeded this ticket: EdgarClient.earnings_history() serves
years of real filing dates with real acceptance clocks (T083b), but the
tools FETCH it per call and persist NOTHING — earnings_observed
self-accumulates only from the forward FMP window (T083). So base rates
and the T116b days-lens caveats start thin for any symbol the owner
hasn't watched for months, while the history sits free on EDGAR.

    py scripts\\earnings_backfill.py SPY QQQ NVDA
    py scripts\\earnings_backfill.py --watchlist     # every watchlist symbol

Per symbol: fetch the item-2.02 8-K history, derive the time hint from the
real acceptance clock (before 09:30 ET = bmo, after 16:00 ET = amc, else
during — a measured fact, not a guess), and upsert via the store's own
record_events (idempotent: existing rows are never overwritten, re-running
is safe). eps figures stay None — EDGAR filings don't carry estimates,
and a None is honest where FMP's forward window later enriches (T121).
Source-labeled "edgar-backfill" so every row's provenance survives.

Sandbox note: sec.gov is unreachable from the agent sandbox (I002-class);
tests inject fakes and the owner runs this live. Exit 0 ok / 1 failures
named / 2 not configured.
"""

import argparse
import sys
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from data.earnings_store import record_events  # noqa: E402
from data.edgar import EdgarClient, EdgarError  # noqa: E402
from settings import ConfigError  # noqa: E402

DEFAULT_DB = REPO_ROOT / "kubera.sqlite3"
ET = ZoneInfo("America/New_York")


class _Event:
    """The duck record_events expects: symbol/date/time_hint/eps fields."""

    def __init__(self, symbol, date_, time_hint):
        self.symbol = symbol
        self.date = date_
        self.time_hint = time_hint
        self.eps_estimated = None
        self.eps_actual = None


def hint_from_acceptance(acceptance_utc) -> str | None:
    """bmo/amc/during from the REAL filing clock (T083b's whole point) —
    None when EDGAR omitted the timestamp; never a guess."""
    if acceptance_utc is None:
        return None
    ts = acceptance_utc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    et = ts.astimezone(ET)
    minutes = et.hour * 60 + et.minute
    if minutes < 9 * 60 + 30:
        return "bmo"
    if minutes >= 16 * 60:
        return "amc"
    return "during"


def backfill_symbol(session, edgar, symbol: str) -> tuple[int, int]:
    """(rows_changed, filings_seen). Raises EdgarError upward — the caller
    names it per symbol and continues."""
    hist = edgar.earnings_history(symbol)
    events = [_Event(hist.symbol, f.filing_date,
                     hint_from_acceptance(f.acceptance_utc))
              for f in hist.filings]
    changed = record_events(session, events, source="edgar-backfill")
    return changed, len(hist.filings)


def _watchlist_symbols(session) -> list[str]:
    from data.models import WatchlistEntry  # local: table may not exist

    rows = session.execute(select(WatchlistEntry)).scalars().all()
    return sorted({r.symbol for r in rows})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Backfill EDGAR earnings dates into earnings_observed.")
    ap.add_argument("symbols", nargs="*", help="symbols to backfill")
    ap.add_argument("--watchlist", action="store_true",
                    help="backfill every watchlist symbol")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = ap.parse_args(argv)
    if not args.db.exists():
        print(f"NOT CONFIGURED — no database at {args.db}")
        return 2
    if not args.symbols and not args.watchlist:
        print("REFUSED: name symbols or pass --watchlist — backfilling "
              "nothing is not a run")
        return 1
    try:
        edgar = EdgarClient()
    except ConfigError as e:
        print(f"NOT CONFIGURED: {e}")
        return 2
    engine = create_engine(f"sqlite:///{args.db.as_posix()}")
    failures = 0
    try:
        with sessionmaker(bind=engine)() as session, edgar:
            symbols = list(args.symbols)
            if args.watchlist:
                symbols += _watchlist_symbols(session)
            symbols = sorted({s.upper() for s in symbols})
            if not symbols:
                print("watchlist is empty — nothing to backfill (that is "
                      "an answer)")
                return 0
            for sym in symbols:
                try:
                    changed, seen = backfill_symbol(session, edgar, sym)
                    print(f"{sym}: {seen} earnings 8-Ks on EDGAR, "
                          f"{changed} new row(s) stored "
                          f"({seen - changed} already present)")
                except EdgarError as e:
                    failures += 1
                    print(f"{sym}: FAILED — {e}")
        return 1 if failures else 0
    finally:
        engine.dispose()


# A polite pause between symbols is unnecessary: EdgarClient already
# rate-limits itself to the SEC's published etiquette (T083b) — stated so
# nobody adds a sleep out of caution and doubles the owner's wait.

if __name__ == "__main__":
    raise SystemExit(main())
