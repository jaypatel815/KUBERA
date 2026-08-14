# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
When this file exceeds ~150 lines, move old entries to /project-memory/archive/.

## 2026-08-14 — T091 done: attribution — every outcome credited to the conditions that opened it
signal_log now carries regime_label (the loop persists what the classifier saw — on
ordered, no_trade, AND rejected rows, so restraint is attributable too),
sub_strategy (the router names its leg via a last_leg attribute), and entry_bucket
(ET session fifths: pre/first_hour/midday/last_90/post — boundaries tested).
Transaction gains order_id — the join key from a broker fill back to the logged
decision that placed it (migrations f71b527814ef + 89e88db0d156). analysis/
attribution.py: FIFO round trips, each consumed slice's P&L credited to the ENTRY
lot's tags (hand-walked: one sell consuming two lots across two regimes), manual
trades land in "unattributed" (visible, never dropped), oversold surfaced, win rates
per tag, and the standing note: narrate COUNTS with every P&L figure. get_attribution
(registry 24, guards ×3) + GET /api/attribution with activity-by-regime counts.
Verified: verify.py PASS — 437 passed, 3 skipped (ruff sorted imports).
The D020 #2 question — "is the regime classifier adding value?" — now answers itself
as fills accumulate. Owner: trade the loop a while, then ask the Orb "what's my
attribution look like?".
Next: T090 liquidity costs or T093 portfolio risk+reconciliation; T082 Orb = Gemini.
Blockers: none.

## 2026-08-14 — T036 done: fills are ground truth now + the loop respects the clock
The biggest unlock ships. data: get_fills (activities API) + get_clock (the BROKER'S
clock — is_open/next_open, no local tz guessing); data/fills.py syncs fills into
transactions deduped per (account, external_id) — rerun-safe, proven by test.
Loop: enforce_market_hours — closed market → no_action with the honest reason ("an
order now would queue for the open print — the entry the doctrine forbids"), logged
with source=alpaca-clock; entry_delay_minutes joins the T055 no-trade reasons for
BUYS only (9:40 ET blocked at delay 30, 10:31 proceeds, 9:35 SELL passes — all
tested; ET math via the broker timestamp + zoneinfo). scripts/sync.py syncs fills
every run ("fills +N/M known"); paper_trade.py guards ON by default (--after-hours
escape, --entry-delay 30 default per doctrine). Owner-visible: the loop now refuses
to trade a closed market and won't buy the open print unless told to.
Verified: verify.py PASS — 429 passed, 3 skipped (ruff trimmed one unused import).
UNLOCKED: T088 slippage, T089 live MAE/MFE, T091 attribution, T060 TWR — the whole
measurement family now has its data source. Owner: run python scripts\sync.py to
start accumulating fills.
Blockers: none.

## 2026-08-13 — D021: the shorting question asked and ANSWERED — defer 30 days
Owner-uploaded PDF gap analysis (sixth batch, repo-aware). Its key catch: T081 pairs
is impossible long-only — and long-only is a deliberate rail, so the choice went to
the owner. DECIDED: defer ~30 days; long-only stands until paper DQS history proves
discipline; revisit on evidence ≈2026-09-12 (DQS trend, override rate, tier trips).
ADOPTED: strategy-decay DEMOTION into T093 (CUSUM drift vs backtest expectation →
promotion_status flips to "demoted" → the loop's gate refuses automatically — T064's
twin). NEW: T094 HRP (written scale trigger), T095 Fama-French loadings (free Ken
French data, dep 60+ snapshot returns). ENRICHED: T068 universe-screener. DEFERRED
with triggers: impact models/VWAP slicing (the ADV cap makes the problem impossible
at this scale). Convergence recorded: six reviews in, the backlog is decision- and
data-constrained — unlocks are T036 fills, T023 keys, T005 push, and now the clock
on the shorting revisit. Dispositions: docs/research/quant-gap-analysis-pdf-….md.
Verified: verify.py PASS — 422 passed, 3 skipped (memory session).
Next: T036 fills sync is now clearly the top build (unlocks T088/T089/T091).
Blockers: none.

## 2026-08-13 — D020: quant-gaps review — the measurement layer begins
Gemini's best review yet (repo-aware; its traps section independently re-derived our
D017/D019 rejections — three agents converged on the same discipline). BUILT the two
pure-math top picks same-session: trade_excursions (MAE/MFE per trade + WINNERS'
average MAE — the stop-calibration number; close-to-close labeled until T036 fills)
and Sortino + Omega in metrics (downside-only honesty; both refuse to fake a value
when there's no downside — error/None, never infinity). NEW T088–T093: execution
quality (slippage_bps, dep T036) · live MAE/MFE · liquidity-aware costs (live
spread_bps + conservative ADV cap) · ATTRIBUTION pack (persist regime/sub-strategy/
entry-bucket at order time — answers "is the classifier adding value") · parameter
stability sweeps (anti-curve-fit) · portfolio risk summary + daily reconciliation +
degradation detection. ENRICHED: T068 ranking criteria, T077b band calibration.
Theme on record: KUBERA can now DECIDE well; D020 is about MEASURING whether the
decisions work. T036 fills = the single biggest unlock left.
Verified: verify.py PASS — 422 passed, 3 skipped.
Next: T036 (fills sync — unlocks T088/T089/T091 attribution family) or T091 schema
prep; T082 Orb pack still prime Gemini bait.
Blockers: none.

## 2026-08-13 — T086 done: position triage — "should I average down?" answered honestly
analysis/triage.py judges an existing position against the LIVE exit plan (tool
composes regime + levels + ATR + active breakout, then compares entry vs latest trade):
EXIT when invalidation is closed through — with the sentence that matters: "adding here
is increasing exposure to a losing idea, not lowering an average" (asserted in tests);
EXIT_AT_TARGET when the range completes ("wanting more is a NEW thesis"); otherwise
HOLD with an honest add-assessment — range adds allowed ONLY in the lower quarter of
the invalidation→target span (buy support, never mid-range: "worst risk/reward"),
trend adds NEVER blessed on dips ("the market arguing with the thesis" — adds happen
on strength). Review-clock expiry flagged. Every reading carries unrealized P&L,
distance to invalidation/target, risk_remaining_atr, and the standing honesty note
pointing at size_position for combined-risk math. triage_position (registry 23,
guards ×3) + GET /api/triage/{symbol}?entry_price=&days_held=.
Verified: verify.py PASS — 418 passed, 3 skipped.
Owner Q&A scoreboard: #4 scale-out/average-down now SHIPPED (5 of 7 fully live).
Next: T087 trade monitor (needs T074/T082 rails) or T081 pairs; T082 Orb = Gemini bait.
Owner: ask the Orb "I'm in SPY from 640, should I add or get out?"
Blockers: none.

## 2026-08-13 — T085 done: "how many shares?" answered by voice
size_position tool (registry 22, guards ×3) + GET /api/size/{symbol}: exact new-buy qty
= min(risk_notional × tier_multiplier, cap_headroom) with tier 3+/breaker → 0 and a
blocked_reason; risk leg from the T078 sizer (equity × 1% / 2×ATR), cap headroom counts
the existing position, price = LATEST TRADE with age + stale flag disclosed (not
yesterday's close), stop_price returned so the narration can say "111 shares, stop
175, risking $1,000". `binding` names the limiter. Hand-proven: cap binds at 111.732 sh
(100k clean), tier-2 halving → 110.056, tier 3 pause, breaker block, headroom erosion
by held position, thin-history refusal.
Verified: verify.py PASS — 408 passed, 3 skipped.
Next: T086 position triage or T081 pairs; owner: ask the Orb "how many shares of SPY
could I buy right now?" — it'll answer with the stop and what limited it.
Blockers: none.

## 2026-08-13 — Owner capability Q&A → three tickets (T085–T087)
Owner asked seven "can KUBERA…" questions. Answers on record: options contract picks =
future phase (doctrine caveat only, no ad-hoc build); probability-of-profit sizing =
reframed to risk-based sizing (shipped) + historical win/payoff context (T077) — single-
trade probability claims stay rejected (D017), fractional-Kelly noted as advisory-only
future view; entry/exit = shipped (router/levels/breakouts/exit plans); scale-out vs
average-down = machinery exists via invalidation + DQS, dedicated advisor ticketed
T086; exact quantity = shipped in the loop, chat exposure ticketed T085 (quick win);
vol-dies-after-entry = observable on demand (T052), proactive monitoring ticketed T087
(deps T074/T082/T036); when NOT to trade = strongest muscle (T055/T067/T064/breaker,
all logged). No code this session — memory only.
Next: T085 is a 30-minute wiring win; T086 after; T081 pairs still queued.
Blockers: none.

## 2026-08-13 — T064 done: the promotion gate — strategies must EARN the paper loop
backtest/stats.py: per-trade stats from the 0/1-weight contract (hand case: +21%/−10%
→ PF 2.1, open-at-end flagged), Calmar (None when undefined), and the ANCHORED
walk-forward: one no-lookahead run, equity segmented, pass = overall > 0 AND ≥ half
the segments non-negative. Honesty in the docstring: parameterless templates can't
overfit, so this screens CONSISTENCY across periods — and flat curves fail (overall 0
is not > 0; no free promotions). Ledger: promotion_status (migration 04e68aa1c90a),
promote_template records verdict + segment returns into params_json, is_promoted is
per (template, symbol) — SPY evidence doesn't transfer to AAPL. Loop: require_promotion
refuses unpromoted BUYS as a logged no_trade (sells always exempt); scripts/promote.py
CLI; paper_trade.py now gates BY DEFAULT with --skip-promotion-gate as the deliberate
escape. Proven in tests: momentum FAILS promotion on chop history, the router PASSES.
Verified: verify.py PASS — 401 passed, 3 skipped.
Next: T081 pairs (must pass this gate to run — fitting), T082 Orb (Gemini), owner:
run `python scripts\promote.py regime_router SPY` before the next paper session.
Blockers: none.

## 2026-08-13 — T056 done: exit plans — THE REGIME PACK IS COMPLETE (T050–T056 + T075)
"How long do I hold?" is now data keyed to the thesis: analysis/exit_plan.py returns
invalidation level (the CLOSE that kills the thesis) with its reason, target (ranges
only — trends are RIDDEN, not targeted; the p95 band is a review point and the code
says so), review horizon in sessions (range 10 / trend 5 / breakout = T053's window /
downtrend 1), stop_distance_atr, reward_risk (guarded against stale levels), and
doctrine notes (mid-range = worst RR; downside break = exit information for a
long-only book; coil = expansion picks the plan). get_exit_plan composes regime +
levels + ATR + active breakout + expected-move p95 in one call (registry 21) +
GET /api/exit-plan/{symbol}.
Verified: verify.py PASS — 389 passed, 3 skipped.
THE OWNER'S DOCTRINE IS FULLY CODE: day-typing (T050), edges (T051), intraday
VWAP/RVOL (T052), volume-judged breakouts (T053), router (T054), no-trade (T055),
exits (T056), confluence (T075) — every claim tested, every number dated.
Next: T081 pairs / T064 rigor / T082 Orb (Gemini) / T023 key check (owner).
Blockers: none.

## 2026-08-13 — T075 done: timeframe confluence — the regime pack's capstone
analysis/confluence.py: assess_confluence takes plain values (decoupled from the
reading dataclasses — the TOOL extracts) and adjusts the DAILY confidence only, never
the regime call: intraday agreement +0.05 / conflict −0.10, VWAP side aligned +0.05 /
against −0.05, churn (≥4 crossings) −0.05; clamped [0.05, 0.90]; every reading states
the D006 absence of volume-delta confirmation. get_confluence (registry 20, guards ×3)
classifies 1Day + 1Hour with the SAME T050 classifier (ISO timestamps serve as dates)
and reads the 5Min session; each intraday view degrades independently with a `gaps`
why. GET /api/confluence/{symbol}. Full-agreement fixture proves adjusted > daily and
cap at 0.9; thin-intraday fixture proves neutral degradation.
Verified: verify.py PASS — 378 passed, 3 skipped.
Regime pack status: T050–T055 + T075 DONE; only T056 (structured exit plans) remains.
Next: T056 to finish the pack, or T081 pairs / T064 rigor / T082 Orb (Gemini). Owner:
/api/confluence/SPY or ask the Orb "do the timeframes agree on SPY?".
Blockers: none.

## 2026-08-13 — T063 done: the decision journal — "why did I buy that?" now has an answer
decision_journal table (migration 080e1c184167, UTCDateTime→sed as usual) captures every
recommendation AT decision time: verdict/confidence/thesis/horizon/entry/target/stop/
key-risk + regime context (D016), and the owner's FOLLOW or OVERRIDE with a note (D018 —
override-rate is the behavioral metric that will feed T067b). The model journals ITSELF:
persona CORE_RULES gains "a recommendation that isn't journaled didn't happen" +
mark_decision on owner report (keyword guard-tested). get_journal returns entries +
summary with v1 calibration: aged entries (past horizon, with entry + direction; hold
excluded) judged on direction vs latest price — hit_rate narrated as a process check,
never a performance claim. Registry 19 tools (record_decision, mark_decision,
get_journal); GET /api/journal.
Verified: verify.py PASS — 368 passed, 3 skipped.
Next: T075 confluence is the last regime-pack item; T082 Orb pack for Gemini; T081
pairs or T064 rigor for the backtest track. Owner: recommendations now self-record —
ask "show me my decision journal" after your next few chats.
Blockers: none.

## 2026-08-13 — T080 done: macro context — the broad-market weather report
data/fred.py: minimal httpx client for four documented series (T10Y2Y, VIXCLS, DFII10,
DFF); skips FRED's "." missing-value placeholders and returns each series' latest REAL
observation with ITS OWN date (FRED calendars differ — narration must show dates);
400 → actionable "check FRED_API_KEY" error; settings.require_fred fail-fast +
.env.example entry. analysis/macro.py: pure composition with conventions documented in
the module (inversion = caution-not-a-timer; VIX calm/normal/elevated/stressed at
15/20/30; real rate >2 restrictive) → labeled reads + cautionary-signal list + count +
"never a trade signal by itself". get_macro_context tool (registry 16; ToolContext
gains a fred slot) + GET /api/macro (503 with key instructions when unconfigured).
Verified: verify.py PASS — 359 passed, 3 skipped (ruff auto-sorted one import block).
Next: T075 confluence or T063 decision journal are the top builds; T082 Orb pack is
prime Gemini bait. Owner: put FRED_API_KEY in .env (free key, link in .env.example),
restart, then ask the Orb "what's the macro picture?" or open /api/macro.
Blockers: none.

## 2026-08-13 — D019: event-intelligence batch reconciled — base rates in, ML gated
Owner's fourth batch (sell-the-news/NLP/XGBoost). Adopted the honest core: T083 event
reaction base rates (post-earnings moves by beat/miss + pre-event runup from our own
bars — evidence, not prophecy) and T084 transcripts-as-labeled-context via the existing
LLM layer; T076 gains the priced-for-perfection flag; T023 tier check now covers
transcripts explicitly. Re-rejected per D017 (no new evidence): 99.9% accuracy; also
rejected now: XGBoost EPS predictor (Phase 7 behind §7.7 + T064; free fundamentals
aren't point-in-time — training would learn corrupted history) and directive outputs
with invented confidence (persona guard). HYGIENE FLAG: the batch reused shipped IDs
T075/76/77 — external AIs need the AGENTS.md resume prompt before proposing.
Dispositions: docs/research/event-intelligence-review-2026-08-13.md.
Verified: verify.py PASS — 349 passed, 3 skipped (memory/docs session).
Next builds unchanged: T080 macro (quick win), T075 confluence, T063 journal; T083
becomes buildable the moment T023 lands earnings dates. Owner action: T023's key
check is the gate on this whole thread — worth doing soon.
Blockers: none.

## 2026-08-13 — T062 done: morning brief, EOD report, weekly review — KUBERA starts the day with you
api/brief.py composes three reads, every number deterministic + timestamped, LLM only
narrates: MORNING — account, risk (tier/breaker/DQS), and for each holding + SPY the
overnight gap (latest trade vs last close, stale flag surfaced — Friday's price never
poses as live), regime + confidence, expected 5-day band, nearest support/resistance.
EOD — every decision today with its reasons (no_trade reasons shine here), day P&L vs
day-start, budget consumption. WEEKLY — the investment-committee review: equity vs SPY
with excess return from snapshots, discipline counts (orders / deliberate no-trades /
rejections / tier restrictions), and facts_for_lessons with the narration rule "draw
lessons from these facts only — never invent numbers". Missing data degrades to
{available: False, why} — the gap is information. T068/T076 absences stated in payload.
get_brief tool (registry 15, guards ×3) + GET /api/brief?type=morning|eod|weekly.
Verified: verify.py PASS — 349 passed, 3 skipped.
Next: T080 macro context (quick win) or T075 confluence or T063 journal. Owner: say
"give me my morning brief" to the Orb — it narrates the whole thing; or /api/brief.
Blockers: none.

## 2026-08-13 — T067 done: graduated risk tiers ENFORCED + Decision Quality Score
The owner's commitment device grows a ladder. risk/tiers.py: daily-loss-budget
consumption → tier 0–4; the paper loop enforces (buys only, sells always exempt):
tier 1 ≥25% doubles the no-trade floors, tier 2 ≥50% halves new-buy notional, tier 3
≥75% pauses entries as a logged no_trade, tier 4 = the breaker, untouched. Precedence
subtlety handled: when the breaker is TRIPPED the tier logic steps aside so the gate
rejects loudly ("halted") instead of a soft no_trade — tested explicitly. risk/dqs.py:
process-not-outcome DQS v1 from signal_log — frequency vs the overtrading guard,
trading-into-drawdown share, sizing CV, restraint (no_trade count) scored FREE; empty
window = 100 ("no activity, no bad habits"). Honesty: v1 scores the loop's pattern;
owner-fill scoring + follow/override rate = T067b (needs T036/T063). get_risk_status
tool (registry 14) + GET /api/risk. One sandbox lesson re-learned: endpoint tests with
in-memory SQLite need StaticPool (TestClient threads).
Verified: verify.py PASS — 337 passed, 3 skipped.
Next: T062 briefs (morning/EOD — now has regime, intraday, expected-move, risk status
to compose from) or T075 confluence or T080 macro. Owner: ask the Orb "what's my risk
status?" or open /api/risk.
Blockers: none.

## 2026-08-13 — T077 done: expected moves as distributions — ranges, never targets
analysis/expected_move.py: overlapping horizon-day returns over the trailing lookback
→ percentile bands via statistics.quantiles(method="inclusive") (hand-verified:
3-sample p05 = −0.08 interpolation), up_frac, median |move|, payoff ratio (avg winner
/ avg loser; None when one side is empty — all-up history has no ratio, tested). Vol
clustering per D016: each sample tagged with trailing-vol at its start, terciled;
reading reports the CURRENT tercile + bands from matching history only — the
quiet-tape test proves conditioned p95 shrinks >5x vs wild-contaminated unconditional.
Honesty hard-coded: every reading carries "NOT a forecast" + the overlap-
autocorrelation caveat; tool description orders ranges-not-targets narration.
get_expected_move (registry 13, guards ×3) + GET /api/expected-move/{symbol}.
Verified: verify.py PASS — 322 passed, 3 skipped.
Next: T067 DQS (the coaching centerpiece) or T062 briefs (both fed now); T077b
(Monte Carlo + loop integration) queued. Owner: /api/expected-move/SPY?horizon_days=5
or ask the Orb "how far does SPY usually move in a week?".
Blockers: none.

## 2026-08-13 — T054+T055 done: the router picks the playbook; "no trade today" is now a decision
T054: make_range (long only the lower half of the trailing range, flat above) +
make_regime_router (structure→momentum, range→range trading, else CASH) on the
closes-only T030 contract via _regime_lite (swing HH/HL + SMA-slope fallback).
THE CATCH OF THE SESSION: first cut leaked longs in bars 39–44 of the BEAR fixture —
between lookback and lookback+5 bars, structure is UNKNOWABLE, and the range trader
treated "can't tell" as "no trend" and bought the falling knife. Fix: _regime_lite
gained an explicit "unknown" state; the range trader refuses anything but a CHECKED
"none". Acceptance: router beats always-momentum in CHOP (0.0 vs >100%), rides BULL,
flat through BEAR. Also learned/encoded: engine weights sit one bar after decisions
(no-lookahead shift) — hand test documents it.
T055: paper loop's new no_trade action (buys only; sells always allowed): overtrading
guard (5/day across everything), ATR cost floor (T077 proxy), quiet-market check via
the full classifier (RVOL < 0.3 + bottom-quartile width). Every no_trade row logs its
reasons + "capital preserved by design".
Verified: verify.py PASS — 311 passed, 3 skipped.
Next: T077 expected-move engine (replaces the ATR proxy, feeds T056 exits), or T075
confluence, or T067 DQS. Owner: python scripts\paper_trade.py SPY --strategy
regime_router — KUBERA now picks the playbook AND can conclude "nothing today".
Blockers: none.

## 2026-08-13 — T052 done: intraday VWAP + time-of-day RVOL — the doctrine's backbone
First ticket of the D018 build order. data: get_intraday_bars(timeframe 1Min…1Hour,
days<=30) — tz-aware UTC bar starts. analysis/intraday.py: sessions grouped by ET date
(zoneinfo; tzdata dep added for the owner's Windows — a 20:30-ET after-hours bar stays
with its ET day even past UTC midnight; boundary TESTED), RTH filter default-on,
cumulative session VWAP on typical price (hand case: 5000/500=10.0), VWAP crossings
counter (running-VWAP side flips — the "crossing without holding = no trend" churn
signal), and intraday RVOL implemented as the doctrine defines it: today's cumulative
volume at this time-of-day vs prior sessions' cumulative volume by the SAME ET time
(hand case: 600 vs 300 → 2.0; a later prior-session bar proves the cutoff). Zero-volume
degrades to None honestly; D006 note on every reading. get_intraday tool (registry 12,
guards ×3 bumped) + GET /api/intraday/{symbol}.
Verified: verify.py PASS (12 new tests; full suite green).
Next per D018 order: T055 no-trade condition (+T054 router alongside), or T075
confluence which just unblocked. Owner: /api/intraday/SPY during market hours, or ask
the Orb "what kind of day is SPY having?" — note: pip install -r backend/requirements.txt
again (tzdata added).
Blockers: none.

## 2026-08-13 — D018: cross-agent review reconciled + three safety nets built
Owner uploaded a repo-aware review (best one yet — it read our memory files). ~70% was
priority votes on existing tickets (accepted: T052 → T055 → T077 → T067/T062; no new
strategy templates before the no-trade condition). BUILT the genuinely-new small items
same-session: (1) stale-data detection — latest trade/quote now carry age_seconds +
stale (>15 min), get_latest tool instructed to never present stale as live (session-
aware upgrade parked in T036); (2) scripts/backup_db.py — timestamped copies, --keep 14,
backups/ git-ignored, Task Scheduler line in docstring; (3) scripts/health_check.py —
server up / breaker tripped (reads risk_state directly, works with server down) / sync
freshness, exit code + best-effort Windows toast via --notify. Enriched T016 (PARKED:
Schwab approval pending — owner directive, Alpaca continues), T036, T060, T063, T064
(promotion_status enforced in loop), T079 (unblocked from T023); minted T082 Orb
upgrade pack (conversations sidebar + portfolio panel + feed badges — Gemini bait).
Postgres deferred on evidence (see D018). Dispositions: docs/research/
agent-review-2026-08-13.md.
Verified: verify.py PASS (full suite green; +8 tests: stale flags, backup retention,
health checks).
Next: T054+T055 together (range strategy + router + no-trade), or T052 intraday first
per the adopted order. Owner: schedule the two scripts (docstrings have the commands);
T005 push remains the highest-value 5-minute action.
Blockers: none.

## 2026-08-13 — T053 done: breakout detector — escape + volume + HOLD, as events
analysis/breakout.py scans daily bars for fresh range escapes (a bar whose close exits
the prior L-bar extremes while the previous bar hadn't — continuations extend, never
restart) and judges each event on the doctrine's three parts: RVOL at the break
(RVOL_CONFIRM/RVOL_FAKEOUT imported from regime.py), hold-outside tracking
(held_bars = consecutive closes beyond the boundary), status judged ONCE on the first
hold_confirm bars: confirmed / failed / unconfirmed / pending, plus scan-level
`active`. The named test test_the_hundred_to_106_to_99_lesson locks the owner's
canonical fakeout: volume-confirmed escape that returns inside → FAILED regardless of
volume. Fixture lesson worth remembering: degenerate h=l=c bars made the 99-return
look like a down-escape — the fix was a realistic range floor in the FIXTURE, not code.
Reachable: get_breakouts tool (registry 11; guards bumped ×3) + GET /api/breakouts/…
Verified: verify.py PASS — 278 passed, 3 skipped.
Next: T054 range strategy + regime router (T050+T051+T053 all feed it now) — the meta-
strategy that picks momentum/range/CASH. Owner: /api/breakouts/SPY or ask the Orb
"did SPY break out recently?".
Blockers: none.

## 2026-08-13 — T051 done: support/resistance — "repeated rejections define the range"
Built analysis/levels.py: swing highs/lows (regime.py's swing_points promoted to public,
shared) pooled and clustered by price proximity (sorted greedy walk, running-mean join
within tolerance_frac=1%); a cluster becomes a LEVEL only with >= min_touches swings
(default 2). Levels carry price (member mean), touches, provenance kind — support /
resistance / mixed (support-becomes-resistance detected and tested), first/last touch
dates, signed distance from last close; reading includes nearest support + resistance
(positional, any provenance — "trade the edges"). Reachable now: get_levels tool
(registry = 10; count guards bumped in 3 test files) + GET /api/levels/{symbol}. Tests:
two hand-walked micro fixtures (3-touch S/R + dropped stray; mixed-kind breakdown with
nearest_support=None), tolerance/min_touches behavior, validation, 60-bar triangle
through tool + endpoint (7-touch levels at 94.5/105.5).
Verified: verify.py PASS — 269 passed, 3 skipped.
Next: T053 breakout detector (T050's escape + T051's levels + RVOL threshold) is now
fully fed; then T054 range strategy + router. Owner: ask the Orb "where's support on
SPY?" or open /api/levels/SPY.
Blockers: none.

## 2026-08-13 — T078 done: vol-parity sizing — position size now answers to volatility
Built: Wilder ATR (true_ranges + atr) in analysis/metrics with hand-computed tests;
risk/sizing.py volatility_parity_notional — a buy may risk at most
equity × risk_per_trade_frac (default 1%, RiskLimits hard-bands it ≤5%) if the
stop_atr_multiple×ATR stop is hit, so size shrinks as volatility grows. Paper loop:
buys sized BEFORE the gate (sizing note logged on bound orders + in SignalLog.reasons),
sells untouched (reducing risk is never blocked), <ATR_WINDOW+1 bars → no_action
fail-closed. Design decision worth keeping: the sizer ONLY shrinks the request — the
RiskEngine's 20% cap still rejects oversized targets loudly; no silent auto-resize of a
rule violation. Legacy loop tests pass unchanged (fixture H/L made sane: ATR=2 → ceiling
44,750 above all legacy deltas). Whipsaw test: ATR 41 → 15k request sized to 12.195
shares — hand-walked.
Verified: verify.py PASS — 256 passed, 3 skipped.
Next: T051 support/resistance or T053 breakout detector (regime pack), or T080 macro
context (quick win). Owner: nothing to do — sizing is automatic in paper_trade.py.
Blockers: none.

## 2026-08-13 — "Institutional precision" batch reviewed (D017): pillars validated, T080/T081 minted
Owner's second batch (quant-fund framing). Verdict: the Three Pillars — E[X] over win
rate, execution discipline, no-trade selectivity — are correct AND already our
architecture (T077 / risk rails / T055); checklist section C was 100% already ticketed
(T078/T079/T033/T035), which is convergent validation. NEW: T080 macro regime context
(FRED: 10Y–2Y, VIXCLS, real rates — free + deterministic + dated) · T081 pairs/stat-arb
template (cointegration screen, spread z-score MR, through the existing engine + T064
gate). ENRICHED: T023 (earnings surprise/13F; news = context not alpha), T077 (seeded
MC v2), T055 (confluence-score no-trade reason). REJECTED with reasons in the review
doc: L2/DOM/dark-pool (D006 honesty), HMM now (unexplainable/untestable), sentiment-as-
alpha, VIX term structure, all "bulletproof/99.9%" language. Binding record:
docs/research/institutional-precision-review-2026-08-13.md.
Verified: verify.py PASS — 234 passed, 3 skipped (memory/docs session).
Next: build tickets unchanged — T051/T053 (regime pack) or T077/T078; T080 is a good
quick win (pure httpx + FRED, no new architecture).
Blockers: none.

## 2026-08-13 — Owner suggestion batch reconciled (D016): T075–T079 minted, four tickets sharpened
Owner delivered a 5-part improvement review. Reconciled without duplication (dispositions
binding in docs/research/owner-suggestions-2026-08-13.md): NEW T075 multi-timeframe
confluence (after T052; volume-delta deferred to SIP) · T076 event-risk calendar guard
(FRED/earnings → pause/scale before FOMC/CPI/NFP) · T077 expected-move distribution
engine (rolling percentile bands, never point forecasts; feeds T055's cost threshold +
T056 exits) · T078 ATR vol-parity sizing (MIN with existing 20% cap — only ever shrinks)
· T079 correlation/overlap guard (engine behind T066's pre-trade correlation check).
EXTENDED: T067 tiers now ENFORCED in the paper loop (25/50/75/100% budget → stricter
R/R / half size / entry pause / breaker), T063 captures regime+targets and calibrates
(human-gated re-weighting), T064 walk-forward = promotion gate, T062 briefs go
voice-first. AGENTS.md gains agent-strengths defaults (Claude math/tests · Gemini UI/web
· ChatGPT ideation-as-data). Already covered: T074, T052, process-over-outcome persona.
Verified: verify.py PASS — 234 passed, 3 skipped (docs/memory session; suite untouched).
Next: T051 support/resistance or T053 breakout detector remain the natural builds;
T077/T078 are strong candidates right after — both are pure deterministic analysis.
Blockers: none.

## 2026-08-13 — T050 done: regime classifier — the doctrine becomes code
The regime pack opener. analysis/regime.py classifies from daily bars, faithful to
docs/research/regime-trading-notes.md: swing-based HH/HL structure (strict local extrema,
SMA-slope fallback since monotone series have no swings), standing 20-bar range + width
percentile across trailing rolling windows (low percentile = the coil), close-escape vs
the prior window with suspected_fakeout when RVOL < 1.0 (the $100→$106→$99 lesson),
RVOL against the symbol's own baseline with volume_feed REQUIRED (D006 label + SIP
caveat in every reading). Decision order matters and is tested: a matured trend outranks
its own escapes. Confidence = fixed 3-signal checklist per label (0.35 + 0.15/pass, cap
0.9 — a daily-bar heuristic never claims certainty); checks dict returned so chat can
say WHY. Shipped reachable: get_regime tool (9 total) + GET /api/regime/{symbol}.
Tests: sawtooth trend fixtures with rising/falling swings, stationary triangle,
coil (13/76 percentile hand-walked), volume-confirmed breakout (15/77), fakeout twin,
plus micro known-answers for rvol/escape/swings/fallback and full validation.
Verified: verify.py PASS — 234 passed, 3 skipped.
Next: T051 support/resistance (feeds the range strategy) or T053 breakout detector;
T054 router wants both. Owner: ask the Orb "what regime is SPY in?" once server restarts.
Blockers: none.

## 2026-08-12 — T073 done: THE KUBERA ORB (Phase 5 opened early)
Owner wants Zoey OS-like experience (fetched zoeyos.com: voice-first workspace, living
visuals, visible agent work). Built the Orb: apps/web/orb.html served at GET / — canvas
orb with state-driven glow (idle/listening/thinking/speaking + audio-amplitude reaction),
browser SpeechRecognition for STT (Chrome/Edge), POST /api/chat(voice=true), streaming
GET /api/tts (edge-tts as lazy SERVER dep — 503 with install hint; text capped 2k),
tool-call chips per reply ("watch the work happen"), typed fallback, and the confirm
checkbox as the deliberate gesture. Tests: root route, tts 503/streaming/empty (fake
edge_tts). Owner setup: pip install edge-tts in the server venv, open localhost:8000.
Zoey's sub-second feel needs a realtime pipeline → T074 filed (LiveKit/Pipecat/OpenAI
Realtime + barge-in; verify landscape at build).
Verified: verify.py PASS — 213 passed, 3 skipped.
Next: owner opens the Orb; T074/T072 for voice polish, or back to T050/T069 substance.
Blockers: none.

## 2026-08-12 — MILESTONE: first spoken conversation (T071 ✔) + naturalness pass
Owner talked to KUBERA and it answered aloud — market snapshot with data-quality
skepticism (flagged DIA's wide spread) and an offer to go deeper. T071 accepted.
Owner feedback: sounds robotic → diagnosis: default SAPI TTS, not the words.
Shipped: KUBERA_VOICE env for edge neural-voice selection (AndrewNeural recommended),
VOICE_STYLE prosody rules (contractions, short varied sentences, natural openers, never
read digit strings — guard-tested), README voice ladder. T072 filed: human-grade TTS
backends (OpenAI TTS, local Kokoro). Also folded in field lint fixes on talk.py.
Verified: verify.py PASS — 209 passed, 3 skipped.
Next: owner flips KUBERA_TTS=edge tonight; T072 or T069/T050 next build.
Blockers: none.

## 2026-08-11 — Gemini (Antigravity) — talk.py CPU device fix & HTTP 503 error reporting
Fixed: (1) `scripts/talk.py` threw `RuntimeError: Library cublas64_12.dll is not found` on Windows when `faster-whisper` defaulted to CUDA. Added `device="cpu"` to `WhisperModel("small", device="cpu", compute_type="int8")` so local STT runs reliably on CPU without CUDA DLL dependencies. (2) Added `'v'` key as an input shortcut alongside `[Enter]` to start push-to-talk recording in `scripts/talk.py`. (3) Added `httpx.HTTPStatusError` exception handling in `scripts/talk.py` so 503/502 server responses print the server's actionable `detail` message (e.g. missing Alpaca or LLM keys in `.env`). (4) `test_llm.py` failed `test_build_provider_allows_keyless_custom_endpoint` when `OPENAI_BASE_URL` was set in `.env` (Ollama setup); added `monkeypatch.delenv("OPENAI_BASE_URL", raising=False)` and explicit `openai_base_url="https://api.openai.com/v1"` parameter to isolate fail-fast testing.
Verified: all 189 tests pass.
Next: T050 (regime pack) or T061 (IPS).
Blockers: none.

## 2026-08-12 — Owner doctrine captured → regime intelligence pack ticketed (T050–T056)
The owner delivered a detailed trading doctrine (day-type classification: trending vs
consolidation vs breakout; range trading at the edges; RVOL + volume-confirmed breakouts
vs fakeouts; VWAP; the no-trade condition as a first-class decision; options theta/IV
caveats). Preserved verbatim-in-spirit at docs/research/regime-trading-notes.md — READ IT
before building T050–T056. Seven tickets seeded: regime classifier, support/resistance,
intraday VWAP/RVOL, breakout detector, range strategy + regime router, no-trade condition
in the paper loop, structured exit_plan ("how long to hold"). Data-honesty constraint
threaded through: IEX feed = relative volume only until SIP upgrade (D006).
"KUBERA decides for me" = already true on paper (T032 loop); live authority stays behind
§7.4 — reaffirmed with the owner.
Next: T050 is the natural opener; T045 (MCP server) still pending in Phase 4.
Blockers: none.

## 2026-08-12 — T061 done (Investment Policy Statement) — KUBERA knows its owner
Built: investment_policy table (migration 08dfc64f8e4b), data/ips.py (partial upserts;
restriction lists replace wholesale; format_ips_for_prompt compact block), IPS injected
into EVERY chat system prompt as hard context ("check every recommendation against it,
state conflicts plainly"). Tools: get_ips (free) + update_ips — the FIRST live
confirmation-gated tool: the owner can set his IPS by talking, KUBERA asks for
confirmation, and only the typed/deliberate confirm flag completes it (T043 gate proven
in production use, not just tests). GET /api/ips for viewing. Registry now 8 tools;
count guards updated; safety guard now asserts gated == {update_ips}.
Verified: verify.py PASS — 209 passed, 3 skipped.
Next: owner should SET his IPS (by voice, fittingly) — then T069 tolerance estimation,
T062 briefs, and the coach all have their foundation. T050 regime pack still open.
Blockers: none.

## 2026-08-12 — T070 done (push-to-talk loop) — KUBERA can be TALKED to
Built: `api/voice_loop.py` — tested orchestration (audio → STT → /api/chat(voice=true) →
TTS): conversation threads across turns, silence never reaches KUBERA, and confirm passes
through ONLY from the typed gesture (all fake-tested). `scripts/talk.py` — Enter-to-talk
capture (sounddevice), STT backends (faster-whisper local default; KUBERA_STT=openai
fallback for py3.14 wheel gaps), TTS backends (pyttsx3/SAPI default; KUBERA_TTS=edge for
neural voices), typing `confirm` is the only confirmed-turn path. requirements-voice.txt
keeps audio deps out of backend CI. README try-it added.
Verified: verify.py PASS — 200 passed, 3 skipped. Spoken round-trip = owner run (T071);
sandbox has no audio hardware.
Next: T071 (owner: talk to it!), then T061 IPS or T050 regime pack.
Blockers: none.

## 2026-08-12 — Voice mode shipped (D015): owner is voice-first
Owner will primarily talk to KUBERA. Shipped now: ChatRequest.voice → run_chat_turn →
build_system_prompt(voice=True) appends VOICE_STYLE — spoken-aloud replies (no markdown/
tables/bullets, ear-rounded numbers, ~120-word default, natural recency phrasing), with
the safety invariant IN the prompt: a spoken "yes" is not the confirm flag. Tests: voice
prompt content, default-off, flag plumbing through the loop. T070 filed: push-to-talk
desktop loop (STT → /api/chat → TTS) — voice lands before Phase 5, not inside it.
Verified: verify.py PASS — 196 passed, 3 skipped.
Next: T070 (hear KUBERA speak) or T061 (IPS). Both high-value; owner's pick.
Blockers: none.

## 2026-08-12 — Time-locked breaker reset (commitment device) + T069
Owner disclosed the pattern: he sets risk limits, passes them, keeps trading. Built the
enforceable half NOW: RiskLimits.cooldown_hours (default 20h) — a trip sets
lockout_until; reset() raises LockoutActiveError until it passes; NO override parameter
exists by design; lockout persists to DB (migration 5b54677a6d1d) so restarts can't
shorten it; risk_reset.py explains the refusal. Tests: refusal with remaining time,
refusal 1 minute before expiry, allowed after, zero-cooldown legacy mode, restart
survival. Honest limits documented in the self-exclusion doctrine (gemini review doc):
KUBERA cannot freeze thinkorswim; friction ≠ cryptography; the structural answer is
KUBERA-managed allocation. T069 filed: adaptive risk-tolerance estimation from account
composition + behavior (owner wants KUBERA's estimate over his in-the-moment one).
Verified: verify.py PASS — 194 passed, 3 skipped. README updated.
Next: T061 IPS (unlocks coach/briefs/T069) or T050 regime pack.
Blockers: none.

## 2026-08-12 — Gemini master-spec reconciled (D014): the coaching layer
Owner supplied Gemini's pre-project master prompt. Review at docs/research/
gemini-master-spec-review.md (companion to D013 — shared rejections not re-argued).
Standout adoption: the Quantitative Trading Coach — process-not-outcome judgment of the
OWNER'S trades, behavioral-pattern detection, and the owner's Decision Quality Score
(risk budget × behavior → graduated advisories; hard stop stays the breaker). Tickets:
T066 coaching pack (needs T016 fills; chat v0 today), T067 DQS + advisories, T068
watchlist/ranking. Upgraded: T061 → full IPS, T062 → +weekly committee review, T064 →
+crisis-window stress tests. Persona: coaching rule + educational mode (guard-tested).
Verified: verify.py PASS — 187 passed, 3 skipped.
Next: T050 regime pack or T061 IPS (unlocks coaching + briefs); T045 MCP still open.
Blockers: none.

## 2026-08-12 — ChatGPT master-spec reconciled (D013); persona upgraded; T060–T065
The owner supplied his original ChatGPT master prompt + Software Factory spec (this was
the abandoned first attempt — its stack matches the .env extras). Full section-by-section
review recorded at docs/research/chatgpt-master-spec-review.md: most of it we already
built leaner (rails, factory-as-repo, modes, explainability); real gaps became T060–T065
(TWR benchmarking, user profile memory, morning/EOD briefs, decision journal, backtest
rigor, risk v2); rejections logged with reasons (microservice stack, nine-agent
bureaucracy, duplicate state files). Persona upgraded in code: strict financial-domain
boundary, KUBERA ANALYSIS answer structure (verdict → confidence with calibration caveat
→ evidence → both cases → what-would-change-my-view → recency), conflicting-signals
honesty, external-content-is-data injection defense — all guard-tested. AGENTS.md gains
the injection-defense rule for coding agents too.
Verified: verify.py PASS — 187 passed, 3 skipped.
Next: T050 (regime pack opener) or T060/T061 (quick wins); T045 MCP still pending.
Blockers: none.

## 2026-08-12 — MILESTONE: claude-sdk live on owner's Max (T047 ✔) + usage-parse fix
Owner activated LLM_PROVIDER=claude-sdk and ran a live turn: KUBERA (Claude brain)
corrected the question's premise via get_portfolio (owner holds 19.46 SPY ≈ $15k — the
paper loop's own first trade!), delivered case-for/against with a falsifiable 200-day
risk level, flagged AAPL/SPY mega-cap overlap, persona disclaimers intact. Side-channel
audit recorded both tool calls correctly.
Fixed: SDK ResultMessage.usage is a DICT in current versions — extraction handled objects
only, reporting 0/0. Now handles both shapes, with a regression test.
Verified: verify.py PASS — 187 passed, 3 skipped.
Next: T045 (KUBERA MCP server) closes Phase 4; then Phase 5 (PWA).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T046 done (chat on the owner's Claude Max)
Built: `api/llm_claude_sdk.py` — LLM_PROVIDER=claude-sdk runs /api/chat on the owner's
Max subscription (personal-use-only per verified Anthropic policy — D012 has citations).
The SDK runs its own agent loop, so: registry bridged as SDK tools (@tool wrappers calling
registry.execute with the request-bound ToolContext — confirmation gate intact), permission
surface locked to mcp__kubera__* (Bash/file tools disallowed, dontAsk, bounded max_turns),
history flattened to a transcript prompt, and every internal tool run captured as a
side-channel event the chat loop persists as tool rows (audit trail complete) + feeds the
recency footer. Lazy optional dependency; ConfigErrors are actionable. Fully mocked tests
(fake claude_agent_sdk module) — 186 passed, 3 skipped.
Owner activation = T047 (install SDK, claude setup-token, flip LLM_PROVIDER).
Next: T045 (KUBERA MCP server) is the last Phase 4 side quest; then Phase 5 (PWA).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T044 done (context budgeting)
Built: `api/context.py` assemble_context — groups history into indivisible blocks (an
assistant tool_call + its results can never split: provider APIs error on orphans, and
the pairing test proves integrity across budgets), drops oldest blocks whole within
KUBERA_CONTEXT_BUDGET_CHARS (default 24k chars), always keeps the newest block, and
elides tool payloads older than the freshest 4 blocks while assistant conclusions
survive. Wired into the chat loop. Long conversations now cost O(budget), not O(history).
Note: "relevant research memory" retrieval deferred to Phase 7 (needs pgvector, D007).
Verified: verify.py PASS — 179 passed, 3 skipped.
Next: T045 (KUBERA MCP server) or T046 (Max/Agent SDK provider). Phase 4 core otherwise
complete — spec §7.4-phase "Done when" needs only real-world conversation mileage.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T043 done (conversation rails as code)
Built: (1) confirmation gate — ToolSpec.requires_confirmation + ConfirmationRequiredError;
ctx.confirmed flows ONLY from ChatRequest.confirm (user's HTTP body — the LLM cannot set
it); chat loop surfaces confirmation_required to the model so it asks the user; guard test
asserts none of the 6 current tools require confirmation (future order tools must flip the
flag consciously). (2) recency post-check — ensure_recency_line appends a deterministic
"Data recency: <tool> asof <ts>" footer from ACTUAL tool timestamps whenever a
data-grounded reply lacks a date (handles str and datetime asof shapes).
Verified: verify.py PASS — 171 passed, 3 skipped. Full two-turn confirm flow tested.
Next: T044 (context budget), T045 (MCP server), or T046 (Max/Agent SDK provider).
Blockers: none.

## 2026-08-11 — Gemini (Antigravity) — terminal environment injection setting
Fixed: enabled `"python.terminal.useEnvFile": true` in `.vscode/settings.json` so integrated terminal sessions automatically inject environment variables from `.env`.
Verified: settings updated cleanly.
Next: T046 (Claude Agent SDK provider) or T043/T044/T045 as planned.
Blockers: none.

## 2026-08-11 — MILESTONE: first live KUBERA conversation (owner-verified)
Owner ran POST /api/chat on his machine with Ollama + nemotron-3.5-lightning (30B MoE,
tools-capable, free/local) via the OPENAI_BASE_URL path. KUBERA called get_latest +
get_symbol_briefing on AAPL and produced a properly hedged, dated, evidence-grounded
answer (verdict, asof-stamped metrics table, assumptions, falsifying risk, no certainty),
correctly noting the owner holds no AAPL. ~5.4k in / 1.3k out tokens per turn.
Environment fact for all agents: local tool-calling models work; nemotron-3.5-lightning
is the validated default for keyless local chat.
Next: unchanged (T043/T044/T045/T046).

## 2026-08-11 — Claude (Cowork) — chat provider options (owner hit API-credits wall)
Context: owner's Anthropic API account has no credits (Max subscription ≠ API billing).
Built: OPENAI_BASE_URL override — the OpenAI adapter now targets any OpenAI-compatible
endpoint (Ollama local = free, Groq, Gemini compat); keyless custom endpoints allowed,
real OpenAI still requires a key. Owner unblock: LLM_PROVIDER=openai +
OPENAI_BASE_URL=http://localhost:11434/v1 + OPENAI_MODEL=<ollama model>.
Filed: T046 — Claude Agent SDK provider to run chat on the owner's Max subscription
(Claude-account auth, registry as SDK tools; verify current subscription terms at build).
Also fixed earlier: conversation_id=0 now means new conversation (Swagger example trap).
Verified: verify.py PASS — 163 passed, 3 skipped.
Next: T046 (high value for owner) or T043/T044/T045 as before.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T042 done — KUBERA CAN TALK
Built: `api/chat.py` run_chat_turn — persona + replayed history → provider.complete →
execute requested registry tools (errors surfaced verbatim, results capped at 6k chars) →
loop until text (bounded by max_tool_rounds=6, honest message on exhaustion). New tables
conversations + chat_messages (migration 7bb8528ec2d3) persist EVERY message, tool call,
tool result, and token count — spec §2.7's "why did KUBERA say that" is a SELECT away.
Endpoints: POST /api/chat (DI: db, alpaca, market, llm provider — each 503s actionably
when unconfigured), GET /api/chat/{id} audit view. README: how to talk to KUBERA via
/docs (needs ANTHROPIC_API_KEY or OPENAI_API_KEY + LLM_PROVIDER).
Verified: verify.py PASS — 161 passed, 3 skipped. First LIVE conversation happens on the
owner's machine (LLM APIs not reachable from sandbox).
Next: T043 (conversation safety post-checks) and T044 (context assembly) polish the loop;
T045 (MCP server) remains the high-leverage side door. Owner: try talking to it!
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T040+T041 done (Phase 4 opened: persona + LLM layer)
Built: `api/persona.py` — build_system_prompt(asof, tools) with 8 CORE_RULES encoding spec
§2 (every number from tools, recency stated, no certainty framing, backtests-are-the-past,
paper clarity, explicit confirmation + risk-engine supremacy for anything order-shaped, no
gap-filling, not-an-advisor) + the analyst voice; guard tests fail if any rule is deleted.
`api/llm.py` — neutral message/tool-call format; AnthropicProvider + OpenAIProvider (thin
httpx, no SDKs) with full both-direction translation (tool_use/tool_result blocks vs
tool_calls/tool role) proven by captured-payload tests; build_provider selects via
LLM_PROVIDER with fail-fast actionable ConfigErrors. Model names are settings with
defaults (claude-sonnet-5 / gpt-5) — verify current names at T042 wiring time.
Verified: verify.py PASS — 154 passed, 3 skipped.
Next: T042 — POST /api/chat: the loop (persona + context → LLM → tool execution via
registry → final answer), conversation persistence, audit trail. Then T043 rails.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T034 done — PHASE 3 CORE COMPLETE
Built: `backtest_runs` table (migration 33592ebf6de6) + `backtest/ledger.py` — every run
recorded with strategy/params/period/metrics; `list_runs` with filters. Shared strategy
TEMPLATES + build_strategy (CLI + API + tools all use one registry). `GET /api/backtests`,
`POST /api/backtests/run`, and `run_backtest` as the 6th registry tool — the future chat
layer can test strategies conversationally, and §7.4 promotion evidence accumulates in the
ledger. Gotcha fixed: in-memory SQLite is per-connection; TestClient threads need
StaticPool (see test_ledger.py comment).
Verified: verify.py PASS — 145 passed, 3 skipped.
Phase 3 status: engine, strategies, risk rails + persistence, paper loop, ledger — DONE.
T036 (fills sync, market-hours guard) remains as optional polish.
Next: Phase 4 (T040 persona → T041 LLM abstraction → T042 /api/chat) or T045 (KUBERA MCP
server — small, high leverage). Owner tasks still open: T005 push, T007 finale.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T035 done (breaker survives restarts)
Built: `risk_state` table (single row, migration 35b6c01bf49b), `risk/persistence.py`
(restore/persist), `RiskEngine.restore()` (persistence-only, documented), paper loop now
restores state before acting and persists after every equity mark. `scripts/risk_reset.py`:
shows state; reset requires --note AND typing RESET. README updated (loop mode now safe;
reset instructions added). Fills-sync + market-hours guard split to T036.
Verified: verify.py PASS — 140 passed, 3 skipped. Killer test: trip → simulated restart
(fresh engine, same DB) → still blocked, zero orders reach the broker.
Next: T034 (results ledger — last Phase 3 ticket) or T036 polish; then Phase 4.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T032 done (paper-trading loop) — KUBERA can trade (paper)
Built: `backtest/paper_loop.py` run_paper_cycle — bars → strategy weight → target value
(weight × allocation × equity) → delta order → RiskEngine pre_trade_check → Alpaca PAPER
order. Every cycle writes a SignalLog row (ordered/rejected/no_action) with the data
snapshot. AlpacaClient.place_order (validates inputs; paper-only by construction).
New table signal_log + migration c09d9671853d. CLI scripts/paper_trade.py (--strategy,
--allocation, --loop). Tests hand-compute the buy qty (15000/179), prove rejected orders
never reach the broker, sells cap at held qty, and the tripped breaker blocks cycle 2.
Verified: verify.py PASS — 136 passed, 3 skipped. README try-it updated per standing rule.
Known gap → T035 filed: risk trip state is per-process; persist to DB so restarts can't
bypass the breaker. Owner should run cycles manually (not --loop) until T035 lands.
Next: T035 (small, safety) then T034 (results ledger) closes Phase 3.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — README testing guide + backtest demo (owner request)
Built: README "Try what's built so far" — every endpoint incl. /docs Swagger explorer,
sync, verify, repair. New `scripts/backtest_demo.py`: compares buy-and-hold / momentum /
SMA-cross / mean-reversion on real history with costs, graceful config/network errors.
NEW STANDING RULE in AGENTS.md session protocol: any session that changes the user-facing
surface updates README's try-it section — the owner tests from it. All agents comply.
Verified: verify.py PASS; demo script degrades cleanly without network (I002).
Next: T032 (paper-trading loop) unchanged.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T031 done (strategy library with regime proofs)
Built: make_momentum(lookback, threshold) and make_mean_reversion(window, band_frac) on the
T030 contract, plus regime test fixtures (BULL +1%/bar, BEAR -1%/bar, CHOP 100/82 range).
Key behavioral proofs: momentum stays 100% flat through the entire synthetic bear (capital
preserved, beats buy-and-hold by construction) and rides the bull after warmup; mean
reversion profits in chop and correctly sits out smooth trends. Hand-tracked equity curves
for both. MR is stateless (no hysteresis) — documented simplification.
Verified: verify.py PASS — 128 passed, 3 skipped.
Next: T032 (paper-trading loop: strategy → risk gate → Alpaca paper orders — the big one)
or T034 (results ledger). T032 recommended; its live pieces will skip in sandbox per I002
and prove out on the owner's machine.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T033 done (risk engine — the hard rails)
Built: `risk/engine.py` — RiskLimits (validated), OrderRequest, RiskDecision (timestamped,
all violated rules with numbers), RiskEngine. Fail-closed: uninitialized engine rejects all
orders. Position cap inclusive at the boundary; sells exempt from cap (they reduce risk).
Circuit breaker: trips at the daily-loss limit exactly, then blocks buys AND sells; neither
recovery nor a new day untrips it — only manual reset(note). Pure logic, no I/O; T032 owns
persistence of trip state and wiring to live equity marks.
Verified: verify.py PASS — 118 passed (22 new risk tests), 3 skipped.
Next: T032 (paper-trading loop through this gate) needs T031 (strategy library) — either
order works; T031 is the smaller bite. T040-T044 (conversation) remain open for any agent.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T030 done; Phase 3+4 backlogs seeded; D010 logged
Built: `backtest/engine.py` — minimal deterministic daily-bar engine (D010: hand-verifiable
over frameworks; revisit triggers logged). No-lookahead enforced by passing the strategy a
prefix slice (tested with a spy). Cost model (bps of shifted equity), weight validation,
flat-strategy Sharpe honestly None. `backtest/strategies.py`: buy_and_hold + make_sma_cross.
Every expected number in the 8 new tests is hand-computed, including a fully hand-tracked
SMA-cross equity curve.
Seeded: Phase 3 tickets T031-T034 (strategy library, risk module, paper loop, results
ledger) and Phase 4 tickets T040-T044 (persona, LLM abstraction, /api/chat, safety rails,
context assembly — unblocked, registry done).
Verified: verify.py PASS — 96 passed, 3 skipped.
Next: T033 (risk module — prereq for the paper loop) or T040/T041 (conversation layer).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T017 done (httpx plumbing unified)
Built: `data/_http.py` — build_client (auth headers, timeout) + checked_get (network-error
wrapping, actionable 401 hints, HTTP>=400 discipline). Both Alpaca clients refactored onto
it; error text preserved byte-for-byte. Pure refactor: same 85 tests pass unchanged.
Remaining Phase 2: T023 (fundamentals/news — owner's machine) and T016 (Schwab read-only —
needs owner's dev-app confirmation). Everything else in Phase 2 is done.
Next: T023 via Antigravity, or begin Phase 4 conversation-layer ticket writing (it can
proceed in parallel — the §3 tool registry it needs is complete).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T025 done (symbol briefing composer)
Built: `analysis/briefing.py` — the deterministic evidence pack behind "should I buy X":
trailing returns (20/60/252 trading days), 60d annualized vol, 252d max drawdown,
distance from 52-week high/low, SMA50/200 trend context (`sma()` added to metrics with
tests), and the owner's current exposure (PositionContext). Degrades gracefully on thin
history (None fields + bars_count, never fake numbers). Registered as tool
`get_symbol_briefing` (registry now 5 tools) + `GET /api/briefing/{symbol}`.
Verified: verify.py PASS — 85 passed, 3 skipped.
Also: owner's venv observed rebuilt on CPython 3.14.7 (I005 nearly closed — needs one
local verify PASS to confirm).
Next: T023 (fundamentals/news — owner's-machine task) or T017 chore. Phase 2 exit then
needs only the Phase 4 narration on top of this briefing.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — IDE config fix (I004)
Fixed: owner's Antigravity showed missing-import errors (Pyrefly) and couldn't bind the
interpreter — no pyrightconfig.json/.vscode existed. Committed pyrightconfig.json (venv
binding, backend extraPaths, alembic versions excluded) and .vscode/settings.json
(defaultInterpreterPath, pytest config). Manual fallback steps in ISSUES I004.
Noted: kubera.sqlite3 exists at repo root — owner has run the migration (T007 nearly done).
Verified: verify.py PASS (unchanged code, config only).
Next: unchanged — T023 via Antigravity, or new "should I buy X" briefing ticket.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T024 done (tool-calling registry)
Built: `api/tools.py` — the spec §3 contract in code. ToolRegistry with @registry.tool
decorator (duplicate names rejected), pydantic argument validation, ToolContext injection
(alpaca/market/db; clear error when missing), error taxonomy (UnknownTool/ToolArgument/
ToolError), and schemas() JSON-schema export consumed directly by LLM function-calling
APIs. Four real tools registered: get_portfolio, get_latest, get_daily_bars,
compare_benchmark. `GET /api/tools` lists them. Adding a Phase-3+ capability is now a
one-decorator registration next to the function it wraps.
Verified: verify.py PASS — 75 passed, 3 skipped.
Next: T023 (fundamentals/news — needs live key checks, best from owner's machine via
Antigravity) or T017 chore; after that Phase 2 needs a "should I buy X" briefing composer
(new ticket to write) to hit the spec §7.2 exit criterion.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T022 done (win/loss breakdown); committed Gemini's fix
Built: `analysis/portfolio.win_loss()` — winners/losers/flat counts, total_gain (>=0) and
total_loss (<=0) with natural signs, net, best/worst position. `/portfolio` now returns a
`win_loss` block ready for the dashboard's green/red chart.
Also: committed Gemini's Windows env fix (ccc5ec4) with attribution — it was left
uncommitted; reminder to all agents: commit before ending a session (AGENTS.md).
Verified: verify.py PASS — 67 passed, 3 skipped (68/68 on Windows per Gemini).
Next: T024 (tool-calling registry — biggest leverage, unblocks Phase 4) or T023
(fundamentals/news). T007 remaining: migrate + sync + open /portfolio once.
Blockers: none.

## 2026-08-11 — Gemini (Antigravity) — Windows subprocess env fix in test_db.py
Fixed: `backend/tests/test_db.py` `test_alembic_migration_matches_models` hardcoded `PATH: /usr/bin:/bin`
when spawning Alembic via `subprocess.run`, overriding `os.environ` completely and breaking Winsock / system DLL loading on Windows (`OSError: [WinError 10106]`). Updated to `{**os.environ, "DATABASE_URL": ...}` so system environment variables (PATH, SystemRoot) are preserved.
Verified: `python scripts/verify.py` passes all tests on Windows (68/68 passed).
Next: T022 (win/loss breakdown) or T024 (tool registry).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T021 done (benchmark comparison)
Built: `analysis/benchmark.py` — strict inner-join date alignment (ValueError <2 overlaps,
message tells the user history accumulates via sync), normalized curves for charting,
per-series metrics (cum return, ann vol, ann Sharpe, max DD; vol/Sharpe None when <3
points), excess return. `data/history.py` — daily equity: last snapshot per day per
account, summed across accounts. `GET /api/benchmark?symbol=SPY&days=90`; DB DI via lazy
engine; 503 with migrate instructions when DB uninitialized; 409 when insufficient overlap.
Verified: verify.py PASS — 65 passed, 3 skipped.
Note: comparison quality grows with snapshot history — owner should run scripts/sync.py
daily (or --loop / Task Scheduler) once T007 is done.
Next: T022 (win/loss breakdown) — small; or T024 (tool registry) — bigger leverage.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T020 done (metrics library, Phase 2 started)
Built: `analysis/metrics.py` — daily_returns, cumulative_return, cagr, volatility, sharpe,
max_drawdown_frac. Conventions locked in the module docstring: values oldest-first and >0,
252 trading days/year, sqrt-annualization, rf/ppy per-period risk-free, drawdown as
positive magnitude, ValueError on any bad input (no silent garbage in a money pipeline).
Verified: verify.py PASS — 56 passed, 3 skipped. All 16 metric tests are hand-computed
known answers, independent of the implementation.
Next: T021 (benchmark comparison vs SPY — uses these metrics + account_snapshots +
market_data bars) or T022 (win/loss breakdown). T021 recommended first.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T015 done — PHASE 1 CODE-COMPLETE
Built: `analysis/portfolio.py` summarize() — totals, per-position returns, weights, sorted
by market value; duck-typed inputs keep analysis decoupled from broker clients. `GET
/portfolio` fetches account + positions live at request time (no cache presented as
current) and returns computed summary + per-position views + asof + source.
Verified: verify.py PASS — 40 passed, 3 skipped (live tests run on owner's machine).
Phase 1 exit criterion met in code; owner sign-off = T007 (quickstart + sync + /portfolio).
Promoted Phase 2 backlog: T020 metrics, T021 benchmark vs SPY, T022 win/loss, T023
fundamentals/news (evaluate owner's FMP/FRED keys), T024 tool registry, T017 chore.
Next: T020 (time-series metrics) — natural start for any agent.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T014 done (snapshot sync job)
Built: `data/sync.py` — sync_once() fetches live account + positions and writes timestamped
snapshot rows; ensure_account() is idempotent per (broker, external_id) — proven by test
(two syncs → one account row, two snapshots). `scripts/sync.py` CLI: one-shot default,
`--loop N` continuous; Windows Task Scheduler can call one-shot mode. AlpacaClient
AccountSnapshot now carries the broker account_number as external_id. README quickstart
gains migrate + sync commands.
Verified: verify.py PASS — 35 passed, 2 skipped.
Next: T015 — `GET /portfolio` (Phase 1 exit criterion). Owner: T007 quickstart + T005 push.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T013 done (database schema v1)
Built: SQLAlchemy 2 models — broker_accounts, account_snapshots, position_snapshots,
transactions (deduped per account by broker fill id); UTCDateTime TypeDecorator that
rejects naive datetimes on write and restores UTC on read (SQLite drops tzinfo);
`data/db.py` engine/session factory; settings gain `database_url` (DATABASE_URL env,
default repo-root SQLite per D007). First alembic migration `bee2b4896cdf` with a
migration-parity test (upgrade head must produce exactly the models' tables).
Gotchas fixed: alembic autogenerate emitted `data.models.UTCDateTime` without importing
it (normalized to `sa.DateTime` — identical DDL); ruff per-file-ignores for generated
migrations (style rules off, F-rules kept — they catch real bugs like that import).
Verified: verify.py PASS — 33 passed, 2 skipped.
Next: T014 (scheduled refresh job writing snapshots) then T015 closes Phase 1.
Owner: T007 quickstart + T005 push still open.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T012 done (market data)
Built: `backend/data/market_data.py` — latest trade, level-1 quote, daily OHLCV bars
(split-adjusted, free IEX feed per D006), every payload carries BOTH `exchange_ts` and
`asof` fetch time. `GET /api/market/{symbol}/latest` and `/bars?days=N` with DI.
Fixed in review: py3.10 `fromisoformat` can't parse Alpaca's variable-precision second
fractions — `parse_rfc3339()` normalizes any width to microseconds, with tests.
Verified: verify.py PASS — 29 passed, 2 skipped (live tests skip in sandbox per I002).
Noticed: owner added the GitHub remote (T005 partial — push + Actions check remain; sandbox
has no GitHub auth so pushes must come from the owner's machine).
Next: T013 (DB schema v1: SQLAlchemy 2 + SQLite + alembic) — last big block before T014/T015
close Phase 1. Owner: T007 quickstart run + T005 push when convenient.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T011 done; owner completed T006
Built: `backend/data/alpaca.py` — thin httpx client (no SDK), `get_account()` +
`get_positions()`, every payload timestamped + sourced, actionable 401 messages, and a hard
code rail: constructing against the live endpoint raises ConfigError until §7.4 exists.
`GET /api/account` with DI (503 + fix instructions when unconfigured). Settings now accept
the owner's `.env` naming (`ALPACA_API_KEY` alias); extra template vars ignored harmlessly.
Verified: verify.py PASS — 20 passed, 1 skipped (live integration test skips in Cowork
sandbox: alpaca.markets not allowlisted, see I002; it will run on the owner's machine).
Owner did T006 (paper keys). Committed on `main`.
Next: T007 is now the highest-value step — running the quickstart on Windows also executes
the live paper-account test for real. Then T012 (market data) or T013 (DB schema).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T010 done (Phase 1 started)
Built: `backend/settings.py` — typed config via pydantic-settings, loads env then repo-root
`.env`, `require_alpaca()` raises ConfigError naming the exact missing vars and pointing at
T006, secrets are SecretStr (leak-proof repr), `alpaca_paper` defaults true per D003.
`/health` now reports `alpaca_configured` and `paper_mode` (state only, never values).
Verified: verify.py PASS — ruff clean, 12/12 tests. Committed on `main`.
Next: T011 (Alpaca paper client) — buildable now; its integration test skips until T006 gives
us real paper keys. Owner tasks T005–T008 still open.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — Phase 0 complete
Built: project-memory working files (TASKS, DECISIONS D001–D008, ISSUES, PROGRESS); backend
skeleton — FastAPI `/health`, first deterministic module `analysis/returns.py`, 7 tests;
ruff + `scripts/verify.py` gate; GitHub Actions CI (verify + gitleaks secret scan);
`.pre-commit-config.yaml`; `.env.example` / `.gitignore` secrets hygiene; README; AGENTS.md
Stack section filled from owner decisions (US equities, paper-first, PWA, free data tiers).
Verified: `verify.py` PASS — ruff clean, 7/7 tests green; live `/health` smoke test returned
timestamped JSON (Linux sandbox, Python 3.10). git initialized on `main`, first commit made.
Also: `/kubera` resume skill saved in Cowork; Mission Control artifact created.
Next: owner actions T005–T008 (GitHub push, Alpaca paper keys, local verify, pre-commit),
then any agent starts T010.
Blockers: none.

## 2026-08-10 — (prior session)
Built: AGENTS.md and PROJECT_SPEC.md — the full contract, architecture, stack rationale,
phased roadmap §7, safety rails §8, and memory-file templates §11.
Next: create the working memory files and Phase 0 scaffolding.
Blockers: none.
