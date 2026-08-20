"""T127 — the Phase 7 gate as CODE (D029/T122): prose can't refuse, this can.

D029 declared "Phase 7 does not start without custody + budgets + isolation."
T110a/T110b BUILT those mechanisms; this script makes the gate itself
mechanical — a pre-flight that must print OPEN before any research
experiment (the Kronos candidate, T122, is the first) runs its first
attempt. Owner usage:

    python scripts\\phase7_gate.py --revision kronos-v1

Four checks, each of which RUNS the thing it verifies (D027 — asserting a
rail exists is not evidence; making it refuse is):

1. CUSTODY — at least one FROZEN holdout exists, and the custody seam
   actually refuses to serve a guarded symbol (assert_servable must raise;
   a rail that doesn't refuse is not a gate).
2. BUDGET — the revision's experiment budget is pre-registered
   (open_budget, T122 step 2) with attempts remaining. Failures count.
3. PRE-REGISTRATION — docs/research/experiments/<revision>.md exists and
   states the contamination rule (T122 step 1: only post-cutoff or
   paper-forward evaluation counts). A protocol nobody wrote down is a
   protocol nobody follows.
4. ISOLATION — live parity smoke through the real boundary, plus a
   two-sided env canary: a planted variable must be VISIBLE in-process
   (proving the canary is alive, not deaf) and INVISIBLE across the
   boundary (proving the boundary strips it).

Exit codes, schedulable: 0 = GATE OPEN, 1 = GATE CLOSED (reasons named),
2 = not configured (no DB / tables missing — run alembic upgrade head).
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

import json  # noqa: E402

from research.custody import FROZEN, CustodyError, guarded_symbols  # noqa: E402
from research.isolation import (  # noqa: E402
    assert_servable,
    run_inprocess,
    run_isolated,
)
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from data.models import ExperimentBudget, HoldoutWindow  # noqa: E402

DEFAULT_DB = REPO_ROOT / "kubera.sqlite3"
DEFAULT_EXPERIMENTS = REPO_ROOT / "docs" / "research" / "experiments"

# The parity/canary probe: reads closes AND peeks for the planted variable.
# In-process the peek must SEE it (canary alive); across the boundary it
# must NOT (boundary strips the environment). Same source, both sides.
_CANARY_VAR = "KUBERA_GATE_CANARY"
_PROBE_SOURCE = f"""
import os
def probe(closes):
    seen = 1.0 if os.environ.get("{_CANARY_VAR}") else 0.0
    return (sum(closes) / len(closes)) + seen * 1000.0
"""


def check_custody(session: Session) -> tuple[bool, list[str]]:
    rows = session.execute(select(HoldoutWindow)).scalars().all()
    frozen = [r for r in rows if r.state == FROZEN]
    lines = [f"holdouts: {len(rows)} total, {len(frozen)} frozen"]
    for r in rows:
        lines.append(f"  {r.name}: {r.state} (hash {r.params_hash})")
    if not frozen:
        lines.append(
            "FAIL: no FROZEN holdout — freeze one BEFORE experiment one "
            "(T122 step 3); a holdout frozen after seeing results is a "
            "training set with extra steps")
        return False, lines
    guarded = guarded_symbols(session)
    if not guarded:
        lines.append("FAIL: custody holds no symbols — an empty holdout "
                     "guards nothing")
        return False, lines
    probe_symbol = sorted(guarded)[0]
    try:
        assert_servable(session, probe_symbol)
    except CustodyError as e:
        lines.append(f"custody seam REFUSED '{probe_symbol}' as required: "
                     f"{str(e)[:80]}...")
        return True, lines
    lines.append(
        f"FAIL: assert_servable SERVED guarded symbol '{probe_symbol}' — "
        "the rail did not refuse, so it is not a gate (D027 #5)")
    return False, lines


def check_budget(session: Session, revision: str) -> tuple[bool, list[str]]:
    row = session.execute(
        select(ExperimentBudget).where(ExperimentBudget.revision == revision)
    ).scalars().first()
    if row is None:
        return False, [
            f"FAIL: no budget for revision '{revision}' — open_budget() "
            "BEFORE the first attempt (T122 step 2, D029); unlimited "
            "attempts turn any selection rule into noise mining"]
    used = len(json.loads(row.attempts_json or "[]"))
    lines = [f"budget '{revision}': {used}/{row.max_attempts} attempts used "
             "(failures count)"]
    if used >= row.max_attempts:
        lines.append("FAIL: budget exhausted — a NEW revision gets a NEW "
                     "pre-registered budget; more tries on the same idea is "
                     "the loop two-strikes exists to stop")
        return False, lines
    return True, lines


def check_preregistration(experiments_dir: Path,
                          revision: str) -> tuple[bool, list[str]]:
    doc = experiments_dir / f"{revision}.md"
    if not doc.exists():
        return False, [
            f"FAIL: no pre-registration at {doc} — write the protocol "
            "BEFORE the first run (T122 step 1): what will be evaluated, "
            "on what window, and the contamination rule in your own words"]
    text = doc.read_text(encoding="utf-8").lower()
    has_rule = "contamination" in text and (
        "post-cutoff" in text or "paper-forward" in text)
    if not has_rule:
        return False, [
            f"FAIL: {doc.name} exists but does not state the contamination "
            "rule (must name 'contamination' and 'post-cutoff' or "
            "'paper-forward') — a backtest on the model's own training data "
            "is not evidence (D037)"]
    return True, [f"pre-registration present: {doc.name} "
                  "(contamination rule stated)"]


def check_isolation() -> tuple[bool, list[str]]:
    closes = [100.0, 101.0, 102.0, 103.0]
    os.environ[_CANARY_VAR] = "planted-by-phase7-gate"
    try:
        inproc = run_inprocess(_PROBE_SOURCE, "probe", closes)
        iso = run_isolated(_PROBE_SOURCE, "probe", closes, timeout_s=30.0)
    finally:
        os.environ.pop(_CANARY_VAR, None)
    if any(v < 1000.0 for v in inproc):
        return False, [
            "FAIL: the canary is DEAF — in-process run did not see the "
            "planted variable, so 'isolated run saw nothing' would prove "
            "nothing (D027 #3)"]
    if iso.error is not None:
        return False, [f"FAIL: isolated run errored: {iso.error}"]
    if iso.weights is None or any(v >= 1000.0 for v in iso.weights):
        return False, [
            "FAIL: the boundary LEAKED — the isolated run saw the planted "
            "environment variable (T110b's allowlist is not holding)"]
    expected = [v - 1000.0 for v in inproc]  # strip the canary marker
    if [round(v, 9) for v in iso.weights] != [round(v, 9) for v in expected]:
        return False, [
            "FAIL: parity broke — isolated output differs from in-process "
            f"on identical input ({iso.weights} vs {expected})"]
    return True, [
        f"isolation: parity holds on {len(closes)} bars, canary alive "
        f"in-process and stripped across the boundary "
        f"({iso.duration_s:.2f}s, {iso.stray_stdout_bytes} stray bytes)"]


def run_gate(session: Session, revision: str,
             experiments_dir: Path) -> int:
    checks = [
        ("custody", lambda: check_custody(session)),
        ("budget", lambda: check_budget(session, revision)),
        ("pre-registration", lambda: check_preregistration(
            experiments_dir, revision)),
        ("isolation", check_isolation),
    ]
    all_ok = True
    for name, fn in checks:
        ok, lines = fn()
        all_ok = all_ok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        for line in lines:
            print(f"    {line}")
    print("-" * 70)
    if all_ok:
        print(f"PHASE 7 GATE: OPEN for revision '{revision}' — every "
              "attempt still consumes budget; the holdout is consumed "
              "exactly once")
        return 0
    print(f"PHASE 7 GATE: CLOSED for revision '{revision}' — reasons named "
          "above; fix them, don't route around them (D029)")
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Pre-flight for any Phase 7 research experiment.")
    ap.add_argument("--revision", required=True,
                    help="experiment revision this gate run is for")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--experiments-dir", type=Path,
                    default=DEFAULT_EXPERIMENTS)
    args = ap.parse_args(argv)

    if not args.db.exists():
        print(f"NOT CONFIGURED — no database at {args.db}; run "
              "`alembic -c backend/alembic.ini upgrade head` first")
        return 2
    engine = create_engine(f"sqlite:///{args.db.as_posix()}")
    try:
        with sessionmaker(bind=engine)() as session:
            try:
                return run_gate(session, args.revision, args.experiments_dir)
            except OperationalError as e:
                print(f"NOT CONFIGURED — custody tables missing ({e}); run "
                      "`alembic -c backend/alembic.ini upgrade head`")
                return 2
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
