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
(none)

## Awaiting review (D023 — a DIFFERENT agent signs these off; see REVIEW.md)
- **T016a (Schwab client + mapping) — AWAITING REVIEW — Claude/Cowork** —
  Reviewer: Gemini/Antigravity, per REVIEW.md. Files: `backend/data/schwab.py` (new),
  `backend/settings.py` (schwab_* + require_schwab), `.env.example`,
  `backend/tests/test_schwab.py` (new, 19 tests), `scripts/reconcile_schwab.py` (new).
  Gate PASS: 712 passed. Fresh-checkout run also PASS. Pyrefly unchanged at 6.
  Suggested review focus: (a) the `_equity_leg` heuristic — "first transferItem with
  BOTH a symbol and a price" is a guess about a shape nobody has seen live; is there a
  case where the fee leg carries a price; (b) whether `map_transactions` should reject
  a TRADE whose cash leg disagrees with qty x price rather than trusting the equity leg;
  (c) the `_utc` "+0000" fixup — is that real or am I defending against a shape Schwab
  does not emit; (d) `test_client_exposes_no_order_methods` is the only thing enforcing
  read-only — is asserting on `dir()` strong enough.
(none — T069 signed PASS, T072 signed PASS, T098 signed PASS)

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
- [ ] T077b — Expected-move v2 (after T077 proves out): seeded block-bootstrap Monte Carlo paths (deterministic given seed, D017); swap the paper loop's ATR cost-floor proxy for the T077 expected-move estimate; wire bands into T056 exit plans and the briefing composer.
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
- [ ] T066 — Trade coaching: pre-trade review (thesis, sizing, concentration, correlation, regime fit, IPS compliance) + post-trade review (expected vs actual, entry/exit quality, rule adherence, lesson) persisted per trade; PROCESS-not-outcome scoring. Depends on T016 for real fills; chat-level v0 works today via conversation.
- [ ] T067b — DQS v2 (after T036/T016/T063 land): score the OWNER's actual fills, add FOMO-into-late-RVOL-spike and cutting-winners-early patterns (need fill timestamps + intraday context), wire follow/override rate from the T063 journal, derive the risk budget from the IPS instead of RiskLimits defaults.
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
- [ ] T101 — Make the last 6 pyrefly errors expressible rather than tolerated (low
  priority, all currently false positives — see the triage in pyrefly.toml): TypedDict
  for the correlation `{"with", "corr"}` dict; a small class instead of attaching
  `last_leg` to the regime_router function; a TypeGuard or non-Optional return on
  `require_fred()`. Each makes the code say what it means, and shrinks the
  known-noise list to zero so a new mark is unambiguous.
- [ ] T100 — Honor `LLM_TIMEOUT_SECONDS` in the claude-sdk provider (I017): the knob
  reaches both httpx providers and NOTHING in llm_claude_sdk.py, which is the owner's
  configured brain. Check whether the installed claude-agent-sdk exposes a per-query
  timeout; if not, wrap the async run in `asyncio.wait_for` and raise the same
  actionable LLMError text ("timeout: claude-sdk did not answer within Ns — raise
  LLM_TIMEOUT_SECONDS"). Test that a hung query raises rather than hangs, and that the
  I014 recovery path still commits a clean assistant row.
- [ ] T071 — Owner: voice acceptance run — `pip install -r requirements-voice.txt`, server up, `python scripts\talk.py`, hold a conversation. If faster-whisper wheels fail on Python 3.14 → `set KUBERA_STT=openai`. Report quirks to ISSUES.
- [x] T069 — Adaptive risk-tolerance estimation — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini — PASS):
  `analysis/risk_tolerance.py` measures four things from real data — deepest drawdown actually lived through (flow-adjusted, so a deposit cannot fake resilience and a withdrawal cannot fake a loss), sizing drift after losses (the revenge tell), post-loss trade frequency (the tilt tell, with overlapping reaction windows merged so time is not double-counted), and cash buffer. Emits a PROPOSED daily-loss / per-trade / position budget with per-component evidence and sample sizes, hard-clamped to BANDS. Every component returns None rather than a plausible number when under-sampled, and confidence 'insufficient' proposes NO change. Registry tool #34 `estimate_risk_tolerance`. Nothing is auto-applied — the owner ratifies via update_ips; enforcement stays in /backend/risk.
  REVIEW VERDICT: PASS. Verified all 4 review focus points: (a) compounding multiplier chain (0.75 * 0.80 * 0.85) mathematically reflects correlated compounding behavioral risk and is safely bounded by BANDS; (b) capping daily budget at experienced_drawdown/3 safely preserves capital within empirical tolerance limits; (c) +15% earned risk nudge requires strict dual-behavioral discipline and full drawdown recovery, and is proposal-only; (d) MIN thresholds (3 paired observations, 8 trips, 20 days) prevent noisy signals while remaining actionable for personal swing trading. All 21 tests pass, tool counts synced.

## Backlog — Phase 2: Analysis & insight engine (agents)
- [ ] T023 — Fundamentals + news ingestion: evaluate the owner's existing FMP/FRED keys (D009) vs Alpaca news; verify key validity + tier limits first (incl. whether the FMP tier covers earnings calendar, consensus estimates, and TRANSCRIPTS — commonly paid-tier; D019), then pick and integrate one source. Evaluation weighs (D017): earnings-surprise momentum, FCF yield/debt ratios, 13F ownership-change availability per tier; news is CONTEXT + event risk (feeds T076), never claimed as sentiment alpha. Unblocks T083 (needs earnings dates).
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
- [~] T091b — Attribution follow-ups. HOLDING-PERIOD HALF DONE 2026-08-16
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
  REMAINING in this ticket: weekly-review integration (T062), regime-attribution
  line in the EOD report, costs decomposition once T090 lands per-symbol spreads.
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
- [~] T016 — Schwab read-only sync — CLIENT + MAPPING BUILT 2026-08-16 (Claude/Cowork,
  AWAITING REVIEW as T016a). Remaining in this ticket and BLOCKED ON THE OWNER: credentials
  in .env, then the reconciliation run that is the real acceptance criterion. Original scope:
  Pull positions, balances and TRANSACTIONS into the existing model shapes so the
  analysis layer can read real fills instead of paper ones. OAuth (app key/secret +
  refresh token) — the account number identifies the account, it is not the credential.
  FIRST TASK inside this ticket: pull the widest date range the transactions endpoint
  accepts and RECORD how far back it actually serves in D026 — that number decides how
  much of T102 is needed. Read-only; no order endpoints, no exceptions (D026, spec §7.4).
  ACCEPTANCE IS RECONCILIATION, not "it ran": imported fills must tie out against the
  owner's own statements for an overlapping month — count, symbols, quantities, prices,
  dates. A subtly wrong import does not crash, it just quietly changes every behavioral
  conclusion downstream. Sandbox cannot reach schwabapi.com, so live tests SKIP here and
  run on the owner's machine (same pattern as Alpaca, I002).
- [ ] T102 — Statement PDF ingest — **NOW THE UNBLOCKED PATH (I019)**: Schwab has the
  app in "Modification Pending" so no API call can succeed for a few days. This ticket
  needs only a statement PDF and no credentials, so it is the useful work in the
  meantime — and its parser has to exist anyway. Original scope: parse Schwab
  statements for history the API cannot reach. Layouts change across years, so the parser
  reports what it could NOT parse rather than silently dropping rows. Its test is the
  overlap window — parsed rows must reconcile against API rows where both exist.
- [ ] T103 — The trading autopsy (D026, blocked on T016 + T102 reconciling): run the
  existing battery over REAL fills — T091b holding periods vs stated style, T069 sizing
  drift and post-loss tempo, T088 slippage by hour, T089 give-back, T060 TWR — and compose
  one report. Little new analysis; the analysis was built first and has been waiting for
  data worth reading. Every figure carries its sample count.
- [ ] T104 — Pre-trade pattern warnings (D026, last): before an action, flag when it
  resembles a setup that historically cost him, with n attached. Refuses to speak when the
  sample is too small — the T069 "insufficient" precedent. Never predictive.
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
- [ ] T045 — KUBERA MCP server (D011): thin FastMCP/official-SDK stdio server exposing the T024 registry tools (get_portfolio, get_latest, get_daily_bars, compare_benchmark, get_symbol_briefing) so Claude Desktop/Antigravity/mobile become KUBERA frontends pre-PWA. Read-only; no order tools until §7.4 exists. Later: streamable-http + auth for remote/mobile.

## Blocked
(none)

## Done
- [x] T098 — Local voice for the Orb + reply text out of URL (D024) — DONE 2026-08-16 (Claude/Cowork):
  `backend/api/tts_engine.py` (local-first speech engine: `auto` default uses kokoro when models exist, falls back to edge; `kokoro` forced returns 503 on missing model; stdlib `wave` + `struct` mono 16-bit WAV encoder without collection-time audio imports; `synthesize_local` cached single-load); `POST /api/tts` on FastAPI (`GET /api/tts` retained for compatibility); `apps/web/orb.html` updated to POST JSON body instead of sending query string (preventing sensitive tickers/P&L from leaking to access logs/browser history) with graceful audio error handling; 19 tests in `test_tts_engine.py`.
  REVIEWED 2026-08-16 by Gemini/Antigravity — PASS
    aligned: Directly executes D024: keeps sensitive portfolio holdings and P&L local, eliminates URL query string leak.
    checked: WAV encoder clamping math [0, 16384, -32767, 32767], auto vs forced 503 error handling, orb.html POST transition & regression guard, verify.py pass (682 passed).
    concerns: none
- [x] T091 — Attribution pack: signal_log gains regime_label + sub_strategy + entry_bucket at decision time (migration `f71b527814ef`); the loop persists the classified regime on EVERY row (incl. no_trades — restraint gets attributed too); regime_router annotates its leg (`last_leg` introspection); Transaction gains order_id (migration `89e88db0d156`) — the join key from fill → logged decision. `analysis/attribution.py`: FIFO round-trip P&L credited to the ENTRY's tags (hand-walked: partial-lot consumption across regimes), unattributed bucket = manual trades (visible, never dropped), oversold shown; win rates per tag; "narrate counts with P&L" note. `get_attribution` (registry 24) + `GET /api/attribution` + activity counts by regime. 8 tests — 2026-08-14. Answers D020 #2 as data accumulates.
- [x] T036 — Fills sync + market-hours guard + entry delay: `AlpacaClient.get_fills` (activities API, RFC3339-safe) + `get_clock` (broker's own market clock — no local tz guessing); `data/fills.py` sync into `transactions` deduped per (account, external_id) — re-running always safe, proven; loop: `enforce_market_hours` (closed → no_action "an order now would queue for the open print", source=alpaca-clock) + `entry_delay_minutes` as a T055 no-trade reason for BUYS only (sells exempt, tested at 9:35 ET); scripts/sync.py now syncs fills each run; paper_trade.py guards ON by default (--after-hours / --entry-delay 30 default). 7 tests — 2026-08-13. UNLOCKS: T088 slippage, T089 live MAE/MFE, T091 attribution, T060 TWR. Session-aware staleness → T036b.
- [x] T086 — Position triage advisor (`analysis/triage.py`): entry + current price judged against the LIVE exit plan — EXIT (invalidation closed through: "the thesis is dead; adding is increasing exposure, not lowering an average" — the honesty note is ASSERTED in tests, not assumed) / EXIT_AT_TARGET (edge-to-edge complete; "wanting more is a NEW thesis") / HOLD with add-assessment: range adds ONLY in the lower quarter of the span ("at the edge"), trend adds ONLY on strength ("a dip toward invalidation is the market arguing with the thesis"); review-clock expiry flagged ("a stale thesis is not a thesis"); risk_remaining_atr + distances returned. `triage_position` tool (registry 23) + `GET /api/triage/{symbol}?entry_price=`. 10 tests — 2026-08-13. Owner Q&A item #4 → SHIPPED.
- [x] T085 — `size_position` by voice: exact NEW-BUY quantity from live equity + latest trade (staleness disclosed) + ATR stop + 20% cap headroom (existing position counted) + tier multiplier (halved at 2, ZERO at 3+/breaker) — every input returned incl. stop_price; `binding` says what limited it (risk_budget / position_cap / blocked). Registry 22 + `GET /api/size/{symbol}`. 7 hand-computed tests — 2026-08-13. Advisory for manual trades; the loop enforces the same math itself.
- [x] T064 — Backtest rigor + PROMOTION GATE (`backtest/stats.py` + ledger + loop): trade extraction from 0/1 weights (contiguous runs; equity[b]/equity[a−1]; open-at-end flagged) → win rate, profit factor, avg/best/worst; Calmar (None when no drawdown); ANCHORED walk-forward — one no-lookahead run, equity sliced into segments, pass = overall > 0 AND ≥ half segments non-negative ("consistency screen, not a promise"; honest note: our templates have no tunable params, so this tests robustness across periods, not overfitting). `promotion_status` on backtest_runs (migration `04e68aa1c90a`); `promote_template`/`is_promoted` per (template, symbol) pair; run_paper_cycle(require_promotion) refuses unpromoted BUYS as no_trade (sells exempt); `scripts/promote.py` CLI; paper_trade.py gates BY DEFAULT (--skip-promotion-gate escape). Momentum fails promotion on CHOP, router passes — tested. 12 tests — 2026-08-13. Follow-ups → T064b.
- [x] T056 — Structured exit plans (`analysis/exit_plan.py`) — REGIME PACK COMPLETE: per-thesis playbook as DATA — range (target = far edge, invalidation = support close-through, 10-session clock, mid-range worst-RR warning), trend_up (invalidation = max(SMA, swing support) below price; NO target — "ridden, not targeted"; p95 as review point never target; 5-session cadence), trend_down (long-only: the exit IS the plan), breakout (hold the boundary, judge within T053's window; downside break = exit information), coil (range plan + expansion-picks-the-plan note); stop_distance_atr + reward_risk computed, stale-level RR guards. `get_exit_plan` tool (registry 21; composes regime+levels+ATR+active breakout+p95) + `GET /api/exit-plan/{symbol}`. 11 hand-computed tests — 2026-08-13.
- [x] T075 — Multi-timeframe confluence (`analysis/confluence.py`): decoupled assess_confluence — daily regime direction vs hourly-classified regime + session-VWAP side + churn (≥4 crossings) adjust the DAILY confidence (+0.05 agree / +0.05 VWAP-aligned / −0.10 conflict / −0.05 wrong-side / −0.05 churn), clamped [0.05, 0.90]; the regime call itself never flips; D006 volume-delta absence stated in every reading. `get_confluence` tool (registry 20) fetches 1Day/1Hour/5Min with per-view graceful gaps + `GET /api/confluence/{symbol}`. 10 hand-computed tests — 2026-08-13. Regime pack now complete EXCEPT T056 (exit plans).
- [x] T063 — Decision journal (`decision_journal` table, migration `080e1c184167` + `data/journal.py`): every recommendation captured AT decision time — verdict (buy/add/hold/trim/sell/avoid), confidence, thesis, horizon, entry/target/stop, key risk, regime + regime confidence; owner FOLLOW/OVERRIDE marking with notes. Persona gains the journal rule ("a recommendation that isn't journaled didn't happen" — guard-tested). Tools: `record_decision` (model self-journals), `mark_decision`, `get_journal` (summary + v1 calibration: direction-hits after horizon vs latest price, hold excluded, "process check not performance claim"). Registry 19; `GET /api/journal`. 9 tests hand-computed — 2026-08-13. v2 → T063b.
- [x] T080 — Macro regime context (`data/fred.py` + `analysis/macro.py`): FRED client (httpx, no SDK; skips "." missing values; actionable 400 message; settings.require_fred + .env.example line) → T10Y2Y / VIXCLS / DFII10 / DFF with EACH SERIES' OWN observation date; composition with documented conventions (inversion flag "caution, not a timer"; VIX buckets <15/<20/<30/30+; real rate >2 restrictive) → cautionary-signal list + count, "never a trade signal by itself" note. `get_macro_context` tool (registry 16; ToolContext gains fred) + `GET /api/macro` (503 w/ key instructions when unset). 10 tests incl. bucket boundaries — 2026-08-13. Owner: FRED_API_KEY in .env activates it. Feeds T062 briefs later.
- [x] T062 — Briefs & reviews (`api/brief.py`): deterministic composition, LLM narrates — morning (account, risk tier + DQS, per-holding + SPY: overnight gap with STALENESS flag, regime, expected 5-day move, nearest levels), eod (today's decisions with reasons, day P&L, budget consumed), weekly (equity vs SPY with excess return, discipline counts incl. tier restrictions, facts_for_lessons + "never invent numbers" narration rule). Sections degrade gracefully with a `why` ("run sync daily"); T068/T076 gaps stated honestly in payload. `get_brief` tool (registry 15) + `GET /api/brief?type=morning|eod|weekly`. 6 seeded-db tests — 2026-08-13. Follow-ups → T062b.
- [x] T067 — DQS + graduated risk tiers, ENFORCED (`risk/tiers.py` + `risk/dqs.py`): budget-consumed ladder in the paper loop — tier 1 (≥25%): cost+RVOL floors doubled · tier 2 (≥50%): new-buy notional HALVED · tier 3 (≥75%): entries paused as no_trade · tier 4 (100%): the untouchable T033/T035 breaker; sells exempt at every tier; breaker PRECEDENCE preserved (tripped → loud gate rejection, not a quiet no_trade — tested). DQS v1: process-not-outcome score from signal_log (frequency vs guard, trading-into-drawdown, sizing CV, restraint counted free) — honest note that owner-fill scoring needs T036/T063 (→ T067b). `get_risk_status` tool (registry 14) + `GET /api/risk`. 15 hand-computed tests — 2026-08-13.
- [x] T077 — Expected-move & payoff distribution engine (`analysis/expected_move.py`): overlapping N-day return samples over trailing lookback → inclusive-interpolation percentile bands (p05..p95, return AND price terms), up_frac (historical hold-N win rate), median |move|, payoff ratio (None when a side is empty); VOL CLUSTERING via trailing-vol terciles — bands conditioned on the current tercile (quiet tape → narrower honest bands, proven in test); overlap-autocorrelation caveat + "NOT a forecast" in every reading. `get_expected_move` tool (registry 13) + `GET /api/expected-move/{symbol}`. 11 hand-computed tests — 2026-08-13. GARCH still deferred on evidence; v2 = T077b.
- [x] T054 — Range strategy + regime router (`backtest/strategies.py`): `make_range` trades only the lower `entry_frac` of the trailing range and REFUSES both trending AND unverifiable structure (`_regime_lite` returns up/down/none/UNKNOWN — the unknown state exists because an early bear is indistinguishable from an unknowable one; leak caught by the BEAR regime test, bars 39–44); `make_regime_router` = structure→momentum, checked-range→range, else CASH. Acceptance proven: router beats always-momentum in CHOP (momentum 0.0, router >100%), rides BULL, all-zero in BEAR. Registry: 6 templates — 2026-08-13. NOTE: closes-only regime-lite per D010 contract; volume-aware checks live in the loop (T055).
- [x] T055 — No-trade condition first-class (`backtest/paper_loop.py`): new `no_trade` signal_log action ("capital preserved by design"), buys-only (sells never blocked): overtrading guard (max_trades_per_day=5 across all symbols), ATR/price cost floor (expected-move proxy until T077), quiet-market check (full T050 classifier: RVOL < 0.3 AND bottom-quartile width). Tests: 6th-buy blocked, sell-still-allowed under guard, quiet fixture, dead-flat tape — 2026-08-13. Confluence-score threshold deferred to T077+backtest evidence per D017.
- [x] T052 — Intraday data + session analysis: `get_intraday_bars` (1Min…1Hour, tz-aware UTC starts, split-adjusted) + `analysis/intraday.py` — ET session grouping (zoneinfo, tzdata added for Windows; a 20:30-ET bar belongs to its ET day across UTC midnight), RTH filter (09:30–16:00, opt-out), cumulative session VWAP (typical price), VWAP crossings (churn detector), and TIME-OF-DAY RVOL — today's cum volume vs prior sessions by the same ET time, the doctrine's exact definition. `get_intraday` tool (registry 12) + `GET /api/intraday/{symbol}`. 12 hand-computed tests — 2026-08-13. Unblocks T075 confluence; the morning brief (T062) gets its "what kind of day is it so far" input.
- [x] T053 — Breakout detector (`analysis/breakout.py`): fresh-escape EVENTS (continuation bars never start one) with boundary, RVOL-at-break (thresholds shared with regime.py — one source of truth), hold-outside tracking, and a judged-once status taxonomy: confirmed (hold+volume) / failed (returned inside the hold window — the $100→$106→$99 fakeout, tested by name) / unconfirmed (held on weak volume — stay suspicious) / pending; `active` flag for live breaks. `get_breakouts` tool (registry 11) + `GET /api/breakouts/{symbol}`, D006 volume_feed label rides along. 9 hand-walked tests — 2026-08-13. Feeds T054 router + T056 exits.
- [x] T051 — Support/resistance levels (`analysis/levels.py`): swing highs/lows (shared `swing_points`, now public in regime.py) pooled + greedy price-proximity clustering (running mean, tolerance_frac) → levels with price (cluster mean), TOUCH COUNTS (min_touches=2 default — "one rejection is an event, two is a level"), provenance kind (support/resistance/MIXED — old floor becoming new ceiling is detected), signed distance, nearest support/resistance vs last close. Reachable: `get_levels` tool (registry 10) + `GET /api/levels/{symbol}`. 13 hand-walked tests incl. the mixed-kind breakdown fixture — 2026-08-13. Feeds T054 range strategy + T056 exit plans.
- [x] T078 — Vol-parity position sizing: `true_ranges`/`atr` (Wilder) in analysis/metrics + `risk/sizing.py` volatility_parity_notional (risk$ = equity × risk_per_trade_frac; ceiling = risk$/(stop_atr_multiple × ATR) × price); RiskLimits gains risk_per_trade_frac (default 1%, hard band ≤5%) + stop_atr_multiple (2.0). Paper loop applies to BUYS only (sells always reduce risk), logs a sizing note on bound orders, and FAILS CLOSED on <15 bars ("insufficient history for ATR"). Deliberate: sizer only shrinks; the engine's 20% cap still REJECTS loudly (no silent auto-resize). 12 new tests hand-computed (TR/ATR 22/9, ceiling 12.5k, whipsaw loop order 12.195 shares) — 2026-08-13.
- [x] T050 — Regime classifier (`analysis/regime.py`): trending_up/down · range_bound · breakout_watch from daily bars — swing-structure HH/HL (SMA-slope fallback for monotone series), 20-bar range + width percentile vs trailing windows (the coil), escape-vs-prior-range with suspected_fakeout on weak RVOL, per-label 3-signal confidence checklist (capped 0.9 — never certainty), volume_feed REQUIRED (D006). Shipped reachable: `get_regime` registry tool (9 tools now) + `GET /api/regime/{symbol}` so the owner can ask the Orb "what kind of market is SPY in?". 18 tests: doctrine fixtures (sawtooth trends, stationary triangle, coil, volume-confirmed breakout, fakeout) + hand-computed micros — 2026-08-13. Decision order doctrine: matured trend outranks its own escapes.
- [~] T097 — REVERTED 2026-08-14 (owner call): the particle FACE was iterated six
  times (voxel grid → sculpted 3D → holographic columns → microscopic rods →
  skull anatomy → green dots) and never reached a convincing likeness. Owner:
  "revert back to the orb". `apps/web/orb.html` restored to 5f77557 (the Orb
  with patience fixes) — no CDN dependency, voice loop untouched. LESSON worth
  keeping: procedural facial likeness is a poor fit for this codebase's
  verify-then-ship loop — each pass needed a human eye to judge, which is the
  one thing the gate can't automate. If a face returns, buy/commission the
  asset (a real head mesh or a point-cloud scan) instead of sculpting it in
  gaussians. Face-era work preserved in git history (8fc9927..82b3a85).
- [x] T097 v2 — Sculpted 3D face (superseded, then reverted — see above):
  continuous gaussian-feature depth field tuned via offline renders, ~12k WebGL
  points (three.js CDN, additive), shader-driven cursor-follow / pupil-lead /
  lip-sync / shimmer / edge-dissolve, 3/4 rest pose per reference — 2026-08-14.
- [x] T097 — The KUBERA Face (owner request 2026-08-14, reference image: voxel head
  dissolving into a particle network): the Orb canvas now renders a procedurally
  generated depth-mapped voxel face — no assets, no libraries, ~1,300 particles
  from two-ellipse silhouette + feature carving (brow/sockets/pupils/nose/lips/
  chin), verified by offline render before shipping. Head yaw/pitch FOLLOWS THE
  CURSOR (smoothed, ±0.55/±0.32 rad), pupils lead the turn with extra gain, idle
  gaze wanders after 4s without mouse. Mouth voxels ride the real TTS amplitude
  (S.amp) when speaking; thinking = violet shimmer; left edge dissolves into a
  drifting wireframe halo per the reference. Same canvas id, click contract,
  state machine, and voice loop as the orb it replaced — zero logic touched —
  2026-08-14.
- [x] T073 — The KUBERA Orb (`apps/web/orb.html` at GET /): voice-first web UI — breathing orb (idle gold / listening teal / thinking violet / speaking amplitude-reactive), browser SpeechRecognition STT, streaming `GET /api/tts` (edge-tts, lazy server dep w/ actionable 503), tool-call chips per reply, typed fallback, "confirm this turn" checkbox as the deliberate gesture; 4 tests (route + fake-edge streaming) — 2026-08-12. Phase 5 opened early per D015. Zoey-grade latency = T074.
- [x] T061 — Investment Policy Statement: `investment_policy` table (migration `08dfc64f8e4b`) + `data/ips.py` (partial upsert, lists replace wholesale, compact prompt block), injected into every chat system prompt; tools `get_ips` (free) + `update_ips` (**requires_confirmation** — first gated tool live: "KUBERA, set my max drawdown to 15%" → asks → you confirm deliberately); `GET /api/ips`; guard test now asserts gated set == {update_ips}; 10 new tests — 2026-08-12
- [x] T070 — Push-to-talk voice loop (code-complete; owner acceptance = T071): `api/voice_loop.py` tested orchestration (conversation threading, silence never reaches KUBERA, typed-only confirm passthrough) + `scripts/talk.py` (sounddevice capture, STT: faster-whisper local / OpenAI fallback, TTS: SAPI / edge-tts, voice=true wired), requirements-voice.txt keeps audio deps out of CI — 2026-08-12
- [x] T046 — Claude Agent SDK provider (`api/llm_claude_sdk.py`, D012): chat on the owner's Max subscription; registry bridged as SDK tools with locked permissions (mcp__kubera__* only, no Bash/files, dontAsk, bounded turns); confirmation gate + audit trail preserved via side-channel events the chat loop persists; policy verified via claude-code-guide agent (personal-use-only); optional dependency with actionable errors; 7 fully-mocked tests — 2026-08-11. Owner activation = T047.
- [x] T044 — Context budgeting (`api/context.py`): block-wise selection (assistant+tool-results indivisible — provider contracts never break), oldest exchanges drop whole, newest always kept, old tool payloads elided while assistant conclusions survive; KUBERA_CONTEXT_BUDGET_CHARS setting (default 24k chars ≈ 6k tokens); 8 tests incl. pairing-never-split across budgets — 2026-08-11. (Research-memory retrieval deferred to Phase 7's vector store per D007.)
- [x] T043 — Conversation safety rails: `requires_confirmation` per tool + ConfirmationRequiredError (ctx.confirmed set ONLY from ChatRequest.confirm — the model can never self-confirm), guard test that no current tool requires confirmation, recency post-check appending a deterministic asof footer when a data-grounded reply lacks a date; 8 new tests incl. full two-turn confirmation flow — 2026-08-11
- [x] T042 — POST /api/chat: bounded conversation loop (persona + history → LLM → registry tools → grounded answer), conversations/chat_messages tables + migration `7bb8528ec2d3`, every message/tool-call/result persisted with timestamps, tool errors surfaced verbatim, GET /api/chat/{id} audit view; 7 scripted-provider tests + endpoint E2E — 2026-08-11
- [x] T041 — LLM abstraction (`api/llm.py`): neutral message/tool format, Anthropic + OpenAI adapters (thin httpx, no SDKs), both-direction translation tested via captured wire payloads, build_provider fail-fast selection (LLM_PROVIDER env; Gemini = future add); settings: ANTHROPIC/OPENAI keys + model overrides — 2026-08-11
- [x] T040 — Persona (`api/persona.py`): build_system_prompt with 8 non-negotiable CORE_RULES (tools-only numbers, recency, no certainty, paper clarity, confirm-before-capital, can't override risk engine, no gap-filling, not-an-advisor) + analyst voice; guard tests prevent silent rule deletion — 2026-08-11
- [x] T034 — Backtest results ledger: `backtest_runs` table + migration `33592ebf6de6`, `backtest/ledger.py` (record/list/run_and_record), shared TEMPLATES + build_strategy, `GET /api/backtests` + `POST /api/backtests/run`, `run_backtest` registry tool (6 tools now); tests incl. StaticPool fix for cross-thread in-memory SQLite — 2026-08-11. **Phase 3 core complete** (T036 polish optional).
- [x] T035 — Risk-state persistence: `risk_state` table + migration `35b6c01bf49b`, `engine.restore()` (persistence-only), `risk/persistence.py`, paper-loop restore/persist hooks, `scripts/risk_reset.py` (note-required, type-RESET confirm); killer test: restarted loop loads tripped breaker from DB and stays blocked — 2026-08-11
- [x] T032 — Paper-trading loop: `backtest/paper_loop.py` (strategy → risk gate → paper order → SignalLog audit row for every decision incl. rejections/no-action), `place_order` on AlpacaClient (paper-only by construction), `signal_log` table + migration `c09d9671853d`, `scripts/paper_trade.py` CLI; 10 new hand-computed tests incl. breaker-blocks-second-cycle — 2026-08-11
- [x] T031 — Strategy library: make_momentum (trailing-return trend filter) + make_mean_reversion (band-below-SMA dip buyer, stateless), validated params; hand-tracked equity tests + regime proofs (momentum flat through the whole synthetic bear; MR profits in chop, sits out smooth bulls) — 2026-08-11
- [x] T033 — Risk engine v1 (`risk/engine.py`, spec §8): fail-closed pre-trade gate, per-symbol position cap (inclusive), daily-loss circuit breaker (trips at limit, blocks buys AND sells, survives recovery and new days, manual reset only), timestamped decisions with all violated rules + numbers; 22 hand-computed tests — 2026-08-11
- [x] T030 — Backtest engine v1 (`backtest/engine.py` + `strategies.py`, per D010): no-lookahead by construction (prefix-enforced, tested), cost model in bps, weight validation, metrics from analysis layer; buy-and-hold + SMA-cross templates; 8 hand-computed tests — 2026-08-11
- [x] T017 — Chore: shared httpx plumbing extracted to `data/_http.py` (build_client + checked_get); both clients refactored, error text byte-identical, same 85 tests green — 2026-08-11
- [x] T025 — Symbol briefing composer (`analysis/briefing.py` + `sma()` in metrics): trailing 20/60/252d returns, 60d ann vol, 252d max DD, 52-week high/low distance, SMA50/200 trend context, owner's exposure; graceful degradation on thin history; `get_symbol_briefing` tool + `GET /api/briefing/{symbol}`; 12 new tests — 2026-08-11
- [x] T024 — Tool-calling registry (`api/tools.py`, spec §3): typed pydantic-validated tools with JSON-schema export (`GET /api/tools`), context injection, clear error taxonomy; 4 tools registered (get_portfolio, get_latest, get_daily_bars, compare_benchmark); 8 tests — 2026-08-11
- [x] T022 — Win/loss breakdown: `analysis/portfolio.win_loss()` (winners/losers/flat, natural-sign gain/loss sums, best/worst), surfaced in `/portfolio` as `win_loss`; hand-computed tests — 2026-08-11
- [x] T021 — Benchmark comparison: `analysis/benchmark.py` (inner-join date alignment, normalized curves, per-series metrics, excess return), `data/history.py` equity_history (last snapshot/day/account, summed), `GET /api/benchmark?symbol=SPY&days=90` with actionable 409/503; 9 new tests — 2026-08-11
- [x] T020 — `analysis/metrics.py`: daily_returns, cumulative_return, CAGR, volatility, Sharpe, max_drawdown_frac — documented conventions (252 ppy, positive-magnitude drawdown, ValueError on bad input), 16 known-answer tests hand-computed — 2026-08-11
- [x] T015 — `GET /portfolio`: live account + positions at request time, totals/weights/returns via `analysis/portfolio.summarize()` (deterministic, tested); 7 new tests. **Phase 1 code-complete** — owner sign-off via T007 — 2026-08-11
- [x] T014 — Snapshot sync job: `data/sync.py` (idempotent account upsert + account/position snapshot writes), `scripts/sync.py` CLI (one-shot / `--loop N`), account model gains `external_id`; idempotency tests — 2026-08-11
- [x] T013 — DB schema v1: SQLAlchemy 2 models (broker_accounts, account_snapshots, position_snapshots, transactions), UTCDateTime type rejecting naive datetimes, engine/session factory, first alembic migration `bee2b4896cdf` + migration-parity test; `alembic -c backend/alembic.ini upgrade head` — 2026-08-11
- [x] T012 — Market data client (`backend/data/market_data.py`): latest trade/quote + daily OHLCV (IEX free feed, split-adjusted), dual timestamps (exchange_ts + asof) on every payload, RFC3339 parser handling Alpaca's variable-precision fractions on py3.10+; `GET /api/market/{symbol}/latest` + `/bars`; 9 new tests — 2026-08-11
- [x] T011 — Alpaca paper client (`backend/data/alpaca.py`): account + positions, timestamped/sourced payloads, actionable 401s, **live-endpoint refusal rail** (§7.4 not implemented = no code path to real money); `GET /api/account`; 8 new tests + skip-guarded live integration test — 2026-08-11
- [x] T010 — Typed settings loader (`backend/settings.py`, pydantic-settings): fail-fast `require_alpaca()`, SecretStr, `/health` reports config state; 5 tests — 2026-08-11
- [x] T004 — git init, CI workflow, gitleaks pre-commit config, .env.example, .gitignore — 2026-08-11
- [x] T003 — Backend skeleton: FastAPI /health, analysis.returns + 7 tests, ruff, verify.py — 2026-08-11
- [x] T002 — project-memory working files (TASKS, DECISIONS, ISSUES, PROGRESS) — 2026-08-11
- [x] T001 — AGENTS.md + PROJECT_SPEC.md authored — 2026-08-10
