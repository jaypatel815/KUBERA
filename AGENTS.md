# AGENTS.md — KUBERA

Read this file in full before doing anything else in this repo. Whether you are Claude Code, Gemini inside Antigravity, GitHub Copilot, or ChatGPT/Codex, this file is the shared contract all four of you follow so the human product owner never has to repeat context between tools or sessions.

KUBERA is a personal financial research and portfolio-analysis assistant, managing one person's own capital. It is not a service offered to other people, and it is not a registered investment adviser.

Full spec, architecture, and phase roadmap: `/project-memory/PROJECT_SPEC.md`
Current state — read this every session: `/project-memory/PROGRESS.md`
Your task queue: `/project-memory/TASKS.md`
Known bugs, so you don't re-diagnose one from scratch: `/project-memory/ISSUES.md`
Why past decisions were made: `/project-memory/DECISIONS.md`

## Priority order when instructions conflict
1. Never present stale, mocked, or placeholder data to the user as if it were current.
2. Never let the LLM compute a number that should come from tested code (see Determinism rule).
3. A task is not done until its tests pass and CI is green.
4. Build the current phase in `PROJECT_SPEC.md` §7 — don't jump ahead to later-phase features just because they're easy to add while you're in the file.

## Determinism rule — non-negotiable
Anything involving money (returns, position sizing, order quantities, risk limits, benchmark comparisons) is computed by tested, deterministic code in `/backend/analysis` or `/backend/risk`. The conversation layer calls these as tools and explains the result in natural language — it never free-hands the arithmetic itself, and no financial figure in a user-facing response should exist only inside an LLM completion.

## Safety rails — non-negotiable
- Paper trading is the default for every strategy, every time, on every broker connection. Live capital requires the promotion checklist in `PROJECT_SPEC.md` §7.4 and the user's explicit, specific approval.
- Position size caps and a daily-loss circuit breaker are enforced in `/backend/risk` code — a hard stop the LLM cannot reason its way around, not a prompt instruction.
- Every recommendation, every trade signal, and every order is logged with a timestamp, the data snapshot it was based on, and its stated confidence/risks.

## Stack
Keep this current — this section should never go stale. Rationale in `/project-memory/DECISIONS.md`.
- Backend: Python 3.11+ / FastAPI · Frontend: PWA (D004) · Database: SQLite → Postgres+pgvector at Phase 3 (D007) · Broker: Alpaca paper (D006) · Market data: Alpaca Data API free tier (D006)
- Markets: US equities first (D002) · Execution: paper-only until spec §7.4 gate passes (D003)
- Setup: `pip install -r backend/requirements.txt` · Verify (lint+tests): `python scripts/verify.py` · Run: `uvicorn --app-dir backend api.main:app --reload`

## Session protocol
**Start of every session:** read this file, then `PROGRESS.md`, then your assigned item in `TASKS.md`. Only read the `DECISIONS.md` entries and `PROJECT_SPEC.md` sections relevant to the module you're touching — you don't need the whole spec every time.
**End of every session, before you stop:** update your task in `TASKS.md` (done / blocked / new tasks discovered), append one dated entry to `PROGRESS.md`, log any unresolved error to `ISSUES.md` with repro steps, and commit with a message referencing the task ID. If the session changed the user-facing surface (endpoints, scripts, commands), update README.md's "Try what's built so far" section in the same session — the owner tests from it. Never leave the tree with failing tests or uncommitted secrets.

## Do not
- Commit secrets, API keys, or `.env` contents.
- Put mock or placeholder data anywhere under `/backend` or `/apps` outside `**/tests/fixtures/`.
- Rename or restructure `/project-memory/` — every agent and every tool depends on these exact paths.
- Present financial analysis as certainty. Every answer states its data recency and its key assumptions.

## Where things live
- `/backend/api` — FastAPI app; conversation layer lands here in Phase 4
- `/backend/data` — broker + market-data clients, database layer
- `/backend/analysis` — deterministic metrics, benchmark comparison
- `/backend/risk` — position limits, circuit breaker, the execution gate
- `/backend/backtest` — strategy sandbox, paper-trading loop
- `/backend/research_agent` — proposes strategy/data ideas only; cannot write to `/backend/risk` or place live orders
- `/apps` — client app(s)
- `/project-memory` — the memory system this file describes

For architecture, the full phase-by-phase roadmap, tech stack rationale, and which of you should own which kind of task, see `/project-memory/PROJECT_SPEC.md`.
