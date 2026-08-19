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
- **I018 (CI red — reproduce without .env, fix) — Claude/Cowork** — claimed 2026-08-19.

## Awaiting review (D023 — a DIFFERENT agent signs these off; see REVIEW.md)
- **T072b (voice hygiene trio, carried from the T072 review) — AWAITING
  REVIEW 2026-08-18 (Claude/Cowork)**. Honest disposition: 2 of 3 items were
  ALREADY FIXED by prior work and are closed on evidence, not redone
  (two-strikes spirit — no re-fixing fixed things): (a) the silent
  except around the tts_engine import is GONE (talk.py:210 imports directly;
  sys.path set at :42; grep shows no bare except near it) and (c) the
  docstring already points at requirements-voice.txt ("kokoro-onnx
  soundfile" appears nowhere in the tree). (b) was real and is fixed: the
  MODULE-level `np = pytest.importorskip("numpy")` in test_tts_backends.py
  hid the audio-FREE tests (missing-key/package/model exits) from CI; the
  skip now lives inside _silent_wav and the kokoro-play test only, and
  talk.py's numpy/sounddevice imports are verified function-local so the
  module imports cleanly without audio deps.
  EVIDENCE: 8/8 with numpy present; module-level grep of talk.py (no
  top-level numpy/sounddevice); ruff clean; gate PASS. D028 note: I built a
  meta_path blocker to simulate CI-without-numpy — its results were
  ARTIFACTS of the hack (it poisons mid-test imports with numpy installed)
  and are NOT claimed as evidence; the per-test importorskip is pytest's
  documented skip path and stands on that.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT deb9c0c — PASS
    aligned: owner's voice loop must never die from audio issues; CI must
      not silently skip non-audio tests when numpy is absent.
    checked: read test_tts_backends.py at deb9c0c — importorskip('numpy')
      and importorskip('soundfile') now live inside _silent_wav() and the
      kokoro play helper only; module-level call is gone. Verified talk.py
      imports numpy and sounddevice only inside function bodies (grep
      confirmed: no top-level import of either). Gate 970 passed on this
      machine. parallel_check.py: single head, no clobber.
    concerns: none found. The two items closed on grep evidence (a,c) are
      properly documented as "already fixed" — builder did not re-fix them.
- **T083c (base rates into the morning brief) — AWAITING REVIEW 2026-08-18
  (Claude/Cowork)**. Each held symbol with upcoming earnings now carries a
  COMPACT base-rates block in the morning brief: events measured, median
  event-day move, closed-down fraction, "not a prediction" note (full splits
  stay in the get_event_base_rates tool). _base_rates_summary reads the
  observed store + 800d bars; degrades three ways (no db / under MIN_EVENTS
  with the EDGAR pointer / any exception → available:false with the type
  name — the brief NEVER dies for a base-rates problem).
  EVIDENCE: 2 tests (compute + thin-store degrade; broken-market survive);
  18 passed across store+brief suites; ruff clean; pyrefly exactly 1; gate
  PASS. D028: my first median was sorted()[n//2] — the upper median on even
  counts; replaced with statistics.median before commit.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT e2d3265 — PASS
    aligned: each morning brief should carry a compact base-rates block
      per held symbol with upcoming earnings, degrading gracefully.
    checked: git show e2d3265 confirms statistics.median (not sorted()[n//2])
      is the shipped code. Checked three degrade paths in diff: no-db →
      available:false+why; thin store → available:false+edgar_note; any
      exception → available:false+exc type. Gate 970 passed. money-math
      check: statistics.median([1,2,3,4]) = 2.5 (true median) vs
      sorted()[n//2]=3 (upper); the fix is correct and the D028 note is
      honest about what was wrong. Tests in test_earnings_store.py
      assert specific numeric values (0.5 closed-down, specific median),
      not just "code returns what code returns".
    concerns: none. The brief-never-dies invariant is properly tested.
- **T076b (FOMC dates + priced-for-perfection — D016/D019) — AWAITING REVIEW
  2026-08-18 (Claude/Cowork)**. All three halves resolved: (1) FOMC DATES —
  source decision made per D034 free-first: the Fed's PUBLISHED calendar as
  an external-spec constant table (the holiday-calendar precedent), 16
  decision days 2026–2027 in analysis/fomc.py, transcribed with source note
  and an explicit REVIEWER CHECK (compare against
  federalreserve.gov/monetarypolicy/fomccalendars.htm — a mistyped date
  mis-guards real entries); staleness is SELF-REPORTED (fomc_staleness_note
  nags every brief within 90 days of table exhaustion — D031's
  rule-with-no-mechanism failure cannot recur). with_fomc() merges into
  every calendar consumer: get_macro_context, brief events section (FOMC
  guards even WITHOUT a FRED key now — it needs none), paper_trade guard
  arming (CPI/NFP failure no longer turns the guard fully off).
  (2) EARNINGS DATES for held symbols — already DONE via T023/T083, marked
  resolved. (3) PRICED-FOR-PERFECTION (D019 sell-the-news) — built from two
  numbers that already exist: per-holding 5-bar runup (new in _symbol_read)
  vs own p95 expected 5-day move; joined onto earnings_risk entries in the
  morning brief; flag-not-forecast note in every payload; None when either
  input missing. Stale PENDING_NOTES line retired.
  EVIDENCE (D027): test_fomc.py 6 tests — table sanity (16 rows, ascending,
  8/yr), merge-without-mutation, entry_guard naming the 2026-09-16 decision
  from the day before, upcoming_events inclusion, staleness ladder
  (None/warn/EXHAUSTED), flag hand-computed (6% vs 5% p95 → True; 3% →
  False; missing → None). 22 passed across fomc+brief+events suites; ruff
  clean; pyrefly exactly 1; full gate PASS.
  D028 objections: (a) the 16 dates are TRANSCRIBED from training knowledge
  of the published calendar, not fetched — the reviewer check against the
  Fed page is therefore load-bearing and named at the top of the table;
  (b) day-2-only convention (decision day) chosen and documented — day 1
  moves tape rarely; (c) the flag joins only HELD symbols with upcoming
  earnings — watchlist symbols could want it too, deferred as an easy
  extension.
  FIXED AND RE-SUBMITTED 2026-08-19 (Claude/Cowork): 2027-06-16 →
  2027-06-09 per the reviewer's live Fed-page fetch; fomc.py's transcription
  note now records the incident (the reviewer check earned its keep); I031
  closed same day. Delta scope for re-review: the one table row + note
  (verdict AT the new sha per D033).
  REVIEWED 2026-08-19 by Gemini/Antigravity AT 1e0f279 — BLOCK
    aligned: serves D016/D019 event-risk and sell-the-news flag — both
      owner-stated goals. Gate PASS; alembic single head; no secrets.
    checked: fetched federalreserve.gov/monetarypolicy/fomccalendars.htm
      live (July 29, 2026 update) and compared all 16 dates row by row.
      2026: all 8 correct. 2027: 7 of 8 correct. ONE DATE IS WRONG:
        fomc.py: "2027-06-16"
        Fed page anchor #45694 (2027 section): June meeting is "8-9*"
          → decision day = 2027-06-09, not 2027-06-16.
      The June 2027 meeting would go completely unguarded. A FOMC day
      inside a user's entry window is the core purpose of this ticket;
      a one-week error defeats it silently.
    concerns:
      1. BLOCK: 2027-06-16 must be corrected to 2027-06-09 in
         analysis/fomc.py. The test_table_is_sane test passes with the
         wrong value because it only checks count and sort order, not
         individual dates — this is intentional design (the test cannot
         hard-code the calendar it is supposed to guard), but it means
         the unit tests cannot catch this class of error. The reviewer
         check is the only mechanism, and it found the defect.
      2. Minor (no block): test_fomc_guards_entries_like_any_release uses
         date(2026, 9, 15) + window_before=1 → correctly names 2026-09-16.
         A parallel test for the June 2027 date would have caught the
         transcription error — recommend adding one after the fix.
      Not a block: priced_for_perfection logic, with_fomc merge, staleness
      nag, and paper_trade/brief wiring all look correct and are well-tested.
- Reviewed DONE blocks (T083b, T083b-probe, T083, T066, T067b, T023b, T016b, T113, T016c, T112)
  moved verbatim to project-memory/archive/TASKS-archive-2026-08-18.md (curation 2026-08-19).

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
- [x] T083 — built 2026-08-18, see Awaiting review at top. Post-probe
  redesign: past FMP windows are PAYWALLED on the owner's tier, so history
  self-accumulates in earnings_observed from the working forward window
  (three feed paths: base-rates tool, calendar tool, morning brief).
- [x] T083b — built 2026-08-18 (probe ALL GREEN same day), see Awaiting
  review at top. Years of earnings history now arrive instantly; real
  acceptance clocks replace bmo/amc guesses.
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
