"""T067b — DQS v2: score the OWNER's own trading, not the paper loop's.

v1 (risk/dqs.py) scores signal_log — what KUBERA's loop did. That was honest
about its own limit: "scoring your own fills arrives with the broker-fill sync
and the decision journal." Both have since landed (T016/T016b/T016c reconciled
his real fills three ways; T063 records decisions), so this module scores the
record that actually matters.

Same philosophy as v1 and T069: PROCESS, NOT OUTCOME. A disciplined loss beats
a lucky rule-break, and every component REFUSES on thin samples rather than
inventing a habit from three trades.

Components (each capped, each hand-computable):
- disposition_effect (≤30): the classic "cut winners, ride losers". Compares
  MEDIAN holding time of winning round trips vs losing ones. Winners held
  much shorter than losers is the tell. Medians, and both sides need
  MIN_TRIPS_PER_SIDE, so one lucky scalp cannot manufacture a verdict.
- revenge_sizing (≤30): reuses T069's sizing_drift measurement verbatim —
  ONE definition of the revenge pattern in the codebase, not two that can
  drift apart. Ratio > 1 = sizing up after losses. NOTE THE SHARED CONTRACT:
  sizing_drift reads `ts_iso` on fills and `exit_ts`/`pnl` on trips; passing
  a `ts` datetime silently yields "no measurement" rather than an error
  (caught while writing these tests — pinned in test_owner_dqs).
- journal_discipline (≤20): share of recorded decisions never marked
  followed/overridden. "A recommendation that isn't journaled didn't happen"
  (T063); one that is never marked cannot be calibrated either. Overriding
  KUBERA is NOT penalised — the owner's judgement is the point of the
  journal; only the un-marked (unmeasurable) share costs.

NOT SCORED, deliberately (T102 — no code for shapes we cannot observe):
FOMO-into-late-RVOL-spike needs an intraday clock on every fill plus that
day's volume profile. Statement-parsed fills are DATE-ONLY (time_known=False),
and the Schwab API fills that do carry execution times live in the DB store,
not the file-based trip record this scores. The gap is named in every report
rather than approximated — see `fomo_note`.

RISK BUDGET FROM THE IPS: budget_from_ips() converts the owner's ratified
max-drawdown tolerance into an implied DAILY loss budget using T069's own
convention (a third of the tolerable drawdown), and reports whether the
engine's enforced limit agrees. It PROPOSES; it never applies. Changing a
safety rail stays a deliberate, human, confirmation-gated act (T061/D014).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any, Sequence

from analysis.risk_tolerance import sizing_drift

MIN_TRIPS_PER_SIDE = 5      # winners AND losers needed before judging holds
MIN_DECISIONS = 5           # journal rows before judging journal discipline
IPS_DRAWDOWN_TO_DAILY = 3.0  # T069 convention: a day may risk 1/3 of the
                             # drawdown the owner says he can live through


@dataclass(frozen=True)
class OwnerDQSReport:
    score: float
    trips_scored: int
    components: dict[str, dict] = field(default_factory=dict)
    ips_budget: dict | None = None
    fomo_note: str = ""
    notes: list[str] = field(default_factory=list)
    note: str = ""


def _get(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _holds_by_outcome(trips: Sequence) -> tuple[list[float], list[float]]:
    """(winner holds, loser holds) in days — only trips with BOTH a P&L and a
    measured duration. Undated lots are skipped, never defaulted to zero."""
    wins, losses = [], []
    for t in trips:
        pnl = _get(t, "pnl")
        held = _get(t, "held_days")
        if pnl is None or held is None:
            continue
        try:
            pnl_f, held_f = float(pnl), float(held)
        except (TypeError, ValueError):
            continue
        if held_f < 0:
            continue
        if pnl_f > 0:
            wins.append(held_f)
        elif pnl_f < 0:
            losses.append(held_f)
    return wins, losses


def disposition_effect(trips: Sequence) -> dict:
    """Median winner hold vs median loser hold.

    ratio = median_winner_hold / median_loser_hold. Below 1 means winners are
    cut faster than losers are — the disposition effect. Penalty scales with
    the gap and caps at 30. Refuses under MIN_TRIPS_PER_SIDE on either side.
    """
    wins, losses = _holds_by_outcome(trips)
    if len(wins) < MIN_TRIPS_PER_SIDE or len(losses) < MIN_TRIPS_PER_SIDE:
        return {"penalty": 0.0, "ratio": None,
                "winners": len(wins), "losers": len(losses),
                "why": (f"insufficient sample — need {MIN_TRIPS_PER_SIDE} "
                        f"winning AND {MIN_TRIPS_PER_SIDE} losing round trips "
                        f"with measured holding times")}
    m_win, m_loss = median(wins), median(losses)
    if m_loss <= 0:
        return {"penalty": 0.0, "ratio": None,
                "winners": len(wins), "losers": len(losses),
                "why": "losers' median hold is zero — same-session trading, "
                       "no multi-day comparison to make"}
    ratio = m_win / m_loss
    penalty = min(30.0, max(0.0, (1.0 - ratio) * 60.0))
    return {
        "penalty": round(penalty, 1),
        "ratio": round(ratio, 4),
        "median_winner_hold_days": round(m_win, 3),
        "median_loser_hold_days": round(m_loss, 3),
        "winners": len(wins), "losers": len(losses),
        "reading": ("winners cut faster than losers — the disposition effect"
                    if ratio < 1 else
                    "winners held at least as long as losers — no cut-winners "
                    "signature in this sample"),
    }


def revenge_sizing(trips: Sequence, fills: Sequence) -> dict:
    """T069's sizing_drift, scored. Ratio > 1 = bigger buys after losses."""
    drift = sizing_drift(trips, fills)
    ratio = drift.get("ratio")
    if ratio is None:
        return {"penalty": 0.0, "ratio": None, "sample": drift.get("sample", 0),
                "why": "insufficient paired observations (T069 floor) — no "
                       "post-loss sizing habit measurable yet"}
    penalty = min(30.0, max(0.0, (float(ratio) - 1.0) * 30.0))
    return {
        "penalty": round(penalty, 1),
        "ratio": ratio,
        "after_loss_median": drift.get("after_loss"),
        "after_win_median": drift.get("after_win"),
        "sample": drift.get("sample"),
        "reading": ("sizes UP after losses — the revenge signature"
                    if float(ratio) > 1 else
                    "no size-up after losses in this sample"),
        "source": "analysis.risk_tolerance.sizing_drift (one definition, T069)",
    }


def journal_discipline(total: int | None, unmarked: int | None) -> dict:
    """Share of journaled decisions never marked followed/overridden.

    Overriding KUBERA is NOT a penalty — the owner's judgement is why the
    journal exists. Only never MARKING costs: an unmarked decision can never
    be calibrated, so the loop that turns decisions into lessons never closes.
    """
    if total is None or unmarked is None or total < MIN_DECISIONS:
        return {"penalty": 0.0, "unmarked_frac": None, "decisions": total or 0,
                "why": f"fewer than {MIN_DECISIONS} journaled decisions — "
                       "nothing to judge yet (record_decision builds this)"}
    frac = unmarked / total
    return {
        "penalty": round(min(20.0, frac * 20.0), 1),
        "unmarked_frac": round(frac, 3),
        "decisions": total,
        "unmarked": unmarked,
        "reading": "unmarked decisions cannot be calibrated — mark them "
                   "followed or overridden as outcomes land",
    }


def budget_from_ips(max_drawdown_frac: float | None,
                    enforced_daily_loss_frac: float | None) -> dict | None:
    """PROPOSE a daily-loss budget from the owner's ratified IPS drawdown.

    Convention (T069's, reused deliberately): a single day may risk a third of
    the drawdown he has said he can live through. Returns the implied figure
    beside what the engine currently ENFORCES, and flags disagreement.

    This never changes a limit. Safety rails move only through the
    confirmation-gated IPS/risk path — a proposal that applied itself would be
    exactly the "talked out of the lockout" failure the tiers exist to prevent.
    """
    if max_drawdown_frac is None or max_drawdown_frac <= 0:
        return None
    implied = max_drawdown_frac / IPS_DRAWDOWN_TO_DAILY
    # Annotated: a bare literal infers `agrees: None` and the later bool
    # assignment becomes a type error (caught by the pyrefly canary).
    out: dict[str, Any] = {
        "ips_max_drawdown_frac": max_drawdown_frac,
        "implied_daily_loss_frac": round(implied, 4),
        "convention": (f"a day may risk 1/{IPS_DRAWDOWN_TO_DAILY:g} of the "
                       "drawdown the IPS says is tolerable (T069's rule)"),
        "enforced_daily_loss_frac": enforced_daily_loss_frac,
        "agrees": None,
        "note": "PROPOSAL ONLY — the engine's enforced limit is unchanged; "
                "ratify through the confirmation-gated IPS path if you want it.",
    }
    if enforced_daily_loss_frac is not None:
        out["agrees"] = abs(implied - enforced_daily_loss_frac) <= 0.001
        if not out["agrees"]:
            direction = ("looser" if implied > enforced_daily_loss_frac
                         else "tighter")
            out["reading"] = (
                f"your IPS implies a {direction} daily budget "
                f"({implied:.2%}) than the engine enforces "
                f"({enforced_daily_loss_frac:.2%})")
    return out


FOMO_NOTE = (
    "NOT MEASURED: chasing a late-session volume spike needs an intraday "
    "timestamp on every fill plus that day's volume profile. Statement-parsed "
    "fills are date-only (time_known=False), so this would be guesswork — the "
    "one thing this stack refuses to do. It becomes measurable once the "
    "time-stamped broker fills (T016c) accumulate in the DB."
)


def score_owner_behavior(trips: Sequence, fills: Sequence, *,
                         journal_total: int | None = None,
                         journal_unmarked: int | None = None,
                         ips_max_drawdown_frac: float | None = None,
                         enforced_daily_loss_frac: float | None = None
                         ) -> OwnerDQSReport:
    """Score the owner's own round trips. 100 minus capped penalties.

    An unmeasurable component costs NOTHING (penalty 0 with a why) — silence
    on thin data is the T069 precedent, and a score that quietly punishes
    missing evidence would teach the wrong lesson.
    """
    disp = disposition_effect(trips)
    rev = revenge_sizing(trips, fills)
    jrn = journal_discipline(journal_total, journal_unmarked)

    penalties = disp["penalty"] + rev["penalty"] + jrn["penalty"]
    measured = [name for name, c in (("disposition_effect", disp),
                                     ("revenge_sizing", rev),
                                     ("journal_discipline", jrn))
                if "why" not in c]
    notes: list[str] = []
    if not measured:
        notes.append("NOTHING MEASURABLE YET — this is a 100 by absence of "
                     "evidence, not by good behaviour. Every component says "
                     "what it needs.")
    elif len(measured) < 3:
        notes.append("partial read: scored " + ", ".join(measured) +
                     "; the rest state what they need")

    return OwnerDQSReport(
        score=max(0.0, round(100.0 - penalties, 1)),
        trips_scored=len(trips),
        components={"disposition_effect": disp, "revenge_sizing": rev,
                    "journal_discipline": jrn},
        ips_budget=budget_from_ips(ips_max_drawdown_frac,
                                   enforced_daily_loss_frac),
        fomo_note=FOMO_NOTE,
        notes=notes,
        note=("DQS v2 scores YOUR round trips (process, not P&L). Components "
              "refuse on thin samples instead of guessing; an unmeasurable "
              "component costs nothing."),
    )
