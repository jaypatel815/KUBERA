# KUBERA incident runbook (T128 — PROJECT_SPEC §7 Phase 8)

The spec asks for "a short runbook for incidents like 'the data feed is
down' or 'a strategy tripped the circuit breaker'". This is that document.
Every command here exists and is exit-coded; a test pins that every script
named below is real, so this file cannot quietly rot.

House rule for every incident: KUBERA is paper-only and advisory — no
incident here risks live capital. The failure mode being managed is BAD
INFORMATION (stale prints, silent gaps), and the cure is always the same:
trust the named refusals, never numbers that arrived without one.

---

## 1. "The data feed is down"

SYMPTOM: `health_check` prints `MARKET DATA FEED unreachable` or
`FEED STALE`; the monitor exits 2 with `BROKER/DATA UNREACHABLE`; chat
answers carry staleness phrases instead of live prices.

CHECK:
    py scripts\health_check.py          # names which of the 5 checks failed
    py scripts\monitor.py               # exit 2 = broker/data, not positions

FIX: usually nothing on our side — Alpaca outages pass. The T036b
staleness lens already labels every degraded read ("STALE — the feed is
behind"), the paper loop's market-hours guard refuses to act on stale
data, and briefs degrade to named notes. When the feed returns, run
`py scripts\sync.py` to refresh snapshots.

NEVER: act on a number that arrived with a staleness phrase attached. The
phrase IS the incident report.

## 2. "The circuit breaker tripped"

SYMPTOM: `health_check` prints `CIRCUIT BREAKER TRIPPED: <reason>`; the
paper loop refuses new entries; chat says the breaker is engaged.

CHECK:
    py scripts\health_check.py          # shows the trip reason from risk_state

UNDERSTAND FIRST: the breaker tripping is the system WORKING — it fired
on the daily-loss limit you set (T115: limits come from .env and are
rails, not suggestions). The reset is time-locked (T035 commitment
device): the cooldown exists because you asked, on a calm day, not to be
able to un-trip it on an angry one.

FIX (after the cooldown, if you still want to):
    py scripts\risk_reset.py            # names the lockout if still active

NEVER: raise `KUBERA_DAILY_LOSS_LIMIT_FRAC` on the same day the breaker
tripped. That is the exact move the rail exists to stop.

## 3. "CI is red"

SYMPTOM: GitHub Actions verify job exits 1.

CHECK, in order (the three historical shapes — I016, I018, I032 — were
all "green on the machine that had the thing, red on the machine that
didn't"):
    python scripts/verify.py            # red locally too? fix the finding
    # green locally? simulate the clean checkout CI actually sees:
    git ls-files -z | tar --null -T - -cf - | tar -x -C /tmp/cico
    cd /tmp/cico && python scripts/verify.py

The gate runs: ruff, pytest, memory budgets, python-pin unity, and
pyrefly at EXACTLY ZERO (T125) — a single new type error is a red gate,
by design.

## 4. "I need to restore the database"

The nightly backup (`scripts/backup_db.py`, 23:30) is only half the
insurance; the restore drill (`scripts/restore_check.py`, T124) is the
proof. To actually restore:

    1. Stop the server (Ctrl+C the uvicorn window).
    2. py scripts\restore_check.py      # 0 = newest backup restores clean;
                                        # 2 = schema drift, note the warning
    3. copy backups\kubera-<newest>.sqlite3 kubera.sqlite3
    4. alembic -c backend\alembic.ini upgrade head   # no-op unless drift
    5. py scripts\health_check.py       # snapshot age will name lost hours
    6. py scripts\sync.py               # re-pull current broker state

Rows written after the backup are gone; the journal is append-only, so
what survived is exactly what the backup's timestamp says.

## 5. "I think a key leaked"

CHECK:
    py scripts\secret_check.py          # scans every tracked file; parity too

FIX: rotate the key at its provider FIRST (Alpaca / FRED / FMP / Finnhub
/ Schwab dashboards), then update `.env`. The repo is public; treat any
suspected leak as real. `.env` is gitignored and the pre-commit hook
blocks it — `secret_check` runs inside the test suite, so a key-shaped
string in tracked files turns CI red on its own.

NEVER: paste a key into chat, a commit message, or an issue while
investigating. Names and lengths only.

## 6. "The server answers with the wrong brain / won't start"

SYMPTOM: replies are from a provider other than `.env`'s `LLM_PROVIDER`
(OS env vars beat .env — I014), or startup fails on config.

CHECK:
    py scripts\brain_check.py           # names which value won and from where
    py scripts\env_check.py             # names/lengths only, never values

## 7. "Schwab calls started failing"

SYMPTOM: `token refresh failed` — the refresh token expires ~weekly.

FIX:
    py scripts\schwab_auth.py --write   # one browser round-trip, paste URL

## 8. "Is Phase 7 allowed to run an experiment?"

    py scripts\phase7_gate.py --revision <name>
    # OPEN only when: a FROZEN holdout exists AND the custody seam refuses
    # a guarded symbol, the revision's budget is pre-registered with
    # attempts left, the pre-registration doc states the contamination
    # rule, and the isolation boundary holds parity with the env canary.

---

## Scheduled tasks (Windows Task Scheduler) — the full set

    schtasks /Create /SC DAILY  /ST 23:30 /TN "KUBERA backup"        /TR "py C:\Users\jaybe\Projects\KUBERA\scripts\backup_db.py"
    schtasks /Create /SC DAILY  /ST 23:45 /TN "KUBERA restore check" /TR "py C:\Users\jaybe\Projects\KUBERA\scripts\restore_check.py"
    schtasks /Create /SC MINUTE /MO 5     /TN "KUBERA health"        /TR "py C:\Users\jaybe\Projects\KUBERA\scripts\health_check.py --notify"
    schtasks /Create /SC DAILY  /ST 08:00 /TN "KUBERA morning brief" /TR "py C:\Users\jaybe\Projects\KUBERA\scripts\brief.py morning"

The monitor is interactive rather than scheduled — run it in a terminal
during sessions you're holding positions:
    py scripts\monitor.py --loop 300 --notify

Exit-code convention across all ops scripts: 0 = healthy/OK, 1 = needs
eyes (reasons printed), 2 = not configured / unreachable (named).
