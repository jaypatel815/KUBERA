# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
When this file exceeds ~150 lines, move old entries to /project-memory/archive/.

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
