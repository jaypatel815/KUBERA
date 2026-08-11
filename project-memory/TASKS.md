# TASKS

One ticket = one focused agent session. Claim by adding your name as owner.
IDs never get reused. Format per PROJECT_SPEC.md §11.

## In progress
(none)

## Backlog — Owner actions (Chotu — nothing else is blocked on these yet, but T005/T006 gate Phase 1 completion)
- [ ] T005 — Create a **private** GitHub repo, push `main`, confirm the Actions CI run is green.
- [ ] T006 — Open an Alpaca account, generate **paper** API keys, copy `.env.example` → `.env`, fill it in. Never commit `.env`.
- [ ] T007 — Install Python 3.11+ on Windows, run the README quickstart, confirm `verify.py` passes locally.
- [ ] T008 — `pip install pre-commit && pre-commit install` (activates the commit-time secret scanner).

## Backlog — Phase 1: Data & portfolio backbone (agents)
- [ ] T011 — Alpaca paper client in `/backend/data`: account + positions fetch, every payload timestamped; integration test against the paper API that skips cleanly when keys are absent (needs T006). Use `settings.require_alpaca()` from T010.
- [ ] T012 — Market data via Alpaca Data API: latest quote + daily history; every payload carries `source` and `asof`; tests.
- [ ] T013 — DB schema v1 (SQLAlchemy 2 + SQLite + alembic): accounts, positions, transactions, snapshots; first migration; tests. (D007)
- [ ] T014 — Scheduled refresh job writing position/quote snapshots; tests.
- [ ] T015 — `GET /portfolio`: live holdings, values, asof — wired through T011–T014; integration test. **Phase 1 exit criterion (spec §7.1).**

## Blocked
(none)

## Done
- [x] T010 — Typed settings loader (`backend/settings.py`, pydantic-settings): fail-fast `require_alpaca()`, SecretStr, `/health` reports config state; 5 tests — 2026-08-11
- [x] T004 — git init, CI workflow, gitleaks pre-commit config, .env.example, .gitignore — 2026-08-11
- [x] T003 — Backend skeleton: FastAPI /health, analysis.returns + 7 tests, ruff, verify.py — 2026-08-11
- [x] T002 — project-memory working files (TASKS, DECISIONS, ISSUES, PROGRESS) — 2026-08-11
- [x] T001 — AGENTS.md + PROJECT_SPEC.md authored — 2026-08-10
