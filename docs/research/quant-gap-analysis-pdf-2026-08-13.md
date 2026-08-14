# "Quant Capabilities Gap Analysis" (owner-uploaded PDF) — 2026-08-13 (binding: D021)

*Source: owner-uploaded PDF (repo-aware: correctly cites paper_loop long-only,
exit_plan trend_down_exit, T078/T079/T081/T064). Sixth cross-agent batch.
Companion to D020 — overlaps are mapped, not duplicated. One item is escalated
to an OWNER DECISION.*

## Gap 1 — Short selling & beta-neutrality → OWNER DECISION (the big one)
The review is RIGHT: pairs/stat-arb (T081) requires shorting the rich leg;
beta-hedging requires shorting SPY. It is also right that we are long-only —
but that is a DELIBERATE v1 safety rail, not an oversight: shorts carry
structurally unbounded loss, and this owner's documented failure mode is
pressing when losing. Paper-shorting teaches habits that transfer to live.
DISPOSITION: escalated to the owner with three honest paths:
  (a) stay long-only; redefine T081 as a long-the-cheap-leg spread proxy
      (weaker, hedge-less — honest about it);
  (b) enable PAPER-only shorting behind hard rails (short-specific caps, the
      promotion gate, tier system applies, breaker unchanged) — unlocks true
      pairs + beta-hedge on paper;
  (c) defer the decision until 30+ days of paper DQS history exists (evidence
      about discipline before expanding the loss surface).
T081 is BLOCKED pending this decision. Recorded in D021 when made.

## Gap 2 — Cross-sectional ranking → T068 enriched (again)
Correct that our momentum is time-series-only. T068's D020 criteria (1/3/6-month
RS) now explicitly include the universe-screener framing: rank N symbols, flag
top/bottom deciles. A cross-sectional momentum TEMPLATE (long top decile) is
recorded as a future strategy — it must pass the T064 promotion gate like
everything, and its short half depends on the Gap-1 decision.

## Gap 3 — HRP / mean-variance optimization → measure first, optimize later
T093 (portfolio vol, marginal risk contribution, effective bets) is the
MEASUREMENT half and ships first. Full HRP is real and deterministic
(correlation-distance clustering + recursive bisection — testable, no unstable
matrix inversion), but it is heavy machinery for a book that typically holds a
handful of positions. NEW T094: HRP allocation, gated on "the book regularly
holds enough positions for optimization to beat common sense" — the trigger is
written down so nobody builds it for a 3-position portfolio.

## Gap 4 — Strategy decay / CUSUM demotion → T093 enriched (adopted fully)
The sharpest idea in the PDF: the promotion gate (T064) has no DEMOTION twin.
Adopted into T093: live strategy equity tracked against its backtest expectation;
sustained deviation (CUSUM-style drift test) flips the ledger's promotion_status
to "demoted" — and the loop's existing require_promotion then refuses new buys
AUTOMATICALLY. Perfect symmetry: earn the loop, keep earning it.

## Gap 5 — Market impact modeling + VWAP/TWAP slicing → premature, measured first
Measurement lands in T088 (slippage_bps) and T090 (live spreads + ADV cap).
The NONLINEAR impact model and execution slicing are scale problems KUBERA does
not have: T090's conservative ADV cap prevents orders large enough to move
anything. Deferred with a written trigger: relevant only if single orders
approach ~0.5% of ADV — the cap makes that structurally impossible today.

## Gap 6 — Factor exposure (Fama-French loadings) → NEW T095
Beta lands with T093. Full factor loadings are buildable honestly: the Ken
French data library publishes factor return series FREE (daily CSVs); portfolio
factor exposure = OLS regression of portfolio returns on factor returns —
deterministic, hand-testable. NEW T095, dep: enough snapshot return history to
regress meaningfully (~60+ daily points); answers "is this alpha or leveraged
beta / a size tilt I didn't intend."

## Convergence note
Six reviews in: every serious reviewer now opens by confirming the foundation
(determinism, fail-closed risk, process-over-outcome) and closes by asking for
the same two things — better MEASUREMENT (D020 family) and more STRATEGY BREADTH
(which mostly hangs on the Gap-1 shorting decision and T023's data unlock).
The backlog is no longer idea-constrained; it is decision- and data-constrained.
