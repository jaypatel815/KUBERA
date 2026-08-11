# KUBERA

A personal financial research and portfolio-management assistant, built 100% by AI agents
with a human product owner. Personal use, own capital only — not investment advice, not an
RIA (see `/project-memory/PROJECT_SPEC.md` §10).

## Resume a session (any agent, any tool)

Paste this into Claude Code, Antigravity/Gemini, Copilot, or ChatGPT:

> Read `/AGENTS.md`, then `/project-memory/PROGRESS.md`, then pick up the top unblocked item
> in `/project-memory/TASKS.md` that fits your strengths. If none fit, tell me what's blocked
> and why instead of picking an unrelated task.

In Claude Cowork: select this folder and type `/kubera`.

## Quickstart (Windows)

```
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
python scripts\verify.py          # lint + tests — must PASS
uvicorn --app-dir backend api.main:app --reload
```

Then open http://127.0.0.1:8000/health — a JSON `"status": "ok"` means the backbone is alive.

With Alpaca paper keys in `.env`, create the database and take a snapshot:

```
alembic -c backend\alembic.ini upgrade head
python scripts\sync.py            # add --loop 300 to snapshot every 5 minutes
```

## Repo map

- `/AGENTS.md` — the contract every AI agent follows. Read first, always.
- `/project-memory/` — shared memory: spec, progress, tasks, decisions, issues.
- `/backend/` — FastAPI app (`api`), deterministic engine (`analysis`, `risk`, `backtest`),
  data layer (`data`), scheduled research process (`research_agent`), tests.
- `/apps/` — PWA client (Phase 5).
- `/scripts/verify.py` — the one gate: green before any session ends. CI runs the same script.

## Status

Current phase and next steps: `/project-memory/PROGRESS.md` (newest entry on top).
Roadmap: `/project-memory/PROJECT_SPEC.md` §7. Phases: 0 Foundations · 1 Data & portfolio ·
2 Analysis engine · 3 Backtesting · 4 Conversation · 5 Cross-platform app + voice ·
6 Hands-free · 7 Continuous learning · 8 Hardening.
