# TASKS

One ticket = one focused agent session. Claim by adding your name as owner.
IDs never get reused. Format per PROJECT_SPEC.md §11.

**Build-order guidance (D018, 2026-08-13):** T052 intraday (doctrine backbone) →
T055 no-trade condition (owner's overtrading failure mode — lands WITH or BEFORE
T054's router, never after) → T077 expected-move → T067 DQS / T062 briefs.
Owner actions that unlock the most: T007 finale. (T005 is DONE — the owner has
been pushing all along; origin/main == local main, 7 Actions runs. Any agent
still writing "CI is dark" is repeating a stale claim: CI RUNS, and it is
currently RED — see I018, which needs the failing log.)

## In progress
- **T066 (trade coaching: pre/post-trade reviews) — Claude/Cowork** — claimed 2026-08-18.

## Awaiting review (D023 — a DIFFERENT agent signs these off; see REVIEW.md)
- **T067b (DQS v2 — score the OWNER's own trading) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS at fdfe6e9)**. v1 scored the paper loop and said so; both of
  its stated prerequisites (broker-fill sync, decision journal) have landed,
  so v2 scores HIS record. Built backend/risk/owner_dqs.py (pure):
  (1) disposition_effect (≤30) — median winner hold vs median loser hold;
  ratio < 1 = cutting winners while riding losers; refuses under 5 trips on
  EITHER side, and a zero loser-median (all same-session) yields no verdict
  rather than a divide-by-zero opinion; (2) revenge_sizing (≤30) — reuses
  T069's sizing_drift VERBATIM so the codebase has one definition of the
  revenge pattern, not two that drift; (3) journal_discipline (≤20) — only
  the UNMARKED share costs; overriding KUBERA is explicitly not penalised
  (his judgement is why the journal exists); (4) budget_from_ips() — converts
  his ratified max-drawdown into an implied daily budget by T069's own
  1/3 convention, prints it beside the ENFORCED limit and flags disagreement,
  as a PROPOSAL that never applies itself (a safety rail that moved on its
  own would be the "talked out of the lockout" failure the tiers exist to
  prevent). FOMO-into-late-RVOL is NOT built and says why in every report:
  statement fills are date-only, so it would be guesswork (T102).
  Wiring: get_risk_status gains an `owner_dqs` block sourced from DB
  Transactions -> attributed_fills_from_rows -> fifo_attribution — the SAME
  path T069 uses, so the two behavioural reads cannot disagree about what a
  round trip was; empty table degrades to a note pointing at sync.py. No new
  tool, so no guard-count bump.
  EVIDENCE (D027): 14 unit tests hand-computed (0.25 ratio -> 45 capped to
  30; 0.75 -> 15.0; winners-held-longer free; sample-floor refusal; undated/
  negative/scratch trips skipped not defaulted; same-session no-verdict;
  revenge ratio 2.0 -> capped 30; unmarked 5/10 -> 10.0; IPS 15%/3 = 5% vs
  enforced 2% flagged looser) + 2 end-to-end through the tool on a seeded DB
  (10 real Transactions -> 10 trips -> ratio 0.25 -> score 70.0; empty DB ->
  available:false naming sync.py). 36 passed across both suites; ruff clean;
  gate PASS.
  D028 objections: (a) MY OWN CANARY CAUGHT ME — the pyrefly count went 1 -> 2
  on a dict literal that inferred `agrees: None`; re-measured (a transient
  fooled me once before), confirmed reproducible, fixed with an explicit
  annotation, back to exactly 1; (b) T069's sizing_drift compares raw
  qty x price, so option notionals are understated 100x — it cancels in the
  RATIO unless the option/equity MIX differs between post-loss and post-win
  buys; I did not change a shared T069 function inside this ticket, and the
  reviewer may reasonably want that as its own; (c) the disposition penalty
  slope (60x the gap) and the IPS 1/3 convention are chosen tunables, both
  commented; (d) held_days comes from attribution, which reads date-only
  statement-sourced rows as whole days — the metric is real but coarse until
  time-stamped Schwab fills accumulate.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS (covering commit fdfe6e9 per D033)
    aligned: Implements DQS v2 for the owner's real trading record across disposition effect, revenge sizing (reusing T069 definition), journal discipline (unmarked decisions penalized, overrides allowed), and IPS-implied budget proposal (pure advisory), while explicitly refusing guesswork on FOMO-into-late-RVOL until intraday timestamps accumulate (T067c).
    checked: Validated commit fdfe6e9: (1) `backend/risk/owner_dqs.py` pure scoring functions with sample floor checks, median zero hold protection, and capped penalties; (2) `backend/api/tools.py` wiring `_owner_dqs_block` into `get_risk_status` using the verified DB -> attribution pipeline; (3) 14 hand-computed unit tests in `test_owner_dqs.py` and 2 tool integration tests in `test_dqs_tiers.py` pass; (4) full `scripts/verify.py` green (924 tests passed, 0 lint errors, memory budgets all within bounds).
    concerns: none
- **T023b (fundamental ratios from FMP statements — D030 #4) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS at 8609e54)**. Built:
  (1) backend/analysis/fundamentals.py (NEW, pure, no I/O) — FCF per fiscal
  year with the T016c principle applied to statements: the statement's OWN
  freeCashFlow is preferred ("reported"), else derived OCF + capex where FMP's
  capex is a NEGATIVE outflow; a POSITIVE capex is an unobserved sign
  convention → the year lands in unparsed, never silently "fixed" (T102).
  FCF yield = latest fiscal FCF / TODAY's market cap, with the backward-
  numerator/live-denominator note; debt/equity SUPPRESSED (None + why) when
  equity is non-positive — a negative ratio reads as "low debt", the exact
  wrong conclusion; debt/assets separately; STALENESS_NOTE in every reading.
  (2) data/fmp.py gains cash_flow_statement (probe-verified), balance_sheet
  (NOT probe-verified — named FmpError on paywall), profile_market_cap
  (probe-verified; None when payload lacks a usable number). (3) briefing
  tool gains a fundamentals block: None without ctx.fmp; FmpError on the
  cash-flow half → available:false with why; a paywalled balance sheet must
  NOT cost the FCF half (pinned in test). (4) scripts/fmp_check.py gains the
  balance-sheet probe row so the owner's next run answers the one endpoint
  the 2026-08-17 probe missed.
  EVIDENCE (D027): 24 tests across test_fundamentals (6, all hand-computed:
  80k/1.6M = 5% yield, 50k/200k = 0.25 D/E, derived 100k−25k = 75k,
  positive-capex refusal, negative-equity suppression, unparsed reporting) +
  test_fmp (+3: fetchers, named paywall, non-list shape refusal, unusable
  profile → None) + test_briefing_tool (+3: null without fmp, hand-computed
  block with fmp, paywalled-balance-sheet survival). ruff clean; pyrefly
  exactly 1 (I023 canary); full gate PASS.
  D028 objections: (a) fixture rows follow FMP's DOCUMENTED statement shape —
  same honesty note as T023 v1; fail-closed unparsed reporting is the
  mitigation and the owner's next briefing run is the live proof; (b) FCF
  yield mixes a fiscal-year numerator with a live denominator — the only
  option without paid TTM data, and the note says so in every payload; (c)
  no income-statement fetch = no margins/EPS — deliberate scope hold (ticket
  names FCF + debt), one request cheaper per briefing on a 250/day budget.
  OWNER PROBE RUN 2026-08-18 (same session): **balance sheet OK (1 row)** —
  debt ratios are LIVE on his tier, no code change needed (the briefing was
  built to light up when the endpoint answers). Full table also corrects one
  stale record: analyst estimates now reads OK (1 row) — the 08-17 "HTTP 400"
  was MY probe's parameter bug, fixed in T023 v1; the endpoint answers on the
  free tier. Estimate FEATURES stay out of KUBERA regardless until a ticket
  argues them in — availability ≠ adoption; estimates are third-party
  opinions (D019/D030 discipline). news/transcripts confirmed paywalled,
  D030's source decisions unchanged. Remaining owner check: one briefing
  with FMP_API_KEY set → fundamentals block, unparsed == [].
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS (covering commit 8609e54 per D033)
    aligned: Brings deterministic FCF yield and debt ratios from annual statements into the symbol briefing with fail-closed sign validation and explicit staleness labeling, keeping within the 250 req/day free budget (D030).
    checked: Validated commit 8609e54: (1) `compose_fundamentals` in `backend/analysis/fundamentals.py` hand-computed math (80k/1.6M = 5% yield, 50k/200k = 0.25 D/E, 100k-25k derived = 75k FCF), negative equity debt/equity suppression ("a negative ratio reads as low debt"), and positive-capex unparsed reporting; (2) `data/fmp.py` statement fetchers and profile market cap; (3) briefing tool fundamentals block and paywall/error graceful degradation paths; (4) owner ran `python scripts/fmp_check.py` on live key confirming balance sheet OK (1 row), cash flow OK (5 rows), income statement OK (5 rows), profile OK. Ran `pytest backend/tests/test_fundamentals.py backend/tests/test_fmp.py backend/tests/test_briefing_tool.py` (24 passed) and full `verify.py` (908 passed, ruff clean, memory budgets all within bounds).
    concerns: none
- **T016b (automated API-vs-statement cross-check) — DONE 2026-08-18
  (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS, third verdict,
  explicitly covering delta fixes 71670b2 + 545f84b; owner acceptance CLEAN
  39/39 exit 0)**. Fully closed: Gemini's final verdict cites the post-fix
  evidence (896 tests, DST window edges 05:00Z/04:00Z, both CLI wirings, the
  owner's clean run) — current as of the last code commit on this ticket.
  D033 RECORDED off this ticket's two review races (verdicts at 16:08 and
  16:18 each went stale within minutes; the second's own evidence — "38
  orders", 893 tests — proved it predated 545f84b): from now on a verdict
  names the SHA it covers, the reviewer confirms it is still the newest
  commit on the ticket's files before signing, and SHA-less verdicts are
  void under D027. Propagated to REVIEW.md §4 + docs/agent-briefs.md.
  Two independent sources agreeing, not a machine agreeing
  with itself; the human tick-off keeps the final word. Built:
  backend/analysis/cross_check.py (pure, no I/O) + scripts/cross_check_schwab.py
  (CLI: live pull + parse_directory(private/), prints MATCHED / API-ONLY /
  STATEMENT-ONLY in full, exit 0 only when clean, SchwabError → named
  "SCHWAB UNAVAILABLE" note, read-only). Join design from the owner's own
  March verification: API executions aggregate BY (order_id, symbol, side)
  with qty-weighted price (his 71+29=100 @ 0.21 to-the-penny case is THE
  fixture); OCC symbols ("NVDA  260320C00177500") normalise to the statement's
  underlying+expiry/right/strike key, fail-closed (unparseable OCC → reported,
  never guessed into an equity match); API UTC times join on their
  America/New_York date (T111). Match = same ET date + instrument key + side +
  qty, price within ±0.01 default (weighted avg vs statement rounding). Greedy
  1:1 within groups — two identical orders need two statement lines. NEVER
  silently reconciles: near-misses (price-out-of-tol same day, or dates ≤3d
  apart with price OK) are labelled notes; the lines stay unmatched. Fee
  comparison (both sides carry broker numbers post-T016c/T108b) is
  informational only, never affects matching.
  EVIDENCE (D027): test_cross_check.py 14 tests, all hand-computed — the
  71+29 case, weighted-avg 0.206 vs printed 0.21 inside tol, 23:30 UTC staying
  on its ET day, both-only buckets, near-miss labels, greedy pairing,
  fail-closed OCC, fee notes, qty/tol validation. Live CLI run in sandbox:
  named degradation confirmed ("SCHWAB UNAVAILABLE", exit 2 — api.schwabapi.com
  unreachable here per I002; the full path needs the owner's machine). ruff
  clean; pyrefly exactly 1 (I023 canary); full gate PASS.
  OWNER RUN #3 (2026-08-18, after the window fix) — **CLEAN, exit 0**:
  39 matched, 0 API-only, 0 statement-only, 0 near-misses, 0 unparseable.
  The window fix pulled the 3/31 session (52 executions vs 51) and his 3/31
  SPY 635P buy matched its confirmation. March 2026 is now verified
  three ways: his hand reconcile (T016), statement-vs-statement audit
  (T108/T108b), and API-vs-statement automated diff (T016b) — all agreeing.
  Owner acceptance COMPLETE; only Gemini's delta review (71670b2 + 545f84b)
  remains open on this ticket.
  OWNER RUN #2 (2026-08-18, after the folder fix): 38 of 38 API orders
  MATCHED their statement lines — dates, symbols, sides, quantities, prices
  agreeing across two independent sources, including the 11-execution and
  2-execution aggregations. The 1 "statement-only" line was MY window bug:
  --end as midnight UTC excluded the final session, so his real 3/31 SPY put
  buy was never in the API pull. Fixed at the root: market_window_utc() in
  analysis/market_time.py (inclusive ET days -> [start, day-after-end) UTC;
  March-2026 DST-straddling edges pinned 05:00Z/04:00Z, his 3/31 15:00 ET
  trade pinned inside), wired into BOTH cross_check_schwab.py and
  reconcile_schwab.py (same defect class — reconcile had silently dropped
  final-day trades too). Also quieted pypdf's per-page "Rotated text" warning
  at the CLI (90+ noise lines; unparsed-count remains the real signal).
  FEE NOTES explained (all 4, verified arithmetic): the confirmation parser
  attributes a DOCUMENT's total commission to one line when several
  same-instrument orders share a day — 3/09 stmt 6.50 = (2+2+6) contracts
  x 0.65; 3/17 9.75 = 15 x 0.65; 3/20 62.40 = 96 x 0.65; 3/27 1.95 = 3 x
  0.65. Sum-level the sources agree exactly; the API's per-order numbers
  (T016c) are the granular truth. Informational-only design behaved
  correctly (no match was blocked).
  OWNER-RUN DEFECT, fixed same session (2026-08-18): his first live run
  parsed "0 files" — my --statements default was private/ but the PDFs live
  in private/statements/ (the path every other script already uses; I didn't
  check the precedent). Worse, the empty side still diffed: 38 fake
  "API-only" problems that were really one missing input. Fixed both: default
  now private/statements, and files_read==0 (or zero fills in window) refuses
  loudly with the path it searched, exit 2 — an unavailable input is not a
  discrepancy report. His visible output also confirmed the API side end to
  end: 51 executions → 38 order lines, the 100 @ 0.21 two-execution case and
  an 11-execution 0.09 aggregation both printed correctly, OCC symbols
  rendered, ET dates matching his verified reconcile.
  D028 objections: (a) my near-miss date branch initially didn't check price —
  would have labelled pairs "all else equal" that also disagreed on price;
  caught in self-review, fixed, pinned by test; (b) known limitation: a GTC
  order filling across MULTIPLE days aggregates to one API line (min date) vs
  per-day statement lines — would surface as unmatched buckets, correct
  behaviour (attention, not absorption), but no observed case exists to build
  against (T102 discipline: no code for unobserved shapes); (c) statement
  trade_dates derived via T+1 (date_source="derived_settle_t1") are only as
  good as T108b's calendar — but that calendar was verified against 83
  explicit dates, and a systematic error would light up as date near-misses,
  which is the tool telling on its own inputs. Owner acceptance path: run
  `python scripts\cross_check_schwab.py --start 2026-03-01 --end 2026-03-31`
  on the machine with .env + private/ and compare its MATCHED count to the
  reconcile you already ticked off.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS (including delta fixes 71670b2 + 545f84b)
    aligned: Provides automated cross-check reconciliation between Schwab API fills and statement-parsed fills without machine self-reconciliation or silent absorption, keeping the human tick-off as final authority (D026).
    checked: Validated delta fixes 71670b2 + 545f84b: (1) default path updated to `private/statements/` with loud refusal on 0 files or 0 in-window fills (exit 2); (2) `market_window_utc()` in `analysis/market_time.py` correctly calculates inclusive ET days across DST flips (`[2026-03-01 05:00Z, 2026-04-01 04:00Z)`), pulling the full final trading session and eliminating the false statement-only edge case on 3/31; (3) wired into both `cross_check_schwab.py` and `reconcile_schwab.py`; (4) owner run #3 clean (39/39 matched, exit 0). Ran `pytest backend/tests/test_market_time.py backend/tests/test_cross_check.py` (24 passed) and full `verify.py` (896 passed, ruff clean, memory budgets step green).
    concerns: 1. Multi-day GTC order fills aggregate to min-date on API side vs daily statement lines (unobserved shape today, surfaces as unmatched attention item if encountered).
- **T113 (utf-8 subprocess hardening + archive_memory tests) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**. D032-clean rebuild of the two ideas salvaged
  from the reverted review-session code. Built: (a) parallel_check.py's two
  subprocess.run calls (git wrapper + alembic heads) gain
  `encoding="utf-8", errors="replace"` — Windows text=True defaults to cp1252,
  which chokes on the em-dashes/middle-dots throughout the memory files this
  script exists to read; errors="replace" degrades one character, never the
  whole safety check. (b) backend/tests/test_archive_memory.py — 5 tests via
  importlib-by-path (T106 precedent, test_install_mcp_config.py pattern, NO
  sys.path mutation), all paths monkeypatched to tmp_path (never touches real
  memory): header preserved verbatim + exact keep-count with newest-first
  verbatim archive & provenance line; same-day double archive → two files (-2
  suffix, moved+kept == 20, move-never-delete arithmetic); keep >= entries →
  clean no-op (file unchanged, no archive dir); check() 0/1/2 ladder at
  100/701/1001 lines (the exact thing verify.py runs); split_progress
  no-entries edge.
  EVIDENCE (D027): 5/5 pass; ruff clean on both files; live
  `python3 scripts/parallel_check.py` exit 0 after the encoding change;
  pyrefly exactly 1 (I023 canary); full gate PASS.
  D028 objections: (a) my first double-archive assertion assumed lexicographic
  order puts the -2 file second — false ("-" sorts before "."), caught by the
  test's own first run and re-pinned order-free; (b) tests load the script
  fresh per call so monkeypatched globals can't leak between tests; (c) the
  cp1252 fix is asserted only by successful live run, not a forced-encoding
  test — a faithful Windows-codepage repro needs the owner's machine, noted
  for the reviewer.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS
    aligned: Hardens parallel agent collision detection against Windows cp1252 encoding crashes on UTF-8 memory files and pins archive_memory.py behavior via isolated importlib-by-path unit tests without sys.path leakage.
    checked: Ran `python scripts/parallel_check.py` (exited 0 cleanly), `pytest backend/tests/test_archive_memory.py` (5 passed: header preservation, exact keep-count, same-day no-overwrite with -2 suffix, clean no-op, --check 0/1/2 ladder, split without entries edge), and full `python scripts/verify.py` (879 passed, ruff clean, memory budgets step green).
    concerns: none
- **T016c (Schwab fills into the daily sync + fee persistence) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**. Built: (1) Transaction gains nullable
  fill_type/commission/fees (alembic 7c3a91e0d5b2, revises 00c4e1efd5c4, single
  head; legacy rows stay NULL = equity/no-cost-data, never guessed); (2) mapper
  extracts fee legs from transferItems (COMMISSION → commission, every other
  feeType → fees, abs(amount)); (3) data/schwab_sync.py sync_schwab_fills —
  30-day trailing window, T036-style dedupe per external_id for Transactions AND
  CashFlow, account keyed by Schwab's hash_value (non-PII), unmapped counted
  never dropped; (4) scripts/sync.py best-effort block: no config → skip note,
  ANY SchwabError → named note (token lapse gets "run schwab_auth.py --write"),
  Alpaca half never dies for a Schwab failure; (5) attribution: AttributedFill
  gains contract_multiplier, FIFO pnl and notional ×100 for option lots,
  attributed_fills_from_rows maps fill_type via the existing contract_multiplier()
  helper — DB option trips were 100x understated before this.
  EVIDENCE (D027): test_schwab_sync.py 5 tests — fees split 0.65/0.01 on the
  probe-shaped option row, I029 placeholder-tradeDate regression at the DB layer
  (occurred_at 15:24 not 05:00), rerun idempotent (+0/3 known), lapsed token
  raises the named weekly error, option round trip pnl $39.00 not $0.39
  (notional $130 = 1×1.30×100). 47/47 across schwab+attribution suites; alembic
  upgrade head on scratch DB → all 3 columns present; ruff clean; pyrefly
  exactly 1 (I023 canary); full gate PASS.
  D028 objections considered: (a) DB and file-based behavioural stack are now
  TWO stores of the same fills — autopsy still reads files; T016b's diff is the
  reconciliation, and get_attribution reading the DB now gets correct option
  math; (b) catching ALL SchwabError in sync.py could mask a real mapping bug —
  no: mapping bugs raise ValueError/KeyError which still propagate, SchwabError
  is transport-only; (c) fees are recorded but not yet subtracted in FIFO pnl —
  deliberate, matches T108's convention (costs decomposed separately, T090/T091b),
  noted for the reviewer.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS
    aligned: Lands owner's real Schwab fills and broker fee legs (COMMISSION vs fees) directly into daily sync and DB without killing the Alpaca sync on token expiration (D026).
    checked: Ran `alembic heads` (single head `7c3a91e0d5b2`), `pytest backend/tests/test_schwab_sync.py backend/tests/test_schwab.py backend/tests/test_attribution.py` (47 passed), full `verify.py` (874 passed, ruff clean, memory budgets green). Verified broker fee splitting (0.65 commission / 0.01 fees), 100x option contract multiplier in FIFO pnl ($39.00 pnl, $130 notional), idempotent deduplication, and non-fatal token lapse degradation.
    concerns: 1. DB store and file-based behavioural stack remain separate until T016b reconciliation. 2. Fees are stored and decomposed separately per T108 convention (not subtracted inside raw FIFO trade pnl).
- **T112 (memory budgets as a gate mechanism — D031) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**.
  CODE ADDED DURING GEMINI'S REVIEW, REVIEWED 2026-08-18 by Claude/Cowork — **PASS**
  (bf730e0 + 1e992ba: test_archive_memory.py [4 tests], parallel_check utf-8
  subprocess hardening, defensive out_label guard). Ran it: 4/4 pass, full gate
  PASS, pyrefly exactly 1 (an initial reading of 2 was a transient — re-measured
  before writing it down). The utf-8 fix is real Windows hardening; the tests pin
  header preservation and keep-count behavior.
  ON THE RECORD, without relitigating (these commits predate D032 by minutes):
  bf730e0 briefly DELETED archive_progress's `path.write_text` — the line that
  trims PROGRESS after archiving — which would have silently duplicated history;
  1e992ba self-caught and restored it. A reviewer editing the script under
  review broke the script under review: that incident is D032's justification,
  generated contemporaneously. Going forward the paste-brief governs.
  Concern (stylistic, non-blocking): the test does module-level sys.path.insert
  — the pattern removed in T106 because it persists across the whole suite;
  works today, one-line importlib cleanup whenever the file is next touched.
  SUPERSEDED 2026-08-18 BY THE OWNER: he removed ALL artifacts of Gemini's
  review session from disk (test_archive_memory.py, its duplicate hermes
  disposition doc, both script edits reverted) — enforcing D032 retroactively,
  which is his call and consistent with the rule's spirit: reviewer-created
  code should not exist, however good. Cleanup committed; gate PASS after
  reverts; pyrefly exactly 1. The two ideas WITH merit are re-filed below so
  a BUILDER session can do them properly:
- [x] T113 — built 2026-08-18, see Awaiting review at top.
  Owner-requested hermes-agent review (disposition: docs/research/hermes-agent-review-
  2026-08-17.md) adopted one lesson our repo proved on measurement:
  PROGRESS.md's own day-one "~150 lines then archive" rule had never executed
  — 2,654 lines, no archive dir. Files: `scripts/archive_memory.py` (NEW —
  --check warns at soft budgets and FAILS the gate at hard caps [error-forces-
  consolidation semantics]; archival is MOVE-never-delete to project-memory/
  archive/ with provenance header, newest 12 PROGRESS entries kept, refuses
  --keep < 5), `scripts/verify.py` (memory-budgets step added to STEPS),
  `project-memory/archive/PROGRESS-archive-2026-08-18.md` (FIRST RUN: 142
  entries moved verbatim, 2,654 -> 210 lines), D031 in DECISIONS.
  EVIDENCE (D027): pre-run --check correctly FAILED (exit 2, named the file
  and the fix); post-run passes with TASKS soft-warning at 901 (by design —
  its compaction needs judgment, so it nags); full gate PASS end-to-end with
  the new step live; ruff clean; pyrefly 1 (known I023).
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. Budget numbers are chosen tunables (commented in BUDGETS) — reasonable
       people could pick others; the mechanism matters more than the values.
    2. The archiver only automates PROGRESS (dated, append-only = mechanical);
       TASKS/ISSUES/DECISIONS warn-only, betting a session will curate when
       nagged — the same bet the old header lost. The difference: the nag now
       prints in every gate run, and the hard cap eventually refuses.
    3. Archive filename stamps the UTC date (storage convention), which on an
       ET evening names "tomorrow" — cosmetic, consistent with storage-is-UTC,
       noted so nobody files it as a T111 regression.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS
    aligned: Keeps project memory human-readable and bounded across parallel agent sessions without losing history (D031).
    checked: Ran `python scripts/archive_memory.py --check` (caught soft warn on TASKS.md 927 lines), `pytest backend/tests/test_archive_memory.py` (4 passed), full `verify.py` (873 passed, memory budgets step green), confirmed 142 entries moved with provenance to archive/.
    concerns: 1. TASKS.md is soft-warning at 927 lines; needs deliberate curation session to archive completed Phase 1/2 blocks. 2. Archive filenames use UTC date, naming "tomorrow" on ET evenings (consistent with storage-is-UTC).
- Older double-signed DONE blocks (T111, T023 v1, T091b-rest, T077b, T109,
  T108b, T108, T104, T107, T103) moved verbatim to
  project-memory/archive/TASKS-archive-2026-08-18.md (curation 2026-08-18).

**Parallel-work quick rules** (full protocol in AGENTS.md → "Parallel work";
brief to paste: docs/agent-briefs.md). Agents build DIFFERENT tickets at the
same time and review each other:
1. REVIEW FIRST — clear anything in "Awaiting review" from the other agent
   before claiming your own next ticket.
2. CLAIM — put `In progress — <ticket> — <agent>` here and commit that line
   alone before coding; pick files the other agent is NOT in.
3. COMMIT BY PATH — one shared working directory: `git add -A` sweeps up the
   other agent's unfinished work. Never use it while another agent is active.
4. HAND OFF — mark `AWAITING REVIEW — <agent>`; only the OTHER agent writes
   DONE, with a signed `REVIEWED <date> by <agent> — PASS/BLOCK` block.
Shared-file hazards: the three tool-count guard tests, PROGRESS/TASKS/DECISIONS
(append your own lines only), the single alembic head, apps/web/orb.html.

## Backlog — Owner actions (Chotu — nothing else is blocked on these yet, but T005/T006 gate Phase 1 completion)
- [x] T099 — Give KUBERA its private voice — done 2026-08-16 (owner): installed `kokoro-onnx` and placed `kokoro-v1.0.onnx` + `voices-v1.0.bin` into `models/kokoro/`. Server and CLI speak locally with zero cloud leakage per D024.
- [x] T005 — GitHub repo created + remote added + main pushed (2026-08-16, owner). CI workflow active on GitHub Actions.
  NOTE: "pushed" and "CI green" are different things. CI is active and FAILING —
  the verify job exits 1 on runs #4 and #7. Tracked as I018.
- [x] T006 — Alpaca paper keys in `.env` — done 2026-08-11 (owner). Note: owner's `.env` uses `ALPACA_API_KEY` naming + extra vars from another template; settings loader accepts both spellings, extras ignored.
- [ ] T007 — **Phase 1 sign-off, nearly done:** verify.py passed on Windows 68/68 incl. the 3 live paper tests (per Gemini's 2026-08-11 session ✔). Remaining: `alembic -c backend\alembic.ini upgrade head` + `python scripts\sync.py` + open `http://127.0.0.1:8000/portfolio` once.
- [x] T008 — pre-commit installed — done 2026-08-11 (owner). Sandbox-side caveat: I003.

## Regime intelligence pack — ✅ COMPLETE 2026-08-13 (T050–T056 + T075 all shipped; doctrine: docs/research/regime-trading-notes.md)
- [ ] (future, logged) Options awareness: theta/IV warnings in low-vol regimes live in the doctrine; full options analytics is a separate future phase — do not build ad hoc.

## Backlog — Owner suggestion batch 2026-08-13 (docs/research/owner-suggestions-2026-08-13.md — read dispositions first; D016)
- [x] T076 — Event-risk guard (CPI/NFP half) — DONE 2026-08-14 (Claude/Cowork):
  `analysis/events.py` (pure calendar-day math: upcoming_events horizon list +
  entry_guard window reasons, fixed-date hand tests incl. window-0 semantics);
  `data/fred.py` release_dates via /fred/release/dates with
  include_release_dates_with_no_data (scheduled FUTURE dates; CPI=10,
  Employment Situation=50; actionable 400 errors); paper loop gains
  event_dates/event_window_days — a first-class T055 no-trade reason for BUYS
  only ("event window: CPI release … — new entries paused"); paper_trade.py
  arms the guard at startup when FRED_API_KEY exists (--event-window,
  --no-event-guard); get_macro_context surfaces upcoming_releases with a
  degrade-to-note on calendar failure.
- [ ] T076b — Event guard follow-ups: FOMC meeting dates (NOT a FRED release —
  needs a source decision: annual Fed schedule table vs scraping, owner input
  welcome); earnings dates for held symbols (dep T023 tier answer);
  sell-the-news "priced-for-perfection" flag (pre-event runup + rich
  expected-move pricing, D019) in guard reasons and briefings.
- [x] T077b — Expected-move v2 — DONE 2026-08-17 (REVIEWED PASS; record in
  archive/TASKS-archive-2026-08-18.md).
- [x] T079 — Correlation & overlap guard — DONE 2026-08-14 (Claude/Cowork):
  `analysis/correlation.py` (pearson/beta/log_returns pure + hand-tested: y=2x→1.0,
  hand-zero vector case, beta=2 doubling; overlap_report with aligned trailing
  windows, MIN_OVERLAP=20 refuse-don't-guess, HIGH_CORR=0.80 pair flags,
  candidate "adds exposure, not diversification" warning, portfolio beta from
  position weights w/ coverage warning). Tool `get_correlation` (#27, guard
  tests bumped in all three files) + `GET /api/correlation?candidate=&days=`.
  Persona-facing description orders the model to run it BEFORE recommending
  buys. T093 extends this (marginal risk contribution, effective bets).
- [x] T082a — Conversations index (the sidebar's BACKEND) — DONE 2026-08-14
  (Claude/Cowork): `data/conversations.py` list_conversations — ordered by LAST
  ACTIVITY not creation (a revived old thread belongs on top, proven in test),
  snippet taken from the owner's FIRST USER message with whitespace collapsed
  and 90-char ellipsis (never a system prompt or tool payload), turn count and
  tool-call count split so a thread shows how much evidence it pulled; empty
  conversations skipped. `GET /api/conversations?limit=` (1..200). 7 tests.
- [x] T082 — Orb upgrade pack FRONTEND — DONE 2026-08-16 (Gemini/Antigravity):
  `apps/web/orb.html` gains three additive panels with zero changes to the voice
  loop, canvas renderer, or send logic. (a) **Conversations sidebar** (left,
  `☰` toggle, collapsed-by-default): fetches `GET /api/conversations?limit=50`
  on load and after every `send()`; lists threads newest-activity-first with
  snippet + "N turns · M calls" meta; click any row calls `resumeConversation(id)`
  which sets `S.conversationId` and highlights the row; `+ new` clears the id.
  (b) **Portfolio snapshot panel** (right, `▣` toggle, collapsed-by-default):
  fetches `GET /portfolio` on open and polls every 60 s while visible; shows
  equity, day P&L colour-coded green/red, top-3 positions by market value;
  degrades to "broker offline" on 502/503. (c) **Freshness chip colours** (T082c /
  T036b): `get_latest`, `get_symbol_briefing`, `get_intraday` chips get a
  colour-coded border via a time-of-day heuristic (RTH 09:30–16:00 ET → teal
  live; outside → gold last_session). Layout uses a three-column flex shell;
  panel widths animate via CSS `transition: width`. No CDN dependencies added.
  HTML structural assertions: 25 IDs checked, all JS functions verified present.
  Verify: pytest gate requires owner's venv — run `.venv\Scripts\pytest -q`
  to confirm 615 passed, 3 skipped (frontend-only; existing tests unaffected).
- [ ] T081 — Pairs / stat-arb strategy template (D017): cointegration screen on log closes (Engle–Granger: OLS hedge ratio + ADF on residual spread, hand-computed tests on synthetic cointegrated series), spread z-score mean-reversion template on the T030 engine contract; runs the T064 walk-forward promotion gate like every template. ⛔ BLOCKED (D021, owner decided 2026-08-13): DEFERRED ~30 days — long-only stands until paper DQS history proves discipline; revisit on evidence ≈2026-09-12 (DQS trend, override rate, tier trips).
- [ ] T094 — HRP portfolio allocation (D021, gated): hierarchical risk parity (correlation-distance clustering + recursive bisection — deterministic, testable, no matrix inversion) sizing the whole book jointly. TRIGGER written down: build only when the book regularly holds enough positions that optimization beats common sense; T093's measurement half ships first.
- [ ] T095 — Factor loadings (D021): OLS regression of portfolio returns on Ken French factor series (free daily CSVs — market/size/value/momentum) → "is this alpha, leveraged beta, or an accidental size tilt"; dep: ~60+ daily snapshot returns. Beta-only version arrives earlier with T093.

## Backlog — Adopted from ChatGPT master-spec review (docs/research/chatgpt-master-spec-review.md)
- [x] T060 — Time-weighted returns — DONE 2026-08-14 (Claude/Cowork), built
  BEFORE the first deposit so the number is right the day it matters:
  `analysis/twr.py` — chain-linked sub-periods across external flows
  (convention documented: a flow dated D applies at the START of D), hand-
  tested on the headline case (1000→1100, +500 deposit, end 1760 → simple
  +76% is a lie, TWR +21% is the truth) plus the withdrawal mirror, flows
  outside the window, and a flow on the opening date (not double-counted).
  `cash_flows` table (migration 69a772af165c) + AlpacaClient.get_cash_activities
  (CSD/CSW, signs normalized) + data/flows.py sync (deduped like fills, wired
  into scripts/sync.py, never fatal). compare_benchmark now returns a
  time_weighted block with excess_vs_benchmark computed from TWR and a note
  telling the model to quote TWR, not the simple figure, once flows exist.
  Bug caught by the tz guard en route: date-only broker fields parse naive —
  normalized to UTC in the client.
- [~] T062b — Brief upgrades: watchlist setups (T068) + event risk (T076) DONE
  2026-08-14 (Claude/Cowork) — morning brief gains `watchlist` (top-3 ranked
  setups with the owner's thesis notes; empty list said plainly) and
  `event_risk` (upcoming CPI/NFP dates; no FRED key or calendar failure
  degrades to a note, core brief still delivers; fred is an OPTIONAL ToolContext
  member for get_brief, /api/brief constructs it best-effort). PENDING_NOTES
  trimmed to the earnings-dates gap (T023/T076b). REMAINING in this ticket:
  PWA push delivery (Phase 5), ET-aware "today" windows (T036b), scheduled
  auto-generation (Task Scheduler hitting /api/brief + TTS).
- [ ] T063b — Journal calibration v2 (after entries accumulate): confidence-vs-outcome calibration curves (was "0.7 confidence" right 70% of the time?), payoff-weighted scoring vs the stated target/stop, override-rate × outcome analysis feeding T067b, weekly-review integration. Any strategy-weight change remains a PROPOSAL the owner ratifies (human-gated).
- [~] T064b — Rigor follow-ups, core DONE 2026-08-14 (Claude/Cowork):
  run_backtest tool output now carries `trades` (full TradeStats), `calmar`,
  and a `promotion` block (is_promoted + latest T092 stability verdict via new
  ledger.latest_stability + the expiry/sweep pointers in a note). PROMOTION
  EXPIRY: is_promoted takes max_age_days (default 180, PROMOTION_MAX_AGE_DAYS)
  — a stale pass silently stops counting, the loop's gate refuses until
  re-promoted (backdated-row test proves it; naive-ts safe). REMAINING:
  crisis-window stress runs (2020/2022 where IEX reaches; 2008 impossible on
  this feed — say so), promote-via-chat (needs the deliberate-act confirmation
  design; parked intentionally, CLI stays the promotion instrument).
- [ ] T065 — Risk engine v2: sector-exposure caps (needs sector data from T023), cancel-all + disable-symbol controls, order-frequency limit (merge with T055 overtrading guard).

## Backlog — Trading coach pack (Gemini spec, D014; doctrine: docs/research/gemini-master-spec-review.md)
- [ ] T066 — Trade coaching: pre-trade review (thesis, sizing, concentration, correlation, regime fit, IPS compliance) + post-trade review (expected vs actual, entry/exit quality, rule adherence, lesson) persisted per trade; PROCESS-not-outcome scoring. T016 dependency SATISFIED 2026-08-17 (live sync reconciled) — real fills available; chat-level v0 works today via conversation.
- [x] T016c — built 2026-08-18, see Awaiting review at top. (Note: dedupe
  against the STATEMENT-parsed history by fill-signature was deferred to T016b
  — the DB and the file-based stack are separate stores today, and T016b's
  API-vs-parsed diff is the designed reconciliation between them.)
- [x] T067b — built 2026-08-18, see Awaiting review at top. (FOMO-into-late-
  RVOL deliberately NOT built — needs an intraday clock on every fill; named
  in every report and re-filed as T067c below.)
- [ ] T067c — FOMO-into-late-RVOL-spike detection (split out of T067b): flag
  entries made into a late-session volume spike. Needs BOTH an intraday
  timestamp per fill (the T016c Schwab sync now records execution times — let
  them accumulate) and that day's intraday volume profile (T052 provides it).
  Build only when real time-stamped fills exist to test against; approximating
  from date-only statement rows is exactly the guesswork T102 forbids.
- [x] T068 — Watchlist + opportunity ranking — DONE 2026-08-14 (Claude/Cowork):
  `watchlist` table (migration 620eeac1a7c9) + data/watchlist.py (idempotent
  add updates note); `analysis/ranking.py` — cross-sectional scoring per D020:
  1/3/6-month (21/63/126-bar) relative-strength PERCENTILES within the list
  (tie-aware ranks, hand-tested), regime-fit mapping (trending_up 1.0 …
  trending_down 0.0, documented heuristic), 5-session payoff context, composite
  0.5/0.3/0.2, top/bottom decile flags (N≥10) else top/bottom; short history =
  listed-not-scored, never guessed. Tools #30/#31 update_watchlist (case-
  normalized add/remove) + get_watchlist (empty list → friendly offer, not an
  error; owner's thesis note rides along) + GET/POST/DELETE /api/watchlist.
  Cross-sectional momentum TEMPLATE (long top decile) remains future work
  behind the T064 gate; short half still awaits the D021 revisit.
- [ ] T074 — Realtime conversation pipeline (the Zoey-latency upgrade): streaming STT + start-TTS-before-reply-completes + barge-in (interrupt while speaking), via LiveKit Agents / Pipecat or OpenAI Realtime API with our registry as functions; target sub-second first-audio; verify current framework landscape + costs at build time. The Orb (T073) is the UI shell this plugs into.
- [x] T072 — Human-grade TTS backends — DONE 2026-08-16 (Gemini/Antigravity; reviewed PASS by Claude/Cowork after one BLOCK round, fd1c10c + 483c522):
  `scripts/talk.py` `make_speaker()` now supports `KUBERA_TTS=openai` (OpenAI TTS API
  `tts-1` / `tts-1-hd` with voice choice via `KUBERA_VOICE`, default `alloy`, `OPENAI_API_KEY`
  required) and `KUBERA_TTS=kokoro` (local near-human via `kokoro-onnx` using `models/kokoro/`
  or `KUBERA_KOKORO_DIR`, default voice `af_heart`). Both fail fast with actionable install / download
  instructions if packages or model weights are missing; playback errors are caught and printed so
  the voice loop never crashes. Voice ladder documented in module docstring, `requirements-voice.txt`,
  and `README.md`. 8 tests in `backend/tests/test_tts_backends.py` (mocked, no hardware or network
  required; CI-safe via `pytest.importorskip` on BOTH numpy and soundfile — the numpy half was
  the BLOCK, see I016). Per D024 kokoro is the RECOMMENDED rung and every rung now states
  whether reply text leaves the machine. Carried forward as small follow-ups (T072b): the
  silent `except Exception` around the api.tts_engine import resolves `~` differently from the
  engine, module-level soundfile skip hides six audio-free tests from CI, and the docstring
  still says `pip install kokoro-onnx soundfile`.
- [x] T101 — Make the last 6 pyrefly errors expressible rather than tolerated — DONE 2026-08-16 (Gemini/Antigravity, REVIEWED 2026-08-16 by Claude/Cowork — PASS):
  `CorrelationMatch` TypedDict in `backend/analysis/correlation.py`; narrowed `pcts` list comprehension in `backend/analysis/ranking.py`; `RegimeRouterStrategy` callable class with `last_leg` attribute in `backend/backtest/strategies.py`; non-None assertion on `s.fred_api_key` in `backend/data/fred.py`. Updated `pyrefly.toml` to 0 remaining known errors. Gate PASS (743 passed).
- [x] T100 — Honor `LLM_TIMEOUT_SECONDS` in the claude-sdk provider (I017) — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini — PASS):
  `backend/api/llm_claude_sdk.py` (wrapped query stream in `asyncio.wait_for(timeout=self.timeout)`; raises actionable `LLMError` citing `LLM_TIMEOUT_SECONDS` on timeout, cleanly discarding partial stream text to avoid unvalidated partial answers), `backend/tests/test_claude_sdk.py` (3 tests). Gate PASS (731 passed).
- [x] T045b — Owner: MCP acceptance run — DONE 2026-08-16 (owner):
  Ran `python scripts/install_mcp_config.py`; verified `%APPDATA%\Claude\claude_desktop_config.json` is configured with `.venv` Python interpreter and `scripts/mcp_server.py` stdio entrypoint.
- [x] T108 — expiry-aware FIFO closing — DONE 2026-08-17 (Claude/Cowork, REVIEWED 2026-08-17 by Gemini/Antigravity — PASS):
  `backend/analysis/autopsy.py` (match_fifo_trips/analyze_autopsy gain `asof`; unsold option lots past expiry close at exit 0 flagged `closed_by="expiry_assumed"`; PerformanceSummary gains expiry_assumed_count/pnl; narrative + caveats incl. the 100%-win-rate BUG SIGNAL), `backend/analysis/pattern_warning.py` (asof threaded; assumed-trip caveat), `backend/analysis/expiry_reconcile.py` (parses Expired/Assigned/Exercised rows from monthly statements, joins per contract), `scripts/reconcile_expiry.py` (CLI), `backend/data/statements.py` (pypdf layout-mode extraction w/ version fallback — I027; monthly-statement refusal; wrapped-option-leg fallback that fails CLOSED; daily-document dedupe — I028), `scripts/autopsy.py`, tests (test_autopsy +9, test_statements +8, test_expiry_reconcile +12). Gate PASS (823 passed, 0 lint errors).
- [x] T108b — Statement-transaction importer — DONE 2026-08-17 (Gemini/Antigravity,
  reviewed BLOCK→PASS by Claude/Cowork; full record in "Awaiting review" section above).
  Reconciliation 13/13 clean; the honest full-history record is now 131 fills, 80 trips,
  -$7,998.86 realized, 53.8% win rate (options -$11,706 / equities +$3,707).
- [x] T109 — Pre-registered selection rule + cost stress — DONE 2026-08-17
  (REVIEWED PASS; record in archive/TASKS-archive-2026-08-18.md).
- [ ] T110 — Phase 7 preconditions: evidence custody for the learning loop
  (D029, GATED — design exists, build when Phase 7 opens): reserved holdout
  window with code-enforced custody outside agent reach (freeze-then-unlock,
  ONE evaluation, no revision after the result is known); per-revision
  experiment budget, failures included, recorded append-only; agent-written
  strategy code runs only in an isolation boundary that has passed BOTH an
  execution-parity test (isolated vs in-process identical numbers) AND an
  adversarial probe (a strategy that tries to read credentials/holdout and
  must come back empty). Phase 7 does not start without this ticket done.
- [x] Owner (Chotu): June + July statements delivered 2026-08-17 — 735P x3 CONFIRMED
  exact (my "x12" was a stale pre-dedupe number; corrected), July verified as a
  no-trading month. Keep dropping each new monthly statement in as it posts.
  The missing-confirmation gaps (692P x8, 660P x8, 733P x35, NVDA 182.5P x2) wait
  for T108b — no need to hunt individual PDFs.
- [x] T107 — Base URLs into settings — DONE (Gemini built; Claude re-reviewed
  PASS 2026-08-17 at 516dca5). The two deliberate hardcodes stand with comments:
  Alpaca PAPER base URL (safety rail) and the option multiplier 100 (market
  fact). Full record in archive/TASKS-archive-2026-08-18.md.
- [x] T106 — MCP context lifecycle — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini/Antigravity — PASS):
  chose close-per-call over build-once — a shared client would serve stale sessions and
  a shared DB session would grow unbounded; the leak was the missing close, not the
  per-call build. managed_tool_context guarantees close on success AND exception paths;
  close failures are logged, never raised. Leak proven by counting fakes: 5 calls =
  15 opened / 0 closed before, 15/15 after.
  REVIEW VERDICT: PASS. Verified implementation and all 13 tests: (a) Close order safely addresses resources; (b) Duck typing with getattr(close) gracefully handles None and non-closable test fakes without raising; (c) Logging rather than raising close errors preserves primary tool execution results/exceptions; (d) Per-call context factory correctly matches MCP request boundary semantics.
- [ ] T071 — Owner: voice acceptance run — `pip install -r requirements-voice.txt`, server up, `python scripts\talk.py`, hold a conversation. If faster-whisper wheels fail on Python 3.14 → `set KUBERA_STT=openai`. Report quirks to ISSUES.
- [x] T069 — Adaptive risk-tolerance estimation — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini — PASS):
  `analysis/risk_tolerance.py` measures four things from real data — deepest drawdown actually lived through (flow-adjusted, so a deposit cannot fake resilience and a withdrawal cannot fake a loss), sizing drift after losses (the revenge tell), post-loss trade frequency (the tilt tell, with overlapping reaction windows merged so time is not double-counted), and cash buffer. Emits a PROPOSED daily-loss / per-trade / position budget with per-component evidence and sample sizes, hard-clamped to BANDS. Every component returns None rather than a plausible number when under-sampled, and confidence 'insufficient' proposes NO change. Registry tool #34 `estimate_risk_tolerance`. Nothing is auto-applied — the owner ratifies via update_ips; enforcement stays in /backend/risk.
  REVIEW VERDICT: PASS. Verified all 4 review focus points: (a) compounding multiplier chain (0.75 * 0.80 * 0.85) mathematically reflects correlated compounding behavioral risk and is safely bounded by BANDS; (b) capping daily budget at experienced_drawdown/3 safely preserves capital within empirical tolerance limits; (c) +15% earned risk nudge requires strict dual-behavioral discipline and full drawdown recovery, and is proposal-only; (d) MIN thresholds (3 paired observations, 8 trips, 20 days) prevent noisy signals while remaining actionable for personal swing trading. All 21 tests pass, tool counts synced.

## Backlog — Phase 2: Analysis & insight engine (agents)
- [x] T023 — Fundamentals + news ingestion — DONE via D030 (owner's probe
  decided sources) + T023 v1 2026-08-17 (REVIEWED PASS): FmpClient,
  get_earnings_calendar (#37), morning-brief earnings_risk. News stays Alpaca;
  transcripts/estimates OUT (paywalled). Full record in
  archive/TASKS-archive-2026-08-18.md. Follow-up split out:
- [x] T023b — built 2026-08-18, see Awaiting review at top.
- [x] T096 — Per-brain tool subsetting — DONE 2026-08-14 (Claude/Cowork):
  `api/tool_policy.py` — CORE_TOOLS (11: portfolio, briefing, latest, regime,
  exit plan, triage, size, brief, risk, record_decision, ips), is_small_brain
  (openai wire format + non-openai base_url = local runtime), tool_names_for /
  filter_schemas. Wired into run_chat_turn AND the persona's advertised list
  (the prompt now names exactly what's offered — a persona listing uncallable
  tools is how "capability missing" + phantom names are born, I008/I011) and
  into claude-sdk allowed_tools (bridge stays full; permission is the knob).
  `KUBERA_TOOL_PROFILE=auto|full|core` overrides either way; unknown values
  degrade to auto rather than killing a session. Guard test asserts CORE ⊆
  registry so a rename can't silently shrink a small brain. 11 tests.
- [x] T088 — Execution quality — DONE 2026-08-14 (Claude/Cowork):
  `signal_log.decision_price` (migration 00c4e1efd5c4) records the price each
  decision was made on; the loop fills it on every row. `analysis/execution.py`
  — slippage_bps with a SIDE-AWARE convention (positive ALWAYS = cost, both
  sides; hand-tested 4 ways), implementation shortfall in dollars, grouping by
  T091 entry bucket and side, MIN_BUCKET_SAMPLE=5 marking thin buckets as
  "anecdotes, not evidence". Tool #32 get_execution_quality joins
  signal_log.order_external_id ↔ transactions.order_id + GET
  /api/execution-quality; unmatched orders are counted and named (fills arrive
  after execution — run sync.py). Empty state is a calm answer, not an error.
  ⇒ "never buy the open print" becomes measurable from the owner's own fills
  once enough accumulate.
- [x] T089 — Live MAE/MFE — DONE 2026-08-16 (Claude/Cowork):
  `analysis/excursions_live.py` — per OPEN position: MAE (worst move against
  since entry, from daily LOWS), MFE (best, from HIGHS), current, GIVE-BACK
  (share of the run-up surrendered — the number behind "it was up 8% and I
  watched it round-trip"), and heat-used vs a 2xATR stop (capped at 1.0 =
  "another move against you triggers the exit"). Hand-tested headline case
  (entry 100, low 94, high 112, close 103 → −6% / +12% / 75% given back) plus
  corrupt-data and stop-above-entry rejection. Tool #33 get_open_excursions +
  GET /api/excursions; book-level worst_mae and biggest_give_back. Honest
  limits in EVERY payload: daily H/L (intraday spikes invisible) and the
  broker's AVERAGE entry as basis. Remaining from the original ticket: the
  winners'-MAE stop-calibration line in the T062 weekly review — needs closed
  trades to accumulate first (T063b/T091b territory).
- [x] T090 — Liquidity-aware costs — DONE 2026-08-14 (Claude/Cowork):
  `analysis/liquidity.py` (spread_bps, half-spread per-side cost with 0.5bps
  floor, ADV over trailing 20 sessions, 1%-participation cap — all hand-tested:
  99.90/100.10 → 20bps/10bps, 1M ADV → 10k-share cap). ADV cap now BINDS inside
  size_position (binding="adv_cap", IEX-understates note in every payload;
  shared BARS_JSON fixture given realistic uniform volume — RVOL-invariant).
  Tool `get_liquidity` (#28, guard bumps ×3; refuses one-sided quotes: "spread
  math would be fiction") + `GET /api/liquidity/{symbol}`. Remaining half
  parked in T091b/T062b: spread-aware cost line in briefings + paper-loop
  per-symbol cost_bps replacing the flat assumption (needs a quote fetch in
  the loop path — separate decision).
- [x] T091b — Attribution follow-ups. HOLDING-PERIOD HALF DONE 2026-08-16
  (Claude/Cowork): FIFO lots now carry their entry timestamp, so every round
  trip records held_days; `holding_period_distribution` reports count / win rate
  / realized P&L per bucket (intraday, 1-3d, 1-2wk, 2wk-1mo, over_1mo) plus
  median, mean, shortest, longest. Rides the existing `get_attribution` payload
  — no new tool, no guard-test collision. Undated lots land in "unknown" rather
  than being dropped; exit-before-entry and unparseable timestamps return None
  instead of a negative duration.
  REVIEWED 2026-08-16 by Gemini/Antigravity — PASS
    aligned: Tracks actual trade holding periods to detect style drift and early-cutting habits.
    checked: Half-open interval boundary edge cases [lo, hi), FIFO partial-sell multi-slice accounting, clock corruptions/undated lot handling in unknown bucket, get_attribution tool doc update, verify.py combined tree (663 passed).
    concerns: none
  REMAINING halves DONE 2026-08-17 as T091b-rest (REVIEWED PASS; record in
  archive/TASKS-archive-2026-08-18.md). Ticket fully closed.
- [x] T092 — Parameter stability sweeps — DONE 2026-08-14 (Claude/Cowork):
  `backtest/stability.py` — SWEEPS map (momentum lookback 20–90, sma_cross fast,
  mean_reversion window, range lookback), pure `stability_report` verdicts
  (insufficient / reject / curve_fit / stable; plateau = ≥50% of other points
  hold ≥50% of best Sharpe AND median > 0 — all hand-tested incl. the exact-
  boundary case), engine-only `run_sweep` (no ledger spam; never-invested
  params score 0 with warning). `stability_json` on backtest_runs (migration
  8d2d7f6c98b8) via `ledger.attach_stability` (lands on the template's latest
  run, loud failure otherwise). CLI `scripts/sweep.py momentum SPY [--record]`.
  Follow-up parked in T064b: surface stability verdict in run_backtest tool
  output + block promotion on curve_fit (needs owner sign-off on strictness).
- [x] T093 (parts 1+3) — Portfolio risk + CUSUM demotion — DONE 2026-08-14
  (Claude/Cowork): `analysis/portfolio_risk.py` (σ_p = √(w'Cw) hand-tested at
  ρ=1/0/−1, Euler contributions summing exactly to σ_p, effective bets 1/Σw²,
  diversification ratio, ≥60%-one-name warning) → tool #29 get_portfolio_risk
  + GET /api/portfolio-risk (thin-history holdings excluded with coverage
  warning). `backtest/decay.py`: expected_daily_return from the promoted run,
  one-sided CUSUM shortfall (hand-tested crossing day incl. an fp-boundary
  lesson), `demote()` flips passed→demoted so the loop's require_promotion
  refuses automatically (promote→demote→refused proven in test);
  `scripts/decay_check.py [--demote]` with the ACCOUNT-PROXY limitation
  printed every run.
- [x] T093b — Snapshot-vs-broker reconciliation — DONE 2026-08-14 (Claude/
  Cowork): health_check gains check_reconciliation — latest account_snapshot
  equity vs live /api/account, warns above 0.5% drift with the snapshot's age
  and the remedy named ("run sync.py; drift that SURVIVES a fresh sync is not
  normal"). Owns exactly ONE failure mode (both sides reachable, disagreeing);
  stays quiet when server-down/no-snapshot — those belong to the existing
  checks. Wired into run_checks → the owner's every-5-min scheduled task and
  --notify toast get it for free. 3 tests (drift/quiet/cannot-judge).
- [ ] T087 — Open-trade monitor (owner Q&A; deps T074/T082/T036): watch held positions during RTH — alert when session RVOL collapses under a breakout thesis, VWAP churn rises, exit-plan invalidation approaches/hits, or the event guard window opens; Windows toast + Orb surface v1, voice barge-in with T074. Advisory only — execution stays in the loop's rails.
- [ ] (advisory note for T077b/T085) Fractional-Kelly sizing VIEW from T077 win-rate/payoff — advisory-only, capped, never autopilot; single-trade "probability of profit" remains rejected per D017.
- [ ] T083 — Event reaction base rates (D019, dep T023 dates): for each historical earnings date, compute from our daily bars the event-day + next-day moves split by beat/miss, and the pre-event runup into each; surface in briefings/chat as BASE RATES ("6 of the last 8 beats still closed down") — the evidence-based answer to "should I hold through earnings", no prediction claimed. Deterministic, hand-computed tests.
- [ ] T084 — Transcripts & filings as labeled CONTEXT (D019; gated on T023 tier check): fetch earnings-call transcripts, summarize via the EXISTING LLM layer (tone/guidance as narration of a document, clearly labeled qualitative context — never a priced signal); 10-K/10-Q YoY textual-change ("Lazy Prices") recorded as a Phase 7 research-agent candidate via SEC EDGAR through §7.7, human-gated. No FinBERT now.
- [x] T016a — Schwab read-only client + transaction mapping — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini — PASS):
  `backend/data/schwab.py` (OAuth token refresh, masked accounts, raw transaction queries, ImportReport with honest unmapped row logging), `backend/settings.py` (schwab_* settings and require_schwab), `.env.example`, `scripts/schwab_auth.py`, `scripts/reconcile_schwab.py`, `scripts/env_check.py`, and `backend/tests/test_schwab.py` (19 unit tests).
  REVIEW VERDICT: PASS. (a) `_equity_leg` safely isolates priced symbol legs from fee/currency legs; (b) `map_transactions` properly preserves execution prices and maps cash movements with signed amounts; (c) `_utc` cleanly parses standard ISO and legacy `+0000` formats; (d) read-only constraint verified via `dir(SchwabClient)` having zero order methods. Gate PASS (728 passed).
  LIVE ACCEPTANCE 2026-08-17 — REOPENED THE SAME DAY BY THE OWNER'S OWN
  TICK-OFF (I029), which is the reconciliation working exactly as designed:
  his March review caught (1) imported dates not matching when he actually
  traded (source-field problem — posting/settle time where execution time
  belongs; the settle-vs-trade class for the THIRD time: T102 statements,
  T108b importer, now the API) and (2) expirations presented as sales when
  his real proceeds were $0 (target state: expiry events at price 0 flagged
  closed_by="expiry_observed", feeding T108 as observation, never a sale).
  **T016 CLOSED 2026-08-17 (second close — the real one).** The full acceptance
  cycle, recorded because it is the model for every future data source:
  (1) owner reconciled March and CAUGHT discrepancies (I029) — my premature
  first "closed" retracted; (2) his probe delivered OBSERVED rows that
  corrected both of my hypotheses; (3) fixes landed against those rows only:
  mapper prefers `time` over the sometimes-placeholder `tradeDate` (regression
  test from observed row ...468374), reconcile prints EASTERN labeled, an
  EXPECTED EXPIRATIONS section lists never-sold lots at $0 (the API emits no
  row for them), and a BY ORDER section reproduces the statement's own
  settle-dated per-order granularity (his 71+29=100 @ 0.21 -> $2,033.48 tied
  to the penny); (4) owner RE-RAN and confirmed: "it does read like my
  statement." That confirmation, after fixes he forced, is the acceptance.
  The Schwab read-only sync is now trusted end-to-end. Unblocked: T016c
  (daily sync — persist the per-trade fees the probe revealed), T016b
  (automated diff under his final word), T066 (coaching on real fills).
- [x] T016b — built 2026-08-18, see Awaiting review at top.
- [x] T102 — Statement PDF ingest — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini/Antigravity — PASS):
  `backend/data/statements.py` parses Schwab confirmations (header trade date, settle date parsing with year boundary rollover, option leg extraction with contract multiplier, continuation window bounded by next row start); `backend/tests/test_statements.py` (12 tests); PII-redacted fixtures in `backend/tests/fixtures/schwab/` with regex identity audit test. Parses 250 fills from 86 real confirmations (147 options, 103 equity). Uncovered I020 (59% options, 62% 0DTE), unblocking T105 and pausing T103 until options land.
  REVIEW VERDICT: PASS. Verified all 4 review focus points: (a) positional row regex properly captures fields with tabular spacing and records unparsed failures without data loss; (b) `redact()` thoroughly sanitizes PII (accounts, addresses, long digits) and `test_committed_fixtures_contain_no_identity` guards fixtures; (c) header trade date extraction avoids 1-2 day settle date shift corruption; (d) agreed T103 must wait for T105 option modeling. Gate PASS (743 passed).
- [x] T105 — Options in the import and the analysis (I020) — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini/Antigravity — PASS):
  `backend/data/schwab.py` (`_security_leg` maps OPTION legs, uses `underlyingSymbol`, filters CURRENCY/FEE, assigns `fill_type="option"`), `backend/analysis/attribution.py` (`HOLD_BUCKETS` sub-day splits: minutes [<1h], hours [1-6.5h], same_day [6.5-24h]; `contract_multiplier` helper), and 5 unit tests in `test_schwab.py` + `test_holding_periods.py`. Unblocks T103.
  REVIEW VERDICT: PASS. (a) 1h / 6.5h session / same_day holding period cuts cleanly distinguish fast scalps from full-session holds without timezone math; (b) agreed that applying contract multiplier to `fifo_attribution` realized P&L belongs in a focused dedicated ticket; (c) filtering CURRENCY and FEE legs while extracting any security leg with symbol+price+amount is safe and complete across all Schwab asset types. Gate PASS (758 passed).
- [x] T103 — The trading autopsy (D026) — DONE 2026-08-16 (Gemini/Antigravity, REVIEWED 2026-08-16 by Claude/Cowork — PASS):
  `backend/analysis/autopsy.py` (TradingAutopsyReport: options vs equities, 0DTE share, FIFO round trips with 100x option contract multiplier and strike separation, sub-day holding period splits, honest unrecorded intraday duration handling for confirmations, T069 revenge sizing drift and tilt tempo detection strictly segregated within asset classes, per-symbol breakdown, honest deterministic narrative with N); `backend/api/tools.py` (`get_trading_autopsy` tool #35); `backend/api/main.py` (`GET /api/autopsy`); `backend/api/mcp_server.py` (`get_trading_autopsy` exposed in `_READ_ONLY_TOOLS`); `scripts/autopsy.py` CLI; `backend/tests/test_autopsy.py` (8 unit tests).
- [x] T104 — Pre-trade pattern warnings — DONE (Gemini built; Claude reviewed
  PASS 2026-08-16, key-drop fix re-verified 2026-08-17 at 516dca5; I026 caveat
  LIFTED by T108). Full record in archive/TASKS-archive-2026-08-18.md. This
  stale duplicate checkbox misled two sessions' "next" pointers — fixed by the
  2026-08-18 curation.
- [x] T036b — Session-aware staleness — DONE 2026-08-14 (Claude/Cowork):
  `analysis/staleness.py` — four states replacing the binary flag: live /
  stale (market OPEN but feed behind = the real hazard, untrustworthy) /
  last_session (market closed, most recent real print — TRUSTWORTHY, the
  Friday-quote-on-Saturday fix) / old (beyond a normal closure = check the
  feed), each with a narration-ready phrase; hand-tested incl. the 96h
  boundary and tz/future-timestamp validation. get_latest now consults the
  BROKER clock (ctx.alpaca optional — absent falls back to the conservative
  wall-clock rule labeled "market state unknown") and returns freshness +
  session (next open/close + "the market opens in 14h" hint). Raw stale flag
  and legacy payload preserved. /api/market/{symbol}/latest routes through
  the tool so the API and chat agree.

## Backlog — Phase 4: Conversation layer (agents; unblocked — §3 registry is done)
- [x] T047 — Owner activated claude-sdk: live /api/chat turn on the Max subscription verified 2026-08-12 02:22 UTC — KUBERA corrected the question's premise (holds SPY, not AAPL), full case-for/against, falsifiable risk level, persona disclaimers intact. Side-channel audit captured both tool calls. Quirk found+fixed: SDK usage is a dict (was parsed as object → 0/0).
- [x] T045 — KUBERA MCP server (D011) — DONE 2026-08-16 (Gemini/Antigravity, REVIEWED 2026-08-16 by Claude/Cowork — PASS):
  `backend/api/mcp_server.py` (FastMCP stdio server dynamically exposing all 30 read-only T024 registry tools by default with typed Pydantic signatures, docstrings, and configurable `ToolContext`; confirmation-gated `update_ips` unconditionally excluded; `confirmed=False` defense in depth), `scripts/mcp_server.py` (stdio CLI entrypoint for Claude Desktop / Antigravity), and `backend/tests/test_mcp_server.py` (9 tests). Gate PASS (760 passed).
- [x] T045b — Claude Desktop config installer (`scripts/install_mcp_config.py`) — DONE 2026-08-16 (Claude/Cowork built installer, verified by Gemini; owner executed installer and verified config at `%APPDATA%\Claude\claude_desktop_config.json`):
  Locates `%APPDATA%\Claude\claude_desktop_config.json`, resolves absolute path to venv interpreter, merges without clobbering other MCP servers, backs up existing file, guards against missing `mcp` import before write. Tested via `test_install_mcp_config_merge`.

## Blocked
(none)

## Done
- Full early-phase DONE list (T098 back to T001) moved verbatim to
  project-memory/archive/TASKS-archive-2026-08-18.md (curation 2026-08-18).
