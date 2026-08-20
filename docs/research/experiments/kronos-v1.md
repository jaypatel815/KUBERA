# Pre-registration: kronos-v1 (T122, D037 — written BEFORE any run)

This document exists so success cannot be redefined after results are
seen. It is the input `scripts/phase7_gate.py --revision kronos-v1`
checks, and the contract every attempt is judged against. Registered
2026-08-20 by Claude/Cowork; the owner's go decision on 2026-08-20 is the
authorization.

## What is being evaluated

NeoQuasar/Kronos-base (102M-param open price-series foundation model,
MIT, CPU-feasible ~400MB F32): can its next-days distribution add
anything to KUBERA's OWN measured expected-move bands (T077)? Kronos
produces a forecast distribution per symbol per day; we score it as a
DISTRIBUTION, never as a point call (D017/D035).

## THE CONTAMINATION RULE (the reason this document exists)

Kronos trained on ~12B K-lines through its training cutoff. A historical
backtest is therefore a test ON ITS OWN TRAINING DATA and is
INADMISSIBLE as evidence, full stop. Only post-cutoff, paper-forward
evaluation counts: the window below is entirely in the future at
registration time, so no result can leak into these choices.

## Frozen evaluation definition (custody: holdout `kronos-v1-fwd`)

- Symbols: SPY, QQQ, NVDA (the owner's actual traded names; liquid; three
  is breadth enough for a first candidate without rate-limit fan-out).
- Window: 2026-08-24 through 2026-10-02 (~30 trading sessions), entirely
  forward of registration.
- params_hash at freeze: `see custody journal — printed by the freeze run
  and recorded in TASKS.md` (the gate cross-checks the DB row, not this
  line).

## Pre-stated success criteria (measured at window end, consumed ONCE)

1. CALIBRATION: Kronos's nominal 90% interval (p05..p95) must cover the
   realized next-day move between 80% and 97% of session-symbol pairs.
   Under 80% = overconfident; over 97% = uselessly wide.
2. USEFULNESS: a pre-committed toy rule (long when Kronos up-odds > 0.55,
   else flat, one decision per day per symbol, T090 costs at 2x) must not
   lose to buy-and-hold SPY over the same window. This is a floor, not a
   promotion — promotion has its own gate.
3. BOTH must hold, or the verdict is FAIL and it is written down. A FAIL
   here is a real answer (AI-Trader's live benchmark — D037 — says FAIL
   is the base rate; measuring it ourselves is the point).

## Budget (pre-registered)

3 attempts for this revision, failures count (T110a). An "attempt" is one
full evaluation run of the frozen window. Bugs in glue code that abort a
run still consume an attempt — that is the two-strikes spirit; a NEW
revision with a NEW pre-registration is the escape hatch, never a raised
budget.

## Hard rules carried from doctrine

- All Kronos inference and glue code runs inside the T110b isolation
  boundary (`run_isolated`); the custody seam (`assert_servable`) refuses
  the guarded symbols to research code outside custody.
- Signals never reach the owner as point predictions: odds and ranges
  only, labeled as an EXPERIMENTAL internal candidate (D035). Nothing
  from this experiment reaches the paper loop except through the T064
  promotion gate + selection rule.
- Fine-tuning on the owner's fills: REFUSED (D037) — 131 fills is a
  memorization set, not a training set.
- The holdout is consumed exactly once, at window end, with the result
  summary written into the custody journal. No peeking mid-window: the
  daily forecasts are LOGGED as they are made (that is the paper-forward
  discipline) but not scored until consumption.

## Owner-machine steps (the parts an agent cannot do)

1. Download the model once: `huggingface-cli download NeoQuasar/Kronos-base`
   (or let the first run fetch it) — ~400MB.
2. Before the first attempt: `py scripts\phase7_gate.py --revision kronos-v1`
   must print GATE OPEN.
3. Each attempt records itself: `record_attempt(...)` is called by the
   runner (T122 build ticket), never by hand.
