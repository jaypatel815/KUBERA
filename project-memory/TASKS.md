# TASKS

One ticket = one focused agent session. Claim by adding your name as owner.
IDs never get reused. Format per PROJECT_SPEC.md §11.

## In progress
(none)

## Backlog — Owner actions (Chotu — nothing else is blocked on these yet, but T005/T006 gate Phase 1 completion)
- [ ] T005 — Create a **private** GitHub repo, push `main`, confirm the Actions CI run is green.
- [x] T006 — Alpaca paper keys in `.env` — done 2026-08-11 (owner). Note: owner's `.env` uses `ALPACA_API_KEY` naming + extra vars from another template; settings loader accepts both spellings, extras ignored.
- [ ] T007 — Install Python 3.11+ on Windows, run the README quickstart, confirm `verify.py` passes locally.
- [x] T008 — pre-commit installed — done 2026-08-11 (owner). Sandbox-side caveat: I003.

## Backlog — Phase 1: Data & portfolio backbone (agents)
- [ ] T012 — Market data via Alpaca Data API: latest quote + daily history; every payload carries `source` and `asof`; tests.
- [ ] T013 — DB schema v1 (SQLAlchemy 2 + SQLite + alembic): accounts, positions, transactions, snapshots; first migration; tests. (D007)
- [ ] T014 — Scheduled refresh job writing position/quote snapshots; tests.
- [ ] T015 — `GET /portfolio`: live holdings, values, asof — wired through T011–T014; integration test. **Phase 1 exit criterion (spec §7.1).**

## Blocked
(none)

## Done
- [x] T011 — Alpaca paper client (`backend/data/alpaca.py`): account + positions, timestamped/sourced payloads, actionable 401s, **live-endpoint refusal rail** (§7.4 not implemented = no code path to real money); `GET /api/account`; 8 new tests + skip-guarded live integration test — 2026-08-11
- [x] T010 — Typed settings loader (`backend/settings.py`, pydantic-settings): fail-fast `require_alpaca()`, SecretStr, `/health` reports config state; 5 tests — 2026-08-11
- [x] T004 — git init, CI workflow, gitleaks pre-commit config, .env.example, .gitignore — 2026-08-11
- [x] T003 — Backend skeleton: FastAPI /health, analysis.returns + 7 tests, ruff, verify.py — 2026-08-11
- [x] T002 — project-memory working files (TASKS, DECISIONS, ISSUES, PROGRESS) — 2026-08-11
- [x] T001 — AGENTS.md + PROJECT_SPEC.md authored — 2026-08-10
