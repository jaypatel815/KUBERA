"""T066 — trade coaching (D014): pre-trade and post-trade reviews as DATA.

PROCESS, NOT OUTCOME — the same doctrine as the DQS: a disciplined loss beats
a lucky rule-break, so nothing here scores P&L. The pre-trade review is a
CHECKLIST, not a verdict: each section lands on ok / attention / missing with
its reason, because a single composite number would launder judgement into
false precision. The post-trade review compares what HAPPENED to what was
RECORDED AT ENTRY (the T063 journal row), emitting facts_for_lessons lines —
the narration layer may draw lessons only from those, never invent its own.

Pure composition: every input arrives as data the tool layer gathered; every
missing input degrades to a "missing" section WITH what would supply it.
Nothing here fetches, guesses, or predicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

OK = "ok"
ATTENTION = "attention"
MISSING = "missing"

# Concentration convention: the engine's per-symbol cap is 20% (risk/engine
# T033). The coach flags earlier — attention at 15% post-trade weight — the
# same "friction before the breaker" idea as the T067 tiers.
CONCENTRATION_ATTENTION_FRAC = 0.15
CONCENTRATION_CAP_FRAC = 0.20

# Regime-fit table: which regimes ARGUE WITH a long entry. Long-only book
# (D021), so "buy" is the entry side under review.
_LONG_UNFRIENDLY = {"trending_down"}
_LONG_CAUTION = {"breakout_watch"}  # a coil: direction unproven, plan required


def _section(status: str, why: str, **facts: Any) -> dict:
    out = {"status": status, "why": why}
    out.update(facts)
    return out


@dataclass(frozen=True)
class PreTradeReview:
    symbol: str
    side: str
    sections: dict[str, dict] = field(default_factory=dict)
    attention_count: int = 0
    missing_count: int = 0
    summary: str = ""
    note: str = ("Process checklist, not a prediction. 'ok' means the check "
                 "passed, not that the trade will work.")
    asof: str = ""


def compose_pre_trade_review(
    symbol: str,
    side: str,
    *,
    thesis: str | None = None,
    invalidation: str | None = None,
    proposed_notional: float | None = None,
    equity: float | None = None,
    current_position_value: float | None = None,
    ips: dict | None = None,
    regime_label: str | None = None,
    regime_confidence: float | None = None,
    regime_failure: str | None = None,
    pattern_verdict: str | None = None,
    pattern_warnings: list[dict] | None = None,
    exit_plan_present: bool = False,
) -> PreTradeReview:
    """Judge a proposed ENTRY against the process rules. Facts in, checklist out.

    Every section explains itself; sections whose inputs are absent land on
    MISSING with the tool or action that would supply them — an absent check
    is surfaced, never silently skipped (the I026 lesson generalised).
    """
    symbol = symbol.upper()
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")
    s: dict[str, dict] = {}

    # 1. Thesis — the question the owner's own doctrine asks first.
    if thesis and thesis.strip():
        if invalidation and invalidation.strip():
            s["thesis"] = _section(OK, "thesis and invalidation both stated",
                                   thesis=thesis.strip()[:200],
                                   invalidation=invalidation.strip()[:200])
        else:
            s["thesis"] = _section(
                ATTENTION,
                "thesis stated but NO invalidation — without 'what would prove "
                "me wrong', an exit is an emotion, not a plan",
                thesis=thesis.strip()[:200])
    else:
        s["thesis"] = _section(
            MISSING, "no thesis stated — one sentence: why THIS, why NOW; "
                     "a trade without a thesis cannot be reviewed afterwards")

    # 2. IPS fit — restrictions are the owner's own written rules (T061).
    if ips is None:
        s["ips_fit"] = _section(
            MISSING, "no Investment Policy Statement on file — record one via "
                     "update_ips; until then there is nothing to check against")
    else:
        restricted = [r for r in (ips.get("restrictions") or [])
                      if str(r).strip().upper() == symbol]
        if restricted:
            s["ips_fit"] = _section(
                ATTENTION,
                f"{symbol} appears in the IPS restrictions list — this is YOUR "
                "written rule; overriding it should be a deliberate act",
                restrictions_hit=restricted)
        else:
            s["ips_fit"] = _section(OK, "no IPS restriction names this symbol",
                                    checked=["restrictions"])

    # 3. Concentration — post-trade weight vs the cap, flagged EARLY.
    if equity is None or equity <= 0 or proposed_notional is None:
        s["concentration"] = _section(
            MISSING, "needs live equity and the proposed notional — "
                     "size_position supplies both")
    else:
        held = max(0.0, current_position_value or 0.0)
        after = (held + proposed_notional) / equity if side == "buy" else \
                max(0.0, held - proposed_notional) / equity
        facts = {"post_trade_weight_frac": round(after, 4),
                 "cap_frac": CONCENTRATION_CAP_FRAC}
        if after > CONCENTRATION_CAP_FRAC:
            s["concentration"] = _section(
                ATTENTION,
                f"post-trade weight {after:.1%} EXCEEDS the {CONCENTRATION_CAP_FRAC:.0%} "
                "cap — the engine will reject this size; it is not advice to "
                "route around the cap", **facts)
        elif after > CONCENTRATION_ATTENTION_FRAC and side == "buy":
            s["concentration"] = _section(
                ATTENTION,
                f"post-trade weight {after:.1%} is inside {CONCENTRATION_ATTENTION_FRAC:.0%}"
                f"–{CONCENTRATION_CAP_FRAC:.0%} — close to the cap, one gap "
                "against you from a forced conversation", **facts)
        else:
            s["concentration"] = _section(
                OK, f"post-trade weight {after:.1%} sits under the early-warning "
                    f"line ({CONCENTRATION_ATTENTION_FRAC:.0%})", **facts)

    # 4. Regime fit — does the CURRENT read argue with this entry?
    if regime_label is None:
        why = ("no regime reading supplied — get_regime answers this"
               if regime_failure is None else
               f"regime read FAILED ({regime_failure}) — the check was "
               "attempted, not skipped; run get_regime to see the full error")
        s["regime_fit"] = _section(MISSING, why)
    else:
        facts = {"regime": regime_label, "confidence": regime_confidence}
        if side == "buy" and regime_label in _LONG_UNFRIENDLY:
            s["regime_fit"] = _section(
                ATTENTION, f"buying into {regime_label} — the classifier's read "
                           "argues with this entry; the doctrine says trends are "
                           "respected, not argued with", **facts)
        elif side == "buy" and regime_label in _LONG_CAUTION:
            s["regime_fit"] = _section(
                ATTENTION, "breakout_watch is a coil: direction is UNPROVEN — "
                           "an entry here is a bet on resolution, so the exit "
                           "plan carries all the weight", **facts)
        else:
            s["regime_fit"] = _section(
                OK, f"{regime_label} does not argue with a {side}", **facts)

    # 5. Pattern history — T104's read of his own record, passed through.
    if pattern_verdict is None:
        s["pattern_history"] = _section(
            MISSING, "no pattern check supplied — check_trade_pattern compares "
                     "this setup to his own historical record")
    elif pattern_verdict == "warning_triggered":
        s["pattern_history"] = _section(
            ATTENTION,
            "this setup resembles ones that historically cost him — the "
            "warnings carry their sample sizes; read them before proceeding",
            verdict=pattern_verdict, warnings=pattern_warnings or [])
    else:
        s["pattern_history"] = _section(
            OK, f"pattern check: {pattern_verdict}", verdict=pattern_verdict)

    # 6. Exit plan — T056's rule: how long do I hold is data, not vibes.
    if exit_plan_present:
        s["exit_plan"] = _section(OK, "a structured exit plan exists for this symbol")
    else:
        s["exit_plan"] = _section(
            MISSING, "no exit plan — get_exit_plan writes the invalidation, "
                     "target/review point, and clock BEFORE entry, when it is "
                     "cheap to be honest")

    attention = sum(1 for v in s.values() if v["status"] == ATTENTION)
    missing = sum(1 for v in s.values() if v["status"] == MISSING)
    ok = len(s) - attention - missing
    return PreTradeReview(
        symbol=symbol, side=side, sections=s,
        attention_count=attention, missing_count=missing,
        summary=f"{ok} ok / {attention} attention / {missing} missing "
                f"of {len(s)} checks",
        asof=datetime.now(timezone.utc).isoformat(),
    )


@dataclass(frozen=True)
class PostTradeReview:
    symbol: str
    sections: dict[str, dict] = field(default_factory=dict)
    facts_for_lessons: list[str] = field(default_factory=list)
    note: str = ("Facts only — the narration layer may draw lessons ONLY from "
                 "facts_for_lessons and must never invent numbers.")
    asof: str = ""


def compose_post_trade_review(trip: Any, journal: dict | None) -> PostTradeReview:
    """One closed round trip vs what was recorded at decision time.

    `trip`: a fifo_attribution trip dict (symbol, pnl, held_days, entry_ts,
    exit_ts, notional). `journal`: the matching T063 row as a dict, or None —
    an unjournaled trade IS the finding, not a reason to skip the review.
    """
    def g(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    symbol = str(g(trip, "symbol", "")).upper()
    pnl = g(trip, "pnl")
    held = g(trip, "held_days")
    s: dict[str, dict] = {}
    facts: list[str] = []

    outcome = ("win" if pnl is not None and pnl > 0 else
               "loss" if pnl is not None and pnl < 0 else "scratch")
    if pnl is not None:
        facts.append(f"{symbol}: {outcome} of {pnl:+.2f}"
                     + (f" over {held:g} day(s)" if held is not None else
                        " (holding time unrecorded)"))

    # 1. Was it journaled? The T063 rule, checked after the fact.
    if journal is None:
        s["journaling"] = _section(
            ATTENTION,
            "no journal entry within the entry window — 'a recommendation that "
            "isn't journaled didn't happen' applies to trades too: nothing was "
            "recorded to be right or wrong ABOUT")
        facts.append(f"{symbol}: traded without a journal entry — expected vs "
                     "actual cannot be judged")
        return PostTradeReview(
            symbol=symbol, sections=s, facts_for_lessons=facts,
            asof=datetime.now(timezone.utc).isoformat())

    s["journaling"] = _section(
        OK, "a journal entry existed at decision time",
        verdict=journal.get("verdict"), confidence=journal.get("confidence"),
        followed=journal.get("followed"))

    # 2. Horizon adherence — held vs the stated horizon.
    horizon = journal.get("horizon_days")
    if horizon is None or held is None:
        s["horizon"] = _section(
            MISSING, "stated horizon or measured holding time absent — "
                     "one of the two sides of the comparison is missing")
    else:
        ratio = held / horizon if horizon > 0 else None
        facts.append(f"{symbol}: held {held:g}d against a stated {horizon}d horizon")
        if ratio is not None and ratio < 0.25 and outcome == "win":
            s["horizon"] = _section(
                ATTENTION,
                f"winner exited at {held:g}d of a {horizon}d horizon (<25%) — "
                "consistent with the cut-winners tell the DQS tracks; one trade "
                "proves nothing, the pattern is what matters",
                held_days=held, horizon_days=horizon)
        elif ratio is not None and ratio > 2.0 and outcome == "loss":
            s["horizon"] = _section(
                ATTENTION,
                f"loser held {held:g}d, over twice the {horizon}d horizon — "
                "a thesis past its clock is not a thesis (T056)",
                held_days=held, horizon_days=horizon)
        else:
            s["horizon"] = _section(OK, "holding time consistent with the "
                                        "stated horizon",
                                    held_days=held, horizon_days=horizon)

    # 3. Stop/target adherence — did the exit respect the recorded levels?
    entry = journal.get("entry_price")
    stop = journal.get("stop_price")
    target = journal.get("target_price")
    if entry is None or (stop is None and target is None):
        s["levels"] = _section(
            MISSING, "no entry+stop/target recorded at decision time — the "
                     "exit cannot be judged against a plan that was never "
                     "written down")
    else:
        # Attribution trips carry pnl/notional but not the exit PRICE, so the
        # exit-vs-level comparison is qualitative: what was ON RECORD when the
        # outcome happened. A price-level adherence check needs per-fill exit
        # prices — future work once trips carry them; never derived here.
        if outcome == "loss" and stop is not None:
            facts.append(f"{symbol}: loss taken with a stop on record at {stop:g}")
            s["levels"] = _section(
                OK, "a stop existed on the record; whether the exit honoured "
                    "it needs the exit PRICE, which attribution trips do not "
                    "carry — judged qualitatively only", stop_price=stop)
        elif outcome == "win" and target is not None:
            facts.append(f"{symbol}: win with a target on record at {target:g}")
            s["levels"] = _section(
                OK, "a target existed on the record", target_price=target)
        else:
            s["levels"] = _section(
                OK, "levels were recorded", stop_price=stop, target_price=target)

    # 4. Follow/override — his call, recorded, never penalised.
    followed = journal.get("followed")
    if followed is None:
        s["follow_override"] = _section(
            ATTENTION, "decision never marked followed/overridden — mark it; "
                       "unmarked decisions never enter the calibration")
    else:
        word = "followed" if followed else "overridden"
        facts.append(f"{symbol}: KUBERA's {journal.get('verdict')} was {word}; "
                     f"trip outcome {outcome}")
        s["follow_override"] = _section(
            OK, f"marked {word} — the calibration loop gets this one",
            followed=followed)

    return PostTradeReview(
        symbol=symbol, sections=s, facts_for_lessons=facts,
        asof=datetime.now(timezone.utc).isoformat(),
    )
