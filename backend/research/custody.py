"""T110a — evidence custody for the learning loop (D029): the two PURE
preconditions, built BEFORE Phase 7 opens so its opening is never blocked.

WHY THIS EXISTS. D029's review of the deep-agents article adopted three hard
preconditions for any research agent: (1) a reserved HOLDOUT window the agent
cannot touch until a deliberate unlock, evaluated EXACTLY ONCE, with no
revision allowed after the result is known — because a holdout consulted
twice is a training set with extra steps; (2) per-revision EXPERIMENT
BUDGETS, failures included, recorded append-only — because unlimited
attempts turn any selection rule into noise mining (and the owner's
two-strikes rule generalises: bounded attempts, always); (3) an isolation
boundary with an adversarial probe — that one needs real sandboxing design
and is EXPLICITLY split to T110b, not half-built here.

Custody state machine (one-way, enforced):
    FROZEN -> UNLOCKED -> CONSUMED
- freeze() stamps a params_hash of (symbols, start, end) so the window
  cannot be quietly redefined after freezing — a changed definition is a
  NEW holdout, not an edit.
- unlock() is the deliberate act (CLI/owner-side when Phase 7 opens); it
  works exactly once, on a FROZEN record.
- consume() records the ONE evaluation (result summary text) and closes the
  record forever. Second unlock, second consume, or consume-before-unlock
  all refuse with named errors.
- Every transition appends to a journal column — the record carries its own
  history; nothing is ever overwritten.

Budgets:
- open_budget(revision, max_attempts) once per revision.
- record_attempt() appends (ok or failed — failures COUNT; that is the
  point) and refuses once attempts == budget, naming the two-strikes spirit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import ExperimentBudget, HoldoutWindow

FROZEN = "frozen"
UNLOCKED = "unlocked"
CONSUMED = "consumed"


class CustodyError(RuntimeError):
    """Named refusal — custody violations are never silent."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def params_hash(symbols: list[str], start: str, end: str) -> str:
    """Deterministic identity of a holdout definition."""
    payload = json.dumps({"symbols": sorted(s.upper() for s in symbols),
                          "start": start, "end": end}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _append_journal(row: HoldoutWindow, event: str) -> None:
    entries = json.loads(row.journal_json or "[]")
    entries.append({"at": _now(), "event": event})
    row.journal_json = json.dumps(entries)


def freeze_holdout(session: Session, name: str, symbols: list[str],
                   start: str, end: str) -> HoldoutWindow:
    """Create a FROZEN holdout. A name can exist once — re-freezing an
    existing name refuses (a redefined holdout is contamination, not admin)."""
    existing = session.execute(
        select(HoldoutWindow).where(HoldoutWindow.name == name)
    ).scalars().first()
    if existing is not None:
        raise CustodyError(
            f"holdout '{name}' already exists (state={existing.state}) — a "
            "holdout is defined ONCE; a different window needs a new name")
    if not symbols or start >= end:
        raise CustodyError("holdout needs symbols and start < end")
    row = HoldoutWindow(
        name=name,
        symbols_json=json.dumps(sorted(s.upper() for s in symbols)),
        start=start, end=end,
        params_hash=params_hash(symbols, start, end),
        state=FROZEN,
        journal_json="[]",
    )
    _append_journal(row, f"frozen with hash {row.params_hash}")
    session.add(row)
    session.commit()
    return row


def _get(session: Session, name: str) -> HoldoutWindow:
    row = session.execute(
        select(HoldoutWindow).where(HoldoutWindow.name == name)
    ).scalars().first()
    if row is None:
        raise CustodyError(f"no holdout named '{name}'")
    return row


def unlock_holdout(session: Session, name: str, by: str) -> HoldoutWindow:
    """The deliberate act. Works exactly once, on a FROZEN record."""
    row = _get(session, name)
    if row.state != FROZEN:
        raise CustodyError(
            f"holdout '{name}' is {row.state} — unlock works ONCE, on a "
            "frozen record; there is no re-lock (a re-lockable holdout is "
            "not a holdout)")
    row.state = UNLOCKED
    _append_journal(row, f"unlocked by {by}")
    session.commit()
    return row


def consume_holdout(session: Session, name: str, result_summary: str,
                    evaluated_hash: str) -> HoldoutWindow:
    """Record THE evaluation. evaluated_hash must match the frozen hash —
    proof the evaluation ran the window as defined, not a variant."""
    row = _get(session, name)
    if row.state == FROZEN:
        raise CustodyError(
            f"holdout '{name}' is still frozen — unlock is the deliberate "
            "act and it has not happened")
    if row.state == CONSUMED:
        raise CustodyError(
            f"holdout '{name}' was already consumed — one evaluation is the "
            f"whole point; its result stands: {row.result_summary!r}")
    if evaluated_hash != row.params_hash:
        raise CustodyError(
            f"evaluated hash {evaluated_hash} != frozen hash "
            f"{row.params_hash} — the evaluation did not run the window as "
            "defined; refusing to record it")
    row.state = CONSUMED
    row.result_summary = result_summary[:1000]
    _append_journal(row, "consumed (single evaluation recorded)")
    session.commit()
    return row


def guarded_symbols(session: Session) -> frozenset[str]:
    """Symbols under ANY unconsumed custody — what a future data layer must
    refuse to serve the research agent (the enforcement hook for T110b)."""
    rows = session.execute(
        select(HoldoutWindow).where(HoldoutWindow.state != CONSUMED)
    ).scalars().all()
    out: set[str] = set()
    for r in rows:
        out.update(json.loads(r.symbols_json))
    return frozenset(out)


# ------------------------------------------------------------------ budgets


@dataclass(frozen=True)
class AttemptReceipt:
    revision: str
    attempt_number: int
    remaining: int


def open_budget(session: Session, revision: str, max_attempts: int) -> None:
    """One budget per revision, set BEFORE experimenting (pre-registration)."""
    if max_attempts < 1:
        raise CustodyError("a budget below 1 is a ban, not a budget")
    existing = session.execute(
        select(ExperimentBudget).where(ExperimentBudget.revision == revision)
    ).scalars().first()
    if existing is not None:
        raise CustodyError(
            f"revision '{revision}' already has a budget of "
            f"{existing.max_attempts} — budgets are set once, before "
            "experimenting; raising one mid-run is how noise mining starts")
    session.add(ExperimentBudget(revision=revision, max_attempts=max_attempts,
                                 attempts_json="[]"))
    session.commit()


def record_attempt(session: Session, revision: str, outcome: str,
                   note: str = "") -> AttemptReceipt:
    """Append one attempt (ok/failed — FAILURES COUNT). Refuses over budget."""
    row = session.execute(
        select(ExperimentBudget).where(ExperimentBudget.revision == revision)
    ).scalars().first()
    if row is None:
        raise CustodyError(f"no budget opened for revision '{revision}' — "
                           "open_budget first (pre-registration, D029)")
    attempts = json.loads(row.attempts_json or "[]")
    if len(attempts) >= row.max_attempts:
        raise CustodyError(
            f"revision '{revision}' has used its budget "
            f"({row.max_attempts} attempts, failures included) — more tries "
            "on the same idea is the loop the two-strikes rule exists to "
            "stop; a NEW revision gets a NEW pre-registered budget")
    attempts.append({"at": _now(), "outcome": outcome, "note": note[:300]})
    row.attempts_json = json.dumps(attempts)
    session.commit()
    return AttemptReceipt(revision=revision, attempt_number=len(attempts),
                          remaining=row.max_attempts - len(attempts))
