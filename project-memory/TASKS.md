# TASKS

One ticket = one focused agent session. Claim by adding your name as owner.
IDs never get reused. Format per PROJECT_SPEC.md §11.

## In progress
(none)

## Backlog — Owner actions (Chotu — nothing else is blocked on these yet, but T005/T006 gate Phase 1 completion)
- [ ] T005 — GitHub repo created + remote added ✔ (2026-08-11). Remaining: push `main` from your machine (sandbox has no GitHub auth) and confirm the Actions CI run is green.
- [x] T006 — Alpaca paper keys in `.env` — done 2026-08-11 (owner). Note: owner's `.env` uses `ALPACA_API_KEY` naming + extra vars from another template; settings loader accepts both spellings, extras ignored.
- [ ] T007 — Install Python 3.11+ on Windows, run the README quickstart, confirm `verify.py` passes locally.
- [x] T008 — pre-commit installed — done 2026-08-11 (owner). Sandbox-side caveat: I003.

## Backlog — Phase 1: Data & portfolio backbone (agents)
- [ ] T014 — Scheduled refresh job writing position/quote snapshots; tests.
- [ ] T015 — `GET /portfolio`: live holdings, values, asof — wired through T011–T014; integration test. **Phase 1 exit criterion (spec §7.1).**

## Backlog — Phase 2 seeds
- [ ] T016 — Schwab Trader API read-only sync (owner's real thinkorswim account): positions + balances alongside Alpaca paper, same timestamped model shapes. Prereqs: owner confirms Schwab developer app/keys are active; agent verifies current API capabilities (paper endpoint? scopes?) before building. Live orders out of scope pending §7.4. (D009)

## Blocked
(none)

## Done
- [x] T013 — DB schema v1: SQLAlchemy 2 models (broker_accounts, account_snapshots, position_snapshots, transactions), UTCDateTime type rejecting naive datetimes, engine/session factory, first alembic migration `bee2b4896cdf` + migration-parity test; `alembic -c backend/alembic.ini upgrade head` — 2026-08-11
- [x] T012 — Market data client (`backend/data/market_data.py`): latest trade/quote + daily OHLCV (IEX free feed, split-adjusted), dual timestamps (exchange_ts + asof) on every payload, RFC3339 parser handling Alpaca's variable-precision fractions on py3.10+; `GET /api/market/{symbol}/latest` + `/bars`; 9 new tests — 2026-08-11
- [x] T011 — Alpaca paper client (`backend/data/alpaca.py`): account + positions, timestamped/sourced payloads, actionable 401s, **live-endpoint refusal rail** (§7.4 not implemented = no code path to real money); `GET /api/account`; 8 new tests + skip-guarded live integration test — 2026-08-11
- [x] T010 — Typed settings loader (`backend/settings.py`, pydantic-settings): fail-fast `require_alpaca()`, SecretStr, `/health` reports config state; 5 tests — 2026-08-11
- [x] T004 — git init, CI workflow, gitleaks pre-commit config, .env.example, .gitignore — 2026-08-11
- [x] T003 — Backend skeleton: FastAPI /health, analysis.returns + 7 tests, ruff, verify.py — 2026-08-11
- [x] T002 — project-memory working files (TASKS, DECISIONS, ISSUES, PROGRESS) — 2026-08-11
- [x] T001 — AGENTS.md + PROJECT_SPEC.md authored — 2026-08-10
