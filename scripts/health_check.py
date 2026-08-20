"""KUBERA health check (D018) — catch silent failures before they cost hours.

Checks, in order:
1. API server reachable (GET /health)
2. Circuit breaker state (from the risk_state table — works even if the server is down)
3. Snapshot freshness (latest account_snapshot older than --max-sync-age minutes)
4. Snapshot-vs-broker reconciliation drift (T093b)
5. Market-data FEED reachable + fresh (T129, Phase 8 "data feed outages":
   SPY probe through the T036b staleness lens; quiet when unconfigured)

Prints one line per problem, exits 0 (healthy) / 1 (problems found), and — best
effort, Windows only — pops a toast notification so you notice without watching a
terminal. Schedule it every 5 minutes:

    schtasks /Create /SC MINUTE /MO 5 /TN "KUBERA health" ^
        /TR "py C:\\Users\\jaybe\\Projects\\KUBERA\\scripts\\health_check.py --notify"

Note: freshness is judged against wall-clock age, not market hours — outside
market hours an old snapshot is expected; read the message, not just the exit code.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from notify import notify_windows  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from data.db import make_engine  # noqa: E402
from data.models import AccountSnapshot, RiskState  # noqa: E402
from settings import get_settings  # noqa: E402

DEFAULT_URL = "http://127.0.0.1:8000"


def check_server(base_url: str, client: httpx.Client | None = None) -> list[str]:
    try:
        c = client or httpx.Client(timeout=5.0)
        r = c.get(f"{base_url}/health")
        if r.status_code != 200:
            return [f"server unhealthy: GET /health returned {r.status_code}"]
    except Exception as e:  # noqa: BLE001 — any transport failure means "down"
        return [f"server unreachable at {base_url}: {type(e).__name__}"]
    return []


def check_breaker(db: Session) -> list[str]:
    row = db.execute(select(RiskState)).scalars().first()
    if row is not None and row.tripped:
        return [f"CIRCUIT BREAKER TRIPPED: {row.trip_reason}"]
    return []


def check_sync_freshness(
    db: Session, max_age_minutes: float, now: datetime | None = None
) -> list[str]:
    latest = db.execute(
        select(AccountSnapshot).order_by(AccountSnapshot.asof.desc())
    ).scalars().first()
    if latest is None:
        return ["no account snapshots yet — has scripts/sync.py ever run?"]
    now = now or datetime.now(timezone.utc)
    asof = latest.asof if latest.asof.tzinfo else latest.asof.replace(tzinfo=timezone.utc)
    age_min = (now - asof).total_seconds() / 60
    if age_min > max_age_minutes:
        return [f"last snapshot is {age_min:.0f} min old (threshold {max_age_minutes:.0f})"]
    return []


RECON_DRIFT_FRAC = 0.005  # 0.5% snapshot-vs-broker drift triggers a warning


def check_reconciliation(base_url: str, db: Session,
                         drift_frac: float = RECON_DRIFT_FRAC,
                         client: httpx.Client | None = None,
                         now: datetime | None = None) -> list[str]:
    """T093b: does our recorded state still match the broker? Compares the
    latest account_snapshot equity against the live server's /api/account.
    Quiet when the server is down or no snapshot exists — those conditions are
    already reported by check_server / check_sync_freshness; this check owns
    exactly one failure mode: BOTH sides reachable but disagreeing."""
    latest = db.execute(
        select(AccountSnapshot).order_by(AccountSnapshot.asof.desc())
    ).scalars().first()
    if latest is None:
        return []
    try:
        c = client or httpx.Client(timeout=5.0)
        r = c.get(f"{base_url}/api/account")
        if r.status_code != 200:
            return []
        live = float(r.json().get("equity", 0.0))
    except Exception:  # noqa: BLE001 — server-down is check_server's report
        return []
    if live <= 0:
        return []
    drift = abs(live - latest.equity) / live
    if drift <= drift_frac:
        return []
    now = now or datetime.now(timezone.utc)
    asof = latest.asof if latest.asof.tzinfo else latest.asof.replace(tzinfo=timezone.utc)
    age_min = (now - asof).total_seconds() / 60
    return [
        f"RECONCILIATION: snapshot equity {latest.equity:,.2f} vs broker "
        f"{live:,.2f} — drift {drift:.2%} (threshold {drift_frac:.1%}); snapshot "
        f"is {age_min:.0f} min old. A stale snapshot after market moves is "
        "normal — run scripts/sync.py; drift that SURVIVES a fresh sync is not "
        "normal — investigate before trusting any number"
    ]


FEED_PROBE_SYMBOL = "SPY"  # the most liquid print there is — if SPY is dark, the feed is down


def check_feed(settings=None, market=None, alpaca=None,
               now: datetime | None = None) -> list[str]:
    """T129 (Phase 8: "data feed outages"). Owns exactly two failure modes:
    the market-data FEED unreachable, and a print that T036b judges stale or
    old. Quiet when Alpaca isn't configured — an unconfigured box is not an
    outage. Market state comes from the broker clock when available; without
    it the T036b wallclock fallback judges conservatively and says so."""
    from analysis.staleness import classify_freshness, wallclock_fallback
    from data.market_data import MarketDataClient
    from settings import ConfigError

    s = settings if settings is not None else get_settings()
    if not s.alpaca_configured:
        return []
    try:
        own_market = market is None
        m = market or MarketDataClient(settings=s)
        try:
            trade = m.get_latest_trade(FEED_PROBE_SYMBOL)
        finally:
            if own_market:
                m.close()
    except ConfigError:
        return []
    except Exception as e:  # noqa: BLE001 — any transport failure IS the outage
        return [f"MARKET DATA FEED unreachable ({FEED_PROBE_SYMBOL} probe): "
                f"{type(e).__name__}: {e}"]

    now = now or datetime.now(timezone.utc)
    market_open = None
    if alpaca is not None:
        try:
            market_open = alpaca.get_clock().is_open
        except Exception:  # noqa: BLE001 — clock is a refinement, not the check
            market_open = None
    if market_open is None:
        fresh = wallclock_fallback(trade.exchange_ts, now,
                                   age_human=trade.age_human)
    else:
        fresh = classify_freshness(trade.exchange_ts, now, market_open,
                                   age_human=trade.age_human)
    if fresh.state in ("stale", "old"):
        return [f"MARKET DATA FEED {fresh.state.upper()}: {fresh.phrase}"]
    return []


def run_checks(base_url: str, db: Session, max_sync_age_min: float) -> list[str]:
    problems = check_server(base_url)
    problems += check_breaker(db)
    problems += check_sync_freshness(db, max_sync_age_min)
    problems += check_reconciliation(base_url, db)
    problems += check_feed()
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="KUBERA health check.")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--max-sync-age", type=float, default=30.0, help="minutes")
    ap.add_argument("--notify", action="store_true", help="Windows toast on problems")
    args = ap.parse_args()

    engine = make_engine(get_settings().database_url)
    with Session(engine) as db:
        problems = run_checks(args.url, db, args.max_sync_age)
    engine.dispose()

    if not problems:
        print(f"OK — server, breaker, and sync all healthy ({datetime.now():%H:%M:%S})")
        return 0
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    if args.notify:
        notify_windows("KUBERA health", " | ".join(problems)[:200])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
