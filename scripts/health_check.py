"""KUBERA health check (D018) — catch silent failures before they cost hours.

Checks, in order:
1. API server reachable (GET /health)
2. Circuit breaker state (from the risk_state table — works even if the server is down)
3. Snapshot freshness (latest account_snapshot older than --max-sync-age minutes)

Prints one line per problem, exits 0 (healthy) / 1 (problems found), and — best
effort, Windows only — pops a toast notification so you notice without watching a
terminal. Schedule it every 5 minutes:

    schtasks /Create /SC MINUTE /MO 5 /TN "KUBERA health" ^
        /TR "py C:\\Users\\jaybe\\Projects\\KUBERA\\scripts\\health_check.py --notify"

Note: freshness is judged against wall-clock age, not market hours — outside
market hours an old snapshot is expected; read the message, not just the exit code.
"""

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

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


def run_checks(base_url: str, db: Session, max_sync_age_min: float) -> list[str]:
    problems = check_server(base_url)
    problems += check_breaker(db)
    problems += check_sync_freshness(db, max_sync_age_min)
    return problems


def notify_windows(title: str, message: str) -> None:
    """Best-effort toast via PowerShell; silently a no-op anywhere it can't work."""
    script = (
        "[reflection.assembly]::loadwithpartialname('System.Windows.Forms')|Out-Null;"
        "$n=New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon=[System.Drawing.SystemIcons]::Warning;$n.Visible=$true;"
        f"$n.ShowBalloonTip(10000,'{title}','{message}','Warning')"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, timeout=15, check=False,
        )
    except Exception:  # noqa: BLE001 — notification is never worth crashing over
        pass


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
