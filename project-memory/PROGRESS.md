# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
Budgets are ENFORCED by the verify gate (T112/D031): archive_memory.py --check
warns at 700 lines and fails at 1,000; `python scripts/archive_memory.py` moves
old entries (verbatim, never deleted) to /project-memory/archive/.

## 2026-08-20 — Gemini/Antigravity — review T116 / T087b / I023 sweep / curation #3 (all PASS)
Reviewed batch of tickets at tip (`4a1dbdb`). Gate PASS (1,042 passed, 0 failed);
python pins agree (3.14.7); alembic single head (`e1a7c4f9b2d3`).
1. T116 (7af3dcc) PASS: `analysis/short_horizon.py` packages conditioned distributions (1d, 3d);
   tool #41 `get_short_horizon` (guard tests bumped 40->41 across 4 files); monitor CLI leads
   with 1d range/up-odds; morning brief leads with short horizon; persona `SHORT_HORIZON_RULE` wired.
   Live monitor run confirmed leading line. 5 tests in `test_short_horizon.py` pass.
2. T087b (8e817c3) PASS: `backend/notify.py` shared hardened PowerShell toast helper with
   quote-doubling/newline-flattening escaping and non-raising contract; `monitor.py --notify` wired.
   4 tests in `test_notify.py` pass.
3. I023 / sweep (afbf8b3, 0488c23) PASS: `mcp_server.py` `cast(Any, fn)` on dynamic `__signature__`;
   `pyrefly.toml` at 0 errors; `ISSUES.md` closures for I023, I029, and I016 verified with evidence.
4. TASKS curation #3 (4a1dbdb) PASS: 6 double-signed entries moved verbatim to
   `archive/TASKS-archive-2026-08-20.md`, keeping `TASKS.md` within budget.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits.

## 2026-08-20 — Gemini/Antigravity — review I033 fix (PASS)
Reviewed I033 fix at tip (`45dc086`). Gate PASS (1,033 passed, 0 failed);
python pins agree (3.14.7); alembic single head (`e1a7c4f9b2d3`).
- I033 fix (45dc086) PASS: `analysis/monitor.py` `describe_regime()` outputs timeframe on every
  label ("trending_up (daily structure - a weeks-to-months lens)"); `PositionCheck` carries
  `week_change_frac`; `scripts/monitor.py` prints contextual explanation when structural uptrend
  coincides with red week. `test_regime_labels_carry_their_lens_i033` passes. D035 timescale
  doctrine and T116 short-horizon-first backlog item align cleanly.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits.

## 2026-08-20 — Gemini/Antigravity — review T087a / T093c / T085b / T115 / TASKS curation (all PASS)
Reviewed batch of 5 items at tip (`e80d14c`). Gate PASS (1,032 passed, 0 failed);
python pins agree (3.14.7); alembic single head (`e1a7c4f9b2d3`).
1. T087a (e80d14c) PASS: `analysis/monitor.py` (four named checks: rvol_collapse, vwap_churn,
   invalidation_hit/near, event_window; named blind spots) + `scripts/monitor.py` owner CLI
   with exit codes. Tested live against paper account on Windows host (SPY position inspected).
2. T093c (f12545c) PASS: Euler marginal risk contributions, effective bets, and diversification
   ratio verified already shipped with T093. Backlog pointer updated without rebuild.
3. T085b (de893c7) PASS: `risk/sizing.py` `fractional_kelly_view` pure calculation from T077
   distribution (quarter-Kelly, 10% advisory cap, negative Kelly reported, named refusals).
   `size_position` payload incorporates view best-effort; recommendation sizing unchanged (D017).
4. T115 (db95da5) PASS: `RiskLimits.from_settings()` duck-typed loader from `.env` with startup
   range validation; all 6 `RiskEngine` instantiation sites settings-built; `.env.example` documented.
5. TASKS curation (967f66e) PASS: 15 double-signed review entries moved verbatim to
   `archive/TASKS-archive-2026-08-20.md`, clearing soft line budget warning (929 -> 384 lines).
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits.

## 2026-08-20 — Gemini/Antigravity — review T114 / T064b-rest / T063b / T065b / T110b / T084 (all PASS)
Reviewed batch of 6 tickets at tip (`755fe5f`). Gate PASS (1,019 passed, 0 failed);
python pins agree (3.14.7); alembic single head (e1a7c4f9b2d3).
1. T114 (755fe5f) PASS: `.env.example` includes `FMP_API_KEY`, de-staled `EDGAR_CONTACT`;
   `README.md` reflects current surface (1,000+ tests, order rails, research map, stress CLI);
   `PROGRESS-archive-2026-08-20.md` contains 32 entries verbatim.
2. T064b-rest (eaa7977) PASS: `stress.py` + `stress_windows.py` enforce coverage, compare
   template at 1x/2x costs against buy-and-hold; `gfc-2008` named impossible on IEX feed. Tested live.
3. T063b (0deb655) PASS: `calibration.py` implements stated-confidence buckets with thin data
   refusal (MIN 5), endpoint-only R against stated stops with invalid geometry detection, and
   override-vs-outcome tracking. 5 hand-computed tests pass.
4. T065b (ba789b5) PASS: `RiskLimits.max_buys_per_day` (default 5) in `pre_trade_check`, counting
   broker-accepted orders; sells exempt; persisted across restarts (`e1a7c4f9b2d3`). 5 tests pass.
5. T110b (93de506) PASS: `isolation.py` child process under `python -I`, boot allowlist env,
   empty cwd, sentinel output, hard timeout; `assert_servable` custody seam; 8 adversarial probe
   tests pass. Threat model honestly stated.
6. T084 (f226d85) PASS: `EdgarClient.earnings_release` (item 2.02 -> largest ex99 exhibit ->
   stdlib html_to_text) + tool #40 `get_earnings_release` qualitative framing. Guards bumped to 40.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits.

## 2026-08-20 — Claude/Cowork — Anthropic FSI/plugin repos reviewed; T117 + T118 built (D036)
Owner asked for a review of anthropics/financial-services,
claude-plugins-official, knowledge-work-plugins. Read the READMEs + the
two most KUBERA-relevant SKILL.md files in full; disposition doc at
docs/research/anthropic-fsi-plugins-review-2026-08-20.md (ab1b055); D036
records the ruling (adopt methodology, never content; all Apache-2.0).
ADOPTED AND BUILT: T117 TLH scan (measurement-only: FIFO open lots with
new ts/mult fields, ST/LT split, wash lookback from the owner's OWN buys,
first-safe-repurchase date, unpriced options listed never guessed, NOT
TAX ADVICE verbatim; tool #42) + T118 earnings-preview composition (next
report + own base rates + realized 1-day distribution labeled
not-options-implied + runup + exposure; no price targets by design; tool
#43). Guards 41->43; MCP +2. REJECTED BY NAME: replacement-security
suggestions (D017), scenario targets (D035), consensus scraping (D030),
subscription connectors (D034). SEEDED: T119 thesis view, T120 plugin
packaging. VERIFIED: test_tlh.py 4 hand-computed + test_fsi_tools.py 3
end-to-end; 1046 passed; pyrefly 0; gate PASS. NEXT: Gemini reviews the
T117+T118 SHA + the disposition commit.

## 2026-08-20 — Claude/Cowork — batch of five #3: T116, T087b, I023, stale-sweep, curation
The owner's D035 direction became SURFACES. Five closed at their SHAs:
7af3dcc T116 — short-horizon FIRST: analysis/short_horizon.py packages
T077's conditioned distributions into the leading read (1d/3d p05..p95 in
% and price, up-odds, typical |move|, BASIS named); tool #41
get_short_horizon; the monitor prints the days line FIRST; the morning
brief's per-symbol read leads with it; persona SHORT_HORIZON_RULE wired
into the built prompt (which-way → distribution + one honest sentence;
every regime word carries its timeframe; session state = the minutes
lens). Every surface composes from ONE function — chat and monitor can
never disagree. 8e817c3 T087b — monitor --notify via backend/notify.py,
promoted from health_check WITH its latent apostrophe-quoting bug fixed
(monitor alert text would have tripped it; escaping pinned by test).
afbf8b3 I023 — pyrefly is a TRUE ZERO: cast(Any, fn) expresses the
__signature__ gap (callable-class rejected in-line: FastMCP coroutine
detection); pyrefly.toml records the history; NEW CANARY = EXACTLY 0.
0488c23 sweep — two healed REOPENED markers (I029 inner, I016 numpy)
closed with evidence, plus I023 bookkeeping. Curation #3 — six signed
entries archived verbatim; TASKS at 441 lines.
VERIFIED: 1039 passed; pyrefly 0; gate PASS per ticket; monitor/health
degradations re-demonstrated live (exit 2 named).
NEXT: Gemini reviews T116 + T087b + I023/sweep at their SHAs. Owner: next
monitor run leads with "next 1d usually X..Y; up-odds Z" — the lens you
asked for; tell KUBERA if the numbers read right.

## 2026-08-19/20 — Claude/Cowork — batch of five #2: curation, T115, T085b, T093c, T087a
Owner asked for another 4–5; five closed, each at its own SHA (D033):
967f66e CURATION (D031) — 15 double-signed entries moved VERBATIM to
archive/TASKS-archive-2026-08-20.md; TASKS 929→384 lines; script asserted
exactly-15-signed/zero-unsigned before writing. db95da5 T115 — all six
RiskLimits knobs from .env via RiskLimits.from_settings (validation
refuses bad values AT STARTUP with the range named); all six RiskEngine
sites now settings-built; defaults pinned against drift; ruff caught 4
missing imports my import-smoke couldn't (function bodies). de893c7
T085b — fractional-Kelly ADVISORY view in size_position (quarter-Kelly,
10% cap, negative f* reported not hidden, named thin-data refusals;
sized qty UNCHANGED — D017 stands). f12545c T093c — CLOSED WITHOUT
BUILDING: mapping-first found marginal contributions + effective bets
shipped WITH T093 on 08-14 (portfolio_risk.py, wired, tested) — grep
evidence, stale backlog pointer fixed, nothing redone. T087a — open-trade
monitor v1: four named checks per held position (rvol_collapse only
under breakout thesis, vwap_churn at the T052 line, invalidation
hit/near vs the SAME T056 plan chat narrates, event windows as
surfaces-not-instructions), named blind spots never crashes, schedulable
exit codes, ADVISORY ONLY; scripts/monitor.py one-pass or --loop; toast/
Orb/voice stay with T087/T074 by design.
VERIFIED: 1029 passed; pyrefly canary 1 — after catching TWO real bugs
in monitor.py's script layer (wrong build_exit_plan signature = crash on
first real run; wrong return annotation); live sandbox degradations
named with real exit code 2. Gate PASS at close.
NEXT: Gemini reviews five at their SHAs. Owner: run
`python scripts\\monitor.py` during RTH with an open position — first
real-world pass decides threshold tuning.

## 2026-08-19 — Claude/Cowork — batch of five: T110b, T065b, T063b, T064b-rest, T114
Owner asked for 4–5 tickets finished in one pass; five closed, EACH AT ITS
OWN SHA for D033 review: 93de506 T110b (isolation boundary: python -I child,
scrubbed env, empty cwd, sentinel-only results, timeout kills named; parity
isolated==in-process==real template; adversaries come back EMPTY — env spy
0 hits, repo imports fail, relative .env unreadable; assert_servable =
custody seam; threat model stated honestly → PHASE 7 PRECONDITIONS
COMPLETE). ba789b5 T065b (engine-level order-frequency rail: max 5 new
buys/market day, persisted via migration e1a7c4f9b2d3, sells exempt,
automatic day rollover, loop wired, risk status shows it — closes the T065
line). 0deb655 T063b (calibration v2: confidence buckets with named
thin-data refusals, payoff-vs-plan R endpoint-only-and-says-so, override×
outcome for T067b; get_journal + weekly review wired; pyrefly caught a
real narrowing gap before commit). eaa7977 T064b-rest (crisis windows
covid-2020/bear-2022 vs buy-and-hold same window, 2x costs, coverage-
enforced slicing refuses partial crashes, 2008 NAMED impossible on this
feed; measurement only; my too-short fixture got refused by my own guard —
fixture fixed, guard unchanged). T114 (docs: FMP_API_KEY was MISSING from
.env.example — fixed; EDGAR comment de-staled; README gains earnings-
intelligence, stress/brief/risk_symbols blocks, 1,000+ tests, research/
in the repo map).
VERIFIED: 1016 passed at batch end; pyrefly canary 1 throughout; every
migration up/down/up exercised; gate PASS per ticket and at close.
NEXT: Gemini reviews five tickets at their SHAs (+T084 from earlier
today). TASKS.md at 929 lines (soft 900) — curation pass is due after
this review wave lands (archiving double-signed entries needs verdicts).

## 2026-08-19 — Claude/Cowork — T084: earnings-release text as labeled context
BUILT (same day its gate was answered): EdgarClient.earnings_release —
newest earnings 8-K → index.json → largest ex99* exhibit (probe-validated
rule) → stdlib html_to_text (deterministic; tables flatten and SAY so);
named fallback to the 8-K primary; five named refusals; truncation visible
(flag + total chars). Tool #40 get_earnings_release: qualitative context —
narrate as a document with filing dates; NEVER a priced signal; scope
honesty in the payload (company's OWN release, not the call Q&A — paid
tier, D034). MCP read-only list +1; CORE_TOOLS deliberately unchanged
(context-heavy long tail stays off small brains). Guards 39→40 ×4 files.
VERIFIED: test_earnings_release.py 8 tests on owner-observed fixtures
(0000320193-26-000018 / 38,350 b / 173,484 b); gate PASS; pyrefly canary 1.
NEXT: Gemini review at this SHA. Backlog: T110b (isolation probe), T074b
(Pipecat spike, owner machine), T063b/T067c data-gated, D021 window ~09-12.

## 2026-08-19 — Gemini/Antigravity — review T074a (PASS) / T084a (PASS) / T110a (PASS) / T062c delta (PASS)
Reviewed 4 items at tip (`e30e479`). Gate PASS (989 passed, 0 failed); python pins agree (3.14.7);
alembic single head (c9f6e3a2d874); parallel_check clean.
1. T074a (e30e479) PASS: `docs/research/realtime-voice-2026-08-19.md` thoroughly researched and
   sourced (14 links). Rejections of OpenAI Realtime (speech-to-speech bypassing KUBERA persona/rails)
   and LiveKit (multi-user media server complexity) are sound. Pipecat adopted pending T074b spike
   (local PyAudio, documented Kokoro TTS, $0/min). Catch acknowledged: custom processor calling
   `/api/chat` needed. T074b/T074c backlog tasks seeded.
2. T084a (3469eaf) PASS: `scripts/edgar_check.py` step 5 parse logic in `summarize_index()` verified
   with 4 unit tests. Live run on owner machine confirmed 17 files in accession `0000320193-26-000018`,
   primary doc `aapl-20260730.htm` (38,350 bytes), and exhibit `a8-kex991q3202606272026.htm`
   (173,484 bytes) with free earnings text. Free EDGAR filing text gate answered.
3. T110a (c54c7e9) PASS: `backend/research/custody.py` implements one-way `FROZEN -> UNLOCKED -> CONSUMED`
   state machine with `params_hash` invariance, single evaluation enforcement, and append-only journal.
   Pre-registered experiment budgets with failure-counting refusal. Migration `c9f6e3a2d874` clean single
   head. All 7 tests pass.
4. T062c delta (c54c7e9) PASS: `scripts/brief.py` moved `AlpacaError` and `httpx` imports to top-level,
   eliminating potential `NameError` in except tuple.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No source/test edits.

## 2026-08-19 — Claude/Cowork — T110a: holdout custody + experiment budgets (Phase 7 preconditions)
BUILT: backend/research/custody.py — one-way FROZEN→UNLOCKED→CONSUMED state
machine for holdout windows (params_hash pins the definition; unlock once;
consume requires hash match + records the ONE result; journal_json append-only
on the row; guarded_symbols() = T110b's enforcement hook) and per-revision
experiment budgets (open once pre-registration, attempts append-only,
FAILURES COUNT, over-budget refusal names two-strikes). Models + migration
c9f6e3a2d874 (up/down/up exercised). Nothing imports research/ yet — Phase 7
inherits it at open instead of bolting it on after the first incident.
VERIFIED: test_custody.py 7 tests, every refusal matched by name; 982 passed;
gate PASS; pyrefly at the 1-error canary — getting BACK to 1 exposed my own
T062c bug (brief.py except-tuple names imported inside the try; import
failure would NameError over the real error) → fixed, T062c re-queued as a
D033 delta on its entry despite its fresh PASS.
NEXT: T084a (EDGAR filing-document probe), then T074a (realtime-voice research).
D028: isolation boundary + adversarial probe stay split to T110b — a
half-built sandbox boundary is worse than a named absence.

ALSO 2026-08-19 — OWNER RAN edgar_check.py (with T084a's step 5): ALL
GREEN. Press-release exhibit ex99.1 = 173,484 bytes FREE (AAPL 2026-07-30,
accession 0000320193-26-000018). T084 gate ANSWERED: earnings release text
comes free from EDGAR; call Q&A stays paywalled (D034 upgrade item). T084
backlog entry updated with the v1 design + scope honesty.

ALSO 2026-08-19 — T074a: realtime-voice research → docs/research/
realtime-voice-2026-08-19.md. Decision: Pipecat (local transports, kokoro
documented, $0/min) pending T074b spike; OpenAI Realtime rejected on
architecture (speech-to-speech replaces the brain → bypasses rails);
LiveKit wrong-shaped for one desktop; no Anthropic voice API. T074b/T074c
seeded with exit criteria. Batch of three complete: T110a + T084a + T074a
all AWAITING REVIEW (Gemini: review each AT its SHA per D033).

ALSO 2026-08-19 — T084a: edgar_check.py step 5 (filing-document probe).
One extra request per run: the earnings 8-K accession's index.json →
primary doc + largest ex99* exhibit, names+bytes only. Gates T084 (free
8-K press-release text vs paywalled transcripts). Pure summarize_index()
pinned by 4 tests; sandbox run shows named degradation; 986 passed.
OWNER: rerun edgar_check.py and paste the table.

## 2026-08-19 — Gemini/Antigravity — review T076b delta (PASS) / I032 (PASS) / T065 (PASS) / T062c (PASS)
Reviewed 4 tickets at tip (`05dfe35`). Full gate PASS (978 passed, 0 failed); python pins agree
(3.14.7); alembic single head (b7e4d2c8f1a5); parallel_check clean.
1. T076b delta (36dcbe3) PASS: June 2027 FOMC decision day confirmed corrected to `2027-06-09`
   (matching live Fed official calendar anchor #45694). All 16 rows now accurate.
2. I032 (fe722cb) PASS: `.python-version` (3.14.7) restored; `check_python_pins.py` parity check
   added and active in verify gate.
3. T065 (11fbdb0) PASS: `analysis/sector_exposure.py` provides clean measurement & 40% concentration
   warning with unknown grouped/named; `RiskEngine._disabled_symbols` blocks buys with named reason
   while exempting sells; persisted in DB via alembic migration `b7e4d2c8f1a5`; `risk_symbols.py`
   CLI tested live.
4. T062c (05dfe35) PASS: `scripts/brief.py` CLI tested live (`--no-save`) against paper data & DB;
   composes morning/eod/weekly without server; handles unconfigured/unreachable degradation; saves to
   gitignored `private/briefs/`.
Self-diff check: edited ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No source/test edits.

## 2026-08-19 — Claude/Cowork — BLOCK fixed + three more: I032 (CI!), T065, T062c
Gemini's T076b BLOCK fixed first: June 2027 FOMC decision day corrected
2027-06-16 → 2027-06-09 per its live Fed-page fetch — the load-bearing
transcription check earned its keep; incident recorded in fomc.py, I031
closed, re-submitted at 36dcbe3. Then three tickets: (1) I032 — the REAL
current CI red found: suite passes clean WITHOUT .env (967), so the red was
workflow-level — ci.yml reads .python-version, which the 08-17 uv cleanup
deleted; restored (3.14.7) + a python-pins gate step so the class fails
locally forever after; next push should go green. (2) T065 — sector
exposure measurement (pure, 40% warning, unknown named; measurement-only by
design — caps await owner-ratified limits) + disable-symbol control in the
ENGINE (buys refused named, sells exempt, restart-proof, corrupt-JSON-safe,
CLI only — no chat path to a rail); order-frequency resolved-by-T055;
cancel-all deferred with reason (nothing rests). (3) T062c — scheduled
brief CLI closing T062b's last item (composes without the server, saves to
private/briefs/, named degradations, Task Scheduler one-liners). All gates
PASS; pyrefly exactly 1 throughout. Next: Gemini reviews the T076b delta +
I032 + T065 + T062c at their shas.

## 2026-08-19 — Gemini/Antigravity — review T076b BLOCK / T083c PASS / T072b PASS
Reviewed three tickets at deb9c0c (tree tip). Gate 970 passed; alembic single head;
parallel_check clean; no clobber signature.
T072b (deb9c0c) PASS: module-level importorskip('numpy') removed from test_tts_backends.py;
skip now inside _silent_wav() and kokoro-play helper only. Grep confirmed talk.py has no
top-level numpy/sounddevice imports. Two items (a,c) correctly closed on evidence, not re-fixed.
T083c (e2d3265) PASS: statistics.median used (not sorted()[n//2]); D028 self-correction
honest. Three degrade paths verified in diff. Test numeric assertions are hand-computable
values, not circular. brief-never-dies invariant tested.
T076b (1e0f279) BLOCK: fetched federalreserve.gov/monetarypolicy/fomccalendars.htm live
(page last updated July 29, 2026). Compared all 16 FOMC dates. 2026: all 8 correct.
2027: ONE WRONG — fomc.py has "2027-06-16"; Fed page anchor #45694 shows June meeting
as "8-9*" → decision day 2027-06-09. One-week error means June 2027 FOMC entirely
unguarded. All other aspects (priced_for_perfection, with_fomc, staleness, wiring) correct.
Defect logged as I031. Claude must fix and re-submit.
Self-diff check: wrote ONLY the three verdict blocks in TASKS.md, this PROGRESS entry,
and I031 in ISSUES.md. No source edits, no new files.

## 2026-08-19 — Gemini/Antigravity — review T083b: PASS at 634d20c (build) + 8e15153 (probe)

Evidence run per D027: `python scripts/verify.py` → 962 passed, 0 failed, ruff clean,
pyrefly exactly 1 (matches commit claim). 24/24 EDGAR-specific tests pass including
owner's 20:30:28Z probe sample (amc), winter/summer DST flip, naive-datetime refusal,
unknown-ticker named error, bad-date reported-never-guessed, 403 User-Agent error,
end-to-end store integration (4 rows source=sec-edgar, timing_assumed all False), and
EDGAR-500 degrade (store still answers). PII discipline confirmed: edgar_contact is
SecretStr, never logged, UA carries it only at runtime. Gap fix verified: chat endpoint
now builds fred/fmp/edgar best-effort; close_tool_context extended to fmp/edgar (T106-
class resource leak closed). No fabricated inputs, no hardcoded secrets, fail-closed
parsing throughout (T102). Diff self-check: every D028 objection in the ticket
correctly documented; strongest objection (archive pagination not fetched) is noted in
the docstring. No defects found. Verdict: PASS.
## 2026-08-18 — Claude/Cowork — Three tickets on the owner's ask: T076b, T083c, T072b
Owner asked for the next three, finished in sequence, each claimed/built/
gated/queued separately. T076b: FOMC decision days as a published-schedule
table (holiday-calendar precedent; 16 dates 2026-27; reviewer check against
the Fed page is load-bearing and named), self-reporting staleness (D031),
merged into ALL calendar consumers — FOMC now guards even without a FRED
key; plus the D019 priced-for-perfection flag (per-holding 5-bar runup vs
own p95) joined onto earnings_risk; stale PENDING_NOTES retired. T083c:
compact base-rates block per held symbol with upcoming earnings (median
event-day move, closed-down frac; three degrade paths; brief never dies).
T072b: honest disposition — 2 of 3 items already fixed by prior work,
closed on grep evidence not redone; the real one fixed (module-level numpy
skip hid audio-free tests from CI; now per-test). D028 catches en route:
upper-median replaced with statistics.median; a flawed proof harness
disclaimed rather than claimed. All gates PASS; pyrefly exactly 1
throughout. Next: Gemini reviews T076b + T083c + T072b at their shas.

## 2026-08-18 — Claude/Cowork — T083b: EDGAR history live (AWAITING REVIEW)
Owner's probe answered ALL GREEN same-session (10,387 tickers; 46 earnings
8-Ks/~11yr for the probe symbol; 46/46 acceptance timestamps), so the build
followed: EdgarClient (two endpoints, cached CIK map, item-2.02 filter,
named 403/429/unknown-ticker errors, fail-closed dates), hint_from_acceptance
(real filing clock → amc/bmo via MARKET_TZ; the owner's 20:30:28Z sample is
the headline test), and get_event_base_rates feeding EDGAR history into the
SAME earnings_observed store — merging is the store. Closed two adjacent
gaps found en route: the chat endpoint built NO fred/fmp (tools claimed
"not configured" over chat with keys present), and close_tool_context's
fixed list would have leaked fmp/edgar per MCP call (T106 class, caught in
self-review). 9 new tests incl. DST clock cases; 22/22 mcp suite; gate
PASS; pyrefly exactly 1. "Hold through earnings?" now answers with years
of history, timing KNOWN not assumed. Next: Gemini reviews at this sha.

## 2026-08-18 — Claude/Cowork — T083b probe: edgar_check.py (AWAITING REVIEW)
The D030 gate on T083b, built free-first per D034: keyless EDGAR probe for
the owner's machine — ticker→CIK map, submissions JSON (8-K count, items
"2.02" presence, filingDate depth), acceptanceDateTime (a real clock that
would upgrade T083's bmo/amc convention from assumed to KNOWN), SEC UA
etiquette with 0.2s spacing. D028 self-catch: v1 embedded his personal
email in committed source of a PUBLIC repo — contact now loads from .env
(EDGAR_CONTACT in .env.example), probe refuses without it, never echoes it.
Sandbox run demonstrates the named-unreachable path; refusal path exit 2;
ruff clean; gate PASS. Owner: add EDGAR_CONTACT to .env, run the probe,
paste the table — it decides the T083b build.
Next: Gemini reviews the probe at its sha; owner's probe run gates the rest.

## 2026-08-18 — Gemini/Antigravity — Review completed for T083 (D032/D033 review-only mode at 531ea20)
Reviewed T083 (Event reaction base rates — D019) and delta redesign per D027 and D033 evidence requirements:
- Deterministic base rate math: verified `backend/analysis/event_rates.py` event-day and next-day returns, 5-bar runup, beat/miss/inline classification strictly from EPS actual vs estimate, amc/bmo timing convention with `timing_assumed` tracking, and MIN_EVENTS=4 threshold.
- Self-accumulated store (D034 paywall adaptation): verified `backend/data/earnings_store.py` recording forward calendar dates into `earnings_observed` table (Alembic `9d1c5b3fa284`) and backfilling actuals, with graceful degradation and clean errors on empty store.
- Tool registration: verified `get_event_base_rates` tool #39 wiring, string-to-date bar conversion, and tool count guard bumps (38->39) across 4 guard test suites.
- Automated tests & gate: 15 tests in `test_event_rates.py` and `test_earnings_store.py` pass; full `scripts/verify.py` green (953 passed, 0 lint errors, memory budgets within bounds). Verdict: PASS at SHA `531ea20`.

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

