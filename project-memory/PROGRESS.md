# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
Budgets are ENFORCED by the verify gate (T112/D031): archive_memory.py --check
warns at 700 lines and fails at 1,000; `python scripts/archive_memory.py` moves
old entries (verbatim, never deleted) to /project-memory/archive/.

## 2026-08-21 - T157i: real index levels + ticking candles (Claude/Cowork)

**Built:** owner round two: /api/indices (Finnhub-live -> FRED-close ->
named unavailable; ETF dollars banned as index levels, %% line labeled)
+ FinnhubClient.quote(); candle panel live-ticks the forming bar every
5s while open, LIVE/CLOSED badge explains after-hours stillness. SHA
ee6f011.

**Verified:** gate PASS 1,206; node 0.

**Next:** owner refreshes DURING MARKET HOURS to see the tick; first
load shows which index rung his keys serve. Gemini queue: ee6f011 +
T157h/g SHAs.

**Blockers:** none.

## 2026-08-21 - T157h: owner feedback round + index37 additions (Claude/Cowork)

**Built:** all 8 owner findings addressed with an approved plan first:
dead-button root cause fixed (document-level ask delegation), home nav,
live-refreshing performance chart, D040 ambient conversation (history
UI retired, silent resume), index37 row (live Dow/S&P/NASDAQ proxy
cards, rotating licensed-feed news, portfolio chart, hand-drawn
candlestick panel of the top holding w/ 5m/1D/1Y/5Y incl. weekly-
aggregated deep history), REAL calendar with /api/events dots
(FOMC + recorded earnings), trading-days matrix, positions table.
New endpoints: /api/events, /api/market/{sym}/intraday-bars.

**Verified:** gate PASS 1,202; node 0; scans clean. SHAs 77e15e3/c7d74cb/361b094.

**Next:** owner refreshes and re-tests his 8 points. Gemini queue:
77e15e3 c7d74cb 361b094 + T157g SHAs.

**Blockers:** none.

## 2026-08-21 - T157g: the approved index36 rebuild ships (Claude/Cowork)

**Built:** owner drove a formal spec process (analyze reference -> map ->
approve) and the page is now index36 with KUBERA organs: header icon
chips + command box, hero greeting with the orb inside the white mic
circle, VISA-anatomy account card, income rows, breaker circle +
budget donut, amber sparkline, monitor-as-activity-manager with P&L
bars + payoff Upgrade card, allocation circles, ET session card, amber
FAB chat drawer. Fonts vendored locally via owner-run fetch_fonts.py +
/fonts route. QA checklist at docs/design/index36-qa.md.

**Verified:** gate PASS 1,198; node --check 0; dangling-id scan clean;
pins extended and green; voice loop untouched.

**Next:** owner: (1) python scripts/fetch_fonts.py once, (2) restart +
refresh, (3) judge against his screenshot - the two eye-items in the QA
doc. Gemini queue: 4100c6d + 9f32007 + close SHA (+ prior UI SHAs).

**Blockers:** none.

## 2026-08-21 - T157f: the index36 experience, from the owner's screenshot (Claude/Cowork)

**Built:** owner posted the target's screenshot (first pixel ground
truth; corrects T157e - index36 is black+violet). Full experience on
real data: pill-nav views, hero gradient card, delta badges, live
status pills, ask-KUBERA corner arrows, violet area chart with tooltip
+ real range pills, conversations/debts tables. SHA 74c85af.

**Verified:** gate PASS 1,197; node --check 0; all pins green.

**Next:** owner refreshes and compares against HIS screenshot. Gemini
queue: 74c85af + prior unsigned UI SHAs.

**Blockers:** none.

## 2026-08-21 - T157e: crypto-admin skin, from source (Claude/Cowork)

**Built:** owner wanted the crypto-admin look; its skin_color.css WAS
fetchable - dark skin adopted verbatim (blue-navy #0c1a32 field, glass
#112547, white-alpha hairlines, amber #ffa800 as THE accent incl. the
chart series, link-blue #4F80D5 interaction, orb states recolored).
Webfonts not adopted (no CDN). Doc tokens v3 with provenance; manifest
colors follow.

**Verified:** gate PASS 1,196; node --check 0; zero-leftover hex scan;
pins green.

**Next:** owner refreshes and judges (third loop). Gemini queue:
b76f444 + 2124b40 + 89e4494 as unsigned.

**Blockers:** none.

## 2026-08-21 - T157d: the glass pass (Claude/Cowork)

**Built:** owner's round-two references were MINABLE - buck-net's
tailwind.config fetched raw; its literal palette + glassmorphism applied
across the dashboard (glass cards on a glowing navy field, one hue per
job: amber brand / teal data / blue interaction), orb states included;
manifest + design-doc tokens v2 with extraction provenance; crypto-admin
+ glasshome unfetchable and said so.

**Verified:** gate PASS 1,196; node --check 0; zero old-hex leftovers by
scan; all pins green.

**Next:** owner opens it (his eyes = acceptance); Gemini reviews 2124b40
(+ 89e4494 batch #15 if unsigned).

**Blockers:** none.

## 2026-08-21 - Batch #15: DASHBOARD V1 ships (Claude/Cowork)

**Built:** the owner sent six dribbble references ("neat, and not just
an Orb") - pages are client-rendered and his Chrome extension was
offline, so the design language (T157a) is genre-derived with that
provenance STATED and his visual review named as the acceptance gate.
T157b: GET /api/household (debts, utilization, staleness, payoff
compare; refusals served, never hidden). T157c: orb.html is now the
trading desk - topbar, 6 KPIs, four cards, conversation docked right,
voice loop byte-identical.

**Verified:** gate PASS 1,196 (+7); node --check 0; no-CDN pin green;
voice/PWA pins untouched and green.

**Next:** owner OPENS IT (uvicorn up -> http://127.0.0.1:8000/) and
corrects against his references - that loop is the design process now.
Gemini reviews b9a3d56 + df9c279 (+ a608682/3ba7642 if unsigned).
T154-T156, T158 remain seeded.

**Blockers:** none.

## 2026-08-21 - Batch #14: PHASE 9 BEGINS - D039 + household schema + payoff planner (Claude/Cowork)

**Built:** Owner directed the next front: household finance + a full
dashboard ("futuristic... like finrobot") with debt payoff, credit
cards, spending, budget. D039 records his three picks (one phase,
chat+CSV, ONE surface). T152: debts/flows/spending schema + strict
store (units refused not guessed; manual-data recency in the schema).
T153: avalanche-vs-snowball payoff engine, hand-computed, impossible
plans refused by name. Seeds T154-T158 queued (budget engine, chat
tools, CSV import, dashboard v1, briefs).

**Verified:** gate PASS 1,189 (+16); alembic single head d4b8f1a6c2e5;
pyrefly 0 (it refused T153's first commit - second live save).

**Next:** Gemini reviews batch #14 + I039 (3ba7642). Then T154+T155
(budget engine + chat tools) next batch; dashboard v1 (T157) after the
math is signed. Owner: alembic upgrade head on his machine when he
pulls; Monday Kronos sequence unchanged.

**Blockers:** none.

## 2026-08-21 - I039: /api/tts 500 fixed (voice-name validation) (Claude/Cowork)

**Built:** owner's incident (edge-tts name in KUBERA_VOICE -> kokoro
assert -> 500 killed speech) fixed at 3ba7642: validate against the
model's own voices list, fall back to default WITH a named log, never a
bare assert; .env.example documents the knob; secret_check taught that
runtime os.environ reads count as "read" (it flagged the new doc line -
checker upgraded, not allowlisted).

**Verified:** gate PASS 1,173 (+4); incident-verbatim test; secret_check
live CLEAN.

**Next:** Gemini reviews 3ba7642 (+ batch #13 still in queue at
70f6f63... batch #13 was PASSed at f5ece0b - queue is 3ba7642 only).
Owner: fix or delete KUBERA_VOICE in .env; voice works either way now.

**Blockers:** none.

## 2026-08-21 — Gemini/Antigravity — review Batch #13 (curation #13, T150, T151) — PASS
Reviewed Batch #13 at 70f6f63:
1. Curation #13 (ed06ed2) PASS: Batch #12 double-signed record archived into `TASKS-archive-2026-08-20.md`; T067c probe note verified (gate stands, query one-liner documented).
2. T150 (0c051a2) PASS: `risk_events_week` in `compose_weekly_review` tested live in Python; quiet week correctly asserts stated fact in `facts_for_lessons`, populated events correctly format counts and quotes the last event verbatim; 2 unit tests pass.
3. T151 (31a7c32) PASS: README documentation updates verified for campaign brief line, notification bell, backup freshness watch, and weekly risk events history.
4. Verification: Full gate PASS (1,169 passed, 3 skipped), pyrefly 0 errors, python pins agree: 3.14.7, alembic single head `c8e4f2a91d63`.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits, no new files, no ISSUES entry (no new defects found).

## 2026-08-21 - Batch #13: curation + weekly risk events + README (Claude/Cowork)

**Built:** curation #13 (ed06ed2, incl. T067c probe note: gate STANDS,
owner one-liner to check time-stamped fill accumulation). T150
(0c051a2): weekly review surfaces the week's risk events - counts, last
event verbatim, quiet week stated as fact (the D021 trail visible where
the owner reads). T151 (31a7c32): README delta for campaign line / bell
/ backup watch / risk events, honest limits in-sentence.

**Verified:** gate PASS 1,169 (+2), pyrefly 0, budgets in bounds.

**Next:** Gemini reviews batch #13. Monday: Kronos sequence; the brief
shows the campaign line.

**Blockers:** none.

## 2026-08-21 — Gemini/Antigravity — review Batch #12 (curation #12, T149, hygiene #8) — PASS
Reviewed Batch #12 at 2a0f114:
1. Curation #12 (1885ca5) PASS: Batch #11 double-signed record archived into `TASKS-archive-2026-08-20.md`.
2. T149 (2e6ff54) PASS: `campaign_section` tested live in Python; 0 attempts returns None, pre-window reports open date, in-window without today's forecast delivers coverage nudge, in-window with forecast is quiet, post-window shows `score --consume` status; anti-peek invariant holds (no outcome keys); 4 unit tests pass.
3. Hygiene #8 (a5af35f) PASS: `AGENTS.md` environment-premise class section verified; stale seeds in `TASKS.md` corrected.
4. Verification: Full gate PASS (1,167 passed, 3 skipped), pyrefly 0 errors, python pins agree: 3.14.7, alembic single head `c8e4f2a91d63`.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits, no new files, no ISSUES entry (no new defects found).

## 2026-08-21 - Batch #12: curation + campaign-in-the-brief + environment lesson (Claude/Cowork)

**Built:** curation #12 (1885ca5). T149 (2e6ff54): morning brief's
research_campaign - attempts/counts/dates only (T133 anti-peek held by
test), window state, missed-day nudge; silent when unconfigured. Hygiene
#8 (a5af35f): I036/I037/I038 named as ONE environment-premise class in
AGENTS.md; stale seeds T122c/T074b corrected.

**Verified:** gate PASS 1,167 (+4), pyrefly 0. CI-drift probe was CLEAN
(ci.yml already runs scripts/verify.py) - killed, not padded.

**Next:** Gemini reviews batch #12 (close SHA carries manifest). Monday:
owner runs the Kronos sequence; the brief now shows the campaign line.

**Blockers:** none.

## 2026-08-21 — Gemini/Antigravity — review Batch #11 (curation #11, T146, T147, T148) — PASS
Reviewed Batch #11 at 38b4ad8:
1. Curation #11 (19617cb) PASS: Verified archive file `TASKS-archive-2026-08-20.md` with Batch #10 and I038 fix double-signed records.
2. T146 (c6bff8f) PASS: Pydantic-settings version capped at `>=2.2,<3` in `requirements.txt` to eliminate environment drift; dead code removed in `brief.py`.
3. T147 (145df84) PASS: Orb notification bell in panel header; permission on user gesture; per-symbol+kind transition tracking prevents burst on enable; honest only-while-open tooltip scope; `node --check` exit 0.
4. T148 (4d45d74) PASS: `scripts/health_check.py:check_backup` tested live in Python across missing/empty/fresh/stale states with `--max-backup-age` flag support; 4 unit tests pass.
5. Verification: Full gate PASS (1,163 passed, 3 skipped), pyrefly 0 errors, python pins agree: 3.14.7, alembic single head `c8e4f2a91d63`.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits, no new files, no ISSUES entry (no new defects found).

## 2026-08-21 - Batch #11: curation + drift pin + the bell + backup watch (Claude/Cowork)

**Built:** curation #11 (19617cb: batch #10 + I038 archived, both
double-signed). T146 (c6bff8f): pydantic-settings capped <3 after the
first observed cross-machine drift (owner's newer build warns on
FastMCP's 'lifespan' - third-party, cosmetic, recorded not "fixed");
dead week_ago swept. T147 (145df84): Orb bell - monitor alerts become
OS notifications on NEW transitions only, permission on gesture,
honest only-while-open scope (push stays a named gap). T148 (4d45d74):
health_check watches backup freshness (newest mtime >30h or empty dir
-> named problem + what to do; --max-backup-age).

**Verified:** full gate PASS 1,163 tests, pyrefly 0, node --check 0,
new-cap pip resolve confirmed live.

**Next:** Gemini reviews batch #11 (close SHA carries manifest).
Owner: Kronos pre-Monday sequence unchanged; push to origin.

**Blockers:** none.

## 2026-08-21 — Gemini/Antigravity — review I038 fix (89a016c) — PASS
Reviewed I038 ambient-env test isolation fix at 89a016c:
1. Conftest autouse session fixture `_ambient_settings_env_stripped` removes all model-derived settings environment variables from `os.environ` before any test runs.
2. Verified 3 new isolation tests in `test_env_isolation.py` and tested all 62 config/missing-key tests with planted hostile ambient environment variables (`EDGAR_CONTACT`, `FINNHUB_API_KEY`, `FMP_API_KEY`, `SCHWAB_*`, `ALPACA_*`, `LLM_TIMEOUT_SECONDS`).
3. 4 test files restored to clean `KuberaSettings(_env_file=None)` syntax without per-test keyword overrides.
4. Full verify gate PASS (1,158 passed, 3 skipped), pyrefly 0 errors, python pins agree: 3.14.7.
Self-diff check: touched ONLY `project-memory/TASKS.md` and `project-memory/PROGRESS.md`. No code edits, no new files, no ISSUES entry.

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

