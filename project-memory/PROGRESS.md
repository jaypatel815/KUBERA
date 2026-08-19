# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
Budgets are ENFORCED by the verify gate (T112/D031): archive_memory.py --check
warns at 700 lines and fails at 1,000; `python scripts/archive_memory.py` moves
old entries (verbatim, never deleted) to /project-memory/archive/.

## 2026-08-18 — Claude/Cowork — D034: free tier now, paid at autonomy (owner policy)
Owner clarified the data-source strategy in his own words: free tiers until
KUBERA runs autonomously, then he pays for the paid tiers. Recorded as D034
with the rules it implies — free-first (a paywall never stalls a ticket;
find the free path or accumulate forward), upgrades must be configuration
events with zero code changes (named non-fatal paywall errors are the
mechanism, already the house style), self-accumulated stores survive as
verification sources, and an upgrade-day checklist now lives in the
decision (FMP: past windows backfill T083 + cross-check; Alpaca SIP:
resolves the D006 volume caveat — re-verify RVOL thresholds). Memory-only
session; T083 still awaits Gemini's review at 531ea20.

## 2026-08-18 — Claude/Cowork — T083 delta: probe said PAYWALLED — history now self-accumulates
Owner's probe answered same-session: past FMP calendar windows are PAYWALLED
on his tier (forward answers). Redesigned against the measurement:
earnings_observed table (9d1c5b3fa284) records forward-window dates BEFORE
they happen — three feed paths (base-rates tool, calendar tool, morning
brief), dedupe per (symbol,date), later fetches backfill eps_actual. The
tool reads past events from the store and NEVER makes a paywalled request;
empty store → named error explaining that history builds as quarters pass.
The new store tests exposed a LATENT BUG in the first commit (DailyBar.date
is a string; str-vs-date would have crashed the first real run) — fixed.
T083b filed: SEC EDGAR 8-K dates as fast history, gated on its own probe.
6 new tests + 9 unchanged; migration applies; gate PASS; pyrefly exactly 1.
Gemini's T083 review should target THIS sha (D033).

## 2026-08-18 — Claude/Cowork — T083: event reaction base rates (AWAITING REVIEW)
"Hold through earnings?" answered from the symbol's own bars, as base rates
never predictions. analysis/event_rates.py: amc-moves-the-NEXT-bar timing
convention (missing hints default bmo AND counted), event-day + next-day
moves, 5-bar pre-event runup, beat/miss from eps_actual vs estimate ONLY
(never inferred from price — circular), closed-down counts per split,
MIN_EVENTS=4 refusal, unmeasured events reported. EarningsEvent gains
eps_actual; tool #39 get_event_base_rates (guard bumps x4); fmp_check gains
the PAST-window probe row (the unprobed shape — D030 pattern again). 9
hand-computed tests; gate PASS; pyrefly exactly 1. D028: caught my own
inverted ascending-dates guard before the first test run. Owner: one
fmp_check run decides whether beat/miss lights up on his tier.
Next: Gemini reviews T083 at its sha. Backlog: T063b (data-gated), T076b.

## 2026-08-18 — Gemini/Antigravity — Review completed for T066 (D032/D033 review-only mode at 1f6014c)
Reviewed T066 (Trade coaching: pre/post-trade reviews, persisted) per D027 and D033 evidence requirements:
- Deterministic review composition: verified `backend/analysis/coaching.py` pre-trade 6-section checklist (thesis+invalidation, IPS compliance, concentration warning at 15%, regime fit, T104 pattern history, exit plan) with explicit status categorization (ok, attention, missing with supplier tool named), and post-trade adherence review against T063 decision journal rows (horizon adherence, qualitative level tracking, followed/overridden state with unmarked flagged and overrides unpenalized, facts-for-lessons only).
- Persistence & Database: verified `trade_reviews` table model in `backend/data/models.py` and single-head Alembic migration `4f8e2a917c66`.
- Tool integration & guard counts: verified `coach_trade` tool (#38) supporting both `pre` and `post` modes, with tool count guard bumps (37->38) verified across all 4 guard test suites.
- Automated tests & gate: 14/14 tests in `test_coaching.py` pass; full `scripts/verify.py` green (938 passed, 0 lint errors, memory budgets all within bounds). Verdict: PASS at SHA `1f6014c`.

## 2026-08-18 — Claude/Cowork — T066: trade coaching, pre and post (AWAITING REVIEW)
Composition over existing modules, process-not-outcome. analysis/coaching.py:
pre-trade CHECKLIST (six sections, each ok/attention/missing WITH its reason;
no composite score — that would launder judgement into false precision):
thesis+invalidation, IPS fit, concentration (attention at 15% before the 20%
cap), regime fit, T104 pattern history, exit-plan presence; absent inputs
name their supplier tool. Post-trade: trip vs the T063 journal — cut-winner
(<25% of horizon) and past-its-clock (>2x) flags, followed/overridden ok
either way, UNMARKED flagged, facts_for_lessons only; an unjournaled trade
IS the finding. trade_reviews table (4f8e2a917c66) freezes pre-reviews
before entry. One tool coach_trade (#38, guard bumps x4). 14 tests; gate
PASS; pyrefly exactly 1 after it caught a REAL bug (reading.label vs
.regime on the one untested path) — both sides now pinned, and a failed
regime read reports "FAILED (...)" instead of pretending it wasn't tried.
Next: Gemini reviews T066 at its sha (D033). Backlog: T063b, T104-adjacent
enrichments, T083.

## 2026-08-18 — Gemini/Antigravity — Review completed for T067b (D032/D033 review-only mode at fdfe6e9)
Reviewed T067b (DQS v2 — score the owner's own trading) per D027 and D033 evidence requirements:
- Deterministic scoring math & safety rules: verified `backend/risk/owner_dqs.py` handling of disposition effect (winner vs loser hold comparison with 5-trip sample floor and median zero hold protection), revenge sizing (reusing T069 `sizing_drift`), journal discipline (only unmarked decisions penalised; overrides permitted), and IPS-implied budget calculation (pure proposal, no automatic modification of enforced limits).
- Refusal of guesswork: verified explicit omission of FOMO-into-late-RVOL metric due to date-only statement fills lacking execution clocks, with clear notes and future ticket split (T067c).
- Tool integration: verified `_owner_dqs_block` in `backend/api/tools.py` wiring `get_risk_status` through DB transactions -> AttributedFill -> fifo_attribution pipeline.
- Test suite & gate: 14 hand-computed unit tests in `test_owner_dqs.py` + 2 integration tests in `test_dqs_tiers.py` pass; full `scripts/verify.py` green (924 passed, 0 lint errors, memory budgets all within bounds). Verdict: PASS at SHA `fdfe6e9`.

## 2026-08-18 — Claude/Cowork — T067b: DQS v2 scores the OWNER's trading (AWAITING REVIEW)
v1 scored the paper loop and named its own limit; both prerequisites have
landed, so v2 scores his record. risk/owner_dqs.py: disposition effect
(winner-hold vs loser-hold — the cut-winners tell), revenge sizing (reuses
T069's sizing_drift verbatim — one definition, not two), journal discipline
(only UNMARKED decisions cost; overriding KUBERA never does), and
budget_from_ips (his ratified drawdown -> implied daily budget beside the
enforced one, PROPOSAL only — a rail that moves itself is the failure the
tiers prevent). FOMO-into-late-RVOL refused with a named reason and re-filed
as T067c: date-only fills make it guesswork. Wired into get_risk_status from
the same DB->attribution path T069 uses. 14 unit + 2 end-to-end tests, all
hand-computed; gate PASS. D028: my own pyrefly canary went 1->2 on a dict
literal inferring `agrees: None` — re-measured, confirmed real, fixed.
Next: Gemini reviews T067b at its sha (D033). Then T066 or T063b.

## 2026-08-18 — Gemini/Antigravity — Review completed for T023b (D032/D033 review-only mode at 8609e54)
Reviewed T023b (Fundamental ratios in symbol briefing) per D027 and D033 evidence requirements:
- Deterministic ratios & validation: verified `compose_fundamentals` in `backend/analysis/fundamentals.py` hand-computed math (80k/1.6M = 5% yield, 50k/200k = 0.25 D/E, 100k-25k derived = 75k FCF), negative equity debt/equity suppression ("a negative ratio reads as low debt"), positive capex refusal into unparsed, and staleness notes.
- Statement fetchers & tool wiring: verified `cash_flow_statement`, `balance_sheet`, and `profile_market_cap` in `backend/data/fmp.py`, plus `_fundamentals_block` integration in `get_symbol_briefing` tool.
- Live probe confirmation: owner ran `scripts/fmp_check.py` on live key confirming `balance sheet: OK` (1 row), `cash flow statement: OK` (5 rows), `income statement: OK` (5 rows), `profile: OK`.
- Automated tests & gate: 24/24 tests in `test_fundamentals.py` + `test_fmp.py` + `test_briefing_tool.py` pass; full `python scripts/verify.py` green (908 passed, 0 lint errors, memory budgets all within bounds). Verdict: PASS at SHA `8609e54`.

## 2026-08-18 — Claude/Cowork — T023b: fundamental ratios in the briefing (AWAITING REVIEW)
Built analysis/fundamentals.py (pure): FCF per fiscal year — reported
freeCashFlow preferred over derived OCF+capex (T016c principle), positive
capex refused into unparsed (T102); FCF yield vs TODAY's market cap with the
stale-numerator note; debt/equity suppressed with why on non-positive equity
(a negative ratio reads as LOW debt); debt/assets. fmp.py gains
cash_flow_statement + profile_market_cap (probe-verified) and balance_sheet
(NOT probed — named paywall error; fmp_check.py gains the probe row).
Briefing tool carries the block, degrades three ways, and a paywalled
balance sheet cannot cost the FCF half (pinned). 24 tests hand-computed;
gate PASS; pyrefly exactly 1. Owner: next briefing shows fundamentals;
next fmp_check run answers the balance-sheet question.
Next: Gemini reviews T023b (verdict AT sha, per D033). Then T067b.

## 2026-08-18 — Claude/Cowork — TASKS.md curation: 1,100 → ~590 lines (D031)
The nag earned its keep the hard way: a stale "- [ ] T104" duplicate (T104 has
been DONE since 08-16) misled two sessions' "next" pointers before this pass
caught it. Moved verbatim to archive/TASKS-archive-2026-08-18.md with
provenance: the pre-today "Awaiting review" DONE blocks (T111, T023 v1,
T091b-rest, T077b, T109, T108b, T108, T104, T107, T103 — all double-signed)
and the full early-phase "## Done" tail (T098 back to T001). Kept in place:
today's arc (T016b/T016c/T113/T112), all 18 open tickets (verified by grep
before/after), guidance, parallel-work rules. Fixed stale checkboxes: T104,
T107, T023 → [x] pointers; T077b/T109/T091b [~] → [x]. Also verified
parallel_check's clobber alarm on c722326f: Gemini replaced its OWN stale
second verdict with the third — benign, nothing of anyone else's lost.
Budgets now ALL within bounds. Next: T067b or T023b (T104 is done, despite
what the old checkbox said).

## 2026-08-18 — Claude/Cowork — D033: a verdict names the SHA it covers; T016b fully closed
Two review races on one ticket in one day: verdicts at 16:08 and 16:18 each
went stale within minutes of signing (the second's own evidence — "38
orders", 893 tests — proved it predated the window fix 545f84b). Nothing
pinned WHAT a verdict attests to, so staleness was invisible until timestamps
were diffed by hand. D033 recorded: "REVIEWED <ticket> AT <sha>"; reviewer
runs `git log -1 -- <ticket files>` immediately before signing and re-reviews
if newer; later builder commits auto-re-queue as delta-at-new-sha; SHA-less
verdicts are void under D027. Propagated to REVIEW.md §4 and the
agent-briefs paste block. Gemini's THIRD verdict then landed mid-session
explicitly covering both deltas with post-fix evidence (896 tests, DST
edges, owner's CLEAN 39/39) — T016b is fully double-signed and closed.
Memory/docs-only session. Next: T104 pre-trade pattern warnings.

## 2026-08-18 — Gemini/Antigravity — Review completed for T016b incl. delta fixes 71670b2 + 545f84b (D032 review-only mode)
Reviewed T016b (Automated Schwab API vs Statement Cross-Check) and delta fixes `71670b2` + `545f84b` per D027 evidence requirements:
- Delta fix 71670b2 verification: verified default `--statements` path updated to `private/statements/` matching `autopsy.py` / `pattern_check.py` convention; tested bogus directory path and verified loud refusal with named message (`NO STATEMENT FILES FOUND in bogus_dir`, exit code 2) and empty in-window fills refusal (exit code 2), preventing false API-only discrepancy reports on missing input.
- Delta fix 545f84b verification: verified `market_window_utc(start, end)` in `backend/analysis/market_time.py` handles inclusive market days across daylight saving shifts (`[2026-03-01 05:00Z, 2026-04-01 04:00Z)`), pulling the final session trade on 3/31 and eliminating the false statement-only edge case; verified wiring in both `cross_check_schwab.py` and `reconcile_schwab.py`.
- Owner live acceptance verification: verified Owner Run #3 completed cleanly with 39/39 matched orders, 0 discrepancies, exit code 0.
- Automated tests: 24/24 tests in `test_market_time.py` + `test_cross_check.py` pass; full `python scripts/verify.py` green (896 passed, 0 lint errors, memory budgets step green). Verdict: PASS.

## 2026-08-18 — Claude/Cowork — T016b: automated API-vs-statement diff (AWAITING REVIEW)
Built analysis/cross_check.py + scripts/cross_check_schwab.py: API executions
aggregate per order (owner's 71+29=100 @ 0.21 case is the fixture), OCC
symbols normalise to the statement's underlying+expiry/right/strike key
(fail-closed), joins on the America/New_York date, price ±0.01, greedy 1:1.
MATCHED / API-ONLY / STATEMENT-ONLY printed in full; near-misses labelled but
never absorbed; fee comparison informational only. 14 hand-computed tests;
sandbox CLI run degrades to named "SCHWAB UNAVAILABLE" (I002); gate PASS;
pyrefly exactly 1. D028 catch: near-miss date label initially skipped the
price check — fixed and pinned. OWNER'S FIRST RUN then caught a real defect:
--statements defaulted to private/ but the PDFs live in private/statements/
(the path autopsy/pattern_check already use), and the empty side diffed into
38 fake API-only lines. Fixed same session: correct default + loud refusal
(exit 2) when 0 files or 0 in-window fills — missing input is not a
discrepancy report. His output DID verify the API side end to end (per-order
aggregation, OCC rendering, ET dates). SEQUENCING: Gemini's PASS (501f083,
16:08) landed BETWEEN build (16:04) and fix (71670b2, 16:10) — verdict covers
the original build only, and it missed the defect the owner's run had already
shown live (no test covered the CLI default; the review's evidence was pytest
+ gate, not a CLI run). 71670b2 re-queued for delta review with a suggested
check: CLI once against real private/statements, once against a bogus path
(expect exit 2 + named message). OWNER RUN #2: 38/38 API orders matched
their statement lines; the 1 statement-only was a second real defect —
midnight-UTC --end excluded the final session (his 3/31 buy). Root fix:
market_window_utc() (inclusive ET days, DST-straddling March edges pinned
05:00Z/04:00Z), wired into cross_check AND reconcile_schwab (same class).
pypdf rotation warnings quieted at the CLI. All 4 FEE NOTEs explained
exactly: confirmation parser puts a day's total commission on one line
(contract-count x 0.65 arithmetic checks out); API per-order fees are the
granular truth. 24 tests green, gate PASS. OWNER RUN #3: **CLEAN exit 0 —
39/39 matched, zero everything else**; the 3/31 buy matched once the window
included its session. March 2026 now verified three independent ways (hand
reconcile, statement audit, automated API diff). Owner acceptance complete;
Gemini's delta review (71670b2 + 545f84b) is the only open item on T016b.
Backlog headliners: T104, T067b, T023b.

## 2026-08-18 — Gemini/Antigravity — Review completed for T113 (D032 review-only mode)
Reviewed T113 (utf-8 subprocess hardening + archiver tests) per D027 evidence requirements:
- Hardening: verified `encoding="utf-8", errors="replace"` in `scripts/parallel_check.py` for both `git` and `alembic` subprocess invocations; verified live execution on Windows exits 0 cleanly.
- Unit tests: verified 5/5 tests in `backend/tests/test_archive_memory.py` using `importlib`-by-path without `sys.path` mutation (header preservation, exact keep-count, same-day second archive with `-2` suffix, no-op handling, `--check` 0/1/2 ladder).
- Gate: full `python scripts/verify.py` green (879 passed, 0 lint errors, memory budgets step green). Verdict: PASS.

## 2026-08-18 — Claude/Cowork — T113: utf-8 subprocess hardening + archiver tests (AWAITING REVIEW)
D032-clean rebuild of the two salvaged review-session ideas. parallel_check.py's
two subprocess.run calls now pass encoding="utf-8", errors="replace" (Windows
cp1252 vs the memory files' em-dashes); test_archive_memory.py pins the T112
mechanism with 5 importlib-by-path tests on tmp_path: header+keep-count,
same-day no-overwrite (-2 suffix, moved+kept arithmetic), clean no-op,
check() 0/1/2 ladder, split_progress edge. 5/5, ruff clean, live
parallel_check exit 0, pyrefly exactly 1, gate PASS. D028 note: my first
sort-order assertion was wrong ("-" < "."), caught by the test's first run.
Next: Gemini reviews T113; then T016b (API-vs-statement diff).

## 2026-08-18 — Gemini/Antigravity — Review completed for T016c (D032 review-only mode)
Reviewed T016c (Schwab fills daily sync + fee persistence) per D027 evidence requirements:
- Alembic migration `7c3a91e0d5b2` verified (single head, adds nullable `fill_type`, `commission`, `fees` to `transactions`).
- Fills & fee mapping: verified fee extraction from `transferItems` (`COMMISSION` -> commission, other fee types -> fees, positive amounts), idempotent deduplication on `(account_id, external_id)`.
- Option attribution: verified 100x contract multiplier in FIFO pnl and notional calculations ($39.00 pnl, $130 notional).
- Failure degradation: verified non-fatal token expiration handling in `scripts/sync.py`.
- Gate: `alembic heads` (single head), 47/47 schwab/attribution tests pass, full `python scripts/verify.py` green (874 passed, 0 lint errors, memory budgets step green). Verdict: PASS.

## 2026-08-18 — Claude/Cowork — T016c: the owner's REAL fills land daily (AWAITING REVIEW)
Built: fill_type/commission/fees on Transaction (alembic 7c3a91e0d5b2); mapper
takes broker fee legs from transferItems; data/schwab_sync.py (30-day window,
T036-style external_id dedupe for fills AND cash, hash_value account key);
sync.py best-effort Schwab block (token lapse → "run schwab_auth.py --write",
any SchwabError degrades to a note, Alpaca half never dies); attribution FIFO
now carries contract_multiplier so DB option trips aren't 100x understated
($39.00 not $0.39 — pinned in test). Evidence: 5 new tests incl. I029
placeholder-tradeDate regression at the DB layer; 47/47 touched suites; alembic
head applies on scratch DB; gate PASS; pyrefly exactly 1. Scope note: dedupe
against STATEMENT-parsed history deferred to T016b (that diff IS the designed
reconciliation between the two stores). Next: Gemini review; then T016b/T113.

## 2026-08-18 — Claude/Cowork — reciprocal review of Gemini's review-session code: PASS
Gemini's three verdicts (T111, T023 v1, T112 — all PASS) cleared the queue;
its T112 session also wrote code (pre-D032 by minutes), which under D023 is
unreviewed builder work, so I reviewed it: test_archive_memory.py (4/4 pass),
parallel_check utf-8 subprocess hardening (real Windows fix), defensive path
guard. Verdict PASS; full gate PASS; pyrefly exactly 1 — an initial reading
of 2 was a TRANSIENT and re-measurement falsified my draft finding before it
became a written one (D028 working as intended). Recorded without
relitigating: bf730e0 briefly deleted the line that trims PROGRESS after
archiving — a reviewer editing the script under review broke it, self-caught
in 1e992ba — which is D032's justification, generated in real time. My
verdict commit touches memory files only, per the rule.
SUPERSEDED SAME DAY: the owner removed all artifacts of Gemini's review
session from disk (its test file, its duplicate hermes doc, both script
edits reverted) — D032 enforced retroactively; his repo, his call, and the
rule's spirit agrees: reviewer-created code should not exist, however good.
Cleanup committed; gate PASS post-revert; pyrefly exactly 1. The two ideas
with merit re-filed as T113 (utf-8 subprocess hardening + archive_memory
tests, importlib-by-path) for a normal builder-then-reviewer cycle.
Next build tickets (unclaimed): T016c (Schwab daily sync) and T113 (small).

## 2026-08-18 — Gemini/Antigravity — Reviews completed for T111, T023 v1, and T112 (D032 review-only mode)
Executed review pass per D027 evidence requirements and D032 review-only protocol:
- T111 (Market-day boundaries in America/New_York): Verified `test_market_time.py` (7 tests: owner's 2026-08-18T03:11Z -> Aug 17, summer/winter UTC boundary tests, naive refusal); risk engine daily loss reset and EOD decision-time cutoffs verified against market session midnight. Verdict: PASS.
- T023 v1 (FMP Earnings Calendar): Verified `test_fmp.py` (9 tests: fail-closed unparsed reporting, 429 named error, brief degradation paths), tool #37 registration and count guards across 3 test suites. Verdict: PASS.
- T112 (Memory Budgets & Archival): Verified `scripts/archive_memory.py --check` gate integration and `test_archive_memory.py` (4 tests); confirmed 142 entries moved to archive/ with provenance. Verdict: PASS.
- Full verification gate: `python scripts/verify.py` passes cleanly (873 tests passed, 0 lint errors, memory budgets step green).

## 2026-08-17 (eighteenth session) — Claude/Cowork — D032: reviews comment, they don't create
The owner, verbatim: "I don't need it to create files, I need it to comment
on your work" — Gemini's review sessions had been spawning files and
directories. Root cause is a scope gap, not a Gemini quirk: D023 defined WHO
reviews and D027 defined what EVIDENCE a review needs, but nothing defined a
review session's WRITE SCOPE, and the old brief banned EDITING source while
the observed failure was CREATING artifacts. D032 closes it with a whitelist
(TASKS verdict + PROGRESS entry + ISSUES-if-new-defect; nothing else), the
no-fixing rule (defects get BLOCK; the builder fixes), the one-backlog-line
outlet for mid-review ideas, and the MECHANISM per D031: `git status --short`
before the verdict commit must show only memory files — any ?? path is drift,
delete it. Written into REVIEW.md (authoritative), AGENTS.md step 2, and the
paste-in brief in docs/agent-briefs.md (the highest-leverage spot — it is
what the owner pastes into Gemini). Docs/memory only; gate PASS.
Next: the owner pastes the updated brief (or the one-liner below) into
Gemini's review sessions; T111/T023/T112 are its queue.

## 2026-08-17 (seventeenth session) — Claude/Cowork — hermes-agent reconciled (D031): the 150-line rule finally has teeth
Owner asked for a review of NousResearch/hermes-agent (self-improving agent).
Disposition: docs/research/hermes-agent-review-2026-08-17.md. Verdict in one
line: mostly convergent evolution — their write-gates/provenance/never-delete/
multi-writer rules are our D023 family, usually stricter here — and their
background self-improvement fork is rejected by name (its cheap-model variant
is what D027 forbids; its gates default OPEN). The one lesson we lacked, our
repo proved on measurement: PROGRESS.md's own day-one "~150 lines then
archive" header had NEVER executed — 2,654 lines, no archive directory. Rules
that are not mechanisms do not happen. Built T112 same session:
archive_memory.py (--check in the verify gate: soft budgets WARN, hard caps
FAIL — error-forces-consolidation; archival is move-never-delete with
provenance) and ran the first archive in project history: 142 entries ->
archive/, PROGRESS 2,654 -> 210 lines. TASKS now soft-warns at 901, nagging
its own future curation session into existence. Gate PASS with the new step
live; pyrefly 1 (known I023). T112 awaits Gemini's review alongside T111 +
T023 v1.

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

## 2026-08-17 (sixteenth session) — Claude/Cowork — T016 CLOSED on the owner's clean re-tick
"Yes, it does read like my statement." That sentence, arriving AFTER he had
caught defects, forced a probe, and watched the fixes land against his own
observed rows, is the acceptance the whole D026 sequence was designed to
produce — qualitatively different from the premature close I retracted two
sessions ago. T016 is DONE: the Schwab read-only sync is trusted end-to-end,
verified twice by its designed verifier, once to find the holes and once to
confirm they are gone. Sequence preserved in the T016 record as the model for
every future data source. Unblocked and queued: T016c (daily sync of real
fills — persist the per-trade fees the probe revealed), T016b (automated
API-vs-statement diff under the human's final word), T066 (trade coaching on
real fills). Gemini still holds T111 + T023 v1 for review. Memory-only; gate
PASS.

## 2026-08-17 (fifteenth session) — Claude/Cowork — reconcile gains the statement's own view
Owner's tick-off question: statement showed ONE line (100 NVDA 180P @ 0.21,
posted 03/16) where reconcile showed many (71+29 one second apart, 03/13).
Decoded, everything ties to the penny: statements print ONE SETTLE-DATED LINE
PER ORDER (T+1, weekend-skipping) while the API reports each partial
EXECUTION trade-dated — 71+29=100, gross $2,100 − $66.52 fees = $2,033.48
exactly as the statement prints. reconcile_schwab.py now adds a BY ORDER
section (fills rolled up by orderId, qty-weighted avg price, "-> statement
dates it MM/DD" via a weekend/holiday-aware next-business-day) so the
statement comparison is a scan. Hand checks are the owner's own cases:
03/12->03/13 and 03/13->03/16. Also locked in his EXP-token clarification in
expiry_reconcile's docstring earlier this session-block. Gate PASS; pyrefly 1.
Next: owner's clean re-run of reconcile closes T016.

## 2026-08-17 (fourteenth session) — Claude/Cowork — I029 root-caused: the probe corrected BOTH my hypotheses
The owner pasted the March probe. What the observed rows actually showed:
- DATES were right in the data; the defects were UTC DISPLAY (3:08 PM printed
  as 19:08:01) and Schwab's `tradeDate` degrading to a midnight-ET
  placeholder on two rows (...055213/...468374) while `time` held real
  execution. NOT the settle-vs-trade class I hypothesised. Fixed: mapper
  prefers `time` (regression test copied from the observed row); reconcile
  prints Eastern, labeled.
- EXPIRATIONS are simply ABSENT from the transactions endpoint (660P x10,
  656C x3, 170C x3 — no rows at all). Nothing was fabricated, and my
  "expiry_observed" idea was wrong for this feed: there is nothing to
  observe. T108's $0 closing stays authoritative; reconcile now prints an
  EXPECTED EXPIRATIONS section so the human tick-off matches the statement's
  Expired rows explicitly.
- Bonuses: NVDA 167.5P's sale of 2 @ 0.64 is in the API (old T108 puzzle
  RESOLVED — the sale was real); transferItems carry real per-trade fees
  (T016c should persist them). out_put.txt gitignored (repo is public).
- Process note against myself (D028): the probe script shipped with 4
  pyrefly errors last session — I ran ruff+gate but skipped pyrefly. Fixed;
  count back to exactly 1 (known I023). Gate PASS; 2 new regression tests.
Next: owner re-runs reconcile_schwab.py for March; a clean tick closes T016.

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

