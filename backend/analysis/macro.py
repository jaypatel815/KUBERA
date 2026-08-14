"""Macro regime context (T080, D017) — the broad-market weather report.

Pure composition over injected FRED observations: labeled reads with documented
conventions, a cautionary-signal COUNT (evidence list, not a verdict), and the
standing rule that this is CONTEXT for narration — never a trade signal by itself.

Conventions (stable, documented — argue in DECISIONS.md, not in code review):
- Yield curve (T10Y2Y): inverted when spread < 0. Inversions have preceded
  recessions historically; an inversion is a caution flag, not a timer.
- VIX buckets: < 15 calm · 15–20 normal · 20–30 elevated · >= 30 stressed.
  Elevated or worse is a caution flag.
- Real 10y rate (DFII10): positive = real yields compensate; > 2 counts as
  restrictive (a caution flag).
Each series carries ITS OWN observation date — FRED calendars differ by series
and the narration must show the dates.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MacroRead:
    name: str
    series_id: str
    value: float
    date: str
    label: str


@dataclass(frozen=True)
class MacroContext:
    reads: list[MacroRead]
    cautionary_signals: list[str]
    caution_count: int
    note: str


def _vix_bucket(v: float) -> str:
    if v < 15:
        return "calm"
    if v < 20:
        return "normal"
    if v < 30:
        return "elevated"
    return "stressed"


def compose_macro_context(
    yield_curve: tuple[str, float],
    vix: tuple[str, float],
    real_rate: tuple[str, float],
    fed_funds: tuple[str, float],
) -> MacroContext:
    """Each input is (observation_date, value) for the documented series."""
    yc_date, yc = yield_curve
    vix_date, vx = vix
    rr_date, rr = real_rate
    ff_date, ff = fed_funds

    reads = [
        MacroRead("yield_curve_10y2y", "T10Y2Y", yc, yc_date,
                  "inverted" if yc < 0 else "normal"),
        MacroRead("vix", "VIXCLS", vx, vix_date, _vix_bucket(vx)),
        MacroRead("real_rate_10y", "DFII10", rr, rr_date,
                  "restrictive" if rr > 2 else ("positive" if rr > 0 else "negative")),
        MacroRead("fed_funds", "DFF", ff, ff_date, "policy rate"),
    ]

    cautions = []
    if yc < 0:
        cautions.append(
            f"yield curve inverted ({yc:+.2f} as of {yc_date}) — historically a "
            "caution flag, not a timer"
        )
    if vx >= 20:
        cautions.append(f"VIX {_vix_bucket(vx)} at {vx:.1f} (as of {vix_date})")
    if rr > 2:
        cautions.append(f"10y real rate restrictive at {rr:.2f}% (as of {rr_date})")

    return MacroContext(
        reads=reads,
        cautionary_signals=cautions,
        caution_count=len(cautions),
        note=(
            "Macro context for narration — evidence, never a trade signal by "
            "itself. Series publish on different calendars; each read carries its "
            "own date."
        ),
    )
