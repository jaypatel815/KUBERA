# TASKS

One ticket = one focused agent session. Claim by adding your name as owner.
IDs never get reused. Format per PROJECT_SPEC.md §11.

## In progress
(none)

## Backlog — Owner actions (Chotu — nothing else is blocked on these yet, but T005/T006 gate Phase 1 completion)
- [ ] T005 — GitHub repo created + remote added ✔ (2026-08-11). Remaining: push `main` from your machine (sandbox has no GitHub auth) and confirm the Actions CI run is green.
- [x] T006 — Alpaca paper keys in `.env` — done 2026-08-11 (owner). Note: owner's `.env` uses `ALPACA_API_KEY` naming + extra vars from another template; settings loader accepts both spellings, extras ignored.
- [ ] T007 — **Phase 1 sign-off:** run the README quickstart on Windows (Python 3.11+): `verify.py` green runs the 3 live paper-account tests, then `alembic upgrade head` + `python scripts\sync.py` + open `http://127.0.0.1:8000/portfolio` — live holdings with timestamps = Phase 1 officially done.
- [x] T008 — pre-commit installed — done 2026-08-11 (owner). Sandbox-side caveat: I003.

## Backlog — Phase 2: Analysis & insight engine (agents)
- [ ] T020 — Time-series metrics in `/backend/analysis`: daily returns, CAGR, volatility, Sharpe, max drawdown — known-answer tests (hand-computed fixtures). Spec §7.2.
- [ ] T021 — Benchmark comparison: portfolio equity history (account_snapshots) vs SPY or any symbol (market_data bars), aligned by date; `GET /api/benchmark?symbol=SPY&days=90`.
- [ ] T022 — Win/loss breakdown across positions (green vs red, counts + magnitudes) feeding the future dashboard chart; extend `/portfolio`.
- [ ] T023 — Fundamentals + news ingestion: evaluate the owner's existing FMP/FRED keys (D009) vs Alpaca news; verify key validity + tier limits first, then pick and integrate one source.
- [ ] T024 — Tool-calling registry (spec §3): typed registration mapping conversation-layer tools to analysis/data functions; foundation for Phase 4.
- [ ] T017 — Chore: unify shared httpx plumbing between `data/alpaca.py` and `data/market_data.py` (no behavior change; tests stay green).
- [ ] T016 — Schwab Trader API read-only sync (owner's real thinkorswim account): positions + balances alongside Alpaca paper, same timestamped model shapes. Prereqs: owner confirms Schwab developer app/keys are active; agent verifies current API capabilities (paper endpoint? scopes?) before building. Live orders out of scope pending §7.4. (D009)

## Blocked
(none)

## Done
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
