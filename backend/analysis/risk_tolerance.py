"""T069 — adaptive risk tolerance: what the owner's behavior says his budget should be.

The owner asked for this one directly, and asked for something unusual with it:
that KUBERA's estimate be allowed to OVERRIDE his in-the-moment self-assessment.
That request is the whole design brief. A trader's stated risk tolerance is
collected on a calm afternoon; the tolerance that matters is the one operating
at 2pm on a red day. Those are different numbers, and only one of them leaves
evidence in the fills.

So this module never asks how much risk he can handle. It measures four things
that are hard to argue with:

  1. DRAWDOWN LIVED THROUGH — the deepest peak-to-trough he has actually sat
     through, measured on a flow-adjusted index so a deposit cannot disguise
     itself as resilience and a withdrawal cannot masquerade as a loss.
     A 20% stated tolerance that has never been tested below 6% is a belief,
     not a data point, and gets labelled as one.
  2. SIZING DRIFT — does position size grow after a loss? That is the revenge
     tell, and it is the single most expensive habit in retail trading, because
     it correlates size with the exact moments judgment is worst.
  3. POST-LOSS TRADE FREQUENCY — trading faster after a loss than the baseline.
     The tilt tell. Same logic, different axis.
  4. DRY POWDER — a fully-invested account has a higher effective risk than its
     stated limits imply, because there is no cash to absorb a forced decision.

WHAT THIS DOES NOT DO: it does not change any limit. It produces a PROPOSAL the
owner ratifies into the IPS, exactly like every other rule change (D014/T061) —
enforcement stays in `/backend/risk` where the LLM cannot reason around it. An
estimator that could quietly widen its own risk budget would be the single most
dangerous object in this repo.

HONESTY RULE, and the reason half the code here is guards: with a young account
there is not enough evidence to say anything, and the correct output is
"insufficient — here is what I need to see", not a confident number derived from
four trades. Every component reports its own sample size, and a component
without the samples to speak returns None instead of a plausible-looking value.

Pure functions, hand-tested. Money math is never LLM-computed (AGENTS.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median

# Minimum observations before a component is allowed an opinion. These are
# deliberately small — this is a personal account, not a research desk — but
# small is not zero, and a "signal" from two trades is noise wearing a suit.
MIN_TRIPS_FOR_BEHAVIOR = 8
MIN_PAIRED_OBSERVATIONS = 3
MIN_DAYS_FOR_DRAWDOWN = 20

# How long after a realized loss a subsequent entry still counts as "reacting
# to it". A trading day, not an arbitrary number: the tell is same-session
# retaliation, not a considered re-entry next week.
REACTION_WINDOW_HOURS = 24.0

# Confidence ladder, by the weakest evidence any speaking component has.
CONFIDENCE_ORDER = ("insufficient", "low", "moderate", "good")


@dataclass(frozen=True)
class Evidence:
    """One measured finding. `signal` is the direction, not the size, of the
    adjustment: negative means the behavior argues for a SMALLER budget."""

    name: str
    finding: str
    sample: int
    signal: float | None = None  # -1.0 .. +1.0, or None when it cannot speak


@dataclass(frozen=True)
class RiskToleranceEstimate:
    asof: str
    confidence: str
    recommended: dict
    current: dict
    stated: dict
    headline: str
    evidence: list[Evidence] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    @property
    def is_proposal(self) -> bool:
        """Always true. Present so callers cannot forget: nothing here is applied."""
        return True


# --------------------------------------------------------------- helpers

def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _flow_adjusted_index(
    equity_curve: list[tuple[str, float]],
    flows: list[tuple[str, float]] | None = None,
) -> list[tuple[str, float]]:
    """Chain-link daily returns into an index starting at 1.0, removing flows.

    Convention matches T060's TWR: a flow dated D is treated as arriving at the
    START of D, so the day's return is measured on the capital actually working.
    Without this, depositing $500 into a $1,000 account prints a 50% "gain" and
    a withdrawal prints as a drawdown he never suffered.
    """
    if len(equity_curve) < 2:
        return [(d, 1.0) for d, _ in equity_curve]

    by_date: dict[str, float] = {}
    for d, amt in (flows or []):
        by_date[d] = by_date.get(d, 0.0) + float(amt)

    out = [(equity_curve[0][0], 1.0)]
    level = 1.0
    for i in range(1, len(equity_curve)):
        prev_date, prev_val = equity_curve[i - 1]
        date, val = equity_curve[i]
        base = prev_val + by_date.get(date, 0.0)
        if base > 0:
            level *= val / base
        out.append((date, level))
    return out


def deepest_drawdown(
    equity_curve: list[tuple[str, float]],
    flows: list[tuple[str, float]] | None = None,
) -> dict:
    """Deepest peak-to-trough on the flow-adjusted index, plus whether it recovered."""
    idx = _flow_adjusted_index(equity_curve, flows)
    if len(idx) < 2:
        return {"depth_frac": None, "days_observed": len(idx),
                "peak_date": None, "trough_date": None, "recovered": None}

    peak = idx[0][1]
    peak_date = idx[0][0]
    worst = 0.0
    worst_peak_date = worst_trough_date = None
    for date, level in idx:
        if level > peak:
            peak, peak_date = level, date
        dd = 0.0 if peak <= 0 else (peak - level) / peak
        if dd > worst:
            worst, worst_peak_date, worst_trough_date = dd, peak_date, date

    recovered = None
    if worst_trough_date is not None:
        trough_i = next(i for i, (d, _) in enumerate(idx) if d == worst_trough_date)
        prior_peak = max(level for _, level in idx[: trough_i + 1])
        recovered = any(level >= prior_peak for _, level in idx[trough_i:])

    return {
        "depth_frac": round(worst, 6),
        "days_observed": len(idx),
        "peak_date": worst_peak_date,
        "trough_date": worst_trough_date,
        "recovered": recovered,
    }


def _buy_notionals(fills) -> list[tuple[datetime, float]]:
    out = []
    for f in fills:
        side = str(_get(f, "side", "")).lower()
        if side != "buy":
            continue
        ts = _parse(_get(f, "ts_iso", None))
        qty, price = _get(f, "qty", 0.0), _get(f, "price", 0.0)
        if ts is None or not qty or not price:
            continue
        out.append((ts, abs(float(qty)) * float(price)))
    return sorted(out, key=lambda p: p[0])


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def sizing_drift(trips, fills) -> dict:
    """Compare buy size right after a LOSING exit vs right after a WINNING exit.

    Ratio > 1 means he sizes UP after losing — the revenge pattern. Medians, not
    means, because one oversized trade should not be able to invent a habit.
    """
    buys = _buy_notionals(fills)
    if not buys:
        return {"after_loss": None, "after_win": None, "ratio": None, "sample": 0}

    window = timedelta(hours=REACTION_WINDOW_HOURS)
    after_loss, after_win = [], []
    for t in trips:
        exit_ts = _parse(_get(t, "exit_ts"))
        pnl = _get(t, "pnl")
        if exit_ts is None or pnl is None:
            continue
        following = [n for ts, n in buys if exit_ts < ts <= exit_ts + window]
        if not following:
            continue
        (after_loss if float(pnl) < 0 else after_win).append(median(following))

    if len(after_loss) < MIN_PAIRED_OBSERVATIONS or len(after_win) < MIN_PAIRED_OBSERVATIONS:
        return {"after_loss": None, "after_win": None, "ratio": None,
                "sample": min(len(after_loss), len(after_win))}

    m_loss, m_win = median(after_loss), median(after_win)
    ratio = None if m_win <= 0 else round(m_loss / m_win, 4)
    return {"after_loss": round(m_loss, 2), "after_win": round(m_win, 2),
            "ratio": ratio, "sample": min(len(after_loss), len(after_win))}


def post_loss_frequency(trips, fills) -> dict:
    """Entries per day in the 24h after a loss, vs the overall baseline rate."""
    buys = _buy_notionals(fills)
    if len(buys) < MIN_TRIPS_FOR_BEHAVIOR:
        return {"baseline_per_day": None, "after_loss_per_day": None,
                "ratio": None, "sample": len(buys)}

    span_days = max((buys[-1][0] - buys[0][0]).total_seconds() / 86400.0, 1.0)
    baseline = len(buys) / span_days

    window = timedelta(hours=REACTION_WINDOW_HOURS)
    losses = [_parse(_get(t, "exit_ts")) for t in trips
              if _get(t, "pnl") is not None and float(_get(t, "pnl")) < 0]
    losses = [x for x in losses if x is not None]
    if len(losses) < MIN_PAIRED_OBSERVATIONS:
        return {"baseline_per_day": round(baseline, 4), "after_loss_per_day": None,
                "ratio": None, "sample": len(losses)}

    # Union of the reaction windows, so overlapping losses do not double-count time.
    spans = sorted((x, x + window) for x in losses)
    merged: list[list[datetime]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    covered_days = sum((e - s).total_seconds() for s, e in merged) / 86400.0
    in_window = sum(1 for ts, _ in buys if any(s < ts <= e for s, e in merged))
    after = None if covered_days <= 0 else in_window / covered_days
    ratio = None if (after is None or baseline <= 0) else round(after / baseline, 4)
    return {"baseline_per_day": round(baseline, 4),
            "after_loss_per_day": None if after is None else round(after, 4),
            "ratio": ratio, "sample": len(losses)}


def dry_powder(equity: float | None, cash: float | None) -> dict:
    """Cash as a share of equity. No cash means no room to be wrong gracefully."""
    if not equity or equity <= 0 or cash is None:
        return {"cash_frac": None}
    return {"cash_frac": round(max(0.0, float(cash)) / float(equity), 6)}


# --------------------------------------------------------------- the estimate

# Hard bands. The estimator may move within these and nowhere else — an
# adaptive budget that can adapt itself upward without limit is just a budget
# that dissolves on the day it matters.
BANDS = {
    "daily_loss_limit_frac": (0.01, 0.05),
    "risk_per_trade_frac": (0.0025, 0.02),
    "max_position_frac": (0.05, 0.25),
}

REVENGE_SIZING_RATIO = 1.25   # sizing up >25% after losses vs after wins
TILT_FREQUENCY_RATIO = 1.50   # trading >50% faster inside the reaction window
THIN_CASH_FRAC = 0.05
DISCIPLINED_SIZING_RATIO = 0.90
DISCIPLINED_TILT_RATIO = 1.10


def _clamp(value: float, key: str) -> float:
    lo, hi = BANDS[key]
    return round(min(max(value, lo), hi), 6)


def estimate_risk_tolerance(
    *,
    equity_curve: list[tuple[str, float]] | None = None,
    flows: list[tuple[str, float]] | None = None,
    trips=(),
    fills=(),
    equity: float | None = None,
    cash: float | None = None,
    stated: dict | None = None,
    current: dict | None = None,
    asof: str | None = None,
) -> RiskToleranceEstimate:
    """Propose a risk budget from demonstrated behavior. Never applies it.

    `stated` is the owner's IPS view of himself; `current` is what the risk
    engine is enforcing today. The output compares all three on purpose — the
    gap between stated and demonstrated is the finding, not a footnote.
    """
    equity_curve = list(equity_curve or [])
    stated = dict(stated or {})
    current = dict(current or {})
    base_daily = float(current.get("daily_loss_limit_frac") or 0.03)
    base_trade = float(current.get("risk_per_trade_frac") or 0.01)
    base_position = float(current.get("max_position_frac") or 0.20)

    dd = deepest_drawdown(equity_curve, flows)
    drift = sizing_drift(trips, fills)
    freq = post_loss_frequency(trips, fills)
    powder = dry_powder(equity, cash)

    evidence: list[Evidence] = []
    caveats: list[str] = []
    multiplier = 1.0
    spoke = 0

    # 1 — drawdown actually lived through
    stated_dd = stated.get("max_drawdown_frac")
    if dd["depth_frac"] is None or dd["days_observed"] < MIN_DAYS_FOR_DRAWDOWN:
        evidence.append(Evidence(
            "drawdown_experience",
            f"only {dd['days_observed']} days of equity history — not enough to know "
            "what drawdown you have actually sat through",
            dd["days_observed"], None))
        caveats.append(
            f"Run scripts/sync.py daily; at {MIN_DAYS_FOR_DRAWDOWN}+ days this "
            "starts measuring the drawdown you have really lived through."
        )
    else:
        spoke += 1
        depth = dd["depth_frac"]
        rec = "recovered" if dd["recovered"] else "not yet recovered"
        if stated_dd and depth < 0.4 * float(stated_dd):
            evidence.append(Evidence(
                "drawdown_experience",
                f"deepest drawdown you have actually lived through is {depth:.1%} "
                f"({dd['peak_date']} to {dd['trough_date']}, {rec}), against a stated "
                f"tolerance of {float(stated_dd):.0%}. The stated figure is a belief, "
                "not yet a tested one — I am not budgeting against it.",
                dd["days_observed"], -0.5))
            # Keep a bad streak inside proven territory: three full budget days
            # should not take him somewhere he has never been.
            base_daily = min(base_daily, max(depth / 3.0, BANDS["daily_loss_limit_frac"][0]))
        else:
            evidence.append(Evidence(
                "drawdown_experience",
                f"deepest drawdown lived through: {depth:.1%} "
                f"({dd['peak_date']} to {dd['trough_date']}, {rec})",
                dd["days_observed"], 0.0))

    # 2 — sizing drift after losses (the revenge tell)
    if drift["ratio"] is None:
        evidence.append(Evidence(
            "sizing_drift",
            f"not enough paired trades yet ({drift['sample']} of "
            f"{MIN_PAIRED_OBSERVATIONS} needed on each side) to see whether size "
            "grows after a loss",
            drift["sample"], None))
    else:
        spoke += 1
        r = drift["ratio"]
        if r >= REVENGE_SIZING_RATIO:
            multiplier *= 0.75
            evidence.append(Evidence(
                "sizing_drift",
                f"after a LOSS you buy {r:.2f}x the size you buy after a win "
                f"(${drift['after_loss']:,.0f} vs ${drift['after_win']:,.0f} median). "
                "That is the revenge pattern: biggest size at the moment judgment "
                "is worst. A tighter daily budget ends the spiral sooner.",
                drift["sample"], -1.0))
        elif r <= DISCIPLINED_SIZING_RATIO:
            evidence.append(Evidence(
                "sizing_drift",
                f"after a loss you size DOWN ({r:.2f}x vs after a win) — "
                "textbook discipline, and rarer than it sounds",
                drift["sample"], 0.5))
        else:
            evidence.append(Evidence(
                "sizing_drift",
                f"size is stable across wins and losses ({r:.2f}x)",
                drift["sample"], 0.0))

    # 3 — trading faster after a loss (the tilt tell)
    if freq["ratio"] is None:
        evidence.append(Evidence(
            "post_loss_frequency",
            f"not enough realized losses yet ({freq['sample']} of "
            f"{MIN_PAIRED_OBSERVATIONS}) to measure post-loss trading pace",
            freq["sample"], None))
    else:
        spoke += 1
        r = freq["ratio"]
        if r >= TILT_FREQUENCY_RATIO:
            multiplier *= 0.80
            evidence.append(Evidence(
                "post_loss_frequency",
                f"in the {REACTION_WINDOW_HOURS:.0f}h after a loss you enter "
                f"{r:.2f}x as often as your baseline "
                f"({freq['after_loss_per_day']:.2f} vs {freq['baseline_per_day']:.2f} "
                "entries/day) — trading to get it back, on the day you should trade least",
                freq["sample"], -1.0))
        elif r <= DISCIPLINED_TILT_RATIO:
            evidence.append(Evidence(
                "post_loss_frequency",
                f"post-loss pace matches baseline ({r:.2f}x) — no tilt signature",
                freq["sample"], 0.5))
        else:
            evidence.append(Evidence(
                "post_loss_frequency",
                f"mildly elevated post-loss pace ({r:.2f}x) — worth watching",
                freq["sample"], -0.25))

    # 4 — dry powder
    if powder["cash_frac"] is None:
        evidence.append(Evidence("dry_powder", "no account composition available", 0, None))
    else:
        spoke += 1
        c = powder["cash_frac"]
        if c < THIN_CASH_FRAC:
            multiplier *= 0.85
            evidence.append(Evidence(
                "dry_powder",
                f"cash is {c:.1%} of equity — effectively fully invested, so your real "
                "risk runs above the stated limits: there is nothing to absorb a "
                "forced decision",
                1, -0.5))
        else:
            evidence.append(Evidence(
                "dry_powder", f"cash buffer {c:.1%} of equity", 1, 0.0))

    # A disciplined record earns a little room — capped, and only when every
    # behavioral component spoke and none of them flagged.
    behavioral = [e for e in evidence
                  if e.name in {"sizing_drift", "post_loss_frequency"} and e.signal is not None]
    if len(behavioral) == 2 and all(e.signal is not None and e.signal >= 0.5 for e in behavioral) \
            and dd["recovered"]:
        multiplier *= 1.15
        caveats.append(
            "Budget nudged UP because the record earns it — capped at +15%, and it "
            "reverses the moment the behavior does."
        )

    if spoke == 0:
        confidence = "insufficient"
    elif spoke == 1:
        confidence = "low"
    elif spoke == 2:
        confidence = "moderate"
    else:
        confidence = "good"

    if confidence == "insufficient":
        recommended = {
            "daily_loss_limit_frac": _clamp(base_daily, "daily_loss_limit_frac"),
            "risk_per_trade_frac": _clamp(base_trade, "risk_per_trade_frac"),
            "max_position_frac": _clamp(base_position, "max_position_frac"),
        }
        headline = (
            "Not enough evidence to estimate your risk tolerance yet, so I am "
            "proposing no change — the conservative defaults stand. Ask me again "
            "once there is trading history to read."
        )
    else:
        recommended = {
            "daily_loss_limit_frac": _clamp(base_daily * multiplier, "daily_loss_limit_frac"),
            "risk_per_trade_frac": _clamp(base_trade * multiplier, "risk_per_trade_frac"),
            "max_position_frac": _clamp(
                base_position * (0.75 if (powder["cash_frac"] or 1.0) < THIN_CASH_FRAC else 1.0),
                "max_position_frac"),
        }
        direction = ("tighter" if recommended["daily_loss_limit_frac"] < base_daily
                     else "wider" if recommended["daily_loss_limit_frac"] > base_daily
                     else "unchanged")
        headline = (
            f"On {confidence} evidence, your demonstrated risk tolerance argues for a "
            f"{direction} daily budget: {recommended['daily_loss_limit_frac']:.2%} of "
            f"equity (currently {base_daily:.2%})."
        )

    caveats.append(
        "This is a PROPOSAL. Nothing is applied — ratify it into your IPS and I will "
        "advise against the new number; the enforced limits live in code, not in chat."
    )
    if stated.get("risk_tolerance"):
        caveats.append(
            f"You describe yourself as '{stated['risk_tolerance']}'. Where that "
            "conflicts with the evidence above, I will use the evidence — your "
            "instruction, and the right one."
        )

    return RiskToleranceEstimate(
        asof=asof or datetime.now(timezone.utc).isoformat(),
        confidence=confidence,
        recommended=recommended,
        current={"daily_loss_limit_frac": round(base_daily, 6),
                 "risk_per_trade_frac": round(base_trade, 6),
                 "max_position_frac": round(base_position, 6)},
        stated=stated,
        headline=headline,
        evidence=evidence,
        caveats=caveats,
    )
