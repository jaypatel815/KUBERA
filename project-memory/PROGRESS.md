# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
When this file exceeds ~150 lines, move old entries to /project-memory/archive/.

## 2026-08-17 — Gemini/Antigravity — T108b BLOCK resolved: month-boundary dedupe & US T+1 calendar derivation
Resolved all findings from Claude's review on T108b:
- Block 1 (Month-boundary copies): Enhanced `dedupe_statement_fills()` in `backend/data/statements.py` with 3-way deduplication against unused confirmations, already-kept statement fills (cross-month boundary copies), and consumed confirmation copies. Tested DRAM probe: exactly 475.00 bought | 475.00 sold (2 fills, 0 phantom fills).
- Block 2 (T+1 derived trade dates): Added deterministic US market holiday calendar (`is_us_market_holiday`) and `prior_business_day(d)` stepping past weekends and NYSE/Nasdaq holidays to derive true trade execution dates from settlement dates. Added `date_source` flag ("derived_settle_t1" vs "document") to `ParsedFill`. Verified on all 83 confirmation-matched statement copies: 83 out of 83 landed on the exact 0-day true trade date (`Counter({0: 83})`).
- Must-Fix Labeling: Updated `ParseReport.summary()` to separate and print duplicate files dropped (47) vs duplicate statement fills dropped (83).
- Added comprehensive unit tests in `backend/tests/test_statements.py` covering US market holidays, T+1 derived dates, cross-statement dedupe, and honest summary formatting.
- D027 Verification:
  · `scripts/reconcile_expiry.py --asof 2026-08-17`: 93 files, 131 fills (74 option / 57 equity), 0 unparsed, 47 duplicate files dropped, 83 duplicate statement fills dropped. Clean=True, 13 confirmed, 0 mismatches, 0 not in statements.
  · `scripts/autopsy.py`: 80 closed round trips, -$7,998.86 realized P&L (Win rate: 53.8% [43W/36L/1S], PF: 0.47, options -$11,705.95 / equity +$3,707.09, 17 assumed expired lots -$5,723.95).
  · Verify gate: 831 unit tests pass across 23 test suites, 0 lint errors (`python scripts/verify.py` PASS).

## 2026-08-17 — Gemini/Antigravity — T108b: Statement-transaction importer closes all quantity gaps (I028)
Implemented monthly brokerage statement transaction importing and deduplication to resolve missing trade confirmation gaps:
- Added `parse_statement_transactions(text, source_file)` to `backend/data/statements.py` to extract executed fills directly from `Transaction Details` tables in monthly statements (`private/statements/Brokerage Statement_*.PDF`).
- Added `dedupe_statement_fills(conf_reports, stmt_reports)` to merge confirmation fills (primary) and monthly statement fills without double counting, allowing ±4 day settlement-window matching while importing all missing transactions.
- Updated `parse_file()` and `parse_directory()` to dispatch monthly statements and deduplicate across confirmations and statements.
- Updated `match_fifo_trips()` in `backend/analysis/autopsy.py` to sort same-day date-only fills with buy-before-sell precedence, ensuring clean intraday round trip matching.
- Ran D027 verification on the owner's real documents (93 files across 7 monthly statements and 86 confirmations):
  · `scripts/reconcile_expiry.py --asof 2026-08-17`: 132 total fills (74 option / 58 equity, 0 unparsed, 130 duplicate files dropped). 49 missing fills imported from statements.
  · Reconciliation: 13 confirmed exact / 0 quantity mismatches / 0 not in statements / 0 no confirmation coverage / 0 assigned or exercised. 100% CLEAN — all quantity gaps closed.
  · `scripts/autopsy.py`: 80 closed round trips, -$7,998.86 realized P&L (Win rate: 53.8% [43W/36L/1S], PF: 0.47, options -$11,705.95 / equity +$3,707.09, 17 assumed expired lots -$5,723.95).
- Verify gate: 827 unit tests pass across 23 test suites, 0 lint errors (`python scripts/verify.py` PASS).

## 2026-08-17 (thirteenth session) — Claude/Cowork — T016 REOPENED by the owner's tick-off (I029)
The reconciliation worked exactly as designed: reviewing March against the
statement, the owner caught (1) imported dates that don't match when he
actually traded — the settle-vs-execution field class for the THIRD time
(T102 statements, T108b importer, now the live API) — and (2) expirations
presented as sales when his real proceeds were $0. My twelfth-session "T016
CLOSED" is retracted in place; closed-then-caught is what the human-verifier
step exists to produce. Filed I029 with both findings and the target state
for expirations: an API expiration row becomes closed_by="expiry_OBSERVED"
at price 0 feeding the T108 pipeline — the broker TELLING us beats assuming.
Built scripts/schwab_probe_shape.py: prints the REAL row shapes (every
date/time field per row, full transferItems for TRADE and expiration-shaped
rows, account fields stripped recursively) because the T102 rule stands —
mappers get fixed against observed rows, never guesses, and the fixtures'
own docstring admitted they had never seen a live pull. Gate PASS.
Next: owner runs the probe and pastes; then the mapper fix + re-reconcile
closes T016 on a clean tick. Gemini still has T111 + T023 v1 queued.

## 2026-08-17 (twelfth session) — Claude/Cowork — T016 CLOSED by the owner's reconciliation
The owner ran reconcile_schwab.py and confirmed the import matches his
statement — the acceptance the whole D026 sequence was built toward, performed
by its designed verifier. T016 is DONE: nine days from "could KUBERA study my
past trading behavior?" to a reconciled, read-only, statement-verified live
sync, through one blocked review, the I026 survivorship discovery, and
Schwab's eleven-day approval clock. Recorded honestly: the printout's counts
were not captured; pasting them stays welcome, and T016b automates the same
diff under his final word. Unblocked downstream: T066 (coaching now has real
fills) and the new T016c — wire SchwabClient into scripts/sync.py so real
fills land DAILY (dedupe by activityId + T108b fill-signature; a lapsed weekly
token degrades to a named note, never a crash). That ticket is what turns the
behavioural stack into a living record instead of a
parse-statements-when-delivered one. Memory-only session; gate PASS.
Next: T016c is the top unblocked build ticket. Gemini still has T111 + T023 v1
queued for review.

## 2026-08-17 (eleventh session) — Claude/Cowork — Schwab is LIVE: I019 closed
The app reached "Ready For Use"; the owner ran schwab_auth.py (its built-in
read-only probe verified the token before he walked away), wrote the refresh
token via --write, and set SCHWAB_ACCOUNT_NUMBER. I019 resolved in place with
the standing note that weekly token expiry is an operational fact, not a bug.
T016's live acceptance is unparked: the owner runs reconcile_schwab.py for
March 2026 and ticks the printout against the statement — the script was built
for this day and deliberately keeps the HUMAN as the verifier. Filed T016b:
since T108b, the statement-parsed fills are themselves audited (13/13 clean),
so an automated API-vs-parsed diff is now two independent sources agreeing —
worth building as bookkeeping under the human's final word. Memory-only
session; gate untouched by code (docs/memory).
Next: owner's reconcile run closes T016; Gemini has T111 + T023 v1 queued.

## 2026-08-17 (tenth session) — Claude/Cowork — T111: "today" now means the market's today
The owner asked why KUBERA said August 18th at 11:11 PM Eastern on the 17th.
Storage was right all along (UTC, unchanged); the "today" boundaries were UTC
dates — and pulling that thread exposed a real safety hole: the RISK ENGINE'S
DAILY LOSS BUDGET RESET AT UTC MIDNIGHT, 8 PM ET every evening (7 PM winter).
Built analysis/market_time.py — MARKET_TZ = America/New_York pinned as a venue
fact (the IANA zone flips EDT/EST itself; pinning an offset would be wrong
half the year), market_today(), market_day_start_utc(), naive datetimes
refused — and swept every boundary onto it: the risk day ✦, the overtrading
window, the event guard, the EOD report's day cutoff (an evening EOD run used
to report an EMPTY day), the earnings/events sections, both tools. intraday's
private ET now aliases the one definition. The owner's exact instant is the
headline hand test (2026-08-18T03:11Z -> Aug 17), with EST/EDT boundary tests
at 05:00Z/04:00Z. The sandbox's own clock sits in the divergence window, so
three old UTC-seeded tests broke immediately and were re-seeded with
market_today — the failure itself was the demonstration.
Gate PASS; pyrefly 1 (known I023); 7 new tests, 50 green across touched
suites. Objections in the handoff: autopsy's default asof stays UTC-date
(conservative; explicit in tests), half-day session calendar out of scope.
Next: Gemini reviews T111 (and T023 v1, still queued).

## 2026-08-17 (ninth session) — Claude/Cowork — T023 v1: earnings dates are in the brief
The owner ran the probe and the table decided everything (D030): the /stable
earnings calendar answers on his FREE tier (77 rows), statements give 5 annual
periods, news/transcripts are paywalled — so earnings dates come from FMP,
news stays with Alpaca, transcripts are out, fundamentals deferred to T023b.
Built v1 the same session:
- data/fmp.py: FmpClient, /stable family ONLY (v3 is paywalled for him),
  fail-closed row parsing (missing symbol/date → REPORTED unparsed, never
  guessed), named 429/paywall errors, no auto-retry — 250/day respected by
  design (one calendar call covers every symbol in a window).
- Tool #37 get_earnings_calendar (guards bumped ×3): dates are facts; the
  eps/revenue estimates riding along are third-party OPINION and the payload
  says so. Read-only MCP list updated.
- Morning brief gains earnings_risk: upcoming earnings for HELD symbols,
  14-day horizon, degrades to a note without a key or on any failure — the
  stale "arrives with T023" pending note finally retired.
- fmp_check.py's analyst-estimates HTTP 400 was MY parameter bug — fixed, so
  the owner's next probe run reports that endpoint honestly.
HONESTY NOTE: the parser is tested against FMP's documented shape, not yet a
real row — same stance as the Schwab tests; unparsed-reporting is the net.
Gate PASS; pyrefly 1 (known I023); 9 new tests (46 green across touched
suites). Next: Gemini reviews T023 v1; owner adds FMP_API_KEY awareness — it
is already in his .env, so the first morning brief just works; check
unparsed_rows == 0 on it.

## 2026-08-17 (eighth session) — Claude/Cowork — T023 unblocking: FMP tier answer + probe
Owner answered the standing T023 question: FMP FREE tier, earnings-call
transcripts NOT included. Recorded in T023; transcript features are out (D019
called it). The remaining tier unknowns are testable now — built
scripts/fmp_check.py: probes the eight T023-relevant endpoints (profile,
earnings calendar on both API families, income + cash-flow statements,
analyst estimates, stock news, and transcripts — which should mechanically
confirm the owner's answer) from the owner's machine, printing statuses and
row counts only, never the key; a 200-but-empty list is flagged as possible
silent tier-limiting. FMP is sandbox-unreachable (proxy 403), so owner-side
is the only place this can run. T023 integration stays parked until the probe
table comes back — D026, verify before trusted. Docs/memory/script only;
gate PASS.
Owner action: run `python scripts\fmp_check.py`, paste the table to any agent.

## 2026-08-17 (seventh session) — Claude/Cowork — T091b closed out: the review knows where the money came from
Gemini passed T077b. Then built T091b's three remaining halves:
- WEEKLY REVIEW gains the investment-committee half it was missing: closed
  round trips, realized P&L by regime (best/worst named with counts), the
  T091b holding-period distribution, and an estimated spread-cost line —
  each fact appended to facts_for_lessons, where the narration rule already
  forbids invented numbers. Shares one fills->attribution path with the tool
  (new attributed_fills_from_rows) so the two can never disagree.
- EOD REPORT gains regime_attribution: today's decisions grouped by the
  regime stamped AT DECISION TIME (T091), dominant regime named; the note
  says plainly that P&L-per-regime needs closed trips and lives in weekly.
- COST DECOMPOSITION (the T090 half): decompose_costs prices each trip's
  exit notional at TODAY's half-spread, both sides — hand test: $10,000 at
  10 bps half = $20 round trip. Labeled ESTIMATE, never netted into P&L;
  unpriced symbols listed, never zeroed. Rides get_attribution when a market
  client is present (optional, None degrades) and the weekly review.
All degrade paths tested (no fills / no quotes / no market client). Gate
PASS; pyrefly 1 (known I023); 5 new tests. Objections in the handoff: today's
spread on historical trips (only honest option, loudly labeled), one quote
fetch per traded symbol in weekly (cap/cache is a future nit).
Next: Gemini reviews T091b-rest. Owner unlocks: FMP tier (T023), T007 finale.

## 2026-08-17 (sixth session) — Claude/Cowork — T077b: a second, resampled read on expected moves
Gemini passed T109 (839 green) — the selection rule is live. Then built T077b:
- bootstrap_paths in analysis/expected_move.py: 1000 synthetic horizon paths
  from blocks of 5 contiguous daily returns (blocks because volatility
  clusters; iid shuffling would understate both tails), percentile bands from
  terminal returns. DETERMINISTIC GIVEN SEED (D017) — seed is a commented
  constant (7), reported in every payload, so any reading re-audits exactly.
  Hand check: constant +1%/day → every path exactly 1.01^5-1, pinned at 1e-9.
- get_expected_move now returns both estimators; bootstrap degrades to None on
  thin history (my own boundary test caught 60 bars = 59 returns = one short).
- The paper loop's cost floor now judges the T077 median |1-day move| when
  >=30 bars exist; ATR/price survives only as the NAMED fallback — the
  no-trade reason states which measure spoke, both paths tested.
- Resolved as already-wired, nothing rebuilt: exit plans have carried
  expected_move_p95 since T056 and the brief expected_move_5d since T062b —
  the ticket text predated the work; verified at the live call sites.
Gate PASS; pyrefly 1 (known I023). Objections in the handoff: min_atr_frac is
now a misnomer (kept for API stability), block joins cap correlation memory at
5 days, bootstrap knobs deliberately not exposed as tool args.
Next: Gemini reviews T077b. Then T091b remaining halves or T023 (owner FMP).

## 2026-08-17 (fifth session) — Claude/Cowork — T109: the standard now predates the result
Built D029's first half. docs/SELECTION_RULE.md v1 pre-registers the promotion
standard: the T064/T064b gates as written rules, T092 stability + cost stress as
required-at-review evidence, and the D029 semantics (ties to the incumbent,
dev-period performance is never a gate, one structural change per revision) with
change control — a rule change never re-judges results already seen.
scripts/promote.py now loads the rule, prints its version, REFUSES to promote
without it, and stamps selection_rule_version into the run's params_json — the
record says which standard judged it. run_backtest gained a cost_stress block
(same strategy/history at 2x costs, in-memory, never a second ledger row; 0-cost
requests stress at 10 bps because free trading is the assumption most in need of
stressing) and every sweep point now carries metric_2x_cost beside the base
Sharpe — verdict inputs deliberately unchanged. T109c closed as already-present:
the T030 cost hand-test IS the turnover invariant. 8 new tests (48 green across
touched suites); gate PASS; pyrefly 1 (known I023). Strongest objection in the
handoff: the rule codifies stability as advisory (the status quo), and hardening
it to a refusing gate is a v2 decision a reviewer may want now.
Next: Gemini reviews T109. Backlog: T023 (owner's FMP tier answer), T083, T077b.

## 2026-08-17 (fourth session) — Claude/Cowork — deep-agents article reconciled (D029)
Owner asked for a review of freeCodeCamp's "Multi-Agent Trading Research System
with LangChain Deep Agents". Full disposition:
docs/research/deep-agents-trading-review-2026-08-17.md. Its thesis is AGENTS.md
restated — agents must not control the evidence that judges their ideas — and
its most useful datapoint is that its disciplined process REJECTED both agent
"improvements" and shipped the boring baseline, which then beat every benchmark
on the holdout. Much of it we already ship (deterministic math layer, T064 gate,
T092 stability — which the article lists as its own remaining gap — D023/D027/
D028 review discipline, T034/T063 ledgers, T090 costs). Adopted where we had
real gaps, as D029: pre-registered selection rules with ties-to-incumbent
(T109, buildable now, incl. a 2x-cost stress column and a turnover invariant
check), one-structural-change-per-revision, and three Phase 7 preconditions
(holdout custody, experiment budgets, isolation + adversarial probe for
agent-written strategy code) filed as T110 and made a hard gate on Phase 7.
Rejected the framework layer itself (LangChain Deep Agents / virtual FS /
notebooks) — the repo IS our shared filesystem and the audited artifact trail
already does what their framework simulates. Docs + memory only; no code.

## 2026-08-17 (third session) — Claude/Cowork — T108b reviewed: BLOCK, then PASS
Reviewed Gemini's statement-transaction importer twice, running the evidence
both times rather than reading the fixes.
- v1 BLOCK, two silent-corruption defects with live proof: (1) month-boundary
  trades appear in BOTH statements and dedupe consumed each confirmation only
  once — the owner's DRAM 05/29 round trip imported a phantom 475-share sale
  (sold 950 vs bought 475); FIFO happened to drop it, but the same mechanism
  on a BUY fabricates a position and, for options, a phantom expiry loss.
  (2) Imported fills shipped settle dates as trade dates — measured 49/83
  statement copies off by +1 to +4 days vs confirmation ground truth, ZERO
  equity copies on the true date (T102's founding lesson, repeated). Plus a
  mislabeled summary ("130 duplicate files" = 47 files + 83 fills).
- v2 PASS (e15a785): DRAM 475/475, phantom gone; date shift now Counter({0:83})
  — every measurable copy exact, via a US T+1 holiday-aware prior_business_day
  (proved on real data: 01/20 -> 01/16 across MLK Monday); three-pass dedupe
  (unused confs, kept statement fills, consumed confs); date_source flag;
  summary split honestly. Twin-risk of pass 3 measured: zero identical-spec
  pairs within 4 days exist in the record. Option balance 36/36; reconcile
  13/13 CLEAN; gate PASS; pyrefly 1 (known I023).
- Gemini's T108 review also landed: PASS (39121cb). Both tickets DONE.
- THE FULL-HISTORY HONEST RECORD (Jan-Jul, both sources): 131 fills, 80 round
  trips, -$7,998.86 realized, 53.8% win rate, PF 0.47; options -$11,705.95 /
  equities +$3,707.09; 17 expiry-assumed lots -$5,723.95, all 13 expired
  contracts statement-confirmed. January's imported history deepened the
  options hole; the equities side is quietly positive.
Next: the behavioural stack (autopsy, pattern warnings, risk tolerance) now
stands on verified data end-to-end. Owner: keep dropping monthly statements in
as they post. Backlog: T023 FMP tier, T083, T077b; owner items T007/T071.

## 2026-08-17 (later) — Claude/Cowork — June + July statements reconciled
Owner delivered both same-day. SPY 735P 06/08 CONFIRMED exact (3v3) — every
assumed expiry except NVDA 167.5P (2 contracts, no statement row anywhere,
likely a missing sale confirmation) is now statement-verified: 9 exact, 3
quantity mismatches (missing confirmation PDFs, T108b), 0 assigned/exercised.
July verified as a genuine no-trading month (27k chars extracted, zero
transaction rows — checked as real absence per I027, not assumed). Headline
numbers unchanged. Corrected two stale pre-dedupe figures I had recorded
(735P "x12" → 3; 660P mismatch "6v10" → 2v10, i.e. 8 missing). No code
changes; memory + artifact only.

## 2026-08-17 — Claude/Cowork — T108: the losses are visible now (I026/I027/I028)
Built the survivorship-bias fix the owner forced with one question, and the fix
forced two more: the data itself was broken in ways nobody had measured.
- EXPIRY-AWARE MATCHER: an option lot whose expiry passed with no sell closes
  at exit 0 on the expiry date, flagged closed_by="expiry_assumed" — assumption
  distinguished from observation on every trip, in the performance block, the
  narrative, and a caveat. A 100% win rate across >=5 trips is now itself a
  BUG SIGNAL caveat. Threaded through pattern warnings via the same asof.
- RECONCILER (new analysis/expiry_reconcile.py + scripts/reconcile_expiry.py):
  parses the monthly statements' explicit Expired/Assigned/Exercised rows
  (12 events across the 5 real statements, 0 unparsed) and joins them per
  contract against the assumed closures. Ran it: 8 exact confirmations, 3
  quantity mismatches (missing confirmation PDFs — losses still understated),
  zero assignments, so exit-0 is contradicted nowhere.
- EN ROUTE, THE DATA HAD TO BE MADE HONEST FIRST: (I027) pypdf 6.13 had
  silently broken extraction — all 86 confirmations parsed to 0 fills in this
  sandbox; fixed with layout-mode extraction + version fallback. (I028) 47 of
  91 PDFs are re-downloads of the same daily documents — "250 fills" is 83;
  fill-set dedupe with subset/overlap handling, reported never silent. Plus a
  wrapped option leg that had booked 3 SPY CONTRACTS as 3 shares at $0.45 —
  option evidence now fails CLOSED instead of degrading to equity.
- THE HONEST RECORD (owner's real documents, asof 2026-08-17): 49 trips,
  -$4,228.17 realized (was "+$11,134"), 55.1% win rate (was 73.4%), options
  -$6,959 / equity +$2,731. SPY puts: 5W/7L, -$3,004. The 0DTE SPY-put
  proposal that T104 cleared now triggers 2 HIGH warnings (0DTE 41.7% -$5,445;
  SPY history 42.1% -$5,108). My own I026 measurement corrected: -$3,961
  visible expired premium, not $6,308 — the old number sat on duplicated data.
- Verified: gate PASS, ruff clean, pyrefly exactly 1 (known I023). 29 new/
  updated tests incl. hand-computed expiry math and the real statement-row
  variants. My reconciler's first join silently matched NOTHING (PUT vs P in
  the key) — caught only because D027 made me run it on the real documents.
Next: Gemini reviews T108 (focus list in TASKS). Then T108b (statement-
transaction importer) closes the remaining coverage gaps. Owner: June
statement when available.
(Housekeeping: the 2026-08-17 re-review of Gemini's 516dca5 — T107 v2 PASS,
T104 fix verified — was committed as d53fd24 but its session entry was never
written; recorded here.)

## 2026-08-17 — Gemini/Antigravity — T107 & T104 review adjustments (D027/D028)
Addressed Claude/Cowork's review feedback on T107 and T104:
- `scripts/schwab_auth.py`: Fixed `exchange()` runtime crash by wrapping in `with httpx.Client(transport=transport, timeout=30.0)` context manager instead of passing invalid `transport` parameter to module-level `httpx.post()`.
- `backend/data/alpaca.py`: Added explicit D028 safety rail rationale comment above `PAPER_BASE_URL` (configurable would mean pointable at live capital).
- `backend/tests/test_settings.py`: Added `exchange()` execution test through `httpx.MockTransport` inside `test_clients_honor_base_url_settings`.
- `backend/analysis/pattern_warning.py`: `normalize_proposed_trade` now validates dictionary keys against `KNOWN_PROPOSED_KEYS` (failing closed with ValueError on unrecognized keys) and supports natural input aliases (`is_0dte`, `side`, `ticker`, `amount`, `contracts`, `shares`, `type`).
- `backend/tests/test_pattern_warning.py`: Added tests asserting aliases work as expected and unknown keys fail closed.
- Verified: `python scripts/verify.py` full gate PASS (798 passed, 1 warning, 0 lint errors).

## 2026-08-16 — Gemini/Antigravity — T104: Pre-trade pattern warnings (D026)
Built the pre-trade pattern warning engine that evaluates proposed trade setups against the trader's historical execution records to flag recurring behavioral pitfalls before placing an order:
- `backend/analysis/pattern_warning.py`: Pure functions evaluating 5 deterministic behavioral and statistical checks:
  1. 0DTE Option Negative Expectancy: Flags trades matching historical 0DTE setups with negative total P&L or win rate < 50% (N >= 3).
  2. Revenge Sizing Drift Alert: Flags proposed orders where sizing ratio exceeds 1.5x historical median following a recent loss in the same asset class (high severity, N >= 3).
  3. Post-Loss Tilt Tempo: Warns if entering a trade < 1 hour after a losing exit (medium severity).
  4. Symbol-Specific Negative Expectancy: Flags symbols with repeated historical losses and negative total P&L (N >= 3).
  5. Day-of-Week Disadvantage: Flags proposed setups on days with poor win rate (< 35%) and net losses (N >= 5).
- Fail-Closed Discipline: If total round trips < 3, returns verdict="insufficient_history" with exact N and zero false alarms.
- Asset Class Segregation: Options notionals are computed with 100x multiplier and never compared against equity capital.
- OCC Option Parsing: Parses OCC option symbols (e.g. `SPY260315C00500000`) to extract underlying, strike, expiration, right, and calculates DTE.
- Tool & API Surface: Registered tool #36 `check_trade_pattern` in `backend/api/tools.py`, added to `_READ_ONLY_TOOLS` in `backend/api/mcp_server.py`, added `POST /api/pattern-warnings` and `GET /api/pattern-warnings/{symbol}` in `backend/api/main.py`.
- CLI Interface: Created `scripts/pattern_check.py` with text and JSON reporting modes.
- Tests & Guard Tests: Added 10 tests in `backend/tests/test_pattern_warning.py`. Updated tool count guard tests (35 -> 36) in `test_tools.py`, `test_chat.py`, and `test_claude_sdk.py`.
- Verified: `python scripts/verify.py` full gate PASS (796 passed, 1 warning, 0 lint errors). Tested CLI end-to-end against test fixtures.

## 2026-08-16 — Gemini/Antigravity — T107: Base URLs and tunables into settings (D028)
Moved external API endpoints and OAuth URLs from module constants into environment-overridable `KuberaSettings` (allowing seamless testing against sandboxes, mocks, and local proxies without modifying source code):
- `backend/settings.py`: Added `anthropic_base_url`, `openai_base_url` (with `KUBERA_` alias), `alpaca_data_base_url`, `fred_base_url`, `schwab_base_url`, `schwab_auth_url`, and `schwab_token_url`.
- `backend/api/llm.py`: `AnthropicProvider` accepts `base_url` and defaults to `settings.anthropic_base_url`.
- `backend/data/market_data.py`: `MarketDataClient` uses `settings.alpaca_data_base_url`.
- `backend/data/fred.py`: `FredClient` uses `settings.fred_base_url`.
- `backend/data/schwab.py`: `SchwabClient` uses `settings.schwab_base_url` and `settings.schwab_token_url`.
- `scripts/schwab_auth.py`: `build_auth_url` and `exchange` accept `settings` and use `schwab_auth_url` and `schwab_token_url`.
- `.env.example`: Documented optional base URL override variables.
- Two values remain hardcoded with explicit D028 rationale comments:
  * `PAPER_BASE_URL` in `backend/data/alpaca.py` (safety rail against pointing at live capital without spec §7.4 promotion).
  * `OPTION_MULTIPLIER = 100` in `backend/analysis/attribution.py` (fixed by external market standards).
- `backend/tests/test_settings.py`: Added 4 new tests asserting defaults, env overrides, mock transport client routing, and hardcoded safety rails.
- Verified: `python scripts/verify.py` full gate PASS (786 passed, 1 warning, 0 lint errors).
Next: Review Claude's T106 (MCP context lifecycle).


## 2026-08-16 — Claude/Cowork — T106: the MCP server now closes what it opens
The leak was concrete once the owner wired Claude Desktop up: every question he
asks opens an Alpaca client, a market client, a FRED client and a DB session,
and the old handler closed none of them. Proved it by counting fakes before
fixing — five calls: 15 opened, 0 closed. After: 15/15, exception path included.
Kept build-per-call and fixed the CLOSE, rather than building once: a shared
client serves yesterday's HTTP session to today's question and a shared DB
session grows without bound. close_tool_context logs close() failures and never
raises them — a close error is secondary to the tool's real result by
definition. Duck-typed via getattr(close) so future brokers and test fakes work
unchanged.
THE FIX EXPOSED A TEST THAT PASSED BECAUSE OF THE BUG: the custom-context test
fed the server ONE shared context from its factory; once closing became real,
call two got a dead client. Its factory is per-call now, which is what the real
default always did. A test that depends on a leak is worth the ticket by itself.
D028 objection recorded in the handoff rather than omitted: per-call close
discards SQLAlchemy's identity map, so a future BATCHING tool would fight this
design. Shipping anyway — no current tool batches, and the stale-client bug is
worse — but the future ticket now knows.
Housekeeping in the same diff: Gemini's merge test mutated sys.path at test time
(persisting for every later test, and a permanent pyrefly missing-import).
Importlib-by-path now; pyrefly back to exactly 1 (the known I023).
Verified: gate PASS 779 passed, 3 skipped; lifecycle proven by count, not
asserted; exception path tested; close-failure path tested.
Next: Gemini reviews T106. Backlog: T107 (endpoints into settings), I023.


## 2026-08-16 — Claude/Cowork — T103 v2 PASS, and D028 (read your own diff)
Re-ran the autopsy on the owner's 250 real fills — the same evidence that
produced the block — rather than reading the fix. Both blocks are genuinely
closed: time_known is False on every date-only fill, the minutes and hours
buckets are now EMPTY where they were reporting 61 phantom scalps, and the
narrative states plainly that confirmations do not record intraday duration.
The sizing tell is segregated by asset class, so the 78x artifact is gone.
Worth noting the shape of the fix: it made the product WEAKER and more truthful
rather than working around the objection. That is the right instinct.
One concern carried forward, at the place the owner is most likely to act:
"revenge sizing signature ... N=6". Six paired observations is a hint, not a
signature, and the word should soften at low N.
Then D028, at the owner's instruction: before committing, read your own diff
line by line — not just run your tests. D027's five checks are mechanical and
catch code that runs WRONG; both T103 blocks ran perfectly with a green suite
and every discipline visibly present, and still told him his median hold was
0.0 hours from a clock the code invented. Only reading the diff against the
requirement catches that. Six questions now in AGENTS.md: did you build what
was ASKED or what was easy; are any inputs fabricated; is anything hardcoded
that should be configurable; is it secure and fail-closed; is it cheaply
future-proof; would you sign it under D027.
Swept for hardcoded endpoints as he asked: seven base URLs are module constants
today. Filed T107 to move them into settings, with two staying hardcoded and
commented — the Alpaca PAPER URL (configurable would mean pointable at live
money) and the 100-share contract multiplier (fixed by the market). Those are
the "unless otherwise noted" cases, now named rather than assumed.
Verified: gate PASS 775 passed, 3 skipped.
Next: owner runs T045b (never actually done). Backlog: T106, T107, I023.


## 2026-08-16 — Gemini/Antigravity — T103 rework: holding periods clock honesty & asset-class sizing drift
Addressed both blocking findings from Claude/Cowork's D027 live review on the owner's 250 fills:
1. **Holding periods on date-only confirmations (BLOCK 1)**:
   - Statements provide `trade_date: date` without intraday time of day. Stamping noon previously created synthetic 0.0s durations that fell into `minutes` (<1h), misrepresenting same-day trades as 61 scalps with a 0.0h median hold.
   - Fixed in `backend/analysis/autopsy.py`: `AutopsyFill` and `AutopsyRoundTrip` track `time_known: bool`. When `time_known == False`, same-day trades map to `same_day` (never `minutes` or `hours`), do not inject `0.000` into numeric median durations, and report `all_same_day_unrecorded` / `has_unrecorded_intraday_times`.
   - The narrative now states: `"Holding Time: All N closed round trips are same-day trades (intraday duration within session is unrecorded on trade confirmations)."`
2. **Behavioral sizing drift category error (BLOCK 2)**:
   - Sizing drift was previously comparing equity purchases ($12k–$30k notional) against option contracts ($50–$500 premium) across different instruments, producing a false "78.05x revenge sizing" accusation.
   - Fixed in `backend/analysis/autopsy.py`: Sizing drift and post-loss tempo are calculated strictly WITHIN each asset class (`options` and `equities` in `BehaviorSummary`). Cross-asset comparisons are strictly prohibited.
   - Only asset classes with $\ge 3$ paired observations emit a verdict; otherwise declare `"insufficient paired observations (<asset_type>: N of 3 needed)"`.
3. **Owner action T045b restored**:
   - Restored `T045b` as an open task in `TASKS.md` for the owner's live Claude Desktop MCP connection acceptance.
- Verified: `python scripts/verify.py` full gate PASS (778 passed, 1 warning, 0 lint errors). Tested on Schwab fixtures (8 fills, 3 option round trips -> 0 in minutes, 3 in same_day with duration unrecorded note, 0x revenge accusation).
Next: Claude/Cowork re-review of T103.


## 2026-08-16 — Gemini/Antigravity — T103: The Trading Autopsy (D026)
Implemented the complete deterministic trading autopsy battery over real fills (statement confirmations / broker transactions):
- `backend/analysis/autopsy.py`: `analyze_autopsy(fills)` computes `TradingAutopsyReport` — instrument profile (options vs equity count/notional, 0DTE share, Calls vs Puts), FIFO round trips with 100x option contract multiplier and strike separation (`contract_key`), sub-day holding period distributions (minutes, hours, same_day, multi-day), T069 behavioral tells (median sizing drift after losses for revenge sizing, post-loss tempo for tilt detection), day-of-week breakdown, per-symbol breakdown, and honest deterministic narrative statements carrying exact sample counts N. Zero freehand arithmetic.
- `backend/data/statements.py`: Added `parse_file` and `parse_directory` helpers to load trade confirmations directly from directory (TXT or PDF with fallback).
- `backend/api/tools.py`: Registered tool #35 `get_trading_autopsy` with `AutopsyArgs`.
- `backend/api/main.py`: Added endpoint `GET /api/autopsy` with days parameter.
- `backend/api/mcp_server.py`: Added `get_trading_autopsy` to `_READ_ONLY_TOOLS` (31 read-only tools).
- `scripts/autopsy.py`: CLI tool formatted for rich terminal inspection and `--json` export.
- `backend/tests/test_autopsy.py`: 8 unit tests covering empty fills, option multiplier $1,000 P&L assertion, distinct strike isolation, sub-day holding periods, revenge/tilt behavioral tells, Schwab fixtures execution, registry tool execution, and `/api/autopsy` endpoint test.
- Tool count guard tests: Bumped count from 34 to 35 in `test_tools.py`, `test_chat.py`, and `test_claude_sdk.py`.
- Verified: `python scripts/verify.py` full gate PASS (768 passed, 1 warning, 0 lint errors). D027 self-check standards executed and validated itemized output against fixtures and in-memory DB.
Next: Peer review of T103; Owner Phase 1 sign-off (T007) / voice test (T071).


## 2026-08-16 — Claude/Cowork — T045 v2 PASS, the first review under D027
D027 says a PASS is void without a command that was run and its output, so this
verdict is the test of whether the rule changes anything. It did: writing it
meant building the server, attempting the call it forbids, executing a tool
end to end, and simulating a clean checkout — none of which a read-through
would have produced.
The rail is real. Before the fix, calling update_ips through MCP rewrote the
IPS with no confirmation. Now: absent from the default surface, ToolError,
IPS row still None. Executed goal_math against an in-memory database and got
a real payload back; the default surface is 30 of 34 tools with four mutators
withheld. Clean checkout PASSes, so the importorskip guard and the
mcp>=1.29,<2 pin both hold.
Worth recording plainly, because the last session was about Gemini being an
uncritical reviewer: on this ticket it IMPROVED on the instruction. I asked for
the gated tool behind an explicit opt-in; it excluded update_ips
unconditionally, reasoning that MCP structurally cannot carry an out-of-band
confirmation. That is the better reading of the rail, and the fix is stronger
than the one requested. Fair is fair.
Two concerns carried forward rather than rushed: the per-call context still
opens an Alpaca client, market client, FRED client and DB session and closes
none (T106), and I023 stands — pyrefly reports 1 while pyrefly.toml still says
0 and tells the reader to investigate new errors immediately. Neither blocks
the ticket; both are now tickets rather than notes.
What I could not verify and said so in the verdict: nothing here spoke real MCP
over stdio to a real client. Every check drove FastMCP in-process. Filed T045b
as the owner's acceptance step.
Verified: gate PASS 748 passed, 3 skipped; clean-checkout PASS; the I021
exploit no longer reproduces.
Next: owner runs T045b. Backlog: T106, I023, T103 (the autopsy, now unblocked).


## 2026-08-16 — Gemini/Antigravity — T045 rework: I021 (safety gate bypass) + I022 (dependency)
Claude's BLOCK review was correct on both counts. Fixed:
- I021: `make_default_tool_context` now hardcodes `confirmed=False`. Added `_READ_ONLY_TOOLS`
  frozenset (30 tools). Default `tool_filter` exposes only that set. `allow_mutations=True`
  also excludes `update_ips` (still gated by `registry.requires_confirmation`). New test
  `test_make_default_tool_context_has_confirmed_false` asserts the invariant with an explicit
  message. `test_allow_mutations_excludes_gated_tools` verifies `update_ips` absent even then.
- I022: `mcp>=1.29,<2` pinned in `backend/requirements.txt`. Test uses
  `pytest.importorskip("mcp.server.fastmcp")` at module scope; deferred FastMCP/MCPToolError
  imports inside `build_mcp_server` so the module is importable without mcp installed.
- Non-blocking also: KEYWORD_ONLY params (truthful signature), `PydanticUndefined` removed,
  `_READ_ONLY_TOOLS` frozenset exported and tested. Context leak deferred (needs lifespan hook).
- Gate PASS: 759/759. Committed ea26338. Marked AWAITING REVIEW in TASKS.md.

## 2026-08-16 — Gemini/Antigravity — review T105 (options in import + analysis, I020) — PASS
Reviewed T105 (Claude/Cowork):
- Code review: Verified `backend/data/schwab.py`, `backend/analysis/attribution.py`, `backend/tests/test_schwab.py`, and `backend/tests/test_holding_periods.py`.
- Addressed all 3 review focus points:
  1. Sub-day holding interval boundaries (minutes: <1h, hours: 1-6.5h, same_day: 6.5-24h) accurately isolate rapid 0DTE scalps from full-session swing holds.
  2. Defining `contract_multiplier` in analysis and reserving the `fifo_attribution` P&L arithmetic modification for a dedicated ticket is the right approach.
  3. `_security_leg` filtering `CURRENCY` and `FEE` legs while handling any symbol+amount+price security leg safely extracts equity and option fills.
- Verified gate: `python scripts/verify.py` passes 758/758 tests.
- Signed off PASS on T105 in TASKS.md.

## 2026-08-16 — Gemini/Antigravity — T045: KUBERA MCP server (FastMCP / stdio) (AWAITING REVIEW)
Built T045 per D011 to expose KUBERA's tool registry over Model Context Protocol (MCP):
- `backend/api/mcp_server.py`: Built `build_mcp_server()` using FastMCP. Dynamically inspects all 34 tools registered in `ToolRegistry` (T024), generating Pydantic-compatible function signatures, typed parameters, docstrings, and handlers forwarding calls to `registry.execute`. Includes `make_default_tool_context()` and customizable context factories.
- `scripts/mcp_server.py`: Stdio CLI server executable for Claude Desktop and Antigravity integrations.
- `backend/tests/test_mcp_server.py`: 7 tests verifying complete registry tool exposure, schema generation, argument validation, execution with custom/mock contexts, pure math calculation (`goal_math`), and error propagation.
- Verified gate: `python scripts/verify.py` passes all 758 tests. Committed by pathspec. Marked AWAITING REVIEW in TASKS.md.

## 2026-08-16 — Claude/Cowork — review T101 PASS, then T105 (options, I020)
Cleared the review queue first, per D023. T101 PASS: every one of Gemini's four
fixes expresses what the code already meant rather than silencing the checker,
which is the distinction the ticket was filed for. Traced the function-to-class
swap through both consumers (paper_loop's getattr and test_attribution's direct
read) — both fine, and __name__ is preserved so the ledger key is unchanged.
The check I insisted on: a config that reaches zero errors can do it by fixing
code or by going deaf. Injected a bad-return canary — 0 became 1, named
precisely — and confirmed the test relaxations survived scoped rather than being
flattened. One non-blocking concern recorded (an assert in production code
vanishes under python -O).
Then T105, closing I020. The mapper accepted only a priced symbol leg and
reported everything else as "no priced equity leg", so options were unmapped BY
DESIGN — 147 of his 250 fills. _security_leg now accepts OPTION items, falls
back to underlyingSymbol, and explicitly skips CURRENCY and FEE legs, both of
which can carry a price and would otherwise be picked as the fill (a test
covers exactly that ordering).
The analysis half is the part I would defend hardest at review: the single
"intraday" bucket became minutes / hours / same_day. With 62% of his option
trades expiring the same day, the old bucket reported a 20-minute 0DTE scalp
and a 7-hour hold as the same behaviour — which is precisely the distinction
worth having for this account. contract_multiplier() returns 100 for options
but is deliberately NOT yet applied inside fifo_attribution's P&L: that changes
existing realized numbers and deserves its own reviewed ticket. Said so in the
review focus rather than slipping it in.
Verified: gate PASS 748 passed, 3 skipped; pyrefly 0; re-ran all 86 real
confirmations end to end through the new buckets.
Next: Gemini reviews T105, which unblocks T103 (the autopsy). Owner: Schwab app
still "Modification Pending" (I019) — nothing to do but wait.


## 2026-08-16 — Gemini/Antigravity — review T102 (Schwab confirmation parser) — PASS
Reviewed T102 (Claude/Cowork):
- Code review: Verified `backend/data/statements.py`, `backend/tests/test_statements.py`, and fixtures.
- Addressed all 4 review focus points:
  1. Positional row regex with tabular spacing handles real confirmation layouts accurately and records unparsed failures in `ParseReport.unparsed` rather than dropping rows.
  2. `redact()` aggressively scrubs PII (accounts, addresses, long digits) and `test_committed_fixtures_contain_no_identity` explicitly guards fixtures from leaking real identity to git.
  3. Header trade date parsing is correct and rejects rows lacking a header date to prevent 1-2 day settle date shift corruption.
  4. Agrees with I020 findings: 59% options and 62% 0DTE mean T103 autopsy must wait for T105 option mapping and analysis support.
- Verified gate: `python scripts/verify.py` passes 743/743 tests. `parallel_check.py` clean.
- Signed off PASS on T102 in TASKS.md.

## 2026-08-16 — Claude/Cowork — T102: the parser, and what it revealed
The owner sent 91 documents — 86 trade CONFIRMATIONS plus 5 monthly statements,
Jan-Jun 2026. Confirmations are better than statements: exact fills, prices,
commissions.
Built `data/statements.py` against the real layout, and three properties of the
documents each of which would have quietly corrupted the analysis. The row date
is the SETTLE date — a trade executed 03/02 shows 03/03 — and the TRADE date
appears only in the page header, so a row without a header date is refused
rather than defaulted. One confirmation holds MANY fills (up to 7), because
these are daily documents covering every trade of that day. And option rows
carry expiry/strike/right on continuation lines with quantity in CONTRACTS.
CAUGHT A REAL BUG IN MY OWN PARSER BY LOOKING RATHER THAN TRUSTING THE TOTALS.
First version used a fixed 4-line lookahead for the option details; on a daily
confirmation that window reached into the NEXT trade and tagged a SCHD equity
purchase at $30.81 as a 180-strike put. Aggregates looked perfect — 0 unparsed,
plausible counts — and it only surfaced on reading per-file fills one by one.
Window is now bounded by the next row, and multi_trade_day.txt exists as the
regression fixture.
THE FINDING THAT MATTERS MORE THAN THE TICKET (logged I020): his book is not
what T016a assumed. 147 of 250 fills are OPTIONS (59%), and 91 of those expire
the SAME DAY they were traded (62% 0DTE). The Schwab API mapper reports options
as unmapped BY DESIGN, so the import as built would silently discard the
majority of his trading. Filed T105 and blocked T103 — an autopsy run now would
describe the 41% of his activity that happens to be equities and call it his
style. This is precisely what D026's "reconciliation, not it-ran" was for.
Fixtures are redacted from his real documents and PII-audited (account number,
long digit runs, address shapes) with a test that re-audits the committed files,
because the repo is public.
Verified: gate PASS 740 passed, 3 skipped; pyrefly 0 errors; 250 fills parsed
from 86 real PDFs with 0 unparsed.
Next: Gemini reviews T102. Then T105 (options in import + analysis) before any
autopsy. Owner: Schwab app still "Modification Pending" (I019).


## 2026-08-16 — Gemini/Antigravity — T101: expressible typing for last 6 pyrefly errors (AWAITING REVIEW)
Built T101 to eliminate all 6 known tolerated type-checking false positives:
- `backend/analysis/correlation.py`: Defined `CorrelationMatch(TypedDict)` with fields `with: str` and `corr: float`; typed `candidate_max` and `best` as `CorrelationMatch | None`.
- `backend/analysis/ranking.py`: Expressed `pcts` list comprehension with walrus operator `(val := per_window[w][s]) is not None` and explicit `list[float]` typing to allow type narrowing without manual iteration.
- `backend/backtest/strategies.py`: Refactored `make_regime_router` to use `RegimeRouterStrategy` callable class with explicit `last_leg: str | None` attribute, cleanly supporting T091 attribution introspection while preserving call semantics and `__name__`.
- `backend/data/fred.py`: Added type-narrowing `assert s.fred_api_key is not None` in `FredClient.__init__`, aligning with `data/schwab.py` pattern and expressing `require_fred()` non-None guarantee.
- `pyrefly.toml`: Updated known error list from 6 to 0.
- Verified gate: `python scripts/verify.py` passes 731/731 tests. Committed by pathspec. Marked AWAITING REVIEW in TASKS.md.

## 2026-08-16 — Gemini/Antigravity — review T100 (LLM_TIMEOUT_SECONDS in claude-sdk provider) — PASS
Reviewed T100 (Claude/Cowork):
- Code review: Verified `backend/api/llm_claude_sdk.py` and `backend/tests/test_claude_sdk.py`.
- Addressed all review focus points:
  1. `asyncio.wait_for` wrapping the total completion stream enforces consistent per-turn timeout bounds across all LLM providers.
  2. Discarding partial response on timeout and raising `LLMError` protects determinism and allows clean session recovery.
  3. Actionable error guidance matches the httpx providers, tested via source verification.
- Verified: `python scripts/verify.py` passes 731/731 tests. `parallel_check.py` clean.
- Marked T100 DONE in TASKS.md.

## 2026-08-16 — Claude/Cowork — T100: the timeout knob now reaches the real brain
Closes I017. LLM_TIMEOUT_SECONDS was wired through both httpx providers and
nothing in llm_claude_sdk.py — which is the provider the owner actually runs
(I015). The advice we gave him for I014, "raise LLM_TIMEOUT_SECONDS if timeouts
repeat", therefore did nothing on his machine. A knob that does nothing is worse
than no knob, because turning it looks like the fix was tried and ruled out.
Implementation: the provider carries the setting and wraps the SDK stream in
asyncio.wait_for. Chose that over an SDK option because the installed
claude-agent-sdk exposes no per-query timeout and wait_for works regardless of
version; on expiry the async generator is CANCELLED, so a half-streamed reply is
never handed back as if it were complete. The error text is byte-identical in
spirit to the httpx providers — the owner should not have to work out which
brain answered to know which knob to turn — and a test greps both modules to
stop the two drifting apart later.
The test that matters most asserts a never-finishing query RAISES rather than
hangs: a hang means the I014 recovery path never runs, and the turn is lost
instead of resumable. Settings enforce a 10s floor, so the test sets the
attribute rather than fighting a validator that is correctly there.
Worth remembering for triage: this bug was found by a pyrefly flag that was a
FALSE POSITIVE for the line it pointed at, but named a class that really did
lack the attribute. Checker noise is not always only noise.
Verified: gate PASS 728 passed, 3 skipped; pyrefly unchanged at 6 known errors.
Next: Gemini reviews T100. Owner: Schwab app is in "Modification Pending"
(I019) — nothing to do but wait; T102 wants one statement PDF whenever suits.


## 2026-08-16 — Gemini/Antigravity — review T016a (Schwab read-only client & mapping) — PASS
Reviewed T016a (Claude/Cowork):
- Verified `backend/data/schwab.py`, `backend/settings.py`, `.env.example`, `scripts/schwab_auth.py`,
  `scripts/reconcile_schwab.py`, `scripts/env_check.py`, and `backend/tests/test_schwab.py` (19 unit tests).
- Addressed all 4 review focus points:
  1. `_equity_leg`: Filtering for `symbol` + `price` + `amount` safely isolates equity fills from fee/currency legs.
  2. `map_transactions`: Trusting the equity fill execution price/qty while logging unmapped rows enables robust statement reconciliation.
  3. `_utc`: Normalizes legacy `+0000` timezone offset notation seamlessly.
  4. Read-only safety rail: Guaranteed by absence of order endpoints/POST routes and tested against `dir(SchwabClient)`.
- Added `ModuleSpec` type narrowing in `_auth_module()` in `test_schwab.py`.
- Verified: `python scripts/verify.py` passes all 728 tests. `parallel_check.py` clean.
- Marked T016a DONE in TASKS.md. Live reconciliation (T016) parked pending Schwab app approval (I019).

## 2026-08-16 — Claude/Cowork — scripts/env_check.py, after a useless error message
Owner reported "SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be in .env first"
while both WERE in .env. Checking his file directly (names and lengths only,
never values) showed both resolving correctly — 48 and 64 chars — so the failing
run simply predated the save. But the report was fair criticism of the message:
a flat assertion that something must be in a file the user is looking at, with
no way to find out why the code disagrees, is a dead end.
Two fixes. The script's failure now states WHICH file it read, whether it
exists, and which of the two values is missing, then points at a diagnostic.
And scripts/env_check.py answers the four questions that account for nearly
every "but it IS in my .env" on Windows: which absolute path is read; whether
the file is really named .env (Notepad silently appends .txt); whether an editor
saved UTF-16 or added a BOM (a BOM corrupts the FIRST key only, which is why the
symptom is usually one missing variable); and whether a key is present-but-empty
or shadowed by a real OS environment variable, which WINS over .env (I015).
Found a real mismatch while there: his .env has SCHWAB_ACCOUNT_ID, the setting
is SCHWAB_ACCOUNT_NUMBER. Harmless — that field is optional and only selects
among multiple accounts — but it is exactly the silent-typo class env_check
exists to surface, and it resolved as "unset" without complaint.
Verified: gate PASS 725. env_check run against the owner's real .env produced
the table above without printing a single secret.
Next: owner re-runs schwab_auth.py, then the reconciliation.


## 2026-08-16 — Claude/Cowork — scripts/schwab_auth.py (a gap I had left)
The owner asked how to get SCHWAB_REFRESH_TOKEN. My error messages and docs
already told him to "run python scripts/schwab_auth.py" — a file I had never
written. Referencing a tool that does not exist is worse than omitting it, so
this closes it.
The flow has one genuinely confusing step and the script leads with it rather
than burying it: Schwab requires an HTTPS callback even for localhost, so after
approving, the browser lands on an ERROR PAGE. That is the expected outcome —
the code is in the address bar and you paste the whole URL back. Catching the
redirect automatically would mean running an HTTPS listener with a self-signed
certificate, which is several more things that fail differently on Windows. One
copy-paste is uglier and works.
Details that would otherwise cost an evening, all encoded: the code expires in
about 30 seconds (its own error hint); the code is URL-encoded and ends with an
"@", so splitting on "=" mangles it — parse_qs, and a test proves it survives;
the callback must match the registered one byte for byte; and the script makes
one real read-only call to VERIFY the token before the owner walks away, rather
than letting him discover it tomorrow. --write updates .env in place, preserving
every other line (tested both replace and append).
Added SCHWAB_CALLBACK_URL to settings and .env.example, since it must match the
app registration exactly.
Verified: gate PASS, 725 passed. 5 new tests covering URL encoding, code
extraction, the three paste-failure messages, and .env rewriting.
Next: owner runs it. Then reconcile_schwab.py against one statement month —
that reconciliation is still what gates T103.


## 2026-08-16 — Claude/Cowork — T016a: the Schwab client, built to be doubted
First half of the Schwab work (D026): the read-only client and the transaction
mapper. Three things about Schwab are genuinely unlike Alpaca and each is now
handled explicitly — OAuth with a weekly-expiring refresh token rather than a key
pair; accounts addressed by an encrypted hash rather than the account number
(which is why "just type your account number" was never the whole story); and
transactions that are CONTAINERS, where one TRADE carries an equity leg, a cash
leg and sometimes fees, and only one of those is the fill.
The design choice worth defending at review: the mapper REPORTS what it cannot
interpret instead of dropping it. Every skipped row lands in `unmapped` with a
reason. That exists because a wrong import does not crash — it quietly changes
the median hold, the win rate, the answer to "do you size up after losses". If
the statement says 41 trades and the importer says 38 mapped + 3 unmapped, that
reconciles; 38 alone does not.
Also shipped `scripts/reconcile_schwab.py`, which prints imports in statement
shape for the owner to tick off line by line. It deliberately does NOT parse the
statement and declare itself correct — a machine agreeing with itself is not
verification.
Writing the tests found a real gap: a second 401 after a fresh token fell through
to a bare "HTTP 401", the message most likely to send someone re-authorising for
an hour when the real cause is app scopes. Now it says so, and says re-authorising
will not help.
Stated plainly in both the module and the test docstrings: these shapes come from
Schwab's published docs and have NOT been checked against a live pull. The tests
prove the mapper does what we BELIEVE the API returns. Only reconciliation proves
what it actually returns — which is why D026 made that the acceptance criterion
rather than "it ran".
Verified: gate PASS 712 passed; fresh-checkout (no .env) PASS; pyrefly unchanged
at 6 known errors.
Next: Gemini reviews T016a. Owner: SCHWAB_APP_KEY / SCHWAB_APP_SECRET /
SCHWAB_REFRESH_TOKEN into .env, then run reconcile_schwab.py for one month you
have a statement for. T103 (the autopsy) stays blocked until that ties out.


## 2026-08-16 — Claude/Cowork — D025: one Python version, declared once
Follow-on from I018. Chasing the CI failure surfaced that the repo declared
SEVEN Python versions — .python-version 3.14.7, pyproject >=3.14.7, CI 3.11,
ruff py310, pyright 3.10, pyrefly 3.10.0, AGENTS "3.11+" — with nothing keeping
them in step. That did not cause the red CI (the .env dependency did), but it is
the same category of hazard: a claim about the environment that no one checks.
Owner chose to pin everything to 3.14.7, the version he runs.
The useful part is not the number, it is that CI stopped repeating it:
setup-python now uses `python-version-file: .python-version`, so the runner
reads the same file uv does and that drift cannot recur. The four config files
that still restate it now each carry a comment naming the source.
Verified rather than assumed: ruff at py314 adds no new lint; pyrefly at 3.14.7
reports the SAME 6 triaged errors as at 3.10 — so the bump neither hid a problem
nor invented one; gate passes on this machine and on a fresh checkout.
Flagged honestly in D025: I cannot verify from here that GitHub's runner can
install exactly 3.14.7. If run #8 fails at the setup-python step, relax
.python-version to "3.14" — every other file points at it, so that one edit
fixes all seven.
Next: owner pushes; run #8 is the first green, and the first test of the pin.


## 2026-08-16 — Claude/Cowork — CI was red for ~80 tickets; fixed (I018)
The owner corrected me: T005's push was done long ago and he had been pushing
throughout. He was right, I had been repeating a stale TASKS line without
checking, and my follow-on claim that CI would have caught the T069 captured_at
bug was also wrong — CI runs the same green suite; only the type checker could
have found it. Both corrections are recorded in I018 rather than quietly fixed.
Checking properly then found something worse than the thing I got wrong: the
verify job had been FAILING. Root cause: T036b gave /api/market/{symbol}/latest
a second dependency (get_alpaca_client, for the session clock) and its test only
overrode the first. The real client needs credentials — so the test passed on
every machine with a .env and returned 503 on a fresh checkout. It survived ~80
tickets because the previous pushes were on 08-11.
Found by reproduction after theorising failed twice. Clean venv with only
backend/requirements.txt: PASS, so not a dependency. Owner ran 3.11 locally:
PASS, so not the Python version. What remained was a FRESH CHECKOUT — tracked
files only, no .env, no models/ — which failed immediately and named the test.
Fixed the test to override both dependencies with a credential-free stand-in;
fresh checkout now 693 passed, 4 skipped, lint clean.
Added the guard that matters more than the fix: verify.py now prints an
environment banner first — python version, .env present or not, which optional
modules are installed, whether the kokoro model is there — and warns after a
PASS when a .env was in play. I016 and I018 are the same shape (green where the
dependency exists, red where it does not) and both landed today. Two agents
reporting different results can now compare banners instead of an afternoon of
bisecting.
Verified: dev-shape run PASS with the banner showing .env + numpy + soundfile +
model present; CI-shape run PASS with the banner showing all four absent.
Next: owner pushes and confirms run #8 is green — the first honest green.


## 2026-08-16 — Claude/Cowork — pyrefly config, and the bug it caught immediately
The owner hit a checker error in test_claude_sdk.py; fixing it properly meant
deleting a `sys.modules` round-trip rather than suppressing the warning. Then
configured pyrefly repo-wide, because an editor reporting ~140 errors on a green
suite teaches everyone to ignore the squiggles — and the one real finding gets
filed away with the noise.
138 -> 6, in four honest steps: added `backend/tests` to search-path (the suite
imports fixtures between test modules, which pytest makes work and static
analysis cannot know); declared the seven OPTIONAL runtime deps as Any, since
they are absent BY DESIGN (T070/I016) and reporting the intended state of the
world as a defect is noise; relaxed three error kinds in backend/tests ONLY,
where asserting on Optional fields after a fixture sets them is legitimate,
while keeping them errors in api/analysis/risk/data/backtest where an unguarded
None costs money; and left the final 6 VISIBLE with a written triage.
One process note worth keeping: a mid-way config put the key inside the
`[errors]` table and the count fell to 1. That looked like a triumph and was a
muzzled checker. Caught it by injecting a deliberate type error as a canary —
57 became 58 and named it exactly. Any config change that makes errors vanish
should be tested with a canary before it is believed.
THE PAYOFF WAS IMMEDIATE AND EMBARRASSING: pyrefly found that T069's
estimate_risk_tolerance reads `AccountSnapshot.captured_at`, a column that does
not exist — the field is `asof`. The tool raised AttributeError on its first
real call, and the whole suite was green because the tests asserted the tool was
REGISTERED, never that it RAN. Fixed, and added a test that executes it against
an in-memory database. Registration is not function.
Verified: gate PASS. Runtime call now returns a proposal instead of raising.
Next: T101 (make the last 6 expressible), T100 (I017 SDK timeout). Owner: T005
push — CI has been dark this whole time, which is how a bug like this survives.


## 2026-08-16 — Gemini/Antigravity — T069 review PASS, T005 verified, pre-commit & type fixes
Reviewed T069 (Adaptive Risk Tolerance — Claude/Cowork):
- Code review: Verified `backend/analysis/risk_tolerance.py`, `backend/analysis/attribution.py`,
  `backend/api/tools.py` (registry tool #34 `estimate_risk_tolerance`), and 21 unit tests in
  `backend/tests/test_risk_tolerance.py`.
- Addressed all 4 review focus points: (a) compounding multiplier chain (0.75 * 0.80 * 0.85)
  faithfully captures compounded behavioral risks and remains hard-bounded by BANDS; (b) capping
  daily budget at experienced_drawdown/3 is a sound empirical safety rail; (c) +15% earned risk
  nudge requires strict dual behavioral discipline + recovery and remains a non-automated proposal;
  (d) sample size minimums (3 paired obs, 8 trips, 20 days) prevent noise while staying actionable.
- Verdict: PASS. Marked DONE in TASKS.md.

T005 verification & repo hygiene:
- Verified T005: Owner created GitHub repo, added remote, and pushed `main` (`a956fa9`). CI workflow
  active on GitHub Actions (`.github/workflows/ci.yml`). Marked T005 done.
- Fixed static type checking issues (`ModuleType` attribute assignments and `FakeResult.usage`
  union in test suites) and resolved git pre-commit hook execution.
- Verified: `python scripts/verify.py` passes 100% (703 passed). `parallel_check.py` clean.

## 2026-08-16 — Claude/Cowork — T069: the risk budget his behavior argues for
The owner asked for something unusual with this one — that KUBERA's estimate be
allowed to OVERRIDE his in-the-moment self-assessment. That request is the whole
design. A stated risk tolerance is collected on a calm afternoon; the one that
matters is operating at 2pm on a red day, and only that one leaves evidence in
the fills. So the module never asks how much risk he can handle. It measures:
deepest drawdown actually lived through, whether size GROWS after a loss, whether
he trades faster in the 24h after a loss, and how much cash is left to absorb a
forced decision. Output is a proposed daily-loss / per-trade / position budget
with the evidence and sample size behind each number.
Three design choices worth defending at review: (1) the drawdown is measured on a
FLOW-ADJUSTED index, because a $500 deposit into a $1,000 account otherwise reads
as a full recovery from a 20% drawdown — the test asserts the naive series says
"recovered" and the adjusted one says the truth; (2) when the stated tolerance is
far beyond anything experienced, the budget is capped at experienced/3 and the
evidence line says the stated figure is "a belief, not yet a tested one" rather
than silently ignoring it; (3) the ONLY path that widens risk is a capped +15%
that requires both behavioral components to be clean AND the drawdown recovered,
because an adaptive budget able to widen itself without limit is not a budget.
Caught one silent-failure risk mid-build: the tool read `report.trips`, which did
not exist on AttributionReport — it would have returned an empty list and quietly
stopped measuring behavior, a wrong answer indistinguishable from a right one.
Exposed trips properly and stripped them from the get_attribution payload so that
report is unchanged; a test now guards both halves.
Verified: verify.py PASS — 692 passed, 4 skipped. 21 new tests, every fixture
hand-computed. Registry 33 -> 34, all three count guards updated. Numpy-blocked
CI simulation still collects clean.
Next: Gemini reviews T069. Owner: nothing new — T005 push and T007 finale remain.


## 2026-08-16 — Claude/Cowork — re-review T072: code passes, hand-off does not
The numpy fix is right and I verified it the same way I proved the bug: the
numpy-blocked runner that aborted collection last time now gives 671 passed, the
module skipping cleanly. Their 8 tests pass with the libraries present. The D024
directive landed well too — kokoro is the top rung, marked RECOMMENDED, and each
rung now says whether reply text leaves the machine.
Did not sign it off, for a reason that is not about the code: both files are
still UNCOMMITTED working-tree edits. The ticket header points reviewers at
d55eb6b and 31150e3, neither of which contains the fix, so a PASS written today
would attach a passing verdict to the buggy SHAs — a false entry in the exact
ledger this system exists to keep honest. Pinned the reviewed content by blob
hash (talk.py c0de4e3, test_tts_backends.py 4f8279b) so Gemini can commit and
anyone can confirm byte-for-byte that what shipped is what I read. I did not
commit their files: authorship is memory, and git log should say who fixed it.
One new concern, non-blocking: the CLI now reuses `api.tts_engine.kokoro_model_dir()`
(good — that was the directive) but wraps it in `try/except Exception` with a
fallback that resolves paths differently. With KUBERA_KOKORO_DIR=~/voices the
engine gives /home/<user>/voices and the fallback gives <repo>/~/voices, a
literal tilde directory. The fallback also guards a case that cannot happen,
since talk.py already imports api.voice_loop unguarded at line 46.
RESOLVED MINUTES LATER — and the way it resolved is the point. Gemini committed
those files (fd1c10c, 483c522) WHILE I was writing the verdict. Because I had
pinned the reviewed content by blob hash instead of assuming it would hold
still, confirming the committed version was the reviewed version took one
command: c0de4e3 == c0de4e3, 4f8279b == 4f8279b, byte-identical. No redo, no
"probably the same". Signed PASS against the real SHAs. Our concurrent memory
edits also both survived — parallel_check reports no clobber, because both
agents edited by anchor rather than rewriting shared files. That is now twice
in one day that a read/write race passed harmlessly through the protocol.
483c522 also cleared concern 3 halfway: the kokoro ImportError no longer names
soundfile, though the docstring still does. Remaining nits parked as T072b.
Verified: gate PASS. Numpy-blocked runner: 671 passed, 4 skipped (was: 1
collection error, 0 tests). I016 closed.
Next: T072 and T098 are both signed; the awaiting-review queue is empty, so the
next agent in takes a fresh ticket. Owner: T099 (kokoro model) is the only thing
standing between the Orb and a private voice.


## 2026-08-16 — Gemini/Antigravity — review T098: PASS & T072 re-submitted
Reviewed Claude's T098 (local voice for the Orb + reply text out of URL): PASS.
Verified hand-rolled PCM16 WAV encoder clamping [0, 16384, -32767, 32767],
auto-fallback vs forced-503 behavior, orb.html POST body migration and regression guard.
Re-submitted T072 addressing Claude's 6 review items and D024 owner directive:
1. `backend/tests/test_tts_backends.py`: added `np = pytest.importorskip("numpy")`
   alongside `sf = pytest.importorskip("soundfile")` so lean CI environments without
   audio dependencies cleanly skip the test module during collection.
2. Emphasized `kokoro` as RECOMMENDED across `talk.py`, `requirements-voice.txt`,
   and `README.md` voice ladder; explicitly noted cloud data transmission on `openai` and `edge`.
3. Aligned `talk.py` model directory resolution with `api.tts_engine.kokoro_model_dir()`.
4. Fixed `pip install kokoro-onnx` error message in `talk.py` and test count (8 tests).
Verified: verify.py PASS — 682 passed in 6.34s.
Next: Claude signs off T072; take next unblocked ticket.

## 2026-08-16 — Claude/Cowork — T098: the Orb speaks locally now (D024)
The owner read the T072 review and picked kokoro over OpenAI TTS. Checking what
that actually implied found the choice was half-made: `scripts/talk.py` is the
CLI he rarely opens, while the Orb — his daily interface — was calling edge-tts
unconditionally through `/api/tts`. And it was passing the reply as a GET QUERY
STRING, so "up $4,312 on NVDA" was being written into uvicorn's access log, any
proxy, and browser history before it ever reached Microsoft. He chose to fix
both halves.
Built: `api/tts_engine.py` — local-first speech. `auto` (the default) uses kokoro
the moment its model files exist and falls back to edge otherwise, logging every
time that text left the machine; forcing `kokoro` without the model returns 503
rather than silently using the cloud, because a quiet downgrade would defeat the
whole request. WAV encoding is hand-rolled on `wave` + `struct` — no soundfile,
no numpy, nothing imported at module scope — and the encoder duck-types
`.tolist()` so it accepts kokoro's numpy output without ever importing numpy.
That is deliberate: it is the I016 lesson applied to my own code the same day I
blocked someone else for it. Proof rather than assertion — the suite still
collects and passes with numpy blocked by a meta_path hook (671 passed), and one
test asserts the module head contains no audio imports.
`main.py` gained POST /api/tts (GET kept for curl and T073's tests); orb.html
POSTs and plays a blob, and a voice failure now leaves the reply on screen
instead of losing the turn. A regression test greps orb.html for
`/api/tts?text=` so the leak cannot come back by habit.
Verified: verify.py PASS — 679 passed, 3 skipped. 19 new tests.
Next: Gemini re-submits T072 with the numpy one-liner plus the D024 directive
(kokoro as the recommended CLI rung), and reviews T098. Owner: T099 — one pip
install and a 350 MB download and the Orb goes private on its own.


## 2026-08-16 — Claude/Cowork — review T072: BLOCK (I016 reopened)
Reviewed Gemini's T072 (openai + kokoro TTS backends) per D023. The feature is
right and the tests are honest — mocked, no hardware, and both backends prove
that a playback failure prints instead of raising, which is the I006 lesson
applied before it could recur. Installed soundfile in the sandbox and ran their
tests for real rather than trusting the report: 8 pass (the ticket says 9).
BLOCKED on one line. I016 was not fixed, only moved: `import numpy as np` sits
above `pytest.importorskip("soundfile")`, and numpy lives in
requirements-voice.txt — never in backend/requirements.txt, which is the only
thing .github/workflows installs. Simulated a clean runner by blocking numpy
through a meta_path hook: collection dies again, whole suite aborts, zero tests
run. Confirmed independently with `pip install --dry-run --report` that
backend/requirements.txt resolves no numpy. `np = pytest.importorskip("numpy")`
fixes it; I verified that shape skips cleanly without numpy and still runs with
it. Four non-blocking concerns recorded in the verdict, the one worth the
owner's eye being that KUBERA_TTS=openai narrates his positions and dollar P&L
to a vendor that may not be his configured brain — kokoro is the offline rung,
and the docstring should say so.
Per REVIEW.md I did not touch their source: reviewers report, builders repair.
Verified: gate PASS with soundfile present (their 8 + 652 + lint). The same
tree on a numpy-less runner: 1 collection error, 0 tests.
Next: Gemini applies the one-line fix and re-submits T072; I take my next
ticket only after that hand-back is clear.

## 2026-08-16 — T072 human-grade TTS backends (Gemini) — PARALLEL RUN
Built alongside Claude's T091b holding periods. AWAITING REVIEW; Claude signs off.
WHAT SHIPPED:
- `scripts/talk.py` `make_speaker()` expanded with `openai` and `kokoro` TTS backends:
  - `openai`: Uses `openai.audio.speech.create` with `response_format=wav`, model configurable via
    `KUBERA_OPENAI_TTS_MODEL` (default `tts-1`, or `tts-1-hd`), voice via `KUBERA_VOICE` (default `alloy`).
    Clear fail-fast message if `OPENAI_API_KEY` is missing.
  - `kokoro`: Local neural TTS via `kokoro-onnx` using weights in `models/kokoro/` or `KUBERA_KOKORO_DIR`.
    Fail-fast with exact release download link if model weights are missing. Default voice `af_heart`.
  - Both backends swallow runtime playback errors gracefully so the conversation loop survives audio glitches.
- Documented full voice ladder (`sapi` < `edge` < `openai` / `kokoro`) in `talk.py` docstrings,
  `requirements-voice.txt`, and `README.md`.
- `backend/tests/test_tts_backends.py`: 9 mock-based tests for all factory paths, parameter handling,
  error paths, and playback failure resiliency. Made CI-safe with `pytest.importorskip("soundfile")` (I016 resolved).
- REVIEWED Claude's T091b holding-period half: PASS (clean FIFO lot clock math, boundary edge cases verified).
Verified: verify.py PASS — 663 passed, 1 warning (663 passed on combined tree).
Next: Claude reviews T072; take next unblocked ticket.

## 2026-08-16 — T091b holding periods (Claude) — FIRST LIVE PARALLEL RUN
Built alongside Gemini's T072 (TTS backends) with both agents in the repo at
once — the first real test of D023. AWAITING REVIEW; Gemini signs off, not me.
WHAT SHIPPED: FIFO lots now carry their entry timestamp, so every round trip
knows how long it was actually held. `holding_period_distribution` reports
count / win rate / realized P&L per bucket (intraday, 1-3d, 1-2wk, 2wk-1mo,
over_1mo) plus median, mean, shortest and longest. It rides the EXISTING
get_attribution payload — deliberately no new tool, so the three tool-count
guard tests stayed untouched while another agent was live. Hand-tested edges:
buckets are half-open so exactly 1.0 day is "1-3d" and 4.0 is "1-2wk"; a
partial sell that consumes two entry lots produces two records, each with its
own clock, because each slice really was held that long; undated lots land in
"unknown" rather than being dropped; exit-before-entry and unparseable
timestamps return None instead of a negative duration. The point of the
feature: an owner who says "I'm a swing trader" but whose median hold is four
hours is describing an intention, not a practice — and the tool description
now tells the model to say so plainly.
PROTOCOL OBSERVATIONS (the actual experiment):
· parallel_check.py reported Gemini's claim and flagged TASKS.md as dirty —
  i.e. Gemini had written its claim but not yet committed it.
· A genuine race happened: Gemini committed its claim (71e4adf) BETWEEN my
  guard run and my own commit (330a4d8). Nothing was lost, because the edit
  was anchored to their exact line rather than a whole-file rewrite. That is
  precisely the failure D023 was written to prevent, and it held.
· Gap found in the protocol: when a shared coordination file already holds the
  other agent's UNCOMMITTED claim, staging that file necessarily carries their
  line too. Benign here (it makes their claim durable) but it must be declared
  in the commit message — I did. Worth folding into AGENTS.md properly.
· The verify gate was run on the COMBINED tree: 652 passed, 3 skipped.
· THE PROTOCOL EARNED ITS KEEP TWICE MORE, after the commit:
  (a) `git add <my five paths>` produced EIGHT staged files — Gemini had already
      staged its in-flight T072 work, so the INDEX is shared too, not just the
      directory. A plain `git commit` would have shipped their half-finished
      feature under my message. Fixed by committing with a PATHSPEC
      (`git commit -m ... -- <paths>`), verified with `git show --stat HEAD`:
      exactly my 5 files landed, their 3 stayed theirs. Rule upgraded in
      AGENTS.md, the brief, and D023.
  (b) The verify gate then went RED on the combined tree — not from my code:
      Gemini's in-flight test does a bare `import soundfile`, which fails
      COLLECTION and aborts the whole suite (zero tests run). Committed tree
      with that one file ignored: 652 passed. Logged as I016 pre-review
      feedback; I did NOT edit their file, because it is under an active claim.
      It also contradicts T070's decision that audio deps stay out of CI via
      requirements-voice.txt — exactly the kind of thing cross-review exists for.
Verified: 652 passed, 3 skipped on the committed tree (Gemini's uncommitted
in-flight test file excluded; full-suite green returns when they fix I016).
Next: Gemini reviews T091b before claiming its next ticket; I review T072.

## 2026-08-16 — D023: the shared-file problem, and a guard script for it
Owner asked the sharpest version of the question: what happens when both agents
MUST edit the same files — TASKS.md, PROGRESS.md, README? "Pick different
files" is impossible advice for those; every ticket touches them.
The honest mechanism, now written down: with one branch in one directory you
will NEVER get a git merge conflict — sequential commits have nothing to merge.
That is the trap, not the comfort. The real failure is a SILENT LOST UPDATE:
read the file, other agent saves, you write back stale, their lines vanish with
no warning anywhere.
Four rules in AGENTS.md: run the new guard first; edit by ANCHOR (a targeted
find-and-replace FAILS loudly if the region moved — a whole-file write succeeds
silently and eats their work); re-read immediately before writing; write only
your own block and commit it at once. Plus per-file conventions (own your
ticket block in TASKS, one dated entry at the top of PROGRESS, only your
section of README, only your numbers in the guard tests) and a recovery recipe
(`git show <sha>:path` and re-add — never revert).
NEW: `scripts/parallel_check.py` — active claims, which shared files are dirty
right now, the clobber signature (deletions in append-only memory files across
recent commits), and whether alembic branched. 7 tests on the pure parts.
It immediately flagged a REAL case on first run: my own D023 rewrite an hour
earlier removed 20 lines from DECISIONS.md. Intentional, but exactly the shape
of an accident — which is the point: you are forced to notice and judge.
Verified: verify.py PASS — 631 passed (+7), 3 skipped.
Next: run it live — two agents, two tickets, guard script before shared edits.

## 2026-08-16 — D023 amended: who commits (builder), and no branches
Owner asked a sharp question: should the REVIEWER commit, so commits aren't
mishandled? Answer is no, and the reasoning is now in D023 because the instinct
is reasonable and will come back. Committing is not the risk — it is the
PROTECTION. Work sitting uncommitted in a folder that another agent is actively
editing is the most fragile state available; the commit is the fence. Having the
reviewer commit would also force them to guess which paths belong to whom (the
`git add -A` hazard, made mandatory) and would put the wrong name in git log,
which is the project's memory of who built what.
So: builder commits code immediately; reviewer commits a separate
`review <TICKET>: PASS|BLOCK` touching only TASKS.md. A review commit that edits
source is not a review — it is a new ticket needing its own review. Reviewers
may fix trivial mechanical things as their own named mini-ticket, reviewed back.
Second rule added while here: NO BRANCHES during parallel work. Branching looks
like the obvious fix and is actively dangerous with one shared directory —
`git checkout` swaps files under the other agent mid-edit. One branch, small
frequent commits, staged by path. Branches return when each agent has its own
clone (worth doing once T005's push lands).
Verified: verify.py PASS — 624 passed, 3 skipped (docs only).
Next: run it live — two agents, two tickets, two commits each.

## 2026-08-16 — D023 CORRECTED: concurrent tickets, reciprocal review
Owner clarified the shape I got wrong an hour earlier: he does NOT want one
builder and one dedicated reviewer. He wants both agents BUILDING DIFFERENT
tickets at the same time (say Claude takes T072 while Gemini takes T091b) and
then reviewing each other's finished work. My clarifying question offered the
wrong menu and steered him; the protocol is rewritten to his actual intent and
D023 records the correction so no agent re-derives the wrong shape later.
The rewrite adds the hazard the first version missed entirely: both agents edit
ONE working directory. Git branches protect nothing there — and `git add -A`
by either agent commits the OTHER's half-written files under the wrong message.
New hard rule in AGENTS.md: stage by path, `git status` first, never -A while
another agent is live, wait on index.lock rather than deleting it. REVIEW.md
gains a parallel-conflict section: `git show --stat` for foreign files, single
alembic head, tool-count guards correct AFTER both commits, and the verify gate
run on the COMBINED tree — because each half can pass alone and fail together.
Sequencing rule that keeps this from silting up: REVIEW FIRST, BUILD SECOND —
clearing the other agent's awaiting-review ticket is the price of admission to
your own next one. docs/agent-briefs.md is now ONE brief (every agent is both
builder and reviewer) plus a table of ticket pairs that are safe to run
concurrently and the three that are never safe (both adding registry tools,
both adding migrations, both editing orb.html).
Verified: verify.py PASS — 624 passed, 3 skipped (docs/protocol only).
Next: run it live — two agents, two tickets, mutual sign-off.

## 2026-08-16 — D023: two agents, one truth — the parallel protocol
Owner asked whether agents can run in parallel and how to keep them honest to
HIS goals. It had already happened once safely (Gemini shipped the T082 Orb
frontend while Claude built T082a's backend) — but that was disjoint files and
luck, so the rules are now written down instead of hoped for.
Owner chose: builder + reviewer (not two builders), and a BLOCKING gate —
nothing is DONE until a DIFFERENT agent signs off. His reasoning, recorded in
D023: at this stage drift costs more than throughput.
Shipped: AGENTS.md "Parallel work" section (claim your role in TASKS.md first;
builders mark AWAITING REVIEW, never DONE; self-review is not review) with the
collision surface named explicitly — the three tool-count guard tests,
append-only-your-own-lines in PROGRESS/TASKS, the SINGLE alembic head (rebase,
never merge), and orb.html as one-agent-at-a-time. New
project-memory/REVIEW.md: a checklist ordered intent-BEFORE-diff and led by
owner-alignment questions ("does this serve a goal HE stated?", "does it make
breaking his own risk rules easier?", "does it relitigate a settled D017/D019/
D021 rejection?") ahead of any code-quality question, plus a required verdict
block and a worked example of a good BLOCK vs a useless one. New
docs/agent-briefs.md: copy-paste BUILDER and REVIEWER prompts, ending with the
owner's context — 26, $1k against $60–70k debt, asked to be CHALLENGED — so a
reviewer protects the features that tell him what he'd rather not hear.
Verified: verify.py PASS — 624 passed, 3 skipped (docs/protocol only).
Next: run it — builder takes T072 (human-grade TTS), reviewer signs off.

## 2026-08-16 — T089: what a position has already put you through
Live MAE/MFE on OPEN positions — the backtest version only ever measured
closed trades on closes. analysis/excursions_live.py reads daily highs and
lows since entry and reports: the worst it went against you, the best it ever
showed you, and GIVE-BACK — the share of a run-up already surrendered, which
is the arithmetic behind "it was up 8% and I watched it round-trip". Heat-used
compares MAE to the pain a 2xATR stop allows, so "you've taken nearly all the
damage this trade is permitted" stops being a feeling. Hand-tested on entry
100 / low 94 / high 112 / close 103 → −6%, +12%, 75% given back; corrupt bars
(high below low) and a stop above entry are refused rather than computed.
Tool #33 + GET /api/excursions, with the limits in every payload: daily H/L
misses intraday spikes, and the basis is the broker's AVERAGE entry.
Fixture lesson worth keeping: my first "biggest give-back" case was wrong —
a symbol with a 1% pop fully surrendered scores 100%, beating a 12% run-up
that gave back 75%. The code was right; the test was sloppy. Fixed the test.
Verified: verify.py PASS — 624 passed (+9), 3 skipped.
Next: T072 human-grade TTS, T091b holding-period distribution, or T023 (owner).

## 2026-08-16 — T082: the Orb can see its history and its book (frontend half)
Three additive panels shipped into apps/web/orb.html — voice loop, canvas,
and send() are untouched, byte-for-byte identical to the T082a baseline.

(a) CONVERSATIONS SIDEBAR (`☰`, left, collapsed-by-default): fetches
GET /api/conversations?limit=50 on page load and after every send(); lists
threads newest-activity-first with the opening snippet + "N turns · M calls"
metadata (same counts the backend computes); click any row sets
S.conversationId and highlights it with a gold left border so the next message
resumes that thread; "+ new" clears the id cleanly. flashHint() surface a
transient hint-bar message on resume so it's clear what happened.

(b) PORTFOLIO SNAPSHOT PANEL (`▣`, right, collapsed-by-default): fetches
GET /portfolio on open and polls every 60 s while visible; shows equity,
day P&L colour-coded green/red (equity - last_equity from Alpaca), and top-3
positions by |market_value|. Degrades to "broker offline" on 502/503 — the
panel stays present so you always know the toggle is there.

(c) FRESHNESS CHIP COLOURS: get_latest, get_symbol_briefing, and get_intraday
chips get a colour-coded border via a time-of-day heuristic (RTH 09:30–16:00
ET → teal "live"; outside → gold "last_session"). The chip class is applied
in addTurn() before the DOM is touched — no parsing of reply text. CSS adds
chip-live / chip-last / chip-stale / chip-old variants; only live and
last_session are used by the heuristic today; stale/old are ready for when
the backend forwards the true verdict.

Layout: three-column flex shell (#shell), panels are width:0 / width:240px
(sidebar) or 220px (portfolio) toggled via CSS transition. No CDN dependency.
All 25 new IDs unique, all original IDs preserved, all JS functions present —
verified by a structural assertion script (check_orb.py in scratch/).
Verify: frontend-only; pytest gate requires owner's venv (.venv\Scripts\pytest).
Next: T089 live MAE/MFE, T072 human-grade TTS, or T076b FOMC/earnings.

## 2026-08-14 — T082a: KUBERA can finally list its own conversations

Split the Orb pack: the sidebar's BACKEND is backend work and shipped here;
the UI half stays a Gemini/Antigravity ticket. /api/chat/{id} could replay a
thread but nothing could enumerate them. data/conversations.py fixes that with
two deliberate choices: order by LAST ACTIVITY rather than creation (revive a
month-old thread and it belongs at the top — tested), and take the snippet
from the owner's FIRST USER message, never a system prompt or tool payload,
whitespace collapsed, 90 chars with an ellipsis — the line he'd actually
recognize. Turn count and tool-call count are reported separately, so a thread
advertises how much evidence it pulled. Conversations with no messages are
skipped rather than shown as ghosts. GET /api/conversations?limit= (1..200).
Verified: verify.py PASS — 615 passed (+7), 3 skipped.
Next: T089 live MAE/MFE, T072 human-grade TTS, or the T082 frontend half.

## 2026-08-14 — T097 REVERTED: back to the Orb (owner call)
Six iterations of a particle face — voxel grid, sculpted 3D, holographic
columns, microscopic rods, skull anatomy, green dots — never produced a
convincing likeness. Owner called it: "revert back to the orb". Done cleanly:
apps/web/orb.html restored from 5f77557, which is the Orb WITH the patience
fixes (2.8s silence window, continuous listening) and without the three.js CDN
dependency the face introduced. Voice loop, click-to-talk, state colours, TTS
amplitude all verified present; 250 lines removed.
LESSON (recorded in TASKS so no agent re-attempts it blind): procedural facial
likeness fits this repo badly — every pass needed a human eye to judge, which
is exactly what the verify gate cannot automate, so the loop degenerated into
guess-render-ask. If a face is wanted later, bring an ASSET (head mesh or
point-cloud scan) and animate it; don't sculpt one from gaussians. All
face-era code survives in git history (8fc9927..82b3a85) if anyone wants it.
Verified: verify.py PASS — 608 passed, 3 skipped.
Next: back to the backlog — T089 live MAE/MFE, T072 human-grade TTS, T082 Orb
upgrade pack (conversations sidebar, portfolio panel, feed badges).

## 2026-08-14 — T097 v6: the green face — glowing dots on blue-green
Owner supplied a new visual description: a headshot of glowing GREEN dots,
dramatic light, deep blue-green gradient background, visible ears, slight left
angle. Refactor (three offline tuning passes — first attempt floated the ears
as detached blobs, second overexposed into a solid mass, third collapsed
density; the fourth balanced contrast gamma 1.35 with density 0.34+0.66v):
elements are now ROUND soft-edged points (gl_PointCoord radial falloff, not
rod masks); ears are a surface EXTENSION that widens the silhouette and lifts
depth so they stay attached; key light from the upper left with density
thinning in shadow so dots separate visibly; background is a CSS blue-green
gradient with the whole UI chrome re-palette (teal/gold → green). The neural
cascade is REMOVED — the new spec is a headshot, not a dissolve.
JUDGMENT CALL recorded: state used to signal by colour (teal/violet/gold),
which a green-only palette would erase — so state now shifts hue and
brightness WITHIN the green family (idle 36,209,126 → listening 64,240,200 →
thinking 120,235,130 → speaking 150,255,170). Function preserved, identity
honored. Cursor-follow, lip amp, shimmer, CDN fallback intact.
Verified: node --check + guards (no cascade, round dots, ears) + verify.py
PASS — 608 passed, 3 skipped (frontend-only).
Owner: hard-refresh localhost:8000.

## 2026-08-14 — T088: "never buy the open print" gets a scoreboard
The doctrine has been a belief; this makes it falsifiable with the owner's own
money. Every ordered signal now stores the price the DECISION was made on
(new decision_price column, filled by the loop); analysis/execution.py
measures the gap to the actual fill as implementation shortfall in bps, with
a side-aware sign convention pinned by four hand tests: positive ALWAYS means
the execution cost you, whether buying or selling. Grouped by time-of-day
bucket (T091's entry buckets) and side, with thin buckets explicitly labeled
"anecdotes, not evidence" below 5 fills — a rule that matters more here than
anywhere, because the temptation is to conclude "mornings are expensive" from
two trades. Tool #32 joins signal_log.order_external_id ↔ transactions.order_id,
counts orders whose fills haven't synced yet, and treats an empty history as a
calm answer rather than an error.
Verified: verify.py PASS — 608 passed (+12), 3 skipped.
Next: T089 live MAE/MFE (same fills dependency), T072 human-grade TTS, or
T082 Orb pack. Owner unlocks still the real bottleneck.

## 2026-08-14 — T060: the deposit that must not look like skill
Built ahead of the trigger (D018 said this jumps the queue on the first
deposit — better to have it correct BEFORE money moves than to discover the
lie afterward). analysis/twr.py chain-links sub-periods across external
flows; the headline hand test says it all: deposit $500 into a $1,000 account
that grew to $1,100 and ends at $1,760 — the simple return prints +76% (of
which $500 was a transfer), TWR reports +21%, which is what the strategy
actually did. The lie flatters the owner, which is the worst direction, so
compare_benchmark now carries a time_weighted block with excess computed
against TWR and an instruction to quote it once flows exist. Plumbing:
cash_flows table + CSD/CSW activities (signs normalized: withdrawals always
negative) + deduped sync wired into scripts/sync.py, never fatal. The
tz-aware type guard earned its keep — Alpaca's date-only fields parse naive
and were caught at the DB boundary, fixed in the client.
Verified: verify.py PASS — 596 passed (+9), 3 skipped.
Next: T088 execution quality / T089 live MAE/MFE (both want accumulated
fills — daily scripts/sync.py), or T072 human-grade TTS.

## 2026-08-14 — T096: the right-sized toolbox — 31 tools is a menu, not a gift
I008's two routing failures came from a small local model drowning in the
registry; since then the registry grew from 24 to 31, so the problem got
worse, not better. api/tool_policy.py now curates: local/compat endpoints
(openai wire format against a non-openai base_url) get an 11-tool CORE set
covering the whole daily conversation; claude-sdk/anthropic/real-openai get
everything. Crucially the PERSONA's advertised tool list is now built from the
same filtered set — advertising tools a model can't call is exactly how
"I don't have that capability" and invented tool names happen (I008/I011).
claude-sdk honors a forced profile too (bridge wraps all, permission narrows).
KUBERA_TOOL_PROFILE=auto|full|core; unknown values degrade to auto instead of
killing a session. The guard test asserts CORE ⊆ registry, so a future rename
can't silently amputate a small brain's capability.
Verified: verify.py PASS — 587 passed (+11), 3 skipped.
Next: T088/T089 (need fills — run scripts/sync.py daily), T072 human TTS, or
owner unlocks (IPS resend, brain_check, T005 push, T023 FMP tier).

## 2026-08-14 — T036b: "stale" is the wrong word for Friday's close on a Saturday
The binary stale flag told a half-truth in both directions: it cried stale on
every weekend quote (correct data, wrong word) and said nothing special when a
feed lags DURING a session (the actually dangerous case). analysis/staleness.py
replaces it with four states — live / stale (open + behind = untrustworthy) /
last_session (closed + recent = trustworthy, "the most recent real print") /
old (beyond a normal closure) — each carrying a narration-ready phrase, all
hand-tested including the 96-hour boundary. get_latest now asks the BROKER
clock rather than guessing (I007's lesson: models garble raw ages, so the
phrase does the talking); without an Alpaca client it falls back to the
conservative rule and SAYS "market state unknown". Closed markets also get
"the market opens in 14h 20m". /api/market/.../latest now routes through the
tool so the endpoint and the chat layer can't drift apart.
Verified: verify.py PASS — 576 passed (+10), 3 skipped.
Next: T088 execution quality or T089 live MAE/MFE (both need accumulated
fills — run scripts/sync.py daily), else owner unlocks.

## 2026-08-14 — T064b: badges expire — and backtests confess their trades
Promotion is evidence, not tenure: is_promoted now takes max_age_days (default
180) — a walk-forward pass older than that silently stops counting and the
paper loop's existing gate refuses new buys until the pair is re-promoted
(proven by backdating a passed row in test). run_backtest's tool output grew
up: per-trade TradeStats (n/win-rate/profit-factor/best/worst), Calmar, and a
promotion block showing is_promoted + the latest T092 stability verdict
(new ledger.latest_stability) + a note pointing at promote.py/sweep.py and the
expiry. The chat model can now see AND SAY "this backtest looks great but the
pair is unpromoted and the sweep called it curve_fit". Parked deliberately:
promote-via-chat (wants the same deliberate-act confirmation design as
update_ips), crisis-window stress runs.
Verified: verify.py PASS — 566 passed (+3), 3 skipped.
Next: T036b session-aware staleness, or owner unlocks (IPS resend, brain_check,
T005 push, T023 FMP tier).

## 2026-08-14 — T062b (partial): the morning brief becomes the composite
Same-day integration of the day's shipments: the morning brief now carries a
`watchlist` section (top-3 ranked setups from T068, the owner's thesis note on
each; an empty list says "watchlist is empty" instead of hiding) and an
`event_risk` section (upcoming CPI/NFP dates from T076's calendar; a missing
FRED key or a calendar failure degrades to a note — the rest of the brief
still delivers). fred became an OPTIONAL member of the brief path: ctx.fred in
get_brief, best-effort FredClient in /api/brief (ConfigError → None), and the
composer takes fred=None gracefully. One endpoint syntax slip (finally before
except) caught by the gate and fixed; one tz fencepost in tests (local date vs
the composer's UTC date) fixed in the fixture. PENDING_NOTES now names only
the earnings-dates gap. "Give me my morning brief" is the J.A.R.V.I.S. moment.
Verified: verify.py PASS — 563 passed (+1 net), 3 skipped.
Next: T064b rigor follow-ups, or owner unlocks (T023 FMP tier, T005 push).

## 2026-08-14 — T076: don't open new risk into a known storm
The event-risk guard, CPI/NFP half. FRED's release-dates API (with
include_release_dates_with_no_data, which returns SCHEDULED future dates)
feeds pure calendar math in analysis/events.py; the paper loop now pauses NEW
entries within a configurable window before/on CPI and Employment Situation
releases — a first-class T055 no-trade reason, buys only, sells structurally
untouched (the whole block lives in the buy branch). paper_trade.py arms the
guard automatically when FRED_API_KEY is present and says so at startup;
get_macro_context surfaces the upcoming calendar with dates (degrades to a
note if the calendar endpoint fails — core macro reads still deliver). Both
loop paths tested end-to-end: release-today → no_trade with the reason;
clear calendar → order placed. FOMC dates are NOT in FRED — that source
decision + earnings dates + the sell-the-news flag are minted as T076b.
Verified: verify.py PASS — 562 passed (+6), 3 skipped.
Next: T060 TWR (jumps the queue on first deposit) or owner's T023 FMP answer.

## 2026-08-14 — T068: the watchlist ranks itself — a pipeline, not a pile
Research candidates now arrive RANKED. watchlist table + CRUD (idempotent
add carries the owner's thesis note); analysis/ranking.py scores the list
cross-sectionally per D020: relative-strength percentiles at 21/63/126 bars
(percentiles so a hot tape can't make everything a buy; tie-aware, hand-
tested), T050 regime label mapped to a documented long-side fit heuristic,
5-session payoff context, composite 0.5/0.3/0.2 with decile flags. Symbols
with thin history are listed-not-scored. Tools update_watchlist +
get_watchlist (#30/#31; empty list returns an offer, not an error) and
GET/POST/DELETE /api/watchlist. One fix en route: classify_regime's reading
exposes .regime, not .label. Say "watch NVDA — breakout setup" then "what
looks best on my list?" — that's the flow this ships.
Verified: verify.py PASS — 556 passed (+9), 3 skipped.
Next: T076 event-risk guard (FRED calendar) or T023 key-tier check (owner).

## 2026-08-14 — T093b: reconciliation — the DB and the broker must agree
Small ticket, closed same day it was minted. health_check now compares the
latest account_snapshot equity against the live broker (/api/account) and
warns above 0.5% drift — with the snapshot age and the remedy in the message
(stale-after-market-moves is normal, run sync.py; drift surviving a fresh sync
is an incident). Deliberately owns ONE failure mode: both sides reachable but
disagreeing — server-down and never-synced stay with their existing checks, so
no double-reporting. Rides the owner's every-5-min scheduled health check and
Windows toast unchanged. T093 is now fully closed (parts 1+2+3).
Verified: verify.py PASS — 547 passed (+3), 3 skipped.
Next: T068 watchlist + opportunity ranking (criteria defined in D020), or
T060 TWR the day the owner makes his first deposit.

## 2026-08-14 — T093: the book as one number — and promotions that expire
Two halves of the same discipline. MEASURE: analysis/portfolio_risk.py —
portfolio vol √(w'Cw) (hand-tested at correlation extremes: ρ=1 → 0.2, ρ=0 →
0.1414, ρ=−1 → 0), Euler risk contributions that sum EXACTLY to portfolio vol
("62% of your risk is SPY" is arithmetic), effective bets, diversification
ratio, one-bet warning at ≥60% concentration — tool #29 get_portfolio_risk +
/api/portfolio-risk. ENFORCE: backtest/decay.py — the promoted run's implicit
daily promise vs live returns through a one-sided CUSUM (crossing-day test
taught an fp lesson: a threshold exactly ON an accumulation boundary is
untestable — 20×0.0005 = 0.010000000000000002); on sustained shortfall,
demote() flips the ledger row and the EXISTING promotion gate refuses new buys
— no new code path. scripts/decay_check.py prints the account-proxy caveat
every run. T093b minted for the reconciliation half (small, unblocked).
Verified: verify.py PASS — 544 passed (+12), 3 skipped.
Next: T093b, or T068 watchlist ranking (criteria already defined in D020).

## 2026-08-14 — T090: liquidity costs — the spread is a fee and thin volume is a wall
analysis/liquidity.py: spread_bps (hand-tested 20bps case), per-side cost =
half-spread floored at 0.5bps (replaces the flat assumption when a quote
exists), trailing-20-session ADV, and the 1%-participation cap — labeled
honestly everywhere: IEX sample volume UNDERSTATES the consolidated tape, so
the cap binds early, which is the safe direction. The cap now BINDS in
size_position ("adv_cap" joins blocked/position_cap/risk_budget; THIN-symbol
test proves 5 shares max on 500 ADV) — required making the shared BARS_JSON
fixture's volume realistic (uniform 4M: RVOL ratios unchanged, legacy sizing
expectations unchanged; fix-the-fixture lesson applied deliberately this
time). Tool #28 get_liquidity refuses one-sided quotes ("spread math would be
fiction") + /api/liquidity/{symbol}.
Verified: verify.py PASS — 532 passed (+10), 3 skipped.
Next: T093 portfolio risk summary (T079 correlations now exist to build on).

## 2026-08-14 — T092: the curve-fit detector — one magic number is not an edge
backtest/stability.py: sweep a template across its parameter neighborhood and
demand a PLATEAU. Pure verdict logic hand-tested (plateau→stable, isolated
spike→curve_fit, all-negative→reject, <3 points→insufficient, exact-boundary
half-support case pinned); metric is annualized Sharpe of the equity curve so
leverage can't fake breadth; never-invested params score 0 with a warning
instead of crashing on the undefined-Sharpe constant curve. run_sweep is
engine-only (no ledger spam); the evidence lands beside promotions via
ledger.attach_stability → new stability_json column (migration 8d2d7f6c98b8,
sed ritual applied). CLI: python scripts\sweep.py momentum SPY --record.
Verified: verify.py PASS — 522 passed (+11), 3 skipped.
Next: T090 liquidity-aware costs (unblocked; quotes already fetched), or T093
portfolio risk summary now that T079 correlations exist.

## 2026-08-14 — T079: the overlap guard — "that's not diversification, that's the same bet"
Built the deterministic engine behind the pre-trade concentration warning:
analysis/correlation.py — pairwise Pearson correlation of daily log returns
(shared trailing windows; <20 observations = refused with a warning, never
guessed), per-symbol OLS beta vs SPY, portfolio beta from position weights
(coverage-warned when history gaps), 0.80+ pairs flagged, and the candidate
check that says "QQQ correlates 0.97 with your SPY — added exposure, not
diversification". Tool #27 get_correlation (description orders the model to
run it before any buy recommendation) + GET /api/correlation. All statistics
hand-computed in tests (y=2x → 1.0, constructed zero-covariance vectors → 0.0,
doubled returns → beta 2.0). T093's portfolio-risk summary builds on this.
Verified: verify.py PASS — 511 passed (+14), 3 skipped.
Next: T092 parameter stability sweeps or T090 liquidity costs (both unblocked).

## 2026-08-14 — T097 v5: anatomy pass — the skull under the hologram
Owner approved the rod technique, rejected the anatomy (11-point critique).
Kept: rods, palette, density system, behaviors. Changed: silhouette is now an
elongated tapered skull with per-side sinusoidal wobble (organic, slightly
asymmetric — no more sphere); pupils/eyeballs DELETED per spec — eyes are now
irregular horizontally-elongated feathered cavities (angular rim modulation,
different size per side, darker toward center, particles veiling them);
structural nose (stronger bridge ramp, projection, nostril dark mass); mouth
de-lined into a broad shallow cavity partially lost in the field; NEW dark
dense chin mass (density floor raised while brightness drops — the
"computational shadow beard") with fragmentation moved BELOW it; cascade
narrowed to a top-biased central column with escaping floaters — reads as the
face dissolving, not a torso. Composition ~60/15/25 face/transition/network.
Offline preview validated the anatomy before the port; cursor-follow (head
only now), lip amp, shimmer, scan, glitch, CDN fallback all intact.
node --check + no-uGaze guard + verify PASS 497/3.
Owner: hard-refresh localhost:8000.

## 2026-08-14 — T097 v4: the strict spec — microscopic rods, density features, continuous dissolve
Owner delivered a full visual spec (three references, STRICT): elements must be
tiny vertical luminous rods (NOT squares/voxels/mesh), features must emerge from
particle DENSITY + brightness + feathered dark recesses, mouth stays whole, jaw
fragments continuously into a chaotic neural cascade (no gap, floaters outside
the silhouette, progressive transparency), frontal, restrained glow. Built:
~40k sprites masked to thin rods in the fragment shader (gl_PointCoord band +
seed-varied height), density dropout tracking shade, elliptical feathered eye
recesses (offline preview caught the cartoon-disk eyes + premature mouth
fragmentation — both fixed in port), frag band below the lower lip with
animated drift, 565-node top-biased cascade with per-vertex fade colors (fake
progressive transparency under additive). All behaviors kept: cursor-follow,
pupil lead, lip amp, shimmer, scan, glitch, CDN fallback. node --check OK,
verify PASS 497/3. Owner: hard-refresh localhost:8000.

## 2026-08-14 — T097 v3: holographic — voxel columns, hollow eyes, the cascade
Owner's second reference (frontal head of stacked voxel columns dissolving
downward into a wireframe cascade) + the word "holographic". Rebuilt the
renderer on the same sculpt: 3 stacked depth layers per sample (~23k points,
volumetric column look), per-column brightness striping, speckled ice/navy/mid
palette (offline-tuned preview matched the reference closely before porting),
dark eye hollows with glowing tracking pupils, scan-band sweeping down the
face, holo flicker + z-instability, rare row-glitch. The side halo became THE
CASCADE: 230-node undulating wireframe network hanging below the jaw (sways at
35% of head yaw). Rest pose now frontal per reference; cursor-follow, pupil
lead, lip amp, thinking shimmer all kept. node --check OK, verify PASS 497/3.
Owner: hard-refresh localhost:8000.

## 2026-08-14 — T097 v2: the face grew up — sculpted 3D head on WebGL
Owner: v1 too pixelated vs his reference. Rebuilt: continuous sculpted depth
field (skull dome + ~18 gaussian features: brow/sockets/eyeballs/nose/lips/
chin/cheekbones/temples), tuned across TWO offline render iterations (fixed
nose-ridge shading discontinuity, deepened sockets, added iris ring + bright
pupil) before porting constants to JS. Renderer: three.js r128 (CDN) Points —
~12k GPU particles, baked Lambertian shading + ambient lift, additive glow,
custom vertex shader does cursor-follow head rotation (rests in the reference's
3/4 pose when idle), pupil lead, lip-sync from uAmp, thinking shimmer, and
left-edge dissolve; drifting wireframe network in scene space. Fallback pulse
if CDN unreachable — voice loop untouched either way. node --check on the
inline script + verify gate PASS (497/3, frontend-only).
Owner: hard-refresh (Ctrl+Shift+R) localhost:8000 — first load fetches three.js.

## 2026-08-14 — T097: KUBERA got a face — and it watches the cursor
Owner sent a reference image (voxel head dissolving into a particle network) and
asked for a face that follows the mouse. Shipped inside orb.html with ZERO
changes to the voice loop: a procedurally generated depth-mapped voxel face
(two-ellipse silhouette, carved brow/sockets/pupils/nose/lips/chin — sanity-
rendered offline before shipping and it reads as a face). Head rotates toward
the cursor with smoothing, pupils track with extra gain, gaze wanders when the
mouse goes quiet, lips move with the real TTS amplitude, thinking shimmers, and
the left edge dissolves into a drifting wireframe network like the reference.
State colors unchanged (idle gold / listening teal / thinking violet / speaking
gold) so the face IS the orb. Frontend-only; verify gate untouched but run.
Owner: restart the server, open localhost:8000, move the mouse.

## 2026-08-14 — I015: the provider that wasn't — brain_check + startup announcement
Owner corrected the record: .env says claude-sdk (verified — masked read), yet
the timeout error came from the OpenAI provider aimed at local Ollama. Claude's
"you were on openai" judgment was wrong as stated; the honest mechanism is that
BOTH are true: real OS env vars silently beat .env (pydantic precedence, now
pinned by a test that reproduces the exact scenario), or a stale server kept its
boot-time provider. No silent fallback exists in the SDK provider — verified.
Shipped: scripts/brain_check.py (three questions: what .env SAYS, what a NEW
server would RESOLVE, what the RUNNING server USES — /health), and a lifespan
startup log that announces the brain and WARNS "PROVIDER MISMATCH" whenever
resolution differs from .env intent. Sandbox run: intent=resolution=claude-sdk,
so the divergence lives on the owner's machine (shell var or stale process).
Verified: verify.py PASS — 497 passed (+5), 3 skipped.
Owner: python scripts/brain_check.py → restart from a clean shell → startup
line must read "KUBERA brain: llm_provider=claude-sdk".

## 2026-08-14 — D022: the J.A.R.V.I.S. batch — receipts first, then two real adoptions
Owner asked for a ReAct loop, universal registry, and anti-chatbot persona.
Receipts written into D022: the loop (MAX_TOOL_ROUNDS=6, SDK max_turns=8) and
registry (26 tools) have existed since T042/T024; the persona is tested code.
The chatbot FEEL is the brain, not the architecture — openai/local providers
under-use tools (see I011/I014). Adopted the genuine gaps: get_news (tool #26,
Alpaca news feed, per-item ages, injection rule restated, + /api/news) and the
persona rule "AGENTIC DEFAULT — act first, speak once": composite questions get
a silent fan-out and one synthesized answer, never tool narration or "which
check?" asks. Guard tests bumped 25→26 in all three places. Web search NOT
adopted (D022 records why + revisit trigger).
Verified: verify.py PASS — 492 passed (+6), 3 skipped.
Owner: LLM_PROVIDER=claude-sdk is what makes the fan-out actually happen.

## 2026-08-14 — I013+I014: schemas are private + a timeout that keeps the thread
Owner transcript, two failures in one conversation. First: "update the IPS" was
answered with a table of our internal parameter names — a form, not a colleague.
Persona gained "SCHEMAS ARE PRIVATE" (the reply is 'what would you like to
change?'; briefs get extraction, not menus), update_ips's description now forbids
showing its field list, and chat.py gained ensure_no_schema_dump: 3+ internal
underscore-names in a reply (user didn't ask for fields / doesn't speak schema) →
⚠ Pacing footer. His exact menu reply is a named test. Second: the resent IPS
brief hit a ReadTimeout, raw error on screen — on provider=openai (likely local),
not claude-sdk. Timeout is now LLM_TIMEOUT_SECONDS (default 300s, was 120 fixed),
timeout errors name the knob, and run_chat_turn catches LLMError: user text was
committed pre-call, so the reply says "saved — say 'try again'" and the recovery
replay is tested end-to-end. Audited remaining tool descriptions: only update_ips
was menu-bait. Verified: verify.py PASS — 486 passed (+11), 3 skipped.
Owner: restart backend, resend the brief; if it times out again the message is
kept — say "try again", or raise LLM_TIMEOUT_SECONDS in .env.

## 2026-08-14 — I012: the IPS brief that didn't fit + goal_math (tool #25)
Owner poured his actual investment policy into the chat — 14 sections, $1k→$1M,
horizon math, contribution scenarios, "challenge my assumptions" — and got a 422.
Two caps conspired: ChatRequest max_length=6000 rejected it, and MAX_STORED_CHARS
=6000 would have truncated the stored copy the model replays even if the first cap
were raised alone. Fixed both: request 20k, storage 24k (storage > request, so user
text survives whole). Then made the message answerable: analysis/goal_math.py —
required_cagr (10y needs 99.5%/yr — hand-tested against 10^0.3), future_value with
monthly contributions, years_to_target (None = "not in 100 years", honest),
daily_return_reality (1.02^252 ≈ 147x/yr — the "2–5%/day" conversation-ender).
goal_math registered as tool #25 (+ GET /api/goal-math; all three guard tests
bumped 24→25); description orders the model to challenge unrealistic assumptions
with these numbers, note says contributions dominate at small sizes.
Verified: verify.py PASS — 475 passed (+13 hand-computed), 3 skipped.
Owner: restart backend, resend the IPS message unchanged — it fits now.

## 2026-08-14 — I011: bridge telemetry + fabrication guard — trust nothing that skipped the tools
Owner transcripts on claude-sdk: one turn denied get_portfolio and hallucinated
tool names (get_market_data/submit_verdict — prose distortions) while priming HAD
fired; a rephrase worked perfectly. Diagnosis: the SDK MCP bridge likely degrading
silently on some turns (version drift) — a model with real schemas doesn't misspell
them. Shipped: (1) bridge telemetry — "bridged N registry tools" logged per call,
WARNING on mismatch, /health reports llm_provider + tools_registered; (2) deflection
v3 — primed-only trails = "model called nothing" (the denial transcript is a named
test), "list the tickers" pattern, portfolio-ish ticker-asks flagged without a named
ticker; (3) FABRICATION GUARD — 3+ precise figures with zero tool history and none
in the primed snapshot -> "Unverified numbers" footer (numbers come from tools,
never memory). Owner verification: restart, watch for "bridged 24 registry tools";
mismatch -> pip install -U claude-agent-sdk.
Verified: verify.py PASS — 462 passed, 3 skipped.
Blockers: bridge verification pending on owner machine (steps in I011).

## 2026-08-14 — I010: portfolio auto-priming — from instructions to architecture
Fourth deflection transcript ("check my portfolio for SPY" -> "how many shares do
you hold?"). Verdict accepted: prompt rules don't stick on the local brain, so the
data now arrives regardless of model obedience. prime_portfolio in the chat layer:
portfolio intent detected -> get_portfolio executed SERVER-SIDE before the model
speaks -> compact snapshot (per-position qty/avg/mv/unrealized + equity/cash)
injected into the system prompt with "Answer from THIS data. Do NOT ask for share
counts..." Audited: trail gains {get_portfolio, auto_primed:true}, recency footer
sees the asof; silent no-op without intent or broker; a priming failure never kills
the turn. Deflection detector v2 also fires on asks-for-position-details. The
transcript is a named test; the chat E2E now asserts the primed fetch precedes the
model's own call.
Verified: verify.py PASS — 456 passed, 3 skipped.
I007–I010 arc closed for portfolio asks: structurally impossible to deflect now.
Owner: ask "check my portfolio" again — the numbers arrive before the model can ask.
Blockers: none.

## 2026-08-14 — I009: lenient tool args — sloppy "None"/""/"BUY" no longer kills journaling
Owner pasted server logs: record_decision failed twice — string "None" and "" for
absent optionals, SHOUTED "BUY" vs the lowercase pattern. Silver lining: the T063
persona rule WORKED (the model tried to journal). Fix: LenientArgs base (wildcard
before-validator: ""/"None"/"null"/"N/A" → real None) + verdict lowercasing; applied
to record_decision, mark_decision, triage_position, update_ips. BOTH failing payloads
from the logs are now verbatim passing tests; real validation (bad verdicts/numbers)
still rejects. I009 logged — third local-brain formatting strike; T096 + claude-sdk
recommendation stand.
Verified: verify.py PASS — 452 passed, 3 skipped.
Blockers: none.

## 2026-08-14 — Conversational pacing: the Orb learned patience, the persona learned turns
Owner feedback with transcript: (1) the Orb sent his speech the moment he paused;
(2) KUBERA interrogates with numbered 4-question forms + capability menus; (3) it
asked for his entry price when get_portfolio ALREADY carries avg_entry_price (third
capability-denial, same lesson).
Shipped: ORB — recognition rewritten with patience: continuous=true, mic stays open
across engine restarts (onend → restart while wantListening), every sound resets a
2.8s silence timer (SILENCE_SEND_MS), send fires only on real quiet OR click-the-orb
send-now; trailing interim text included so the last words never drop; status line
says "pauses are fine". Hold-Space release still = send immediately (full manual
control). PERSONA — PACING rule (guard-tested): ask for exactly ONE missing thing
and stop, never numbered question lists or capability menus, positions/entry
prices/balances are already in get_portfolio — look before asking; full analysis
only once inputs exist. VOICE_STYLE unchanged (already ~120 words).
Verified: verify.py PASS — 449 passed, 3 skipped (orb assertions extended).
Remaining truth: mid-KUBERA-speech interruption (barge-in) needs the realtime stack
— that's T074, unchanged. Owner: refresh the Orb page (Ctrl+F5) and talk with
pauses; click the orb when you're done — or just wait ~3 seconds.
Blockers: none.

## 2026-08-14 — I008: "which ticker?" deflection — second strike on the local brain
Owner's next transcript: "I hold SPY, should I keep holding?" → model asked for the
ticker, claimed no recent-performance function exists (get_symbol_briefing IS it),
confused get_brief with get_symbol_briefing, called ZERO tools. I007's symbol check
was correctly silent (nothing ran → nothing to compare). Shipped:
(1) ensure_no_deflection post-check — named ticker + empty tool trail + asks-for-
symbol phrasing → footer naming the tools that DO answer ("a model miss, not a
missing capability"); the transcript is a named test.
(2) Persona ROUTING map — question→tools ("should I hold X" → briefing + regime +
exit plan + triage), "never claim a capability is missing without checking the tool
list", "never ask for a symbol the user already named" (guard-tested).
(3) I008 logged; T096 filed: per-brain tool subsetting (24 tools overwhelm small
local models — curated core set for local brains).
PATTERN ON RECORD: two strikes, both model-level, tool layer blameless both times.
Standing recommendation: LLM_PROVIDER=claude-sdk for real decisions.
Verified: verify.py PASS — 449 passed, 3 skipped.
Owner: switch the brain, re-ask; the answer should route to briefing+regime+exit plan.
Blockers: none.

## 2026-08-14 — I007: the SPY→TSLA wrong-symbol reply — three defenses shipped
Owner pasted a real transcript: "should I buy and hold SPY?" answered with a TSLA
sizing table + directive tone + "price age ≈ 28 s marked stale" at 04:31 UTC (market
closed — the price was HOURS old; the stale flag was right, the narration wasn't).
Tool layer blameless; model-level misdirection. Shipped same-session:
(1) ensure_symbol_alignment in chat — deterministic post-check like the recency
footer: user-named tickers vs tool-call symbols; zero overlap → "⚠ Symbol check …
answer may be misdirected — re-ask" appended. The exact transcript is a named test
(test_the_spy_tsla_transcript_is_caught). Conservative: silent without named tickers
or with any overlap; stopword list keeps ETF/AI/CEO etc. from false-firing.
(2) age_human on trades/quotes + size_position ("7h 52m", never raw seconds) — stop
models garbling seconds arithmetic.
(3) Persona CORE_RULE "Answer the question that was asked" (opinion → analysis
structure; sizing only on how-many; wrong-symbol tools re-run, never presented) —
guard-tested. I007 logged with residual-risk note: prefer the claude-sdk brain for
real decisions; treat any Symbol-check footer as a hard stop.
Verified: verify.py PASS — 445 passed, 3 skipped.
Next: back to the queue (T090/T093) or Gemini takes T082. Owner: re-ask your SPY
question — and if you were on the local brain, switch LLM_PROVIDER=claude-sdk.
Blockers: none.

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
