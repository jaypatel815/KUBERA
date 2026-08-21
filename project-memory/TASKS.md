# TASKS

One ticket = one focused agent session. Claim by adding your name as owner.
IDs never get reused. Format per PROJECT_SPEC.md §11.

**Current state (hygiene #7, 2026-08-20 — the old D018 build-order here
referenced tickets shipped a week ago):** batches run under D038 (size
follows coupling). The active front is the KRONOS CAMPAIGN — pre-registered,
gate OPEN, window 2026-08-24..2026-10-02; owner sequence: shape check →
`kronos_run.py start` → daily `forecast` → `score --consume` once at end.
The D021 revisit (~2026-09-12) decides shorts/pairs/HRP on evidence —
`scripts/d021_evidence.py` assembles it; risk-event history records from
2026-08-20. Owner actions that unlock the most: T007 finale, pushing to
origin (local runs ahead — CI confirms green only on push), and triggering
Gemini on anything in Awaiting review.

## In progress
- **T141 (symbol universe + find_symbol) - Claude/Cowork** - claimed
  2026-08-20 on the owner's direction: "KUBERA shouldn't only focus on
  specific symbols - it should have knowledge of every symbol in the
  market." Probe findings: the data tools are ALREADY universal (any
  symbol on demand), but ticker RESOLUTION relies on LLM memory - the
  I007 wrong-symbol class. Fix: EdgarClient's already-fetched SEC
  company_tickers.json (every US registrant: ticker/name/CIK, keyless)
  becomes a directory; new deterministic find_symbol tool (#45) resolves
  names -> tickers with scored candidates, a labeled live-quote probe
  for ticker-shaped misses (ETFs/trusts absent from the SEC map), and
  named refusals - never a guessed ticker. Guards 44->45; MCP +1.
## Awaiting review (D023 — a DIFFERENT agent signs these off; see REVIEW.md)
- **Batch #9: T122c-fix + curation#9 + T136 + T137 + T140 +
  T074b-headless + ISSUES-sweep - AWAITING REVIEW 2026-08-20
  (Claude/Cowork; owner asked 8-10, probes yielded 7 real units + the
  BLOCK-fix, D038 never pads). SHAs per D033: 1a9ed3a (T122c fix -
  ALSO re-queues batch #7's blocked ticket at this SHA) / 8b3bb2f
  (curation #9) / f822255 (T136) / 954751d (T137) / 0b995b7 (T140) /
  0fec77a (T074b) / close SHA on this commit (ISSUES sweep + memory).**
  T122c-FIX at 1a9ed3a: Gemini's clean venv caught the naked pandas
  import my sandbox's ambient pandas hid - narrow ignore + incident
  comment added (I036 closed); the environment-dependence lesson is in
  the commit: a clean-checkout gate run (D027 #2) would have caught it
  before review.
  T136 - PWA SHELL at f822255 (Phase 5 BEGINS, per D004's PWA decision
  not the spec's Flutter line - tension named): manifest + original SVG
  icon + service worker + registration + routes. THE doctrine call: the
  shell is cache-first, but /api/*, /portfolio and /health are
  network-ONLY - a cached price is stale data presented as current.
  Pinned by test: the money guard runs BEFORE any cache logic and the
  shell list may never contain an API path. Owner field test: open the
  Orb on the phone, the browser offers Install.
  T137 - EARNINGS BACKFILL at 954751d: EDGAR history (years, real
  acceptance clocks) was fetched per-call and persisted nowhere;
  scripts/earnings_backfill.py derives bmo/amc/during from the REAL
  clock (hand-checked incl. the 09:30 boundary; None when EDGAR omits),
  upserts idempotently through the store's own semantics (second run
  changes zero rows; FMP-enriched rows keep eps + provenance), names
  failures per symbol. Owner: py scripts\earnings_backfill.py --watchlist.
  Verification caught a wrong model-name guess (WatchlistEntry) before
  ship.
  T140 - ONE MODEL LOAD at 0b995b7: adapter splits _predictor (once) +
  _one_symbol; forecast_batch runs all holdout symbols on one load
  (three ~102M loads/day -> one) and a venv/config mistake surfaces on
  the single call BEFORE any row logs. predict_batch deliberately NOT
  used - its equal-length constraint would silently truncate; refusal
  named in source and pinned by test. call_model_batch returns
  (dists, named_errors) - a failed symbol never poisons neighbors,
  proven via a BAD-symbol child through the real boundary. --func
  defaults forecast_batch; shape check keeps the single path; adapter
  121 lines, under the reviewability pin.
  T074b (SANDBOX HALF) at 0fec77a: the probe held - pipecat 0.0.108
  imports headless, API introspected LIVE (TranscriptionFrame fields,
  process_frame/push_frame signatures). KuberaChatProcessor routes
  utterances through OUR /api/chat (the hard part T074a named):
  voice=True every turn, conversation id carried across turns, dead
  server becomes a SPOKEN degradation ending "Nothing was decided or
  placed." pipecat pinned in requirements-voice.txt ONLY; per-test
  importorskip (I016); pipecat imports carry I036-class ignores
  PROACTIVELY. Remaining owner-machine: audio transport, STT, kokoro,
  latency + barge-in measurement.
  ISSUES SWEEP (close commit): 19 already-fixed entries moved verbatim
  from Open to Resolved; Open now holds exactly the five live ones
  (I035 pipe rule, I021/I022 blocking caveats, I015 diagnostic, I005).
  EVIDENCE (D027): +11 tests this batch (4 PWA incl. the
  guard-before-cache order pin; 3 backfill incl. idempotency +
  enrichment-survives; 4 batch-call incl. per-symbol isolation through
  the real boundary; 3 voice seam) - all green; RAN LIVE: pipecat
  install + introspection, node --check on sw.js, backfill no-args
  refusal, full gate PASS bare-exit before every commit (I035 rule
  held all batch).
  D028 objections: (1) T136's PWA is installable but push delivery
  remains the named gap (needs a push service; T062b's remainder
  stands). (2) T140 changes forecast mechanics pre-window - legitimate
  (no forecast exists; the frozen hash covers symbols/dates, not
  plumbing) but a reviewer should confirm they agree. (3) The voice
  seam tests call _chat_turn directly rather than through a full
  pipecat pipeline - the pipeline harness needs a running loop and
  audio frames; the seam contract is what the sandbox can honestly
  pin. BATCH COUPLING NOTE (D038): T122c-fix + T140 both touch the
  kronos files (sequential, one builder); everything else disjoint.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 752318c (SHAs: 1a9ed3a, 8b3bb2f, f822255, 954751d, 0b995b7, 0fec77a, 752318c) — BLOCK (CRITICAL on T074b, PASS on T136 / T137 / T140 / Curation #9 / ISSUES sweep)
    aligned: Batch #9 — T122c-fix, PWA shell (T136), EDGAR earnings backfill (T137), one model load batching (T140), Pipecat voice chat seam (T074b), ISSUES sweep & curation #9.
    checked:
      - T136 (PASS): Read `apps/web/sw.js`, `manifest.json`, `orb.html`, `backend/tests/test_pwa.py`: verified cache-first shell with network-only money guard for `/api/*`, `/portfolio`, `/health`. 4 unit tests pass.
      - T137 (PASS): Read `scripts/earnings_backfill.py`, `backend/tests/test_earnings_backfill.py`: verified EDGAR clock parsing (bmo/amc/during), idempotent store upsert, per-symbol error reporting. 3 unit tests pass.
      - T140 (PASS): Read `scripts/kronos_adapter.py`, `backend/research/kronos_runner.py`, `backend/tests/test_kronos_runner.py`: verified `_predictor` singleton, `forecast_batch` execution, per-symbol failure isolation. 4 unit tests pass.
      - Curation #9 & ISSUES sweep (PASS): Verified archive and issues cleanup.
  FIXED by builder (2026-08-20): all four inline pipecat imports in the
  test file now carry the narrow ignore (I037 closed); canary exactly 0;
  T074b RE-QUEUED for re-review at the fix SHA (D033). Same lesson as
  I036 one layer deeper - the clean-checkout gate run (D027 #2) is the
  only local defense against ambient-dependency blindness.
      - T074b (BLOCK - CRITICAL): Read `backend/tests/test_voice_pipeline.py`. Lines 63, 64, 92, 105 have unsuppressed `from pipecat...` imports without `# pyrefly: ignore`. Because `pipecat` is in `requirements-voice.txt` (optional, not installed in the standard environment where `scripts/verify.py` and `scripts/check_pyrefly.py` run), running `verify.py` fails with 4 errors (`ERROR Cannot find module pipecat... [missing-import]`), failing the verify gate (`types (pyrefly = exactly 0)`).
    concerns:
      1. CRITICAL: Add `# pyrefly: ignore` to `from pipecat...` import lines in `backend/tests/test_voice_pipeline.py` (lines 63, 64, 92, 105) so the type gate stays at exactly zero errors. Tracked as I037 in ISSUES.md.

- **Batch #7: T122c + T133 + curation #8 - AWAITING REVIEW 2026-08-20
  (Claude/Cowork; honestly sized at 3 - the backlog held no more
  unblocked work, and D038 says size is a target never a quota).
  SHAs per D033: 1731adf (T122c+T133, one commit - they share
  kronos_run.py) / close SHA on this commit (curation #8 + memory).**
  T122c - THE ADAPTER, against the DOCUMENTED API: Kronos README fetched
  fresh 2026-08-20 (KronosPredictor.predict over an OHLCV DataFrame;
  `model` package lives in the Kronos repo, not pip). Three consequences
  built: (1) runner payload gains aligned OHLCV (misalignment refuses by
  name); (2) machine-local paths NEVER enter committed files - the repo
  location rides `--model-config kronos_repo=...` into the payload;
  (3) sample_count stays 1 and the adapter draws N_PATHS=30 independent
  samples to build empirical percentiles, because the documented
  sample_count AVERAGES paths and an averaged point is exactly what the
  pre-registration refuses. kronos_shape_check.py proves the adapter
  answers on SYNTHETIC bars before an attempt is spent (fixture data by
  design, logged nowhere). Adapter reviewability is the control for the
  recorded T122b objection - pinned by test: under 140 lines, no machine
  paths, sample_count=1 present. The out-of-repo `model` import carries
  the narrowest pyrefly ignore with its reason (I023 rule intact:
  canary back to exactly zero).
  T133 - CAMPAIGN STATUS as a CLI subcommand (deliberately NOT a
  registry tool: no guard-count coupling; chat gets it later if usage
  demands, the T119 disposition logic): holdout state+hash, window with
  days-to-open/remaining, budget used, forecast counts per symbol/
  session - and NOTHING ELSE. Anti-peek pinned by test: no price,
  return, or coverage figure can appear mid-window; the one evaluation
  happens at consumption.
  CURATION #8 - T122b's double-signed record (Gemini PASS at e5fdaeb,
  review cd8b53b, concerns none) moved verbatim to
  archive/TASKS-archive-2026-08-20.md.
  EVIDENCE (D027): test_kronos_runner.py now 15 tests (+3 T122c: ohlcv+
  config PROVEN to cross the real boundary via echo-child; misalignment
  refused; adapter reviewability pins; +1 T133 status on a real file DB
  with the anti-peek assertion). RAN LIVE: `kronos_run.py status`
  against the real DB (opens in 4 days, 0/3 attempts, 0 logged, BY
  DESIGN note printed); pyrefly at exactly 0 after the narrow ignore;
  full gate PASS at close.
  D028 objections, written down: (1) the adapter is UNEXECUTED code -
  the sandbox cannot run Kronos; the controls are the documented-API
  fetch, its enforced smallness, call_model's output validation at every
  use, and the owner-run shape check that must PASS before `start`. If
  the README's API drifted since publication, the shape check is where
  it surfaces, not mid-campaign. (2) PROCESS SLIP on the record: the
  first T122c commit landed past a red pyrefly because a semicolon broke
  the && chain, and backticks in -m executed as command substitution
  and ate a message line - caught in the same minute, amended to
  1731adf; commit messages now go through -F files, chains stay pure &&.
  (3) N_PATHS=30 gives coarse p05/p95 granularity (nearest-rank on 30
  samples); acceptable for a first candidate whose bar is a WIDE
  calibration band, and raising it is a one-constant change the
  pre-registration does not pin.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 1731adf (SHAs: 1731adf, 7356c8b) — BLOCK (CRITICAL on T122c, PASS on T133 / Curation #8)
    aligned: Batch #7 — T122c (Kronos adapter & shape check), T133 (campaign status CLI), Curation #8.
    checked:
      - T133 (PASS): Read `scripts/kronos_run.py` status subcommand; anti-peek invariant verified by test and live run.
      - Curation #8 (PASS): Archive verified.
      - T122c (BLOCK - CRITICAL): Read `scripts/kronos_adapter.py`. Line 50 has unsuppressed `import pandas as pd`. Because `pandas` is not in KUBERA's root venv, running `python scripts/verify.py` or `python -m pyrefly check` from `backend/` fails with 1 error (`ERROR Cannot find module pandas [missing-import]`), failing the verify gate (`types (pyrefly = exactly 0)`).
    concerns:
      1. CRITICAL: `scripts/kronos_adapter.py:50` requires narrow `# pyrefly: ignore` with an explanatory comment (like line 55) so the type checker gate stays at exactly zero. Tracked in ISSUES.md as I036.
  FIXED by builder at 1a9ed3a (2026-08-20): pandas import carries the
  narrow ignore + incident comment; gate PASS bare-exit; I036 closed.
  T122c RE-QUEUED for re-review AT 1a9ed3a (D033 - the old verdict
  covers 1731adf and nothing after).
  REVIEWED (re-review) 2026-08-20 by Gemini/Antigravity AT 1a9ed3a — PASS
    aligned: T122c BLOCK resolution — narrow `# pyrefly: ignore` added to `scripts/kronos_adapter.py:50`.
    checked:
      - Read `scripts/kronos_adapter.py:50`: verified ignore comment and explanation; pandas error in pyrefly resolved.
      - Shape check verified on owner's machine (`SHAPE CHECK: PASS`).
    concerns: none.



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
- [x] T076b — built 2026-08-18, see Awaiting review at top (published-table
  FOMC dates + priced-for-perfection flag; earnings half was already done
  via T023/T083).
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
  buys. T093's extension (marginal risk contribution, effective bets) SHIPPED with parts 1+3 — see analysis/portfolio_risk.py (T093c verified 2026-08-19).
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
  trimmed to the earnings-dates gap (T023/T076b). REMAINING trimmed by hygiene #6
  (2026-08-20): ET-aware windows shipped as T036b/T111, scheduled
  generation as T062c (scripts/brief.py, no server needed) — both
  consumed. Still open here: PWA push delivery only (Phase 5, Flutter).
- [x] T063b — BUILT 2026-08-19, see Awaiting review (ships thin-data-honest now; grows informative as the journal ages).
- [x] T064b — Rigor follow-ups COMPLETE 2026-08-19: core (richer
  run_backtest + promotion expiry) DONE 2026-08-14; crisis-window stress
  runs BUILT 2026-08-19 (see T064b-rest in Awaiting review; 2008 named
  impossible on this feed). Promote-via-chat stays parked by design — the
  deliberate-act confirmation design doesn't exist yet; CLI remains the
  promotion instrument.
- [x] T065 — Risk engine v2 COMPLETE 2026-08-19 across two tickets: sector-exposure measurement + disable-symbol (T065, PASSED at 05dfe35-era review) and the order-frequency rail (T065b, see Awaiting review). Cancel-all deliberately unbuilt — nothing rests (market orders only); hard sector CAPS wait on owner-ratified limits (T061) by design.

## Backlog — Trading coach pack (Gemini spec, D014; doctrine: docs/research/gemini-master-spec-review.md)
- [x] T066 — built 2026-08-18, see Awaiting review at top. (Correlation
  section deliberately not duplicated — persona already orders
  get_correlation before buys; entry/exit PRICE quality needs exit prices
  on attribution trips, a future enrichment.)
- [x] T016c — built 2026-08-18, see Awaiting review at top. (Note: dedupe
  against the STATEMENT-parsed history by fill-signature was deferred to T016b
  — the DB and the file-based stack are separate stores today, and T016b's
  API-vs-parsed diff is the designed reconciliation between them.)
- [x] T067b — built 2026-08-18, see Awaiting review at top. (FOMO-into-late-
  RVOL deliberately NOT built — needs an intraday clock on every fill; named
  in every report and re-filed as T067c below.)
- [x] T121b - BUILT 2026-08-20, REVIEWED PASS by Gemini (batch #4; record
  in archive/TASKS-archive-2026-08-20.md). Stale seed closed by hygiene #6.
- [~] T122 - CAMPAIGN STARTED 2026-08-20: the owner ran `kronos_run.py
  start` on his machine - gate printed OPEN (all four rails, isolation
  0.10s), ATTEMPT 1 of 3 recorded, confirmed from the sandbox via
  `status` (1/3 used, 0 forecasts, window opens in 4 days). Remaining
  before Monday's first forecast: the SHAPE CHECK (kronos_shape_check.py
  with the model venv) - it costs no budget, and a broken adapter found
  Monday morning would cost a session's coverage instead (paper-forward:
  a missed session can never be forecast later). Then daily `forecast`,
  `score --consume` once after 2026-10-02.
  (was) PRE-REGISTERED 2026-08-20 (owner picked Kronos as the next
  front; Claude/Cowork executed the registration): docs/research/
  experiments/kronos-v1.md written BEFORE any run (symbols SPY/QQQ/NVDA,
  window 2026-08-24..2026-10-02 forward-only, calibration 80-97% coverage
  + toy-rule-vs-b&h success criteria pre-stated, FAIL is a real answer);
  holdout `kronos-v1-fwd` FROZEN on the live DB (params_hash
  f3237504f1c9e3b1); budget kronos-v1 opened at 3 attempts.
  `phase7_gate.py --revision kronos-v1` run LIVE: all four checks PASS,
  GATE OPEN (custody refused NVDA on the record). REMAINING: owner
  downloads the model (~400MB, huggingface); T122b (seed below) builds
  the runner. Original protocol text preserved below - it is now ALSO
  enforced by the gate script:
  (was) Kronos candidate experiment (Phase 7-GATED; D037; MIT model
  NeoQuasar/Kronos-base 102M params, CPU-feasible ~400MB F32). PRE-
  REGISTERED PROTOCOL REQUIRED BEFORE ANY RUN: (1) THE CONTAMINATION RULE:
  Kronos trained on 12B K-lines through its cutoff - a historical backtest
  is a test ON ITS OWN TRAINING DATA; only post-cutoff or paper-forward
  evaluation counts, full stop. (2) open_budget() BEFORE the first
  attempt; failures count (T110a). (3) holdout frozen before experiment
  one; consumed once (T110a). (4) any glue code runs inside the T110b
  boundary. (5) a Kronos-derived signal reaches the paper loop ONLY
  through the T064 promotion gate + selection rule, like every other
  strategy. (6) D035 stands: forecasts are internal signals; the owner
  hears odds and ranges, never "the model says 770". Fine-tuning on the
  owner's fills: REFUSED (D037).
- [x] T122b - BUILT 2026-08-20, see Awaiting review at top (runner +
  migration + JSON seam + gated CLI; 14 tests; live DB migrated).
- [ ] T122c - the Kronos ADAPTER (last piece before attempt one): a
  self-contained kronos_adapter.py defining forecast(payload)->dict
  {p05_frac,p50_frac,p95_frac,up_odds} that loads NeoQuasar/Kronos-base
  and maps its output distribution to next-day return percentiles.
  Runs ONLY on the owner's machine (model venv with torch; ~400MB
  weights) through kronos_run.py's --model-file/--python seam. Agent
  half: write the adapter + a shape-check script the owner runs before
  `start`; owner half: create the model venv, download weights, run the
  shape check. NOTE the D028 objection recorded on T122b: the adapter
  executes with the model venv's full site-packages - keep it small
  enough to READ before running it.
- [x] T119 - BUILT 2026-08-20 (tool #44 get_thesis_view), REVIEWED PASS by
  Gemini (batch #4; archive/TASKS-archive-2026-08-20.md). Stale seed closed.
- [x] T120 - BUILT 2026-08-20 (.claude-plugin + commands/, owner installed
  live; manifest owner-object fix at fc2d7ff), REVIEWED PASS by Gemini
  (batch #4; archive/TASKS-archive-2026-08-20.md). Stale seed closed.
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
- [ ] T074 — Realtime conversation pipeline (the Zoey-latency upgrade): streaming STT + start-TTS-before-reply-completes + barge-in. FRAMEWORK DECIDED by T074a research (2026-08-19, docs/research/realtime-voice-2026-08-19.md): **Pipecat** — LocalAudioTransport/SmallWebRTC need NO media server (LiveKit's room/media-server design is wrong-shaped for one user on one desktop), KokoroTTSService is a documented service so D024's voice drops in, fully-local stacks hit sub-second in the wild, $0/min. OpenAI Realtime REJECTED on architecture (a speech-to-speech model replaces the brain — persona/rails/tool gates bypassed), not just cost ($0.05–0.46/min measured). No Anthropic speech-to-speech API exists (re-check at build). Build via T074b→T074c below.
- [ ] T074b — Pipecat spike (probe-first, D030): LocalAudioTransport + faster-whisper (or whisper.cpp) STT + CUSTOM processor that calls OUR /api/chat (the hard part — voice-KUBERA must be the same KUBERA: context assembly, tool loop, rails) + existing kokoro TTS. Measure round-trip latency + interruption. Exit: a working persona conversation, or a written finding that the chat-endpoint processor fights the framework (then audio-half-only fallback gets its own ticket).
- [ ] T074c — (after T074b) VAD/interruption tuning, latency vs push-to-talk, Orb mode switch (SmallWebRTCTransport if browser audio beats PyAudio). Push-to-talk stays as a permanent fallback mode.
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
- [x] T101 - pyrefly errors made expressible - DONE 2026-08-16 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).
- [x] T100 - LLM_TIMEOUT_SECONDS in claude-sdk provider (I017) - DONE 2026-08-16 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).
- [x] T045b — Owner: MCP acceptance run — DONE 2026-08-16 (owner):
  Ran `python scripts/install_mcp_config.py`; verified `%APPDATA%\Claude\claude_desktop_config.json` is configured with `.venv` Python interpreter and `scripts/mcp_server.py` stdio entrypoint.
- [x] T108 - expiry-aware FIFO closing - DONE 2026-08-17 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).
- [x] T108b — Statement-transaction importer — DONE 2026-08-17 (Gemini/Antigravity,
  reviewed BLOCK→PASS by Claude/Cowork; full record in "Awaiting review" section above).
  Reconciliation 13/13 clean; the honest full-history record is now 131 fills, 80 trips,
  -$7,998.86 realized, 53.8% win rate (options -$11,706 / equities +$3,707).
- [x] T109 — Pre-registered selection rule + cost stress — DONE 2026-08-17
  (REVIEWED PASS; record in archive/TASKS-archive-2026-08-18.md).
- [x] T110 — Phase 7 preconditions COMPLETE 2026-08-19: T110a (holdout
  custody + experiment budgets, PASSED by Gemini at c54c7e9) + T110b
  (isolation boundary + adversarial probe — see Awaiting review). The
  D029 gate 'Phase 7 does not start without this ticket done' is now
  satisfiable: custody, budgets, parity-proven isolation, custody seam.
- [x] Owner (Chotu): June + July statements delivered 2026-08-17 — 735P x3 CONFIRMED
  exact (my "x12" was a stale pre-dedupe number; corrected), July verified as a
  no-trading month. Keep dropping each new monthly statement in as it posts.
  The missing-confirmation gaps (692P x8, 660P x8, 733P x35, NVDA 182.5P x2) wait
  for T108b — no need to hunt individual PDFs.
- [x] T107 — Base URLs into settings — DONE (Gemini built; Claude re-reviewed
  PASS 2026-08-17 at 516dca5). The two deliberate hardcodes stand with comments:
  Alpaca PAPER base URL (safety rail) and the option multiplier 100 (market
  fact). Full record in archive/TASKS-archive-2026-08-18.md.
- [x] T106 - MCP context lifecycle - DONE 2026-08-16 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).
- [ ] T071 — Owner: voice acceptance run — `pip install -r requirements-voice.txt`, server up, `python scripts\talk.py`, hold a conversation. If faster-whisper wheels fail on Python 3.14 → `set KUBERA_STT=openai`. Report quirks to ISSUES.
- [x] T069 - adaptive risk-tolerance estimation - DONE 2026-08-16 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).

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
- [x] T116 — BUILT 2026-08-20 (batch #3, REVIEWED PASS): short_horizon.py +
  monitor/brief/persona all lead with the days lens (evidence: brief.py:87
  short_horizon in _symbol_read, persona.py:96 LEAD-with-range rule, tool
  #41). REMAINING split to T116b (event-aware lens — in batch #6). Original
  direction preserved below for T116b's contract:
  (was) Short-horizon FIRST (owner direction 2026-08-20, D035): every
  surface leads with the days lens — monitor/symbol briefing/morning brief
  open with "from HERE: next 1-3 day range p05..p95, up-odds, typical
  |move|" (T077 conditioned distribution + T083 base rates when an event
  is near), THEN session state (T052/T087a), THEN structure with its lens
  named (I033 pattern). Persona: when the owner asks "which way will it
  go", answer with the distribution + the honest sentence about why point
  predictions are refused (D017/D035) — never a bare label. Sweep ALL
  chat/brief surfaces for unlabeled-lens regime mentions (the I033 class).
- [~] T087 — Open-trade monitor: ANALYSIS + CLI shipped as T087a (2026-08-19), toast wiring as T087b, and the ENDPOINT as T087c (2026-08-20, api/monitor_service.py shared by CLI + GET /api/monitor — see Awaiting review). REMAINING here: the Orb panel (render /api/monitor's payload; the serialization is ready for it) and voice barge-in (dep T074) — delivery surfaces only, the judgment is done.
- [x] (advisory note, consumed) Fractional-Kelly VIEW — BUILT 2026-08-19 as
  T085b (REVIEWED PASS; kelly_view in size_position, capped, advisory-only).
- [x] T083 — built 2026-08-18, see Awaiting review at top. Post-probe
  redesign: past FMP windows are PAYWALLED on the owner's tier, so history
  self-accumulates in earnings_observed from the working forward window
  (three feed paths: base-rates tool, calendar tool, morning brief).
- [x] T083b — built 2026-08-18 (probe ALL GREEN same day), see Awaiting
  review at top. Years of earnings history now arrive instantly; real
  acceptance clocks replace bmo/amc guesses.
- [x] T084 — BUILT 2026-08-19, see Awaiting review (the gate was answered by the owner's probe the same morning; 10-K/10-Q YoY textual change stays a Phase 7 candidate).
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
