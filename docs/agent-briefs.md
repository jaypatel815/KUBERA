# Agent briefs — paste this to start a parallel session (D023)

Both agents build DIFFERENT tickets at the same time and review each other's
finished work. There is one brief, not two — every agent is both a builder and
a reviewer. Paste the same text into Claude (Cowork/Code) and into Gemini
(Antigravity); they sort themselves out through `TASKS.md`.

---

## THE BRIEF (paste into any agent)

```
Read /AGENTS.md (especially "Parallel work"), then /project-memory/PROGRESS.md,
then /project-memory/TASKS.md. Another agent is working in this repo AT THE SAME
TIME, in the same folder.

STEP 1 — REVIEW FIRST, BUILD SECOND.
If TASKS.md shows a ticket "AWAITING REVIEW" from a DIFFERENT agent, review it
now, before you claim anything. Follow /project-memory/REVIEW.md: read the
intent before the diff, run `python scripts/verify.py` yourself, work the
checklist (owner alignment first, then truthfulness, doctrine, mechanics, and
the parallel-conflict checks), then write the verdict block into TASKS.md and
mark it DONE or send it back. Commit your review by path.

STEP 2 — CLAIM A TICKET THAT DOESN'T COLLIDE.
Pick the top unblocked ticket whose files the other agent is NOT in. Check their
"In progress" line first. Add "In progress — <ticket> — <your agent name>" to
TASKS.md and commit that single line before writing code.

STEP 3 — BUILD IT.
Follow AGENTS.md: deterministic money math with hand-computed test values, every
payload timestamped and sourced, paper-only, sells never blocked, no mock data
outside tests/fixtures.

STEP 4 — COMMIT SAFELY. THIS IS THE ONE THAT BITES.
We share ONE working directory. NEVER `git add -A` or `git commit -a` — you will
sweep up the other agent's half-written files. Run `git status`, then stage BY
PATH, only files you touched. If .git/index.lock exists, the other agent is
mid-commit: wait, don't delete it.

STEP 5 — HAND OFF, DON'T SELF-CERTIFY.
Run the verify gate (must PASS), mark your ticket "AWAITING REVIEW — <your agent
name>" in TASKS.md, append ONE PROGRESS.md entry (append — never rewrite the
other agent's lines), and commit. Do NOT mark your own work DONE. The other
agent reviews it next session.

If you and the other agent disagree twice on a review, stop and escalate to
Chotu with both positions in three lines each.
```

---

## Owner's context every reviewer should hold

Chotu is 26, starting with ~$1,000 against $60–70k of debt, aiming at $1M over
decades, voice-first, and explicitly asked KUBERA to **challenge his assumptions
rather than validate them**. He has said he blows through his own limits — which
is why the risk rails are un-overridable by design. The features that matter
most are the ones that tell him something he'd rather not hear: the curve-fit
verdict, the decay demotion, "that's not diversification", the 147x-a-year
reality check, and time-weighted return refusing to call a deposit performance.

A reviewer who protects that property is doing the job. A reviewer who only
checks syntax is not.

---

## Ticket pairs that are safe to run at the same time

| Agent A (backend-leaning) | Agent B (UI/field-leaning) | Overlap |
|---|---|---|
| T091b holding-period distribution | T082 remaining Orb polish | none |
| T072 human-grade TTS backends | T082 freshness badges | none |
| T083 event base rates (needs T023) | T087 open-trade monitor surface | none |
| T094 HRP / T095 factor loadings | phone install / PWA | none |

**Do NOT pair:** two tickets that both add registry tools (three shared guard
tests), two tickets that both add database tables (single alembic head), or two
tickets that both edit `apps/web/orb.html`.
