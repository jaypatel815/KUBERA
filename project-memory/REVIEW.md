# REVIEW.md — the blocking cross-check (D023)

Agents work on DIFFERENT tickets at the same time and review each other's
finished work. Everyone builds; everyone reviews; nobody signs off on their own
commit. The reviewer's job is not to admire the code. It is to answer one
question on the owner's behalf:

> **Does this actually serve what Chotu is trying to do — and does it tell him
> the truth even when the truth is unflattering?**

The builder marks `AWAITING REVIEW`. The OTHER agent writes `DONE`.

**When to review:** at the START of your next session, before you claim a new
ticket. Reviewing is the price of admission to your next build — that is what
keeps the queue from silting up while both agents chase new work.

---

## How to review (30–45 minutes, in this order)

### 1. Read the intent before the diff
Read the ticket in `TASKS.md`, then the relevant `DECISIONS.md` entries, then
the owner's IPS (`GET /api/ips` or the `investment_policy` table). Only then
read `git show <commit>`. Reviewing a diff without the intent produces
style notes instead of judgment.

### 2. Run the gate yourself
`python scripts/verify.py` must PASS on your machine, not just the builder's.
If it fails, that is an automatic BLOCK — no exceptions, no "it passed for me".

### 3. Work the checklist

**Owner alignment — the part only a human-aware reviewer can do**
- [ ] Does this serve a goal Chotu actually stated, or a goal an AI invented for
      him? (If you cannot point to the ticket, a DECISION, or his own words,
      BLOCK and ask.)
- [ ] Does it respect the deliberate constraints: paper-only, long-only until
      the D021 revisit, live capital needs §7.4 + explicit approval?
- [ ] Does it contradict a settled decision without new evidence? D017/D019/D021
      rejections (99.9% accuracy claims, XGBoost-now, sentiment-as-alpha,
      L2/dark-pool, single-trade probability-of-profit) are settled. Relitigating
      one without evidence is a BLOCK.
- [ ] Would this make it EASIER for him to break his own rules (oversize, revenge
      trade, override the breaker)? If yes, BLOCK regardless of code quality —
      the un-overridable rails are the product.

**Truthfulness — KUBERA's core promise**
- [ ] Is every financial number computed in tested deterministic code, never by
      the LLM?
- [ ] Are hand-computed expected values in the tests, or does the test merely
      assert that the code returns what the code returns? (A test that recomputes
      the implementation is not a test — BLOCK.)
- [ ] Does every payload carry `asof` + `source`, and does stale/limited data
      SAY so? (IEX volume understates, daily bars miss intraday, average entry
      price blends fills — these labels must travel with the number.)
- [ ] Does the failure path tell the truth? Empty state, missing key, no history
      → an honest "here's why" and never a fabricated figure or a silent zero.
- [ ] If it added a tool: does the description tell the model what NOT to
      conclude, not just what the tool returns?

**Doctrine fit — his trading rules, as code**
- [ ] Regime-aware where it should be (trend vs range vs no-trade)?
- [ ] Does it preserve "sells are never blocked"? Every guard is buys-only.
- [ ] Does it respect "the biggest enemy is overtrading" — does this make
      trading MORE tempting or more deliberate?
- [ ] Process over outcome: does it judge decisions by quality, not by whether
      they made money?

**Mechanics**
- [ ] Tool count guards bumped in all three files if a tool was added.
- [ ] Alembic: single head after this change (`alembic heads`).
- [ ] Memory updated: TASKS entry, one PROGRESS entry, ISSUES if anything broke.
- [ ] No secrets, no mock data outside `tests/fixtures/`.

### 4. Write the verdict in `TASKS.md`, under the ticket

```
REVIEWED <date> by <agent> — <PASS | BLOCK>
  aligned: <one line: which owner goal this serves>
  checked: <what you actually ran/read — be specific>
  concerns: <none | numbered list>
```

A PASS with unlisted concerns is worthless. If something bothers you and you
cannot justify blocking, write it as a concern anyway — the owner reads these.

### 5. Commit the REVIEW, never the code
Your review is its own commit: `review <TICKET>: PASS` or `... : BLOCK`,
staging ONLY `project-memory/TASKS.md` (plus `ISSUES.md` if you found a bug
worth logging). You do NOT commit the builder's source files — they already
did, which is what protected their work from you while you were both editing
the same folder.

If you find something that needs a code change, you have two honest options:
- **BLOCK** — write the reason; the builder fixes and re-submits. Default.
- **Fix it yourself ONLY if trivial and mechanical** (a typo, a wrong count in
  a guard test). Then it is your own mini-ticket: separate commit, your name,
  and say so in the verdict — because now that change is unreviewed, and the
  builder reviews it back.

---

## What a BLOCK looks like (be specific and kind)

> BLOCK — the sizing tool now defaults `risk_frac` to 0.02 when the IPS is
> missing. That silently doubles his stated risk budget in exactly the case
> where we know least. Fail closed instead: refuse and say the IPS is unset.

Not:

> BLOCK — I'd have written this differently.

## Reviewing your own agent's earlier work
Allowed and encouraged — the ban is on reviewing the commit you just wrote.
A fresh session reviewing last week's ticket is a real review.

## Conflict check — the part that only matters in parallel
Because both agents edit ONE working directory, add these to every review:
- [ ] `git show --stat <their commit>` — does it contain files that belong to
      YOUR ticket? If yes, they ran `git add -A` and swept up your work. Say so;
      that is a BLOCK and the fix is a follow-up commit, not a revert.
- [ ] `alembic heads` — exactly one head? Two means concurrent migrations
      branched; the newer one must be rebased onto the older.
- [ ] Tool-count guards: if both of you added tools this cycle, do the three
      counts match the registry NOW, after both commits?
- [ ] Did they overwrite your PROGRESS/TASKS lines instead of appending?
      `python scripts/parallel_check.py` reports the clobber signature
      automatically — run it as part of every review.
- [ ] Run the verify gate on the CURRENT tree (both agents' work combined) —
      each half can pass alone and fail together. This is the check that a
      single-agent workflow never needs and a parallel one lives or dies by.

## When the reviewer and builder disagree twice
Stop and escalate to the owner with both positions in three lines each. Do not
ping-pong; his time is the scarce resource, but a deadlock costs him more.
