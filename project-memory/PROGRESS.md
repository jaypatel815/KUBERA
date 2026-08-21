# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
Budgets are ENFORCED by the verify gate (T112/D031): archive_memory.py --check
warns at 700 lines and fails at 1,000; `python scripts/archive_memory.py` moves
old entries (verbatim, never deleted) to /project-memory/archive/.

## 2026-08-21 - Batch #10: curation + D021 countdown + Orb benchmark panel + persona rule + README (Claude/Cowork)

**Built:** Five independent units under D038. Curation #10 (59e3a9e):
T141 + batches #9/#7 double-signed -> archive; TASKS 661->450, PROGRESS
743->182 (reviewer's soft-budget NOTE actioned). T142 (af7d9ee): weekly
review counts down to the D021 revisit - governance_d021 key + facts
line within 10 days of ~2026-09-12, exact command included, past-due
stays loud; frozen-date tested. T144 (70fd3f4): persona CORE_RULE -
names resolve via find_symbol before any symbol tool; ambiguity asked.
T143 (01185df): /api/benchmark drawn on a raw canvas in the Orb's
portfolio panel (gold you / gray SPY / dotted start), you-SPY-excess
footer, named degradations, no chart lib, 10-min self-throttle. T145
(135f9ca): README - ask-by-name, phone install + panel, Kronos CLI
quick-ref.

**Verified:** Full gate PASS - 1,155 passed + skips, pyrefly exactly 0,
budgets in bounds post-curation. node --check on Orb JS. Pins: brief
+4, persona +2 keywords, orb_panel +1 test.

**Next:** Gemini review of batch #10 (six SHAs, close SHA carries the
manifest). Owner: push to origin; pre-Monday Kronos sequence unchanged
(shape check -> daily forecast from 08-24). Review queue before this
batch was EMPTY - everything through T141 double-signed.

**Blockers:** none.

## 2026-08-20 — Gemini/Antigravity — review T141 (PASS) + T074b re-review (PASS)
Reviewed two items in the Awaiting review queue:
1. T141 (3f45129) PASS: `find_symbol` tool #45 executed LIVE (exact ticker, name, ambiguity, ETF probe, no-edgar refusal all correct). 7 tests pass. Full verify PASS: 1150 passed, pyrefly 0 errors. Guards bumped 44->45 x4. Alembic single head. Two NOTEs recorded: `asof` in output reflects call time not fetch time (non-blocking; directory changes slowly); PROGRESS.md at 736 lines (soft 700 — builder should run archive_memory.py before next session).
2. T074b re-review (e56c88b) PASS: All four inline pipecat imports in `backend/tests/test_voice_pipeline.py` confirmed to carry narrow `# pyrefly: ignore  # I037: voice-only dep`. Pyrefly 0 errors. Full verify PASS. I037 closed.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits, no new files, no ISSUES entry (no new defects found).

## 2026-08-20 — Claude/Cowork — T141: the symbol universe (owner direction) + T074b fix

Owner: "KUBERA shouldn't only focus on specific symbols - it should know
every symbol in the market." Answered honestly: the data tools were
already universal; the gap was ticker RESOLUTION from LLM memory (I007
class). find_symbol (tool #45, 3f45129) now resolves names -> tickers
deterministically against the SEC's full registrant directory (already
fetched by EdgarClient, keyless), with ambiguity returned as candidates
and a labeled live-quote probe for ETF/trust misses. Guards 44->45.
Also: Gemini BLOCKED T074b on the test file's pipecat imports (I037 -
the same ambient-dependency class as I036, one layer deeper); fixed at
e56c88b, re-queued. Mid-T141 the I035 refuse-guard scored its first
live save: the gate went red on a narrowing break and the commit was
REFUSED until fixed. Gate PASS at close (1,150 tests). Queue for
Gemini: T141 at 3f45129, T074b at e56c88b.

## 2026-08-20 — Gemini/Antigravity — review Batch #9 & T122c re-review (T122c PASS, Batch #9 BLOCK on T074b)
Reviewed queue items:
1. T122c (re-review at 1a9ed3a) PASS: `scripts/kronos_adapter.py:50` narrow `# pyrefly: ignore` added. Verified clean import and shape check passes on owner's machine.
2. Batch #9 (752318c):
   - T136 (f822255) PASS: PWA shell (`apps/web/sw.js`, `manifest.json`, `orb.html`, `test_pwa.py`) with cache-first shell and network-only money guard for `/api/*`, `/portfolio`, `/health`.
   - T137 (954751d) PASS: EDGAR earnings history backfill (`scripts/earnings_backfill.py`) with bmo/amc/during timing and idempotent store upsert.
   - T140 (0b995b7) PASS: Single model load (`_predictor` singleton + `forecast_batch`) with isolated per-symbol failures.
   - Curation #9 & ISSUES sweep (752318c) PASS: Verified archive and resolved issues.
   - T074b (0fec77a) BLOCK (CRITICAL): `backend/tests/test_voice_pipeline.py` lines 63, 64, 92, 105 import `pipecat` without `# pyrefly: ignore`. Because `pipecat` is in `requirements-voice.txt` (not standard venv), `pyrefly check` reports 4 missing-import errors, breaking verify gate (`types (pyrefly = exactly 0)`). Logged as I037 in ISSUES.md.
Self-diff check: touched ONLY `project-memory/TASKS.md`, `project-memory/PROGRESS.md`, and `project-memory/ISSUES.md`. No code edits.

## 2026-08-20 — Gemini/Antigravity — review T122d, Batch #8, Batch #7 (T122d PASS, Batch #8 PASS, Batch #7 BLOCK on T122c)
Reviewed remaining queue items:
1. T122d (89ca9cf) PASS: `scripts/kronos_run.py` accidental restart guard refuses `start` when attempts > 0 unless `--another-attempt` provided. Tested live.
2. Batch #8 (4430e61) PASS: `risk_events` table (migration `c8e4f2a91d63`), deduplicated observation recording in brief, `scripts/d021_evidence.py` packet, hygiene #7 + briefs refresh. 5 tests pass; live DB migrated.
3. Batch #7 (1731adf):
   - T133 PASS: `kronos_run.py status` anti-peek verified.
   - Curation #8 PASS: Archive verified.
   - T122c BLOCK (CRITICAL): `scripts/kronos_adapter.py:50` has unsuppressed `import pandas as pd`, causing `pyrefly check` to fail with 1 error, breaking verify gate (`types (pyrefly = exactly 0)`). Needs narrow `# pyrefly: ignore`. Logged as I036.
Self-diff check: touched ONLY `project-memory/TASKS.md`, `project-memory/PROGRESS.md`, and `project-memory/ISSUES.md`. No code edits.

## 2026-08-20 — Gemini/Antigravity — review T122b (Kronos runner) (PASS)
Reviewed T122b at tip (`e5fdaeb`). Gate PASS (1,122 passed, 0 failed);
pyrefly 0 errors; python pins agree (3.14.7); alembic single head (`a3d9e8c1f5b7`).
1. T122b (e5fdaeb) PASS: `ResearchForecast` table + migration `a3d9e8c1f5b7` (unique constraint prevents re-forecast);
   `run_isolated_json` process isolation with model venv interpreter injection; `research/kronos_runner.py`
   paper-forward history refusal, hand-computed coverage/toy-rule scoring, and consume-once custody binding;
   `scripts/kronos_run.py` CLI (`start` gate subprocess check, `forecast` isolated execution, `score` cost calculation).
   14 unit tests in `test_kronos_runner.py` and `test_isolation.py` pass; `phase7_gate.py --revision kronos-v1` live PASS.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits.

## 2026-08-20 — Gemini/Antigravity — review Batch #6 (9 tickets per D038) (all PASS)
Reviewed batch #6 at tip (`4199c69`). Gate PASS (1,108 passed, 0 failed);
pyrefly 0 errors; python pins agree (3.14.7); alembic single head (`e1a7c4f9b2d3`).
1. T126 (2435dd7) PASS: `AGENTS.md` + `REVIEW.md` + `DECISIONS.md` codified D038 batch protocol.
2. Hygiene #6 (6dbfa34) PASS: 5 stale seed checkboxes closed with archive pointers; T062b remainder trimmed.
3. T127 (a471ff6) PASS: `scripts/phase7_gate.py` code-enforced gate (custody, budget, contamination rule, isolation);
   8 tests in `test_phase7_gate.py` pass.
4. T129 (355d2c2) PASS: `scripts/health_check.py` feed outage checks (unreachable and stale feed); 5 tests pass.
5. T130 (f844f8f, d371830) PASS: `scripts/secret_check.py` tracked-file scan, `.env.example`<->`settings.py` parity,
   `SecretStr` floor; 7 tests pass.
6. T116b (355a3c0) PASS: `short_horizon.py` event-aware caveat note without distorting distribution bands; 5 tests pass.
7. T087-Orb (a5b0c02) PASS: `apps/web/orb.html` monitor panel rendering `/api/monitor` (days lens first, alerts, blind spots,
   advisory footer, HTML escaping); 2 tests pass.
8. T128 (5f5c6c4) PASS: `docs/RUNBOOK.md` 8 incident procedures grounded in shipped scripts; 2 tests pass.
9. T132 (4199c69) PASS: `README.md` delta for all new surfaces.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits.

## 2026-08-20 — Gemini/Antigravity — review Batch #5 (T125, T124, T087c, T123, curation #5) (all PASS)
Reviewed batch #5 at tip (`0885039`). Gate PASS (1,079 passed, 0 failed);
pyrefly 0 errors; python pins agree (3.14.7); alembic single head (`e1a7c4f9b2d3`).
1. T125 (c5b2985) PASS: `scripts/check_pyrefly.py` checks returncode 0 and 0 errors; wired as verify step;
   `pyrefly>=1.2,<2` pinned in requirements. Installed pyrefly in venv; verified 0 errors.
2. T124 (371d46e) PASS: `scripts/restore_check.py` read-only restore drill (temp copy, PRAGMA integrity_check,
   per-table comparison vs live DB, schedulable exit codes 0/1/2). 8 unit tests in `test_restore_check.py` pass.
3. T087c (055b775) PASS: `backend/api/monitor_service.py` shared fetch-and-judge service; `GET /api/monitor`
   endpoint wired with labeled lenses (days first, timeframe on structure, week change, context note); 7 unit
   tests in `test_monitor_service.py` pass.
4. T123 (a909a03) PASS: `AGENTS.md` contract refresh (pyrefly gate, 5 free-tier sources, D035 doctrine, D033 review SHAs).
5. Curation #5 (0885039) PASS: Batch #4 signed review entry + 5 signed backlog blocks (T101, T100, T108, T106, T069)
   archived verbatim to `archive/TASKS-archive-2026-08-20.md`, keeping `TASKS.md` within budget (~450 lines).
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits.

## 2026-08-20 — Claude/Cowork — Batch #9: BLOCK fixed, Phase 5 begins, voice seam proven
Gemini's verdicts arrived mid-claim: T122d PASS, batch #8 PASS, batch #7
BLOCK on T122c (naked pandas import - his clean venv caught what my
ambient sandbox hid). Fixed FIRST at 1a9ed3a (I036 closed, batch #7
re-queued at that SHA). Then seven probe-backed units: curation #9
(T122d + batch #8 archived); T136 PWA shell at f822255 - Phase 5 begins
per D004, and the service worker may cache the SHELL but never money
(pinned: the /api guard runs before any cache logic); T137 EDGAR
earnings backfill at 954751d (idempotent, real-clock bmo/amc, owner runs
--watchlist); T140 at 0b995b7 - one model load per campaign day instead
of three, per-symbol failures isolated, predict_batch refused by name
(equal-length constraint would silently truncate); T074b sandbox half at
0fec77a - pipecat 0.0.108 probed live and the KuberaChatProcessor routes
voice through OUR /api/chat with the thread carried across turns and
failures SPOKEN; ISSUES swept (19 fixed entries out of Open; five live
remain). +11 tests; gate PASS bare-exit before every commit - the I035
rule held all batch. Next: Gemini re-reviews T122c at 1a9ed3a + reviews
batch #9; owner's pre-Monday sequence unchanged (shape check, then
Monday forecasts now via forecast_batch by default).

## 2026-08-20 — owner + Claude/Cowork — KRONOS CAMPAIGN STARTED (attempt 1/3)
The owner ran `kronos_run.py start`: gate OPEN on his machine, attempt 1
recorded with 2 remaining. Confirmed from the sandbox against the same
DB (`status`: 1/3 used, 0 forecasts, window opens 2026-08-24). The first
Phase 7 experiment is live under the pre-registered protocol. Before
Monday: the shape check (no budget cost; a broken adapter found Monday
would cost session coverage instead — paper-forward days don't come
back). Terminal note passed to owner: the black-diamond characters in
his console are cp1252 rendering of em-dashes, cosmetic only
(`chcp 65001` or PYTHONIOENCODING=utf-8 fixes the display).

## 2026-08-20 — Claude/Cowork — Batch #8: D021 evidence machinery + paperwork truth
Probe-sized at 3, and the probe SPLIT a fourth ticket out: tier/breaker
history was persisted NOWHERE — the Sept-12 D021 revisit would have
arrived evidence-less. T135 at 3032c73: risk_events table (migration
c8e4f2a91d63, live DB migrated) + deduped observation-based recording
wired into the brief's risk section (engine stays pure); recording began
today and every consumer SAYS so. T134 same commit:
scripts/d021_evidence.py assembles exactly the deferral's three metrics
(weekly DQS trend via the brief's own scorer, override rate from the
journal — UNKNOWN when unmarked, never zero — and the event history),
recommends NOTHING, ran live (found 1 journaled decision, all gaps
named). Hygiene #7 + briefs at 49bb5c8: TASKS header replaced (was
recommending a week-old build order), agent-briefs gains the D034-D038 +
pyrefly-zero doctrine card and stops recommending shipped ticket pairs.
Verified: 5 fixture tests + live packet run + migration on the live DB;
two-strikes rule fired for real on a fixture (two NOT-NULL discoveries →
copied a working constructor instead of a third try). Gate PASS at
close. Batches #7 AND #8 now await Gemini. Owner: push to origin when
convenient (local ~15 commits ahead; CI proves green only on push).

## 2026-08-20 — Claude/Cowork — Batch #7: T122c adapter + T133 status + curation #8
Honestly sized at 3 (the backlog held no more; D038: target, never
quota). T122c at 1731adf: the adapter written against the FRESHLY-FETCHED
Kronos README API - OHLCV rides the payload (misalignment refuses),
machine paths ride --model-config (never committed), and the
distribution is drawn (N_PATHS=30 independent samples; sample_count
stays 1 because the documented parameter AVERAGES paths - an averaged
point is what the pre-registration refuses); kronos_shape_check.py
proves the adapter answers on synthetic bars BEFORE an attempt is spent;
adapter reviewability pinned by test (T122b objection made it the
control). T133: `status` subcommand, counts and dates only, anti-peek
pinned (no price/coverage can appear mid-window); run live (opens in 4
days, 0/3, 0 logged). Curation #8: T122b's double-signed record
archived. Process slip recorded: backticks-in--m + a semicolon-broken
chain let a commit land past a red pyrefly - caught same-minute, amended
to 1731adf, messages now via -F. Canary exactly 0 (one narrow, reasoned
ignore for the out-of-repo model import). Gate PASS at close. OWNER
SEQUENCE before Monday: clone Kronos repo + make its venv, run
kronos_shape_check.py (downloads weights, must PASS), then
`kronos_run.py start`.

## 2026-08-20 — Claude/Cowork — T122b: the Kronos runner (campaign machinery)
Owner confirmed GATE OPEN on his machine (T127 acceptance), then the
runner shipped: ResearchForecast + migration a3d9e8c1f5b7 (scratch-proven,
live DB migrated), run_isolated_json (JSON seam, same T110b guarantees,
model venv via python=), kronos_runner.py (log-as-made with re-forecast
refused, paper-forward enforced AT THE SEAM - history reaching the target
date refuses, hand-computed coverage + equal-weight toy-rule scorer,
UNSCORABLE never consumes, consume-once via real custody), kronos_run.py
CLI (start spends 1 of 3 attempts only if the gate subprocess prints
OPEN; forecast has NO built-in model by design; score --consume once with
2x-T090 default costs). Verified: 14 new tests incl. real boundary
subprocesses; CLI smoked live - the smoke FOUND a raw traceback on
missing table (named to NOT CONFIGURED exit 2) and the pipe-eats-exit-
codes trap tried me again (caught, codes re-measured bare). Gate PASS
1,119. Remaining before attempt one (owner): model download + write the
adapter file (forecast(payload)->dict against Kronos) - seeded as T122c.
Window opens Mon 2026-08-24.

