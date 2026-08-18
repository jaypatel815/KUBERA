# Review: NousResearch/hermes-agent ("the agent that grows with you")

Reviewed 2026-08-17 by Claude/Cowork at the owner's request. Read this before
re-proposing anything from that project — much of it is convergent evolution
with what KUBERA already does, one lesson was adopted immediately because our
own repo proved it (D031/T112), and the rejections have reasons.

Source: https://github.com/nousresearch/hermes-agent (docs: memory, skills,
curator, security, architecture, agent-loop).

## What it is

A general-purpose self-improving personal agent: a built-in learning loop that
writes bounded memory files and "skills" (procedural memory) from experience,
a background review fork that quietly persists lessons after turns, and a
"curator" that maintains what was learned (staleness, consolidation, archival)
— with optional human write-approval gates, provenance tracking, snapshots,
and rollback.

## Convergent evolution — they built what we built (validation, not adoption)

| hermes-agent | KUBERA equivalent |
|---|---|
| Memory files + skills as the agent's persistence | Repo-as-memory: AGENTS.md, PROGRESS/TASKS/DECISIONS/ISSUES, docs/research dispositions — git-versioned, which they lack |
| Human write-approval staging | D023: a DIFFERENT agent reviews every ticket; owner ratifies IPS/promotions. Ours is on by default and cross-agent; theirs defaults OFF ("write freely") |
| Provenance (`created_by`, write origins) | Agent names on every entry, git authorship on every commit |
| "Never auto-delete; worst outcome is archival, which is recoverable" + pre-pass snapshots | Move-never-delete + git history IS the snapshot (adopted formally in D031) |
| Multi-writer corruption warning ("two processes on one home compound each other's entries") | D023's whole parallel protocol: pathspec commits, anchored edits, parallel_check.py — we hit this exact failure live and wrote the rules from it |
| Hardline blocklist beneath YOLO mode | The breaker/tiers "cannot be talked out of"; update_ips unreachable via MCP |
| Frozen-snapshot prompt (state read once at session start) | The /kubera resume protocol reads state at session start |
| Iteration budgets, stop-with-summary | Loop max_trades_per_day, SDK max_turns |

The most striking line in their docs is our experience verbatim: "Without
maintenance, you end up with dozens of narrow near-duplicates that pollute the
catalog and waste tokens."

## Adopted (D031; T112 built same day)

**Bounded memory with forced, never-silent consolidation.** Their memory tool
returns an ERROR when a write would exceed the bound — "instead of silently
dropping entries" — which forces same-turn curation. Our repo proved the need
the moment we measured: PROGRESS.md's own day-one header says "when this file
exceeds ~150 lines, move old entries to /project-memory/archive/" and it stood
at **2,654 lines with no archive directory in existence**. A rule that is not a
mechanism does not happen (D028 said the same about self-review). T112:
`scripts/archive_memory.py` (move-never-delete, newest entries stay, archived
entries keep provenance, the move is an ordinary reviewable commit) plus a
memory-budget check wired into the verify gate — WARN at the soft budget, FAIL
at the hard one, so overflow forces deliberate archiving exactly the way their
error forces consolidation.

**Also folded into D031 as standing rules** (cheap, no build): archival is
always MOVE, never delete; curation runs only over CLOSED/RESOLVED entries
(their "provenance-scoped autonomy" — the curator never touches what a human
authored or what is still open); every curation pass prints what moved (their
run reports).

## Rejected, with reasons

- **Background self-improvement review fork.** Their docs admit it "can burn a
  meaningful share of total tokens," and its cheap-model variant is exactly
  what D027 forbids: a review that did not run the evidence. KUBERA's lessons
  become D-entries through failures examined by a second agent, not through a
  quiet background pass with write-gates that default to open.
- **Skills catalog + curator LLM pass.** Our "skills" are AGENTS.md rules and
  D-decisions; they number ~30, are load-bearing, and every one was reviewed
  in. Staleness is not our failure mode at this scale; unbounded PROGRESS was.
- **Injection scanning of learned content.** Their memory lands in a system
  prompt from many surfaces; ours is a git repo written by two known agents
  and the owner, where review is the scanner. Revisit only if Phase 7 ever
  lets generated content write memory.
- **FTS5 session-search DB.** git grep over the repo is our session search;
  at 5,365 total memory lines (about to shrink), a database is a solution
  shopping for a problem.
- **The framework itself** (gateway, 25 platform adapters, 7 terminal
  backends): KUBERA is a financial system with a deliberately small surface,
  not a personal-agent platform.

## One-line lessons worth keeping (no ticket)

- Their write-gates DEFAULT OFF and the docs recommend enabling them "for
  small models that misjudge what they learned" — defaults-open self-writing
  is the design we already declined to be, on purpose.
- "The container is the security boundary" (dangerous-command checks skipped
  inside sandboxes) — same shape as T110's isolation-boundary precondition:
  decide where the boundary IS, then trust it consistently.
- Telemetry-driven staleness (use counts deciding what goes stale) is the
  right instinct if our docs/research folder ever gets unwieldy.
