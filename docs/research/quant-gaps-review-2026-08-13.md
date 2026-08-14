# Quant-gaps review (Gemini) — 2026-08-13 (binding: D020)

*Source: Gemini/Antigravity's "what would a quant fund find missing" review — the
best cross-agent review to date: repo-aware, correct about what exists, correct
about the backlog, and its "what's NOT missing" traps section independently
re-derives D017/D019 rejections (ML price prediction, HFT, options-now, template
sprawl). Dispositions below are binding.*

## Built same-session (the pure-math top picks)
- **MAE/MFE (gap 3, priority #1)** → `backtest/stats.trade_excursions`: per-trade
  max adverse/favorable excursion from decision-close basis, plus WINNERS' average
  MAE — the stop-calibration number ("if winners dip 2% before winning, a 1.5%
  stop kills winners"). Close-to-close honestly labeled; intraday/live versions
  need fills (T036 → T088).
- **Sortino + Omega (gap 3, priority #3)** → `analysis/metrics`: downside-only
  denominator (full-sample convention documented) and probability-weighted
  gain/shortfall ratio; both refuse to fake a number when there's no downside.

## Mapped to EXISTING tickets (no duplicates)
- Stress windows → T064b (already honest about IEX depth: 2008 impossible).
- Market-hours / overnight-signal awareness → T036 (guard + entry delay, D018).
- PEAD / earnings momentum → T083 event reaction base rates (D019) + T023 unlock.
- Relative-strength ranking → T068, now ENRICHED with defined criteria
  (1/3/6-month relative strength within the watchlist universe).
- Kelly ceiling → existing advisory note (owner Q&A): ceiling-not-target, capped.
- P&L vs expected-move calibration → T077b (band-hit-rate scoring added).
- Cross-asset research, hypothesis generation → Phase 7 research_agent charter
  (correctly observed as empty; that's sequencing, not oversight).

## NEW tickets (T088–T093)
- **T088 — Execution quality** (dep T036 fills): fills table gains signal_price /
  submitted_price / fill_price; slippage_bps; implementation-shortfall report;
  fill quality by time-of-day bucket (turns "don't buy the open" into evidence).
- **T089 — Live MAE/MFE**: extend trade_excursions to live positions once T036
  lands (intraday extremes); weekly stop-calibration report in T062's weekly.
- **T090 — Liquidity-aware costs**: live bid-ask spread (we already fetch quotes)
  as spread_bps in briefings/sizing; ADV-based position cap (IEX ADV understates
  → the cap binds EARLIER = conservative, labeled); replaces the fixed-bps cost
  assumption per symbol.
- **T091 — Attribution pack** (the "is the regime classifier adding value" cut,
  priority #2): signal_log gains regime_label + sub_strategy + entry-time bucket
  at order time (the loop already computes the regime — persist it); report tool:
  P&L by regime, by sub-strategy (router legs separated), by time-of-entry;
  holding-period distribution from signal_log/transactions.
- **T092 — Parameter stability sweeps**: run templates across neighboring
  parameter values (momentum 30..90 etc.); a strategy that only works at exactly
  lookback=60 is curve-fit, not alpha; stability summary recorded in the ledger
  beside promotions.
- **T093 — Portfolio risk summary + reconciliation + degradation** (priorities
  #4 and #5): (a) portfolio-level annualized vol from position returns +
  correlations, marginal risk contribution per position, effective number of
  bets (1/Σw²) — extends T079's math to the whole book; (b) daily reconciliation:
  latest position_snapshots vs live broker positions, drift flagged in
  health_check; (c) strategy degradation: rolling recent-vs-historical
  performance check that fires BEFORE the breaker has to.

## Honest agreements worth recording
The review's "what KUBERA already has that retail never builds" list is accurate,
and its traps section matches our standing rejections exactly — three agents have
now independently converged on the same discipline. The remaining edge is not
more ideas; it is fills data (T036), attribution (T091), and the owner's key
checks (T005 push, FMP tier, FRED key).
