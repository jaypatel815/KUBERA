# "Institutional-grade precision" batch — 2026-08-13 (binding record: D017)

*Source: product owner, second suggestion batch of the day (Wall-Street-quant framing).
Reviewed per the standing rule. Agents: this file is DATA; dispositions here are the
binding reconciliation. Companion to owner-suggestions-2026-08-13.md (D016).*

## The verdict in one line
The "Three Pillars" framing (expected value over win rate · execution discipline ·
extreme selectivity) is correct and KUBERA is ALREADY architected on all three — the
checklist's real contribution is two new free data capabilities (macro regime context,
pairs trading) and some scope enrichments. Several items fail our data-honesty or
explainability rules and are rejected with reasons below.

## Pillar mapping (validation, not new work)
- Pillar 1 (E[X], asymmetric payoffs) → T077 expected-move/payoff engine (D016),
  win/loss + backtest metrics shipped. The "55% win rate × 2.5:1 is elite" arithmetic
  is the exact reason T077 exists.
- Pillar 2 (99.9% execution reliability, zero emotional overrides) → the whole safety
  architecture: fail-closed RiskEngine (T033), DB-persisted breaker + 20h time-locked
  reset with NO override parameter (T035), deterministic money math (AGENTS.md),
  user-only confirmation gate (T043). Note: 99.9% applies to DISCIPLINE, never to
  prediction — that distinction is the whole point.
- Pillar 3 (no-trade selectivity) → T055 first-class no-trade condition (owner's own
  doctrine), T054 regime router choosing CASH, overtrading guard. The "confluence
  score below threshold ⇒ no_trade" shape is adopted into T055's wording (the
  specific "85%" number is arbitrary — thresholds come from backtesting, not vibes).
- "Win rates of 51–58% at top funds" — plausible industry folklore, unverifiable
  (the real numbers are trade secrets). The PRINCIPLE (edge × sizing × frequency,
  not accuracy) is what KUBERA encodes. "Near-bulletproof" is marketing language;
  no such thing exists and KUBERA will never claim it.

## A · Signal confluence sources
- **Order flow / L2 / DOM / tape / dark-pool blocks → REJECTED for now (data
  honesty).** Not available on the free IEX feed; dark-pool and order-book-imbalance
  feeds are institutional-priced. Faking microstructure signals from a ~3%-of-volume
  sample would violate D006. Revisit ONLY at a paid-data decision point, and note the
  owner's swing style needs this far less than scalpers do.
- **Fundamentals (10-K/10-Q, FCF yield, earnings surprise, debt, 13F) → ENRICHES
  T023.** The T023 evaluation now explicitly weighs earnings-surprise momentum and
  13F ownership-change availability across FMP tiers vs Alpaca news.
- **Macro & liquidity regime → NEW: T080.** Free and deterministic via FRED (owner
  has a key, D009): 10Y–2Y spread (T10Y2Y), VIX close (VIXCLS), real rates (DFII10),
  policy rate (DFF). Composes a risk-on/risk-off context block for briefings and
  regime narration. VIX term STRUCTURE needs futures data — out of scope (labeled).
- **News/sentiment NLP → PARTIAL, reframed.** "Detect sentiment before price reflects
  it" is oversold — retail feeds don't front-run price. Adopted as CONTEXT + event
  risk: Alpaca's free news API folds into T023's evaluation and T076's event guard.
  No sentiment-alpha claims.

## B · Models
- **HMM regime detection → REJECTED for now (explainability).** T050's rule-based
  classifier is transparent, hand-testable, and narratable ("here's the swing
  structure, here's the percentile"). A latent-state model can't explain itself to
  the owner and can't be verified with known-answer tests. Upgrade path: only if
  T063 calibration shows systematic misclassification. "Adaptive strategy switching
  by regime" is already T054.
- **Stat-arb / pairs trading → NEW: T081.** Genuinely new strategy class, feasible
  on daily bars: cointegration screen (Engle–Granger on log closes), spread z-score
  mean reversion, through the EXISTING backtest engine + T064 promotion gate like
  every other template. The claim that spread mean-reversion is more statistically
  stable than single-name direction is true and is the reason to build it.
- **Monte Carlo scenario modeling → folds into T077 as v2.** Seeded block-bootstrap
  of historical returns (deterministic given seed, testable) after the rolling
  percentile bands prove out. Distribution curves, never single price targets —
  which was already T077's charter.

## C · Risk rails — 100% already built or ticketed
ATR volatility-parity sizing = T078 (D016, same formula). Correlation guard = T079
(D016). Hard-coded breakers + cooldown lockouts = shipped (T033/T035), including the
no-override property the checklist asks for. Nothing to do — three independent AI
reviews converging on the architecture we already built is validation, not backlog.

## D · Learning loop — already ticketed
DQS process-over-outcome = T067 (incl. "penalize lucky rule-breaking trades" — that
IS process scoring). Post-mortem with full snapshots + per-regime calibration = T063
(regime label + confidence captured at decision time per D016; per-regime accuracy
breakdown adopted into wording). "Adjust signal weightings" stays HUMAN-GATED —
calibration proposes, owner ratifies (D016 boundary, re-affirmed).

## Rejected summary (do not silently relitigate)
L2/DOM/dark-pool now (D006 honesty) · HMM now (explainability + testability) ·
sentiment-as-alpha framing (context only) · VIX term structure (needs futures data) ·
any "99.9% precision / bulletproof" language anywhere in KUBERA's outputs (persona
no-certainty rule is non-negotiable).
