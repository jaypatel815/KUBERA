# TASKS

One ticket = one focused agent session. Claim by adding your name as owner.
IDs never get reused. Format per PROJECT_SPEC.md §11.

## In progress
(none)

## Backlog — Owner actions (Chotu — nothing else is blocked on these yet, but T005/T006 gate Phase 1 completion)
- [ ] T005 — GitHub repo created + remote added ✔ (2026-08-11). Remaining: push `main` from your machine (sandbox has no GitHub auth) and confirm the Actions CI run is green.
- [x] T006 — Alpaca paper keys in `.env` — done 2026-08-11 (owner). Note: owner's `.env` uses `ALPACA_API_KEY` naming + extra vars from another template; settings loader accepts both spellings, extras ignored.
- [ ] T007 — **Phase 1 sign-off, nearly done:** verify.py passed on Windows 68/68 incl. the 3 live paper tests (per Gemini's 2026-08-11 session ✔). Remaining: `alembic -c backend\alembic.ini upgrade head` + `python scripts\sync.py` + open `http://127.0.0.1:8000/portfolio` once.
- [x] T008 — pre-commit installed — done 2026-08-11 (owner). Sandbox-side caveat: I003.

## Backlog — Regime intelligence pack (owner's doctrine: docs/research/regime-trading-notes.md — READ IT FIRST)
- [ ] T050 — Regime classifier (`analysis/regime.py`): from daily bars — range-width percentile (vs trailing history), RVOL (IEX-relative, labeled per D006), higher-high/lower-low trend structure → classify trending_up / trending_down / range_bound / breakout_watch with the underlying numbers + confidence; known-answer tests on synthetic regime fixtures (reuse BULL/BEAR/CHOP).
- [ ] T051 — Support/resistance estimation: swing-high/low clustering over a lookback; returns levels + touch counts; feeds briefing + range strategy; hand-computed tests.
- [ ] T052 — Intraday data: minute bars + session VWAP + intraday RVOL in market_data (timeframe param); VWAP labeled IEX-feed; tests with fixture minute bars.
- [ ] T053 — Breakout detector with volume confirmation: range escape + RVOL expansion threshold + hold-outside check; explicitly annotates weak-volume escapes as suspected fakeouts; tests both paths.
- [ ] T054 — Range strategy template + regime router: support→long→resistance on the T030 contract, and a meta-strategy that picks momentum/range/CASH by T050 regime; backtested across all three synthetic regimes (must beat naive always-momentum in CHOP).
- [ ] T055 — No-trade condition as first-class: paper loop gains "no_trade" signal_log action with reasons (expected move < cost threshold, RVOL floor, regime=quiet) + max-trades-per-day overtrading guard; tests prove the loop can conclude "there isn't a trade today".
- [ ] T056 — exit_plan in briefings/chat: structured hold-horizon guidance per thesis (range: levels; momentum: trend-break level; time-based fallback) — the "how long do I hold" answer as data, not prose.
- [ ] (future, logged) Options awareness: theta/IV warnings in low-vol regimes live in the doctrine; full options analytics is a separate future phase — do not build ad hoc.

## Backlog — Adopted from ChatGPT master-spec review (docs/research/chatgpt-master-spec-review.md)
- [ ] T060 — Time-weighted returns: benchmark comparison currently distorts under deposits/withdrawals; compute TWR from account_snapshots + transactions (needs T036 fills), use it in /api/benchmark; hand-computed tests with a mid-period deposit.
- [ ] T061 — User profile + Investment Policy Statement (IPS): objectives, target return, max acceptable drawdown, horizon, restrictions, prohibited strategies in DB; injected into chat context; every recommendation checked against it, conflicts stated plainly. (Gemini spec upgrade, D014.)
- [ ] T062 — Briefs & reviews: morning brief + end-of-day report + WEEKLY investment-committee review (performance, discipline, behavioral trends, lessons, next priorities); deterministic composition + LLM narration; `GET /api/brief?type=morning|eod|weekly`.
- [ ] T063 — Decision journal: persist every chat recommendation (symbol, verdict, confidence, thesis, horizon, key-risk level) to a table; later scoring pass compares outcomes → measurable calibration (spec §28 self-evaluation).
- [ ] T064 — Backtest rigor pack: walk-forward splits, per-trade stats (win rate, profit factor, avg/best/worst trade), Calmar, and named historical-crisis stress windows (2008/2020/2022 where data allows); extend backtest_runs + ledger.
- [ ] T065 — Risk engine v2: sector-exposure caps (needs sector data from T023), cancel-all + disable-symbol controls, order-frequency limit (merge with T055 overtrading guard).

## Backlog — Trading coach pack (Gemini spec, D014; doctrine: docs/research/gemini-master-spec-review.md)
- [ ] T066 — Trade coaching: pre-trade review (thesis, sizing, concentration, correlation, regime fit, IPS compliance) + post-trade review (expected vs actual, entry/exit quality, rule adherence, lesson) persisted per trade; PROCESS-not-outcome scoring. Depends on T016 for real fills; chat-level v0 works today via conversation.
- [ ] T067 — Decision Quality Score + graduated advisories: rolling DQS from behavioral signals (revenge trading, FOMO, post-loss impulsivity, sizing inconsistency) + risk-budget-consumed (derived from IPS); proactive advisory levels 1–3 ("80% of today's risk budget consumed"); Level 4 hard stop remains the existing breaker, unchanged.
- [ ] T068 — Watchlist + opportunity ranking: watchlist table + ranked view scoring briefings (edge, risk, portfolio fit, confidence) — a ranked research pipeline instead of isolated ideas.
- [ ] T069 — Adaptive risk-tolerance estimation (owner request 2026-08-12): derive a recommended risk budget from account composition (invested vs cash), drawdown history, and demonstrated behavior (sizing drift, post-loss trade frequency); KUBERA proposes, owner ratifies into the IPS (T061); feeds the DQS budget (T067). The owner explicitly wants KUBERA's estimate to override his in-the-moment self-assessment.

## Backlog — Phase 2: Analysis & insight engine (agents)
- [ ] T023 — Fundamentals + news ingestion: evaluate the owner's existing FMP/FRED keys (D009) vs Alpaca news; verify key validity + tier limits first, then pick and integrate one source.
- [ ] T016 — Schwab Trader API read-only sync (owner's real thinkorswim account): positions + balances alongside Alpaca paper, same timestamped model shapes. Prereqs: owner confirms Schwab developer app/keys are active; agent verifies current API capabilities (paper endpoint? scopes?) before building. Live orders out of scope pending §7.4. (D009)

## Backlog — Phase 3: Backtesting & strategy sandbox (agents)
- [ ] T036 — Paper-loop polish (remainder of old T035 scope): sync fills from Alpaca activities into `transactions` (deduped); market-hours guard so cycles outside RTH log no_action instead of placing queued orders.

## Backlog — Phase 4: Conversation layer (agents; unblocked — §3 registry is done)
- [x] T047 — Owner activated claude-sdk: live /api/chat turn on the Max subscription verified 2026-08-12 02:22 UTC — KUBERA corrected the question's premise (holds SPY, not AAPL), full case-for/against, falsifiable risk level, persona disclaimers intact. Side-channel audit captured both tool calls. Quirk found+fixed: SDK usage is a dict (was parsed as object → 0/0).
- [ ] T045 — KUBERA MCP server (D011): thin FastMCP/official-SDK stdio server exposing the T024 registry tools (get_portfolio, get_latest, get_daily_bars, compare_benchmark, get_symbol_briefing) so Claude Desktop/Antigravity/mobile become KUBERA frontends pre-PWA. Read-only; no order tools until §7.4 exists. Later: streamable-http + auth for remote/mobile.

## Blocked
(none)

## Done
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
