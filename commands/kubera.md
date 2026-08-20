---
description: Resume a KUBERA working session — read the project memory and continue from the top unblocked ticket.
---

KUBERA is the financial-assistant project in this repository, built entirely
by AI agents using the repo as shared memory. Resume protocol:

1. Read, in order: `/AGENTS.md`, `/project-memory/PROGRESS.md` (newest entry
   on top), `/project-memory/TASKS.md`. Read `/project-memory/DECISIONS.md`,
   `/project-memory/ISSUES.md`, and `PROJECT_SPEC.md` sections only as the
   task at hand requires.
2. Give a status summary of 3 lines or fewer: current phase, last session's
   result, proposed next task (the top unblocked TASKS.md item that suits
   this environment).
3. Proceed unless redirected. Follow /AGENTS.md strictly: financial math
   only in tested deterministic code, never LLM-computed; paper trading is
   the default; never commit secrets; verify gate green before any session
   ends (`python scripts/verify.py`).
4. Session end, in order: verify gate PASS -> update TASKS.md + append a
   dated PROGRESS.md entry -> commit referencing ticket IDs (by pathspec,
   never `git add -A`) -> close with a summary of 5 lines or fewer.
