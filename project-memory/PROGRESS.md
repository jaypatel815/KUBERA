# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
When this file exceeds ~150 lines, move old entries to /project-memory/archive/.

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
