# PROGRESS

Newest entry on top. One dated entry per session, appended before the session ends.
When this file exceeds ~150 lines, move old entries to /project-memory/archive/.

## 2026-08-16 — Claude/Cowork — T069: the risk budget his behavior argues for
The owner asked for something unusual with this one — that KUBERA's estimate be
allowed to OVERRIDE his in-the-moment self-assessment. That request is the whole
design. A stated risk tolerance is collected on a calm afternoon; the one that
matters is operating at 2pm on a red day, and only that one leaves evidence in
the fills. So the module never asks how much risk he can handle. It measures:
deepest drawdown actually lived through, whether size GROWS after a loss, whether
he trades faster in the 24h after a loss, and how much cash is left to absorb a
forced decision. Output is a proposed daily-loss / per-trade / position budget
with the evidence and sample size behind each number.
Three design choices worth defending at review: (1) the drawdown is measured on a
FLOW-ADJUSTED index, because a $500 deposit into a $1,000 account otherwise reads
as a full recovery from a 20% drawdown — the test asserts the naive series says
"recovered" and the adjusted one says the truth; (2) when the stated tolerance is
far beyond anything experienced, the budget is capped at experienced/3 and the
evidence line says the stated figure is "a belief, not yet a tested one" rather
than silently ignoring it; (3) the ONLY path that widens risk is a capped +15%
that requires both behavioral components to be clean AND the drawdown recovered,
because an adaptive budget able to widen itself without limit is not a budget.
Caught one silent-failure risk mid-build: the tool read `report.trips`, which did
not exist on AttributionReport — it would have returned an empty list and quietly
stopped measuring behavior, a wrong answer indistinguishable from a right one.
Exposed trips properly and stripped them from the get_attribution payload so that
report is unchanged; a test now guards both halves.
Verified: verify.py PASS — 692 passed, 4 skipped. 21 new tests, every fixture
hand-computed. Registry 33 -> 34, all three count guards updated. Numpy-blocked
CI simulation still collects clean.
Next: Gemini reviews T069. Owner: nothing new — T005 push and T007 finale remain.


## 2026-08-16 — Claude/Cowork — re-review T072: code passes, hand-off does not
The numpy fix is right and I verified it the same way I proved the bug: the
numpy-blocked runner that aborted collection last time now gives 671 passed, the
module skipping cleanly. Their 8 tests pass with the libraries present. The D024
directive landed well too — kokoro is the top rung, marked RECOMMENDED, and each
rung now says whether reply text leaves the machine.
Did not sign it off, for a reason that is not about the code: both files are
still UNCOMMITTED working-tree edits. The ticket header points reviewers at
d55eb6b and 31150e3, neither of which contains the fix, so a PASS written today
would attach a passing verdict to the buggy SHAs — a false entry in the exact
ledger this system exists to keep honest. Pinned the reviewed content by blob
hash (talk.py c0de4e3, test_tts_backends.py 4f8279b) so Gemini can commit and
anyone can confirm byte-for-byte that what shipped is what I read. I did not
commit their files: authorship is memory, and git log should say who fixed it.
One new concern, non-blocking: the CLI now reuses `api.tts_engine.kokoro_model_dir()`
(good — that was the directive) but wraps it in `try/except Exception` with a
fallback that resolves paths differently. With KUBERA_KOKORO_DIR=~/voices the
engine gives /home/<user>/voices and the fallback gives <repo>/~/voices, a
literal tilde directory. The fallback also guards a case that cannot happen,
since talk.py already imports api.voice_loop unguarded at line 46.
RESOLVED MINUTES LATER — and the way it resolved is the point. Gemini committed
those files (fd1c10c, 483c522) WHILE I was writing the verdict. Because I had
pinned the reviewed content by blob hash instead of assuming it would hold
still, confirming the committed version was the reviewed version took one
command: c0de4e3 == c0de4e3, 4f8279b == 4f8279b, byte-identical. No redo, no
"probably the same". Signed PASS against the real SHAs. Our concurrent memory
edits also both survived — parallel_check reports no clobber, because both
agents edited by anchor rather than rewriting shared files. That is now twice
in one day that a read/write race passed harmlessly through the protocol.
483c522 also cleared concern 3 halfway: the kokoro ImportError no longer names
soundfile, though the docstring still does. Remaining nits parked as T072b.
Verified: gate PASS. Numpy-blocked runner: 671 passed, 4 skipped (was: 1
collection error, 0 tests). I016 closed.
Next: T072 and T098 are both signed; the awaiting-review queue is empty, so the
next agent in takes a fresh ticket. Owner: T099 (kokoro model) is the only thing
standing between the Orb and a private voice.


## 2026-08-16 — Gemini/Antigravity — review T098: PASS & T072 re-submitted
Reviewed Claude's T098 (local voice for the Orb + reply text out of URL): PASS.
Verified hand-rolled PCM16 WAV encoder clamping [0, 16384, -32767, 32767],
auto-fallback vs forced-503 behavior, orb.html POST body migration and regression guard.
Re-submitted T072 addressing Claude's 6 review items and D024 owner directive:
1. `backend/tests/test_tts_backends.py`: added `np = pytest.importorskip("numpy")`
   alongside `sf = pytest.importorskip("soundfile")` so lean CI environments without
   audio dependencies cleanly skip the test module during collection.
2. Emphasized `kokoro` as RECOMMENDED across `talk.py`, `requirements-voice.txt`,
   and `README.md` voice ladder; explicitly noted cloud data transmission on `openai` and `edge`.
3. Aligned `talk.py` model directory resolution with `api.tts_engine.kokoro_model_dir()`.
4. Fixed `pip install kokoro-onnx` error message in `talk.py` and test count (8 tests).
Verified: verify.py PASS — 682 passed in 6.34s.
Next: Claude signs off T072; take next unblocked ticket.

## 2026-08-16 — Claude/Cowork — T098: the Orb speaks locally now (D024)
The owner read the T072 review and picked kokoro over OpenAI TTS. Checking what
that actually implied found the choice was half-made: `scripts/talk.py` is the
CLI he rarely opens, while the Orb — his daily interface — was calling edge-tts
unconditionally through `/api/tts`. And it was passing the reply as a GET QUERY
STRING, so "up $4,312 on NVDA" was being written into uvicorn's access log, any
proxy, and browser history before it ever reached Microsoft. He chose to fix
both halves.
Built: `api/tts_engine.py` — local-first speech. `auto` (the default) uses kokoro
the moment its model files exist and falls back to edge otherwise, logging every
time that text left the machine; forcing `kokoro` without the model returns 503
rather than silently using the cloud, because a quiet downgrade would defeat the
whole request. WAV encoding is hand-rolled on `wave` + `struct` — no soundfile,
no numpy, nothing imported at module scope — and the encoder duck-types
`.tolist()` so it accepts kokoro's numpy output without ever importing numpy.
That is deliberate: it is the I016 lesson applied to my own code the same day I
blocked someone else for it. Proof rather than assertion — the suite still
collects and passes with numpy blocked by a meta_path hook (671 passed), and one
test asserts the module head contains no audio imports.
`main.py` gained POST /api/tts (GET kept for curl and T073's tests); orb.html
POSTs and plays a blob, and a voice failure now leaves the reply on screen
instead of losing the turn. A regression test greps orb.html for
`/api/tts?text=` so the leak cannot come back by habit.
Verified: verify.py PASS — 679 passed, 3 skipped. 19 new tests.
Next: Gemini re-submits T072 with the numpy one-liner plus the D024 directive
(kokoro as the recommended CLI rung), and reviews T098. Owner: T099 — one pip
install and a 350 MB download and the Orb goes private on its own.


## 2026-08-16 — Claude/Cowork — review T072: BLOCK (I016 reopened)
Reviewed Gemini's T072 (openai + kokoro TTS backends) per D023. The feature is
right and the tests are honest — mocked, no hardware, and both backends prove
that a playback failure prints instead of raising, which is the I006 lesson
applied before it could recur. Installed soundfile in the sandbox and ran their
tests for real rather than trusting the report: 8 pass (the ticket says 9).
BLOCKED on one line. I016 was not fixed, only moved: `import numpy as np` sits
above `pytest.importorskip("soundfile")`, and numpy lives in
requirements-voice.txt — never in backend/requirements.txt, which is the only
thing .github/workflows installs. Simulated a clean runner by blocking numpy
through a meta_path hook: collection dies again, whole suite aborts, zero tests
run. Confirmed independently with `pip install --dry-run --report` that
backend/requirements.txt resolves no numpy. `np = pytest.importorskip("numpy")`
fixes it; I verified that shape skips cleanly without numpy and still runs with
it. Four non-blocking concerns recorded in the verdict, the one worth the
owner's eye being that KUBERA_TTS=openai narrates his positions and dollar P&L
to a vendor that may not be his configured brain — kokoro is the offline rung,
and the docstring should say so.
Per REVIEW.md I did not touch their source: reviewers report, builders repair.
Verified: gate PASS with soundfile present (their 8 + 652 + lint). The same
tree on a numpy-less runner: 1 collection error, 0 tests.
Next: Gemini applies the one-line fix and re-submits T072; I take my next
ticket only after that hand-back is clear.

## 2026-08-16 — T072 human-grade TTS backends (Gemini) — PARALLEL RUN
Built alongside Claude's T091b holding periods. AWAITING REVIEW; Claude signs off.
WHAT SHIPPED:
- `scripts/talk.py` `make_speaker()` expanded with `openai` and `kokoro` TTS backends:
  - `openai`: Uses `openai.audio.speech.create` with `response_format=wav`, model configurable via
    `KUBERA_OPENAI_TTS_MODEL` (default `tts-1`, or `tts-1-hd`), voice via `KUBERA_VOICE` (default `alloy`).
    Clear fail-fast message if `OPENAI_API_KEY` is missing.
  - `kokoro`: Local neural TTS via `kokoro-onnx` using weights in `models/kokoro/` or `KUBERA_KOKORO_DIR`.
    Fail-fast with exact release download link if model weights are missing. Default voice `af_heart`.
  - Both backends swallow runtime playback errors gracefully so the conversation loop survives audio glitches.
- Documented full voice ladder (`sapi` < `edge` < `openai` / `kokoro`) in `talk.py` docstrings,
  `requirements-voice.txt`, and `README.md`.
- `backend/tests/test_tts_backends.py`: 9 mock-based tests for all factory paths, parameter handling,
  error paths, and playback failure resiliency. Made CI-safe with `pytest.importorskip("soundfile")` (I016 resolved).
- REVIEWED Claude's T091b holding-period half: PASS (clean FIFO lot clock math, boundary edge cases verified).
Verified: verify.py PASS — 663 passed, 1 warning (663 passed on combined tree).
Next: Claude reviews T072; take next unblocked ticket.

## 2026-08-16 — T091b holding periods (Claude) — FIRST LIVE PARALLEL RUN
Built alongside Gemini's T072 (TTS backends) with both agents in the repo at
once — the first real test of D023. AWAITING REVIEW; Gemini signs off, not me.
WHAT SHIPPED: FIFO lots now carry their entry timestamp, so every round trip
knows how long it was actually held. `holding_period_distribution` reports
count / win rate / realized P&L per bucket (intraday, 1-3d, 1-2wk, 2wk-1mo,
over_1mo) plus median, mean, shortest and longest. It rides the EXISTING
get_attribution payload — deliberately no new tool, so the three tool-count
guard tests stayed untouched while another agent was live. Hand-tested edges:
buckets are half-open so exactly 1.0 day is "1-3d" and 4.0 is "1-2wk"; a
partial sell that consumes two entry lots produces two records, each with its
own clock, because each slice really was held that long; undated lots land in
"unknown" rather than being dropped; exit-before-entry and unparseable
timestamps return None instead of a negative duration. The point of the
feature: an owner who says "I'm a swing trader" but whose median hold is four
hours is describing an intention, not a practice — and the tool description
now tells the model to say so plainly.
PROTOCOL OBSERVATIONS (the actual experiment):
· parallel_check.py reported Gemini's claim and flagged TASKS.md as dirty —
  i.e. Gemini had written its claim but not yet committed it.
· A genuine race happened: Gemini committed its claim (71e4adf) BETWEEN my
  guard run and my own commit (330a4d8). Nothing was lost, because the edit
  was anchored to their exact line rather than a whole-file rewrite. That is
  precisely the failure D023 was written to prevent, and it held.
· Gap found in the protocol: when a shared coordination file already holds the
  other agent's UNCOMMITTED claim, staging that file necessarily carries their
  line too. Benign here (it makes their claim durable) but it must be declared
  in the commit message — I did. Worth folding into AGENTS.md properly.
· The verify gate was run on the COMBINED tree: 652 passed, 3 skipped.
· THE PROTOCOL EARNED ITS KEEP TWICE MORE, after the commit:
  (a) `git add <my five paths>` produced EIGHT staged files — Gemini had already
      staged its in-flight T072 work, so the INDEX is shared too, not just the
      directory. A plain `git commit` would have shipped their half-finished
      feature under my message. Fixed by committing with a PATHSPEC
      (`git commit -m ... -- <paths>`), verified with `git show --stat HEAD`:
      exactly my 5 files landed, their 3 stayed theirs. Rule upgraded in
      AGENTS.md, the brief, and D023.
  (b) The verify gate then went RED on the combined tree — not from my code:
      Gemini's in-flight test does a bare `import soundfile`, which fails
      COLLECTION and aborts the whole suite (zero tests run). Committed tree
      with that one file ignored: 652 passed. Logged as I016 pre-review
      feedback; I did NOT edit their file, because it is under an active claim.
      It also contradicts T070's decision that audio deps stay out of CI via
      requirements-voice.txt — exactly the kind of thing cross-review exists for.
Verified: 652 passed, 3 skipped on the committed tree (Gemini's uncommitted
in-flight test file excluded; full-suite green returns when they fix I016).
Next: Gemini reviews T091b before claiming its next ticket; I review T072.

## 2026-08-16 — D023: the shared-file problem, and a guard script for it
Owner asked the sharpest version of the question: what happens when both agents
MUST edit the same files — TASKS.md, PROGRESS.md, README? "Pick different
files" is impossible advice for those; every ticket touches them.
The honest mechanism, now written down: with one branch in one directory you
will NEVER get a git merge conflict — sequential commits have nothing to merge.
That is the trap, not the comfort. The real failure is a SILENT LOST UPDATE:
read the file, other agent saves, you write back stale, their lines vanish with
no warning anywhere.
Four rules in AGENTS.md: run the new guard first; edit by ANCHOR (a targeted
find-and-replace FAILS loudly if the region moved — a whole-file write succeeds
silently and eats their work); re-read immediately before writing; write only
your own block and commit it at once. Plus per-file conventions (own your
ticket block in TASKS, one dated entry at the top of PROGRESS, only your
section of README, only your numbers in the guard tests) and a recovery recipe
(`git show <sha>:path` and re-add — never revert).
NEW: `scripts/parallel_check.py` — active claims, which shared files are dirty
right now, the clobber signature (deletions in append-only memory files across
recent commits), and whether alembic branched. 7 tests on the pure parts.
It immediately flagged a REAL case on first run: my own D023 rewrite an hour
earlier removed 20 lines from DECISIONS.md. Intentional, but exactly the shape
of an accident — which is the point: you are forced to notice and judge.
Verified: verify.py PASS — 631 passed (+7), 3 skipped.
Next: run it live — two agents, two tickets, guard script before shared edits.

## 2026-08-16 — D023 amended: who commits (builder), and no branches
Owner asked a sharp question: should the REVIEWER commit, so commits aren't
mishandled? Answer is no, and the reasoning is now in D023 because the instinct
is reasonable and will come back. Committing is not the risk — it is the
PROTECTION. Work sitting uncommitted in a folder that another agent is actively
editing is the most fragile state available; the commit is the fence. Having the
reviewer commit would also force them to guess which paths belong to whom (the
`git add -A` hazard, made mandatory) and would put the wrong name in git log,
which is the project's memory of who built what.
So: builder commits code immediately; reviewer commits a separate
`review <TICKET>: PASS|BLOCK` touching only TASKS.md. A review commit that edits
source is not a review — it is a new ticket needing its own review. Reviewers
may fix trivial mechanical things as their own named mini-ticket, reviewed back.
Second rule added while here: NO BRANCHES during parallel work. Branching looks
like the obvious fix and is actively dangerous with one shared directory —
`git checkout` swaps files under the other agent mid-edit. One branch, small
frequent commits, staged by path. Branches return when each agent has its own
clone (worth doing once T005's push lands).
Verified: verify.py PASS — 624 passed, 3 skipped (docs only).
Next: run it live — two agents, two tickets, two commits each.

## 2026-08-16 — D023 CORRECTED: concurrent tickets, reciprocal review
Owner clarified the shape I got wrong an hour earlier: he does NOT want one
builder and one dedicated reviewer. He wants both agents BUILDING DIFFERENT
tickets at the same time (say Claude takes T072 while Gemini takes T091b) and
then reviewing each other's finished work. My clarifying question offered the
wrong menu and steered him; the protocol is rewritten to his actual intent and
D023 records the correction so no agent re-derives the wrong shape later.
The rewrite adds the hazard the first version missed entirely: both agents edit
ONE working directory. Git branches protect nothing there — and `git add -A`
by either agent commits the OTHER's half-written files under the wrong message.
New hard rule in AGENTS.md: stage by path, `git status` first, never -A while
another agent is live, wait on index.lock rather than deleting it. REVIEW.md
gains a parallel-conflict section: `git show --stat` for foreign files, single
alembic head, tool-count guards correct AFTER both commits, and the verify gate
run on the COMBINED tree — because each half can pass alone and fail together.
Sequencing rule that keeps this from silting up: REVIEW FIRST, BUILD SECOND —
clearing the other agent's awaiting-review ticket is the price of admission to
your own next one. docs/agent-briefs.md is now ONE brief (every agent is both
builder and reviewer) plus a table of ticket pairs that are safe to run
concurrently and the three that are never safe (both adding registry tools,
both adding migrations, both editing orb.html).
Verified: verify.py PASS — 624 passed, 3 skipped (docs/protocol only).
Next: run it live — two agents, two tickets, mutual sign-off.

## 2026-08-16 — D023: two agents, one truth — the parallel protocol
Owner asked whether agents can run in parallel and how to keep them honest to
HIS goals. It had already happened once safely (Gemini shipped the T082 Orb
frontend while Claude built T082a's backend) — but that was disjoint files and
luck, so the rules are now written down instead of hoped for.
Owner chose: builder + reviewer (not two builders), and a BLOCKING gate —
nothing is DONE until a DIFFERENT agent signs off. His reasoning, recorded in
D023: at this stage drift costs more than throughput.
Shipped: AGENTS.md "Parallel work" section (claim your role in TASKS.md first;
builders mark AWAITING REVIEW, never DONE; self-review is not review) with the
collision surface named explicitly — the three tool-count guard tests,
append-only-your-own-lines in PROGRESS/TASKS, the SINGLE alembic head (rebase,
never merge), and orb.html as one-agent-at-a-time. New
project-memory/REVIEW.md: a checklist ordered intent-BEFORE-diff and led by
owner-alignment questions ("does this serve a goal HE stated?", "does it make
breaking his own risk rules easier?", "does it relitigate a settled D017/D019/
D021 rejection?") ahead of any code-quality question, plus a required verdict
block and a worked example of a good BLOCK vs a useless one. New
docs/agent-briefs.md: copy-paste BUILDER and REVIEWER prompts, ending with the
owner's context — 26, $1k against $60–70k debt, asked to be CHALLENGED — so a
reviewer protects the features that tell him what he'd rather not hear.
Verified: verify.py PASS — 624 passed, 3 skipped (docs/protocol only).
Next: run it — builder takes T072 (human-grade TTS), reviewer signs off.

## 2026-08-16 — T089: what a position has already put you through
Live MAE/MFE on OPEN positions — the backtest version only ever measured
closed trades on closes. analysis/excursions_live.py reads daily highs and
lows since entry and reports: the worst it went against you, the best it ever
showed you, and GIVE-BACK — the share of a run-up already surrendered, which
is the arithmetic behind "it was up 8% and I watched it round-trip". Heat-used
compares MAE to the pain a 2xATR stop allows, so "you've taken nearly all the
damage this trade is permitted" stops being a feeling. Hand-tested on entry
100 / low 94 / high 112 / close 103 → −6%, +12%, 75% given back; corrupt bars
(high below low) and a stop above entry are refused rather than computed.
Tool #33 + GET /api/excursions, with the limits in every payload: daily H/L
misses intraday spikes, and the basis is the broker's AVERAGE entry.
Fixture lesson worth keeping: my first "biggest give-back" case was wrong —
a symbol with a 1% pop fully surrendered scores 100%, beating a 12% run-up
that gave back 75%. The code was right; the test was sloppy. Fixed the test.
Verified: verify.py PASS — 624 passed (+9), 3 skipped.
Next: T072 human-grade TTS, T091b holding-period distribution, or T023 (owner).

## 2026-08-16 — T082: the Orb can see its history and its book (frontend half)
Three additive panels shipped into apps/web/orb.html — voice loop, canvas,
and send() are untouched, byte-for-byte identical to the T082a baseline.

(a) CONVERSATIONS SIDEBAR (`☰`, left, collapsed-by-default): fetches
GET /api/conversations?limit=50 on page load and after every send(); lists
threads newest-activity-first with the opening snippet + "N turns · M calls"
metadata (same counts the backend computes); click any row sets
S.conversationId and highlights it with a gold left border so the next message
resumes that thread; "+ new" clears the id cleanly. flashHint() surface a
transient hint-bar message on resume so it's clear what happened.

(b) PORTFOLIO SNAPSHOT PANEL (`▣`, right, collapsed-by-default): fetches
GET /portfolio on open and polls every 60 s while visible; shows equity,
day P&L colour-coded green/red (equity - last_equity from Alpaca), and top-3
positions by |market_value|. Degrades to "broker offline" on 502/503 — the
panel stays present so you always know the toggle is there.

(c) FRESHNESS CHIP COLOURS: get_latest, get_symbol_briefing, and get_intraday
chips get a colour-coded border via a time-of-day heuristic (RTH 09:30–16:00
ET → teal "live"; outside → gold "last_session"). The chip class is applied
in addTurn() before the DOM is touched — no parsing of reply text. CSS adds
chip-live / chip-last / chip-stale / chip-old variants; only live and
last_session are used by the heuristic today; stale/old are ready for when
the backend forwards the true verdict.

Layout: three-column flex shell (#shell), panels are width:0 / width:240px
(sidebar) or 220px (portfolio) toggled via CSS transition. No CDN dependency.
All 25 new IDs unique, all original IDs preserved, all JS functions present —
verified by a structural assertion script (check_orb.py in scratch/).
Verify: frontend-only; pytest gate requires owner's venv (.venv\Scripts\pytest).
Next: T089 live MAE/MFE, T072 human-grade TTS, or T076b FOMC/earnings.

## 2026-08-14 — T082a: KUBERA can finally list its own conversations

Split the Orb pack: the sidebar's BACKEND is backend work and shipped here;
the UI half stays a Gemini/Antigravity ticket. /api/chat/{id} could replay a
thread but nothing could enumerate them. data/conversations.py fixes that with
two deliberate choices: order by LAST ACTIVITY rather than creation (revive a
month-old thread and it belongs at the top — tested), and take the snippet
from the owner's FIRST USER message, never a system prompt or tool payload,
whitespace collapsed, 90 chars with an ellipsis — the line he'd actually
recognize. Turn count and tool-call count are reported separately, so a thread
advertises how much evidence it pulled. Conversations with no messages are
skipped rather than shown as ghosts. GET /api/conversations?limit= (1..200).
Verified: verify.py PASS — 615 passed (+7), 3 skipped.
Next: T089 live MAE/MFE, T072 human-grade TTS, or the T082 frontend half.

## 2026-08-14 — T097 REVERTED: back to the Orb (owner call)
Six iterations of a particle face — voxel grid, sculpted 3D, holographic
columns, microscopic rods, skull anatomy, green dots — never produced a
convincing likeness. Owner called it: "revert back to the orb". Done cleanly:
apps/web/orb.html restored from 5f77557, which is the Orb WITH the patience
fixes (2.8s silence window, continuous listening) and without the three.js CDN
dependency the face introduced. Voice loop, click-to-talk, state colours, TTS
amplitude all verified present; 250 lines removed.
LESSON (recorded in TASKS so no agent re-attempts it blind): procedural facial
likeness fits this repo badly — every pass needed a human eye to judge, which
is exactly what the verify gate cannot automate, so the loop degenerated into
guess-render-ask. If a face is wanted later, bring an ASSET (head mesh or
point-cloud scan) and animate it; don't sculpt one from gaussians. All
face-era code survives in git history (8fc9927..82b3a85) if anyone wants it.
Verified: verify.py PASS — 608 passed, 3 skipped.
Next: back to the backlog — T089 live MAE/MFE, T072 human-grade TTS, T082 Orb
upgrade pack (conversations sidebar, portfolio panel, feed badges).

## 2026-08-14 — T097 v6: the green face — glowing dots on blue-green
Owner supplied a new visual description: a headshot of glowing GREEN dots,
dramatic light, deep blue-green gradient background, visible ears, slight left
angle. Refactor (three offline tuning passes — first attempt floated the ears
as detached blobs, second overexposed into a solid mass, third collapsed
density; the fourth balanced contrast gamma 1.35 with density 0.34+0.66v):
elements are now ROUND soft-edged points (gl_PointCoord radial falloff, not
rod masks); ears are a surface EXTENSION that widens the silhouette and lifts
depth so they stay attached; key light from the upper left with density
thinning in shadow so dots separate visibly; background is a CSS blue-green
gradient with the whole UI chrome re-palette (teal/gold → green). The neural
cascade is REMOVED — the new spec is a headshot, not a dissolve.
JUDGMENT CALL recorded: state used to signal by colour (teal/violet/gold),
which a green-only palette would erase — so state now shifts hue and
brightness WITHIN the green family (idle 36,209,126 → listening 64,240,200 →
thinking 120,235,130 → speaking 150,255,170). Function preserved, identity
honored. Cursor-follow, lip amp, shimmer, CDN fallback intact.
Verified: node --check + guards (no cascade, round dots, ears) + verify.py
PASS — 608 passed, 3 skipped (frontend-only).
Owner: hard-refresh localhost:8000.

## 2026-08-14 — T088: "never buy the open print" gets a scoreboard
The doctrine has been a belief; this makes it falsifiable with the owner's own
money. Every ordered signal now stores the price the DECISION was made on
(new decision_price column, filled by the loop); analysis/execution.py
measures the gap to the actual fill as implementation shortfall in bps, with
a side-aware sign convention pinned by four hand tests: positive ALWAYS means
the execution cost you, whether buying or selling. Grouped by time-of-day
bucket (T091's entry buckets) and side, with thin buckets explicitly labeled
"anecdotes, not evidence" below 5 fills — a rule that matters more here than
anywhere, because the temptation is to conclude "mornings are expensive" from
two trades. Tool #32 joins signal_log.order_external_id ↔ transactions.order_id,
counts orders whose fills haven't synced yet, and treats an empty history as a
calm answer rather than an error.
Verified: verify.py PASS — 608 passed (+12), 3 skipped.
Next: T089 live MAE/MFE (same fills dependency), T072 human-grade TTS, or
T082 Orb pack. Owner unlocks still the real bottleneck.

## 2026-08-14 — T060: the deposit that must not look like skill
Built ahead of the trigger (D018 said this jumps the queue on the first
deposit — better to have it correct BEFORE money moves than to discover the
lie afterward). analysis/twr.py chain-links sub-periods across external
flows; the headline hand test says it all: deposit $500 into a $1,000 account
that grew to $1,100 and ends at $1,760 — the simple return prints +76% (of
which $500 was a transfer), TWR reports +21%, which is what the strategy
actually did. The lie flatters the owner, which is the worst direction, so
compare_benchmark now carries a time_weighted block with excess computed
against TWR and an instruction to quote it once flows exist. Plumbing:
cash_flows table + CSD/CSW activities (signs normalized: withdrawals always
negative) + deduped sync wired into scripts/sync.py, never fatal. The
tz-aware type guard earned its keep — Alpaca's date-only fields parse naive
and were caught at the DB boundary, fixed in the client.
Verified: verify.py PASS — 596 passed (+9), 3 skipped.
Next: T088 execution quality / T089 live MAE/MFE (both want accumulated
fills — daily scripts/sync.py), or T072 human-grade TTS.

## 2026-08-14 — T096: the right-sized toolbox — 31 tools is a menu, not a gift
I008's two routing failures came from a small local model drowning in the
registry; since then the registry grew from 24 to 31, so the problem got
worse, not better. api/tool_policy.py now curates: local/compat endpoints
(openai wire format against a non-openai base_url) get an 11-tool CORE set
covering the whole daily conversation; claude-sdk/anthropic/real-openai get
everything. Crucially the PERSONA's advertised tool list is now built from the
same filtered set — advertising tools a model can't call is exactly how
"I don't have that capability" and invented tool names happen (I008/I011).
claude-sdk honors a forced profile too (bridge wraps all, permission narrows).
KUBERA_TOOL_PROFILE=auto|full|core; unknown values degrade to auto instead of
killing a session. The guard test asserts CORE ⊆ registry, so a future rename
can't silently amputate a small brain's capability.
Verified: verify.py PASS — 587 passed (+11), 3 skipped.
Next: T088/T089 (need fills — run scripts/sync.py daily), T072 human TTS, or
owner unlocks (IPS resend, brain_check, T005 push, T023 FMP tier).

## 2026-08-14 — T036b: "stale" is the wrong word for Friday's close on a Saturday
The binary stale flag told a half-truth in both directions: it cried stale on
every weekend quote (correct data, wrong word) and said nothing special when a
feed lags DURING a session (the actually dangerous case). analysis/staleness.py
replaces it with four states — live / stale (open + behind = untrustworthy) /
last_session (closed + recent = trustworthy, "the most recent real print") /
old (beyond a normal closure) — each carrying a narration-ready phrase, all
hand-tested including the 96-hour boundary. get_latest now asks the BROKER
clock rather than guessing (I007's lesson: models garble raw ages, so the
phrase does the talking); without an Alpaca client it falls back to the
conservative rule and SAYS "market state unknown". Closed markets also get
"the market opens in 14h 20m". /api/market/.../latest now routes through the
tool so the endpoint and the chat layer can't drift apart.
Verified: verify.py PASS — 576 passed (+10), 3 skipped.
Next: T088 execution quality or T089 live MAE/MFE (both need accumulated
fills — run scripts/sync.py daily), else owner unlocks.

## 2026-08-14 — T064b: badges expire — and backtests confess their trades
Promotion is evidence, not tenure: is_promoted now takes max_age_days (default
180) — a walk-forward pass older than that silently stops counting and the
paper loop's existing gate refuses new buys until the pair is re-promoted
(proven by backdating a passed row in test). run_backtest's tool output grew
up: per-trade TradeStats (n/win-rate/profit-factor/best/worst), Calmar, and a
promotion block showing is_promoted + the latest T092 stability verdict
(new ledger.latest_stability) + a note pointing at promote.py/sweep.py and the
expiry. The chat model can now see AND SAY "this backtest looks great but the
pair is unpromoted and the sweep called it curve_fit". Parked deliberately:
promote-via-chat (wants the same deliberate-act confirmation design as
update_ips), crisis-window stress runs.
Verified: verify.py PASS — 566 passed (+3), 3 skipped.
Next: T036b session-aware staleness, or owner unlocks (IPS resend, brain_check,
T005 push, T023 FMP tier).

## 2026-08-14 — T062b (partial): the morning brief becomes the composite
Same-day integration of the day's shipments: the morning brief now carries a
`watchlist` section (top-3 ranked setups from T068, the owner's thesis note on
each; an empty list says "watchlist is empty" instead of hiding) and an
`event_risk` section (upcoming CPI/NFP dates from T076's calendar; a missing
FRED key or a calendar failure degrades to a note — the rest of the brief
still delivers). fred became an OPTIONAL member of the brief path: ctx.fred in
get_brief, best-effort FredClient in /api/brief (ConfigError → None), and the
composer takes fred=None gracefully. One endpoint syntax slip (finally before
except) caught by the gate and fixed; one tz fencepost in tests (local date vs
the composer's UTC date) fixed in the fixture. PENDING_NOTES now names only
the earnings-dates gap. "Give me my morning brief" is the J.A.R.V.I.S. moment.
Verified: verify.py PASS — 563 passed (+1 net), 3 skipped.
Next: T064b rigor follow-ups, or owner unlocks (T023 FMP tier, T005 push).

## 2026-08-14 — T076: don't open new risk into a known storm
The event-risk guard, CPI/NFP half. FRED's release-dates API (with
include_release_dates_with_no_data, which returns SCHEDULED future dates)
feeds pure calendar math in analysis/events.py; the paper loop now pauses NEW
entries within a configurable window before/on CPI and Employment Situation
releases — a first-class T055 no-trade reason, buys only, sells structurally
untouched (the whole block lives in the buy branch). paper_trade.py arms the
guard automatically when FRED_API_KEY is present and says so at startup;
get_macro_context surfaces the upcoming calendar with dates (degrades to a
note if the calendar endpoint fails — core macro reads still deliver). Both
loop paths tested end-to-end: release-today → no_trade with the reason;
clear calendar → order placed. FOMC dates are NOT in FRED — that source
decision + earnings dates + the sell-the-news flag are minted as T076b.
Verified: verify.py PASS — 562 passed (+6), 3 skipped.
Next: T060 TWR (jumps the queue on first deposit) or owner's T023 FMP answer.

## 2026-08-14 — T068: the watchlist ranks itself — a pipeline, not a pile
Research candidates now arrive RANKED. watchlist table + CRUD (idempotent
add carries the owner's thesis note); analysis/ranking.py scores the list
cross-sectionally per D020: relative-strength percentiles at 21/63/126 bars
(percentiles so a hot tape can't make everything a buy; tie-aware, hand-
tested), T050 regime label mapped to a documented long-side fit heuristic,
5-session payoff context, composite 0.5/0.3/0.2 with decile flags. Symbols
with thin history are listed-not-scored. Tools update_watchlist +
get_watchlist (#30/#31; empty list returns an offer, not an error) and
GET/POST/DELETE /api/watchlist. One fix en route: classify_regime's reading
exposes .regime, not .label. Say "watch NVDA — breakout setup" then "what
looks best on my list?" — that's the flow this ships.
Verified: verify.py PASS — 556 passed (+9), 3 skipped.
Next: T076 event-risk guard (FRED calendar) or T023 key-tier check (owner).

## 2026-08-14 — T093b: reconciliation — the DB and the broker must agree
Small ticket, closed same day it was minted. health_check now compares the
latest account_snapshot equity against the live broker (/api/account) and
warns above 0.5% drift — with the snapshot age and the remedy in the message
(stale-after-market-moves is normal, run sync.py; drift surviving a fresh sync
is an incident). Deliberately owns ONE failure mode: both sides reachable but
disagreeing — server-down and never-synced stay with their existing checks, so
no double-reporting. Rides the owner's every-5-min scheduled health check and
Windows toast unchanged. T093 is now fully closed (parts 1+2+3).
Verified: verify.py PASS — 547 passed (+3), 3 skipped.
Next: T068 watchlist + opportunity ranking (criteria defined in D020), or
T060 TWR the day the owner makes his first deposit.

## 2026-08-14 — T093: the book as one number — and promotions that expire
Two halves of the same discipline. MEASURE: analysis/portfolio_risk.py —
portfolio vol √(w'Cw) (hand-tested at correlation extremes: ρ=1 → 0.2, ρ=0 →
0.1414, ρ=−1 → 0), Euler risk contributions that sum EXACTLY to portfolio vol
("62% of your risk is SPY" is arithmetic), effective bets, diversification
ratio, one-bet warning at ≥60% concentration — tool #29 get_portfolio_risk +
/api/portfolio-risk. ENFORCE: backtest/decay.py — the promoted run's implicit
daily promise vs live returns through a one-sided CUSUM (crossing-day test
taught an fp lesson: a threshold exactly ON an accumulation boundary is
untestable — 20×0.0005 = 0.010000000000000002); on sustained shortfall,
demote() flips the ledger row and the EXISTING promotion gate refuses new buys
— no new code path. scripts/decay_check.py prints the account-proxy caveat
every run. T093b minted for the reconciliation half (small, unblocked).
Verified: verify.py PASS — 544 passed (+12), 3 skipped.
Next: T093b, or T068 watchlist ranking (criteria already defined in D020).

## 2026-08-14 — T090: liquidity costs — the spread is a fee and thin volume is a wall
analysis/liquidity.py: spread_bps (hand-tested 20bps case), per-side cost =
half-spread floored at 0.5bps (replaces the flat assumption when a quote
exists), trailing-20-session ADV, and the 1%-participation cap — labeled
honestly everywhere: IEX sample volume UNDERSTATES the consolidated tape, so
the cap binds early, which is the safe direction. The cap now BINDS in
size_position ("adv_cap" joins blocked/position_cap/risk_budget; THIN-symbol
test proves 5 shares max on 500 ADV) — required making the shared BARS_JSON
fixture's volume realistic (uniform 4M: RVOL ratios unchanged, legacy sizing
expectations unchanged; fix-the-fixture lesson applied deliberately this
time). Tool #28 get_liquidity refuses one-sided quotes ("spread math would be
fiction") + /api/liquidity/{symbol}.
Verified: verify.py PASS — 532 passed (+10), 3 skipped.
Next: T093 portfolio risk summary (T079 correlations now exist to build on).

## 2026-08-14 — T092: the curve-fit detector — one magic number is not an edge
backtest/stability.py: sweep a template across its parameter neighborhood and
demand a PLATEAU. Pure verdict logic hand-tested (plateau→stable, isolated
spike→curve_fit, all-negative→reject, <3 points→insufficient, exact-boundary
half-support case pinned); metric is annualized Sharpe of the equity curve so
leverage can't fake breadth; never-invested params score 0 with a warning
instead of crashing on the undefined-Sharpe constant curve. run_sweep is
engine-only (no ledger spam); the evidence lands beside promotions via
ledger.attach_stability → new stability_json column (migration 8d2d7f6c98b8,
sed ritual applied). CLI: python scripts\sweep.py momentum SPY --record.
Verified: verify.py PASS — 522 passed (+11), 3 skipped.
Next: T090 liquidity-aware costs (unblocked; quotes already fetched), or T093
portfolio risk summary now that T079 correlations exist.

## 2026-08-14 — T079: the overlap guard — "that's not diversification, that's the same bet"
Built the deterministic engine behind the pre-trade concentration warning:
analysis/correlation.py — pairwise Pearson correlation of daily log returns
(shared trailing windows; <20 observations = refused with a warning, never
guessed), per-symbol OLS beta vs SPY, portfolio beta from position weights
(coverage-warned when history gaps), 0.80+ pairs flagged, and the candidate
check that says "QQQ correlates 0.97 with your SPY — added exposure, not
diversification". Tool #27 get_correlation (description orders the model to
run it before any buy recommendation) + GET /api/correlation. All statistics
hand-computed in tests (y=2x → 1.0, constructed zero-covariance vectors → 0.0,
doubled returns → beta 2.0). T093's portfolio-risk summary builds on this.
Verified: verify.py PASS — 511 passed (+14), 3 skipped.
Next: T092 parameter stability sweeps or T090 liquidity costs (both unblocked).

## 2026-08-14 — T097 v5: anatomy pass — the skull under the hologram
Owner approved the rod technique, rejected the anatomy (11-point critique).
Kept: rods, palette, density system, behaviors. Changed: silhouette is now an
elongated tapered skull with per-side sinusoidal wobble (organic, slightly
asymmetric — no more sphere); pupils/eyeballs DELETED per spec — eyes are now
irregular horizontally-elongated feathered cavities (angular rim modulation,
different size per side, darker toward center, particles veiling them);
structural nose (stronger bridge ramp, projection, nostril dark mass); mouth
de-lined into a broad shallow cavity partially lost in the field; NEW dark
dense chin mass (density floor raised while brightness drops — the
"computational shadow beard") with fragmentation moved BELOW it; cascade
narrowed to a top-biased central column with escaping floaters — reads as the
face dissolving, not a torso. Composition ~60/15/25 face/transition/network.
Offline preview validated the anatomy before the port; cursor-follow (head
only now), lip amp, shimmer, scan, glitch, CDN fallback all intact.
node --check + no-uGaze guard + verify PASS 497/3.
Owner: hard-refresh localhost:8000.

## 2026-08-14 — T097 v4: the strict spec — microscopic rods, density features, continuous dissolve
Owner delivered a full visual spec (three references, STRICT): elements must be
tiny vertical luminous rods (NOT squares/voxels/mesh), features must emerge from
particle DENSITY + brightness + feathered dark recesses, mouth stays whole, jaw
fragments continuously into a chaotic neural cascade (no gap, floaters outside
the silhouette, progressive transparency), frontal, restrained glow. Built:
~40k sprites masked to thin rods in the fragment shader (gl_PointCoord band +
seed-varied height), density dropout tracking shade, elliptical feathered eye
recesses (offline preview caught the cartoon-disk eyes + premature mouth
fragmentation — both fixed in port), frag band below the lower lip with
animated drift, 565-node top-biased cascade with per-vertex fade colors (fake
progressive transparency under additive). All behaviors kept: cursor-follow,
pupil lead, lip amp, shimmer, scan, glitch, CDN fallback. node --check OK,
verify PASS 497/3. Owner: hard-refresh localhost:8000.

## 2026-08-14 — T097 v3: holographic — voxel columns, hollow eyes, the cascade
Owner's second reference (frontal head of stacked voxel columns dissolving
downward into a wireframe cascade) + the word "holographic". Rebuilt the
renderer on the same sculpt: 3 stacked depth layers per sample (~23k points,
volumetric column look), per-column brightness striping, speckled ice/navy/mid
palette (offline-tuned preview matched the reference closely before porting),
dark eye hollows with glowing tracking pupils, scan-band sweeping down the
face, holo flicker + z-instability, rare row-glitch. The side halo became THE
CASCADE: 230-node undulating wireframe network hanging below the jaw (sways at
35% of head yaw). Rest pose now frontal per reference; cursor-follow, pupil
lead, lip amp, thinking shimmer all kept. node --check OK, verify PASS 497/3.
Owner: hard-refresh localhost:8000.

## 2026-08-14 — T097 v2: the face grew up — sculpted 3D head on WebGL
Owner: v1 too pixelated vs his reference. Rebuilt: continuous sculpted depth
field (skull dome + ~18 gaussian features: brow/sockets/eyeballs/nose/lips/
chin/cheekbones/temples), tuned across TWO offline render iterations (fixed
nose-ridge shading discontinuity, deepened sockets, added iris ring + bright
pupil) before porting constants to JS. Renderer: three.js r128 (CDN) Points —
~12k GPU particles, baked Lambertian shading + ambient lift, additive glow,
custom vertex shader does cursor-follow head rotation (rests in the reference's
3/4 pose when idle), pupil lead, lip-sync from uAmp, thinking shimmer, and
left-edge dissolve; drifting wireframe network in scene space. Fallback pulse
if CDN unreachable — voice loop untouched either way. node --check on the
inline script + verify gate PASS (497/3, frontend-only).
Owner: hard-refresh (Ctrl+Shift+R) localhost:8000 — first load fetches three.js.

## 2026-08-14 — T097: KUBERA got a face — and it watches the cursor
Owner sent a reference image (voxel head dissolving into a particle network) and
asked for a face that follows the mouse. Shipped inside orb.html with ZERO
changes to the voice loop: a procedurally generated depth-mapped voxel face
(two-ellipse silhouette, carved brow/sockets/pupils/nose/lips/chin — sanity-
rendered offline before shipping and it reads as a face). Head rotates toward
the cursor with smoothing, pupils track with extra gain, gaze wanders when the
mouse goes quiet, lips move with the real TTS amplitude, thinking shimmers, and
the left edge dissolves into a drifting wireframe network like the reference.
State colors unchanged (idle gold / listening teal / thinking violet / speaking
gold) so the face IS the orb. Frontend-only; verify gate untouched but run.
Owner: restart the server, open localhost:8000, move the mouse.

## 2026-08-14 — I015: the provider that wasn't — brain_check + startup announcement
Owner corrected the record: .env says claude-sdk (verified — masked read), yet
the timeout error came from the OpenAI provider aimed at local Ollama. Claude's
"you were on openai" judgment was wrong as stated; the honest mechanism is that
BOTH are true: real OS env vars silently beat .env (pydantic precedence, now
pinned by a test that reproduces the exact scenario), or a stale server kept its
boot-time provider. No silent fallback exists in the SDK provider — verified.
Shipped: scripts/brain_check.py (three questions: what .env SAYS, what a NEW
server would RESOLVE, what the RUNNING server USES — /health), and a lifespan
startup log that announces the brain and WARNS "PROVIDER MISMATCH" whenever
resolution differs from .env intent. Sandbox run: intent=resolution=claude-sdk,
so the divergence lives on the owner's machine (shell var or stale process).
Verified: verify.py PASS — 497 passed (+5), 3 skipped.
Owner: python scripts/brain_check.py → restart from a clean shell → startup
line must read "KUBERA brain: llm_provider=claude-sdk".

## 2026-08-14 — D022: the J.A.R.V.I.S. batch — receipts first, then two real adoptions
Owner asked for a ReAct loop, universal registry, and anti-chatbot persona.
Receipts written into D022: the loop (MAX_TOOL_ROUNDS=6, SDK max_turns=8) and
registry (26 tools) have existed since T042/T024; the persona is tested code.
The chatbot FEEL is the brain, not the architecture — openai/local providers
under-use tools (see I011/I014). Adopted the genuine gaps: get_news (tool #26,
Alpaca news feed, per-item ages, injection rule restated, + /api/news) and the
persona rule "AGENTIC DEFAULT — act first, speak once": composite questions get
a silent fan-out and one synthesized answer, never tool narration or "which
check?" asks. Guard tests bumped 25→26 in all three places. Web search NOT
adopted (D022 records why + revisit trigger).
Verified: verify.py PASS — 492 passed (+6), 3 skipped.
Owner: LLM_PROVIDER=claude-sdk is what makes the fan-out actually happen.

## 2026-08-14 — I013+I014: schemas are private + a timeout that keeps the thread
Owner transcript, two failures in one conversation. First: "update the IPS" was
answered with a table of our internal parameter names — a form, not a colleague.
Persona gained "SCHEMAS ARE PRIVATE" (the reply is 'what would you like to
change?'; briefs get extraction, not menus), update_ips's description now forbids
showing its field list, and chat.py gained ensure_no_schema_dump: 3+ internal
underscore-names in a reply (user didn't ask for fields / doesn't speak schema) →
⚠ Pacing footer. His exact menu reply is a named test. Second: the resent IPS
brief hit a ReadTimeout, raw error on screen — on provider=openai (likely local),
not claude-sdk. Timeout is now LLM_TIMEOUT_SECONDS (default 300s, was 120 fixed),
timeout errors name the knob, and run_chat_turn catches LLMError: user text was
committed pre-call, so the reply says "saved — say 'try again'" and the recovery
replay is tested end-to-end. Audited remaining tool descriptions: only update_ips
was menu-bait. Verified: verify.py PASS — 486 passed (+11), 3 skipped.
Owner: restart backend, resend the brief; if it times out again the message is
kept — say "try again", or raise LLM_TIMEOUT_SECONDS in .env.

## 2026-08-14 — I012: the IPS brief that didn't fit + goal_math (tool #25)
Owner poured his actual investment policy into the chat — 14 sections, $1k→$1M,
horizon math, contribution scenarios, "challenge my assumptions" — and got a 422.
Two caps conspired: ChatRequest max_length=6000 rejected it, and MAX_STORED_CHARS
=6000 would have truncated the stored copy the model replays even if the first cap
were raised alone. Fixed both: request 20k, storage 24k (storage > request, so user
text survives whole). Then made the message answerable: analysis/goal_math.py —
required_cagr (10y needs 99.5%/yr — hand-tested against 10^0.3), future_value with
monthly contributions, years_to_target (None = "not in 100 years", honest),
daily_return_reality (1.02^252 ≈ 147x/yr — the "2–5%/day" conversation-ender).
goal_math registered as tool #25 (+ GET /api/goal-math; all three guard tests
bumped 24→25); description orders the model to challenge unrealistic assumptions
with these numbers, note says contributions dominate at small sizes.
Verified: verify.py PASS — 475 passed (+13 hand-computed), 3 skipped.
Owner: restart backend, resend the IPS message unchanged — it fits now.

## 2026-08-14 — I011: bridge telemetry + fabrication guard — trust nothing that skipped the tools
Owner transcripts on claude-sdk: one turn denied get_portfolio and hallucinated
tool names (get_market_data/submit_verdict — prose distortions) while priming HAD
fired; a rephrase worked perfectly. Diagnosis: the SDK MCP bridge likely degrading
silently on some turns (version drift) — a model with real schemas doesn't misspell
them. Shipped: (1) bridge telemetry — "bridged N registry tools" logged per call,
WARNING on mismatch, /health reports llm_provider + tools_registered; (2) deflection
v3 — primed-only trails = "model called nothing" (the denial transcript is a named
test), "list the tickers" pattern, portfolio-ish ticker-asks flagged without a named
ticker; (3) FABRICATION GUARD — 3+ precise figures with zero tool history and none
in the primed snapshot -> "Unverified numbers" footer (numbers come from tools,
never memory). Owner verification: restart, watch for "bridged 24 registry tools";
mismatch -> pip install -U claude-agent-sdk.
Verified: verify.py PASS — 462 passed, 3 skipped.
Blockers: bridge verification pending on owner machine (steps in I011).

## 2026-08-14 — I010: portfolio auto-priming — from instructions to architecture
Fourth deflection transcript ("check my portfolio for SPY" -> "how many shares do
you hold?"). Verdict accepted: prompt rules don't stick on the local brain, so the
data now arrives regardless of model obedience. prime_portfolio in the chat layer:
portfolio intent detected -> get_portfolio executed SERVER-SIDE before the model
speaks -> compact snapshot (per-position qty/avg/mv/unrealized + equity/cash)
injected into the system prompt with "Answer from THIS data. Do NOT ask for share
counts..." Audited: trail gains {get_portfolio, auto_primed:true}, recency footer
sees the asof; silent no-op without intent or broker; a priming failure never kills
the turn. Deflection detector v2 also fires on asks-for-position-details. The
transcript is a named test; the chat E2E now asserts the primed fetch precedes the
model's own call.
Verified: verify.py PASS — 456 passed, 3 skipped.
I007–I010 arc closed for portfolio asks: structurally impossible to deflect now.
Owner: ask "check my portfolio" again — the numbers arrive before the model can ask.
Blockers: none.

## 2026-08-14 — I009: lenient tool args — sloppy "None"/""/"BUY" no longer kills journaling
Owner pasted server logs: record_decision failed twice — string "None" and "" for
absent optionals, SHOUTED "BUY" vs the lowercase pattern. Silver lining: the T063
persona rule WORKED (the model tried to journal). Fix: LenientArgs base (wildcard
before-validator: ""/"None"/"null"/"N/A" → real None) + verdict lowercasing; applied
to record_decision, mark_decision, triage_position, update_ips. BOTH failing payloads
from the logs are now verbatim passing tests; real validation (bad verdicts/numbers)
still rejects. I009 logged — third local-brain formatting strike; T096 + claude-sdk
recommendation stand.
Verified: verify.py PASS — 452 passed, 3 skipped.
Blockers: none.

## 2026-08-14 — Conversational pacing: the Orb learned patience, the persona learned turns
Owner feedback with transcript: (1) the Orb sent his speech the moment he paused;
(2) KUBERA interrogates with numbered 4-question forms + capability menus; (3) it
asked for his entry price when get_portfolio ALREADY carries avg_entry_price (third
capability-denial, same lesson).
Shipped: ORB — recognition rewritten with patience: continuous=true, mic stays open
across engine restarts (onend → restart while wantListening), every sound resets a
2.8s silence timer (SILENCE_SEND_MS), send fires only on real quiet OR click-the-orb
send-now; trailing interim text included so the last words never drop; status line
says "pauses are fine". Hold-Space release still = send immediately (full manual
control). PERSONA — PACING rule (guard-tested): ask for exactly ONE missing thing
and stop, never numbered question lists or capability menus, positions/entry
prices/balances are already in get_portfolio — look before asking; full analysis
only once inputs exist. VOICE_STYLE unchanged (already ~120 words).
Verified: verify.py PASS — 449 passed, 3 skipped (orb assertions extended).
Remaining truth: mid-KUBERA-speech interruption (barge-in) needs the realtime stack
— that's T074, unchanged. Owner: refresh the Orb page (Ctrl+F5) and talk with
pauses; click the orb when you're done — or just wait ~3 seconds.
Blockers: none.

## 2026-08-14 — I008: "which ticker?" deflection — second strike on the local brain
Owner's next transcript: "I hold SPY, should I keep holding?" → model asked for the
ticker, claimed no recent-performance function exists (get_symbol_briefing IS it),
confused get_brief with get_symbol_briefing, called ZERO tools. I007's symbol check
was correctly silent (nothing ran → nothing to compare). Shipped:
(1) ensure_no_deflection post-check — named ticker + empty tool trail + asks-for-
symbol phrasing → footer naming the tools that DO answer ("a model miss, not a
missing capability"); the transcript is a named test.
(2) Persona ROUTING map — question→tools ("should I hold X" → briefing + regime +
exit plan + triage), "never claim a capability is missing without checking the tool
list", "never ask for a symbol the user already named" (guard-tested).
(3) I008 logged; T096 filed: per-brain tool subsetting (24 tools overwhelm small
local models — curated core set for local brains).
PATTERN ON RECORD: two strikes, both model-level, tool layer blameless both times.
Standing recommendation: LLM_PROVIDER=claude-sdk for real decisions.
Verified: verify.py PASS — 449 passed, 3 skipped.
Owner: switch the brain, re-ask; the answer should route to briefing+regime+exit plan.
Blockers: none.

## 2026-08-14 — I007: the SPY→TSLA wrong-symbol reply — three defenses shipped
Owner pasted a real transcript: "should I buy and hold SPY?" answered with a TSLA
sizing table + directive tone + "price age ≈ 28 s marked stale" at 04:31 UTC (market
closed — the price was HOURS old; the stale flag was right, the narration wasn't).
Tool layer blameless; model-level misdirection. Shipped same-session:
(1) ensure_symbol_alignment in chat — deterministic post-check like the recency
footer: user-named tickers vs tool-call symbols; zero overlap → "⚠ Symbol check …
answer may be misdirected — re-ask" appended. The exact transcript is a named test
(test_the_spy_tsla_transcript_is_caught). Conservative: silent without named tickers
or with any overlap; stopword list keeps ETF/AI/CEO etc. from false-firing.
(2) age_human on trades/quotes + size_position ("7h 52m", never raw seconds) — stop
models garbling seconds arithmetic.
(3) Persona CORE_RULE "Answer the question that was asked" (opinion → analysis
structure; sizing only on how-many; wrong-symbol tools re-run, never presented) —
guard-tested. I007 logged with residual-risk note: prefer the claude-sdk brain for
real decisions; treat any Symbol-check footer as a hard stop.
Verified: verify.py PASS — 445 passed, 3 skipped.
Next: back to the queue (T090/T093) or Gemini takes T082. Owner: re-ask your SPY
question — and if you were on the local brain, switch LLM_PROVIDER=claude-sdk.
Blockers: none.

## 2026-08-14 — T091 done: attribution — every outcome credited to the conditions that opened it
signal_log now carries regime_label (the loop persists what the classifier saw — on
ordered, no_trade, AND rejected rows, so restraint is attributable too),
sub_strategy (the router names its leg via a last_leg attribute), and entry_bucket
(ET session fifths: pre/first_hour/midday/last_90/post — boundaries tested).
Transaction gains order_id — the join key from a broker fill back to the logged
decision that placed it (migrations f71b527814ef + 89e88db0d156). analysis/
attribution.py: FIFO round trips, each consumed slice's P&L credited to the ENTRY
lot's tags (hand-walked: one sell consuming two lots across two regimes), manual
trades land in "unattributed" (visible, never dropped), oversold surfaced, win rates
per tag, and the standing note: narrate COUNTS with every P&L figure. get_attribution
(registry 24, guards ×3) + GET /api/attribution with activity-by-regime counts.
Verified: verify.py PASS — 437 passed, 3 skipped (ruff sorted imports).
The D020 #2 question — "is the regime classifier adding value?" — now answers itself
as fills accumulate. Owner: trade the loop a while, then ask the Orb "what's my
attribution look like?".
Next: T090 liquidity costs or T093 portfolio risk+reconciliation; T082 Orb = Gemini.
Blockers: none.

## 2026-08-14 — T036 done: fills are ground truth now + the loop respects the clock
The biggest unlock ships. data: get_fills (activities API) + get_clock (the BROKER'S
clock — is_open/next_open, no local tz guessing); data/fills.py syncs fills into
transactions deduped per (account, external_id) — rerun-safe, proven by test.
Loop: enforce_market_hours — closed market → no_action with the honest reason ("an
order now would queue for the open print — the entry the doctrine forbids"), logged
with source=alpaca-clock; entry_delay_minutes joins the T055 no-trade reasons for
BUYS only (9:40 ET blocked at delay 30, 10:31 proceeds, 9:35 SELL passes — all
tested; ET math via the broker timestamp + zoneinfo). scripts/sync.py syncs fills
every run ("fills +N/M known"); paper_trade.py guards ON by default (--after-hours
escape, --entry-delay 30 default per doctrine). Owner-visible: the loop now refuses
to trade a closed market and won't buy the open print unless told to.
Verified: verify.py PASS — 429 passed, 3 skipped (ruff trimmed one unused import).
UNLOCKED: T088 slippage, T089 live MAE/MFE, T091 attribution, T060 TWR — the whole
measurement family now has its data source. Owner: run python scripts\sync.py to
start accumulating fills.
Blockers: none.

## 2026-08-13 — D021: the shorting question asked and ANSWERED — defer 30 days
Owner-uploaded PDF gap analysis (sixth batch, repo-aware). Its key catch: T081 pairs
is impossible long-only — and long-only is a deliberate rail, so the choice went to
the owner. DECIDED: defer ~30 days; long-only stands until paper DQS history proves
discipline; revisit on evidence ≈2026-09-12 (DQS trend, override rate, tier trips).
ADOPTED: strategy-decay DEMOTION into T093 (CUSUM drift vs backtest expectation →
promotion_status flips to "demoted" → the loop's gate refuses automatically — T064's
twin). NEW: T094 HRP (written scale trigger), T095 Fama-French loadings (free Ken
French data, dep 60+ snapshot returns). ENRICHED: T068 universe-screener. DEFERRED
with triggers: impact models/VWAP slicing (the ADV cap makes the problem impossible
at this scale). Convergence recorded: six reviews in, the backlog is decision- and
data-constrained — unlocks are T036 fills, T023 keys, T005 push, and now the clock
on the shorting revisit. Dispositions: docs/research/quant-gap-analysis-pdf-….md.
Verified: verify.py PASS — 422 passed, 3 skipped (memory session).
Next: T036 fills sync is now clearly the top build (unlocks T088/T089/T091).
Blockers: none.

## 2026-08-13 — D020: quant-gaps review — the measurement layer begins
Gemini's best review yet (repo-aware; its traps section independently re-derived our
D017/D019 rejections — three agents converged on the same discipline). BUILT the two
pure-math top picks same-session: trade_excursions (MAE/MFE per trade + WINNERS'
average MAE — the stop-calibration number; close-to-close labeled until T036 fills)
and Sortino + Omega in metrics (downside-only honesty; both refuse to fake a value
when there's no downside — error/None, never infinity). NEW T088–T093: execution
quality (slippage_bps, dep T036) · live MAE/MFE · liquidity-aware costs (live
spread_bps + conservative ADV cap) · ATTRIBUTION pack (persist regime/sub-strategy/
entry-bucket at order time — answers "is the classifier adding value") · parameter
stability sweeps (anti-curve-fit) · portfolio risk summary + daily reconciliation +
degradation detection. ENRICHED: T068 ranking criteria, T077b band calibration.
Theme on record: KUBERA can now DECIDE well; D020 is about MEASURING whether the
decisions work. T036 fills = the single biggest unlock left.
Verified: verify.py PASS — 422 passed, 3 skipped.
Next: T036 (fills sync — unlocks T088/T089/T091 attribution family) or T091 schema
prep; T082 Orb pack still prime Gemini bait.
Blockers: none.

## 2026-08-13 — T086 done: position triage — "should I average down?" answered honestly
analysis/triage.py judges an existing position against the LIVE exit plan (tool
composes regime + levels + ATR + active breakout, then compares entry vs latest trade):
EXIT when invalidation is closed through — with the sentence that matters: "adding here
is increasing exposure to a losing idea, not lowering an average" (asserted in tests);
EXIT_AT_TARGET when the range completes ("wanting more is a NEW thesis"); otherwise
HOLD with an honest add-assessment — range adds allowed ONLY in the lower quarter of
the invalidation→target span (buy support, never mid-range: "worst risk/reward"),
trend adds NEVER blessed on dips ("the market arguing with the thesis" — adds happen
on strength). Review-clock expiry flagged. Every reading carries unrealized P&L,
distance to invalidation/target, risk_remaining_atr, and the standing honesty note
pointing at size_position for combined-risk math. triage_position (registry 23,
guards ×3) + GET /api/triage/{symbol}?entry_price=&days_held=.
Verified: verify.py PASS — 418 passed, 3 skipped.
Owner Q&A scoreboard: #4 scale-out/average-down now SHIPPED (5 of 7 fully live).
Next: T087 trade monitor (needs T074/T082 rails) or T081 pairs; T082 Orb = Gemini bait.
Owner: ask the Orb "I'm in SPY from 640, should I add or get out?"
Blockers: none.

## 2026-08-13 — T085 done: "how many shares?" answered by voice
size_position tool (registry 22, guards ×3) + GET /api/size/{symbol}: exact new-buy qty
= min(risk_notional × tier_multiplier, cap_headroom) with tier 3+/breaker → 0 and a
blocked_reason; risk leg from the T078 sizer (equity × 1% / 2×ATR), cap headroom counts
the existing position, price = LATEST TRADE with age + stale flag disclosed (not
yesterday's close), stop_price returned so the narration can say "111 shares, stop
175, risking $1,000". `binding` names the limiter. Hand-proven: cap binds at 111.732 sh
(100k clean), tier-2 halving → 110.056, tier 3 pause, breaker block, headroom erosion
by held position, thin-history refusal.
Verified: verify.py PASS — 408 passed, 3 skipped.
Next: T086 position triage or T081 pairs; owner: ask the Orb "how many shares of SPY
could I buy right now?" — it'll answer with the stop and what limited it.
Blockers: none.

## 2026-08-13 — Owner capability Q&A → three tickets (T085–T087)
Owner asked seven "can KUBERA…" questions. Answers on record: options contract picks =
future phase (doctrine caveat only, no ad-hoc build); probability-of-profit sizing =
reframed to risk-based sizing (shipped) + historical win/payoff context (T077) — single-
trade probability claims stay rejected (D017), fractional-Kelly noted as advisory-only
future view; entry/exit = shipped (router/levels/breakouts/exit plans); scale-out vs
average-down = machinery exists via invalidation + DQS, dedicated advisor ticketed
T086; exact quantity = shipped in the loop, chat exposure ticketed T085 (quick win);
vol-dies-after-entry = observable on demand (T052), proactive monitoring ticketed T087
(deps T074/T082/T036); when NOT to trade = strongest muscle (T055/T067/T064/breaker,
all logged). No code this session — memory only.
Next: T085 is a 30-minute wiring win; T086 after; T081 pairs still queued.
Blockers: none.

## 2026-08-13 — T064 done: the promotion gate — strategies must EARN the paper loop
backtest/stats.py: per-trade stats from the 0/1-weight contract (hand case: +21%/−10%
→ PF 2.1, open-at-end flagged), Calmar (None when undefined), and the ANCHORED
walk-forward: one no-lookahead run, equity segmented, pass = overall > 0 AND ≥ half
the segments non-negative. Honesty in the docstring: parameterless templates can't
overfit, so this screens CONSISTENCY across periods — and flat curves fail (overall 0
is not > 0; no free promotions). Ledger: promotion_status (migration 04e68aa1c90a),
promote_template records verdict + segment returns into params_json, is_promoted is
per (template, symbol) — SPY evidence doesn't transfer to AAPL. Loop: require_promotion
refuses unpromoted BUYS as a logged no_trade (sells always exempt); scripts/promote.py
CLI; paper_trade.py now gates BY DEFAULT with --skip-promotion-gate as the deliberate
escape. Proven in tests: momentum FAILS promotion on chop history, the router PASSES.
Verified: verify.py PASS — 401 passed, 3 skipped.
Next: T081 pairs (must pass this gate to run — fitting), T082 Orb (Gemini), owner:
run `python scripts\promote.py regime_router SPY` before the next paper session.
Blockers: none.

## 2026-08-13 — T056 done: exit plans — THE REGIME PACK IS COMPLETE (T050–T056 + T075)
"How long do I hold?" is now data keyed to the thesis: analysis/exit_plan.py returns
invalidation level (the CLOSE that kills the thesis) with its reason, target (ranges
only — trends are RIDDEN, not targeted; the p95 band is a review point and the code
says so), review horizon in sessions (range 10 / trend 5 / breakout = T053's window /
downtrend 1), stop_distance_atr, reward_risk (guarded against stale levels), and
doctrine notes (mid-range = worst RR; downside break = exit information for a
long-only book; coil = expansion picks the plan). get_exit_plan composes regime +
levels + ATR + active breakout + expected-move p95 in one call (registry 21) +
GET /api/exit-plan/{symbol}.
Verified: verify.py PASS — 389 passed, 3 skipped.
THE OWNER'S DOCTRINE IS FULLY CODE: day-typing (T050), edges (T051), intraday
VWAP/RVOL (T052), volume-judged breakouts (T053), router (T054), no-trade (T055),
exits (T056), confluence (T075) — every claim tested, every number dated.
Next: T081 pairs / T064 rigor / T082 Orb (Gemini) / T023 key check (owner).
Blockers: none.

## 2026-08-13 — T075 done: timeframe confluence — the regime pack's capstone
analysis/confluence.py: assess_confluence takes plain values (decoupled from the
reading dataclasses — the TOOL extracts) and adjusts the DAILY confidence only, never
the regime call: intraday agreement +0.05 / conflict −0.10, VWAP side aligned +0.05 /
against −0.05, churn (≥4 crossings) −0.05; clamped [0.05, 0.90]; every reading states
the D006 absence of volume-delta confirmation. get_confluence (registry 20, guards ×3)
classifies 1Day + 1Hour with the SAME T050 classifier (ISO timestamps serve as dates)
and reads the 5Min session; each intraday view degrades independently with a `gaps`
why. GET /api/confluence/{symbol}. Full-agreement fixture proves adjusted > daily and
cap at 0.9; thin-intraday fixture proves neutral degradation.
Verified: verify.py PASS — 378 passed, 3 skipped.
Regime pack status: T050–T055 + T075 DONE; only T056 (structured exit plans) remains.
Next: T056 to finish the pack, or T081 pairs / T064 rigor / T082 Orb (Gemini). Owner:
/api/confluence/SPY or ask the Orb "do the timeframes agree on SPY?".
Blockers: none.

## 2026-08-13 — T063 done: the decision journal — "why did I buy that?" now has an answer
decision_journal table (migration 080e1c184167, UTCDateTime→sed as usual) captures every
recommendation AT decision time: verdict/confidence/thesis/horizon/entry/target/stop/
key-risk + regime context (D016), and the owner's FOLLOW or OVERRIDE with a note (D018 —
override-rate is the behavioral metric that will feed T067b). The model journals ITSELF:
persona CORE_RULES gains "a recommendation that isn't journaled didn't happen" +
mark_decision on owner report (keyword guard-tested). get_journal returns entries +
summary with v1 calibration: aged entries (past horizon, with entry + direction; hold
excluded) judged on direction vs latest price — hit_rate narrated as a process check,
never a performance claim. Registry 19 tools (record_decision, mark_decision,
get_journal); GET /api/journal.
Verified: verify.py PASS — 368 passed, 3 skipped.
Next: T075 confluence is the last regime-pack item; T082 Orb pack for Gemini; T081
pairs or T064 rigor for the backtest track. Owner: recommendations now self-record —
ask "show me my decision journal" after your next few chats.
Blockers: none.

## 2026-08-13 — T080 done: macro context — the broad-market weather report
data/fred.py: minimal httpx client for four documented series (T10Y2Y, VIXCLS, DFII10,
DFF); skips FRED's "." missing-value placeholders and returns each series' latest REAL
observation with ITS OWN date (FRED calendars differ — narration must show dates);
400 → actionable "check FRED_API_KEY" error; settings.require_fred fail-fast +
.env.example entry. analysis/macro.py: pure composition with conventions documented in
the module (inversion = caution-not-a-timer; VIX calm/normal/elevated/stressed at
15/20/30; real rate >2 restrictive) → labeled reads + cautionary-signal list + count +
"never a trade signal by itself". get_macro_context tool (registry 16; ToolContext
gains a fred slot) + GET /api/macro (503 with key instructions when unconfigured).
Verified: verify.py PASS — 359 passed, 3 skipped (ruff auto-sorted one import block).
Next: T075 confluence or T063 decision journal are the top builds; T082 Orb pack is
prime Gemini bait. Owner: put FRED_API_KEY in .env (free key, link in .env.example),
restart, then ask the Orb "what's the macro picture?" or open /api/macro.
Blockers: none.

## 2026-08-13 — D019: event-intelligence batch reconciled — base rates in, ML gated
Owner's fourth batch (sell-the-news/NLP/XGBoost). Adopted the honest core: T083 event
reaction base rates (post-earnings moves by beat/miss + pre-event runup from our own
bars — evidence, not prophecy) and T084 transcripts-as-labeled-context via the existing
LLM layer; T076 gains the priced-for-perfection flag; T023 tier check now covers
transcripts explicitly. Re-rejected per D017 (no new evidence): 99.9% accuracy; also
rejected now: XGBoost EPS predictor (Phase 7 behind §7.7 + T064; free fundamentals
aren't point-in-time — training would learn corrupted history) and directive outputs
with invented confidence (persona guard). HYGIENE FLAG: the batch reused shipped IDs
T075/76/77 — external AIs need the AGENTS.md resume prompt before proposing.
Dispositions: docs/research/event-intelligence-review-2026-08-13.md.
Verified: verify.py PASS — 349 passed, 3 skipped (memory/docs session).
Next builds unchanged: T080 macro (quick win), T075 confluence, T063 journal; T083
becomes buildable the moment T023 lands earnings dates. Owner action: T023's key
check is the gate on this whole thread — worth doing soon.
Blockers: none.

## 2026-08-13 — T062 done: morning brief, EOD report, weekly review — KUBERA starts the day with you
api/brief.py composes three reads, every number deterministic + timestamped, LLM only
narrates: MORNING — account, risk (tier/breaker/DQS), and for each holding + SPY the
overnight gap (latest trade vs last close, stale flag surfaced — Friday's price never
poses as live), regime + confidence, expected 5-day band, nearest support/resistance.
EOD — every decision today with its reasons (no_trade reasons shine here), day P&L vs
day-start, budget consumption. WEEKLY — the investment-committee review: equity vs SPY
with excess return from snapshots, discipline counts (orders / deliberate no-trades /
rejections / tier restrictions), and facts_for_lessons with the narration rule "draw
lessons from these facts only — never invent numbers". Missing data degrades to
{available: False, why} — the gap is information. T068/T076 absences stated in payload.
get_brief tool (registry 15, guards ×3) + GET /api/brief?type=morning|eod|weekly.
Verified: verify.py PASS — 349 passed, 3 skipped.
Next: T080 macro context (quick win) or T075 confluence or T063 journal. Owner: say
"give me my morning brief" to the Orb — it narrates the whole thing; or /api/brief.
Blockers: none.

## 2026-08-13 — T067 done: graduated risk tiers ENFORCED + Decision Quality Score
The owner's commitment device grows a ladder. risk/tiers.py: daily-loss-budget
consumption → tier 0–4; the paper loop enforces (buys only, sells always exempt):
tier 1 ≥25% doubles the no-trade floors, tier 2 ≥50% halves new-buy notional, tier 3
≥75% pauses entries as a logged no_trade, tier 4 = the breaker, untouched. Precedence
subtlety handled: when the breaker is TRIPPED the tier logic steps aside so the gate
rejects loudly ("halted") instead of a soft no_trade — tested explicitly. risk/dqs.py:
process-not-outcome DQS v1 from signal_log — frequency vs the overtrading guard,
trading-into-drawdown share, sizing CV, restraint (no_trade count) scored FREE; empty
window = 100 ("no activity, no bad habits"). Honesty: v1 scores the loop's pattern;
owner-fill scoring + follow/override rate = T067b (needs T036/T063). get_risk_status
tool (registry 14) + GET /api/risk. One sandbox lesson re-learned: endpoint tests with
in-memory SQLite need StaticPool (TestClient threads).
Verified: verify.py PASS — 337 passed, 3 skipped.
Next: T062 briefs (morning/EOD — now has regime, intraday, expected-move, risk status
to compose from) or T075 confluence or T080 macro. Owner: ask the Orb "what's my risk
status?" or open /api/risk.
Blockers: none.

## 2026-08-13 — T077 done: expected moves as distributions — ranges, never targets
analysis/expected_move.py: overlapping horizon-day returns over the trailing lookback
→ percentile bands via statistics.quantiles(method="inclusive") (hand-verified:
3-sample p05 = −0.08 interpolation), up_frac, median |move|, payoff ratio (avg winner
/ avg loser; None when one side is empty — all-up history has no ratio, tested). Vol
clustering per D016: each sample tagged with trailing-vol at its start, terciled;
reading reports the CURRENT tercile + bands from matching history only — the
quiet-tape test proves conditioned p95 shrinks >5x vs wild-contaminated unconditional.
Honesty hard-coded: every reading carries "NOT a forecast" + the overlap-
autocorrelation caveat; tool description orders ranges-not-targets narration.
get_expected_move (registry 13, guards ×3) + GET /api/expected-move/{symbol}.
Verified: verify.py PASS — 322 passed, 3 skipped.
Next: T067 DQS (the coaching centerpiece) or T062 briefs (both fed now); T077b
(Monte Carlo + loop integration) queued. Owner: /api/expected-move/SPY?horizon_days=5
or ask the Orb "how far does SPY usually move in a week?".
Blockers: none.

## 2026-08-13 — T054+T055 done: the router picks the playbook; "no trade today" is now a decision
T054: make_range (long only the lower half of the trailing range, flat above) +
make_regime_router (structure→momentum, range→range trading, else CASH) on the
closes-only T030 contract via _regime_lite (swing HH/HL + SMA-slope fallback).
THE CATCH OF THE SESSION: first cut leaked longs in bars 39–44 of the BEAR fixture —
between lookback and lookback+5 bars, structure is UNKNOWABLE, and the range trader
treated "can't tell" as "no trend" and bought the falling knife. Fix: _regime_lite
gained an explicit "unknown" state; the range trader refuses anything but a CHECKED
"none". Acceptance: router beats always-momentum in CHOP (0.0 vs >100%), rides BULL,
flat through BEAR. Also learned/encoded: engine weights sit one bar after decisions
(no-lookahead shift) — hand test documents it.
T055: paper loop's new no_trade action (buys only; sells always allowed): overtrading
guard (5/day across everything), ATR cost floor (T077 proxy), quiet-market check via
the full classifier (RVOL < 0.3 + bottom-quartile width). Every no_trade row logs its
reasons + "capital preserved by design".
Verified: verify.py PASS — 311 passed, 3 skipped.
Next: T077 expected-move engine (replaces the ATR proxy, feeds T056 exits), or T075
confluence, or T067 DQS. Owner: python scripts\paper_trade.py SPY --strategy
regime_router — KUBERA now picks the playbook AND can conclude "nothing today".
Blockers: none.

## 2026-08-13 — T052 done: intraday VWAP + time-of-day RVOL — the doctrine's backbone
First ticket of the D018 build order. data: get_intraday_bars(timeframe 1Min…1Hour,
days<=30) — tz-aware UTC bar starts. analysis/intraday.py: sessions grouped by ET date
(zoneinfo; tzdata dep added for the owner's Windows — a 20:30-ET after-hours bar stays
with its ET day even past UTC midnight; boundary TESTED), RTH filter default-on,
cumulative session VWAP on typical price (hand case: 5000/500=10.0), VWAP crossings
counter (running-VWAP side flips — the "crossing without holding = no trend" churn
signal), and intraday RVOL implemented as the doctrine defines it: today's cumulative
volume at this time-of-day vs prior sessions' cumulative volume by the SAME ET time
(hand case: 600 vs 300 → 2.0; a later prior-session bar proves the cutoff). Zero-volume
degrades to None honestly; D006 note on every reading. get_intraday tool (registry 12,
guards ×3 bumped) + GET /api/intraday/{symbol}.
Verified: verify.py PASS (12 new tests; full suite green).
Next per D018 order: T055 no-trade condition (+T054 router alongside), or T075
confluence which just unblocked. Owner: /api/intraday/SPY during market hours, or ask
the Orb "what kind of day is SPY having?" — note: pip install -r backend/requirements.txt
again (tzdata added).
Blockers: none.

## 2026-08-13 — D018: cross-agent review reconciled + three safety nets built
Owner uploaded a repo-aware review (best one yet — it read our memory files). ~70% was
priority votes on existing tickets (accepted: T052 → T055 → T077 → T067/T062; no new
strategy templates before the no-trade condition). BUILT the genuinely-new small items
same-session: (1) stale-data detection — latest trade/quote now carry age_seconds +
stale (>15 min), get_latest tool instructed to never present stale as live (session-
aware upgrade parked in T036); (2) scripts/backup_db.py — timestamped copies, --keep 14,
backups/ git-ignored, Task Scheduler line in docstring; (3) scripts/health_check.py —
server up / breaker tripped (reads risk_state directly, works with server down) / sync
freshness, exit code + best-effort Windows toast via --notify. Enriched T016 (PARKED:
Schwab approval pending — owner directive, Alpaca continues), T036, T060, T063, T064
(promotion_status enforced in loop), T079 (unblocked from T023); minted T082 Orb
upgrade pack (conversations sidebar + portfolio panel + feed badges — Gemini bait).
Postgres deferred on evidence (see D018). Dispositions: docs/research/
agent-review-2026-08-13.md.
Verified: verify.py PASS (full suite green; +8 tests: stale flags, backup retention,
health checks).
Next: T054+T055 together (range strategy + router + no-trade), or T052 intraday first
per the adopted order. Owner: schedule the two scripts (docstrings have the commands);
T005 push remains the highest-value 5-minute action.
Blockers: none.

## 2026-08-13 — T053 done: breakout detector — escape + volume + HOLD, as events
analysis/breakout.py scans daily bars for fresh range escapes (a bar whose close exits
the prior L-bar extremes while the previous bar hadn't — continuations extend, never
restart) and judges each event on the doctrine's three parts: RVOL at the break
(RVOL_CONFIRM/RVOL_FAKEOUT imported from regime.py), hold-outside tracking
(held_bars = consecutive closes beyond the boundary), status judged ONCE on the first
hold_confirm bars: confirmed / failed / unconfirmed / pending, plus scan-level
`active`. The named test test_the_hundred_to_106_to_99_lesson locks the owner's
canonical fakeout: volume-confirmed escape that returns inside → FAILED regardless of
volume. Fixture lesson worth remembering: degenerate h=l=c bars made the 99-return
look like a down-escape — the fix was a realistic range floor in the FIXTURE, not code.
Reachable: get_breakouts tool (registry 11; guards bumped ×3) + GET /api/breakouts/…
Verified: verify.py PASS — 278 passed, 3 skipped.
Next: T054 range strategy + regime router (T050+T051+T053 all feed it now) — the meta-
strategy that picks momentum/range/CASH. Owner: /api/breakouts/SPY or ask the Orb
"did SPY break out recently?".
Blockers: none.

## 2026-08-13 — T051 done: support/resistance — "repeated rejections define the range"
Built analysis/levels.py: swing highs/lows (regime.py's swing_points promoted to public,
shared) pooled and clustered by price proximity (sorted greedy walk, running-mean join
within tolerance_frac=1%); a cluster becomes a LEVEL only with >= min_touches swings
(default 2). Levels carry price (member mean), touches, provenance kind — support /
resistance / mixed (support-becomes-resistance detected and tested), first/last touch
dates, signed distance from last close; reading includes nearest support + resistance
(positional, any provenance — "trade the edges"). Reachable now: get_levels tool
(registry = 10; count guards bumped in 3 test files) + GET /api/levels/{symbol}. Tests:
two hand-walked micro fixtures (3-touch S/R + dropped stray; mixed-kind breakdown with
nearest_support=None), tolerance/min_touches behavior, validation, 60-bar triangle
through tool + endpoint (7-touch levels at 94.5/105.5).
Verified: verify.py PASS — 269 passed, 3 skipped.
Next: T053 breakout detector (T050's escape + T051's levels + RVOL threshold) is now
fully fed; then T054 range strategy + router. Owner: ask the Orb "where's support on
SPY?" or open /api/levels/SPY.
Blockers: none.

## 2026-08-13 — T078 done: vol-parity sizing — position size now answers to volatility
Built: Wilder ATR (true_ranges + atr) in analysis/metrics with hand-computed tests;
risk/sizing.py volatility_parity_notional — a buy may risk at most
equity × risk_per_trade_frac (default 1%, RiskLimits hard-bands it ≤5%) if the
stop_atr_multiple×ATR stop is hit, so size shrinks as volatility grows. Paper loop:
buys sized BEFORE the gate (sizing note logged on bound orders + in SignalLog.reasons),
sells untouched (reducing risk is never blocked), <ATR_WINDOW+1 bars → no_action
fail-closed. Design decision worth keeping: the sizer ONLY shrinks the request — the
RiskEngine's 20% cap still rejects oversized targets loudly; no silent auto-resize of a
rule violation. Legacy loop tests pass unchanged (fixture H/L made sane: ATR=2 → ceiling
44,750 above all legacy deltas). Whipsaw test: ATR 41 → 15k request sized to 12.195
shares — hand-walked.
Verified: verify.py PASS — 256 passed, 3 skipped.
Next: T051 support/resistance or T053 breakout detector (regime pack), or T080 macro
context (quick win). Owner: nothing to do — sizing is automatic in paper_trade.py.
Blockers: none.

## 2026-08-13 — "Institutional precision" batch reviewed (D017): pillars validated, T080/T081 minted
Owner's second batch (quant-fund framing). Verdict: the Three Pillars — E[X] over win
rate, execution discipline, no-trade selectivity — are correct AND already our
architecture (T077 / risk rails / T055); checklist section C was 100% already ticketed
(T078/T079/T033/T035), which is convergent validation. NEW: T080 macro regime context
(FRED: 10Y–2Y, VIXCLS, real rates — free + deterministic + dated) · T081 pairs/stat-arb
template (cointegration screen, spread z-score MR, through the existing engine + T064
gate). ENRICHED: T023 (earnings surprise/13F; news = context not alpha), T077 (seeded
MC v2), T055 (confluence-score no-trade reason). REJECTED with reasons in the review
doc: L2/DOM/dark-pool (D006 honesty), HMM now (unexplainable/untestable), sentiment-as-
alpha, VIX term structure, all "bulletproof/99.9%" language. Binding record:
docs/research/institutional-precision-review-2026-08-13.md.
Verified: verify.py PASS — 234 passed, 3 skipped (memory/docs session).
Next: build tickets unchanged — T051/T053 (regime pack) or T077/T078; T080 is a good
quick win (pure httpx + FRED, no new architecture).
Blockers: none.

## 2026-08-13 — Owner suggestion batch reconciled (D016): T075–T079 minted, four tickets sharpened
Owner delivered a 5-part improvement review. Reconciled without duplication (dispositions
binding in docs/research/owner-suggestions-2026-08-13.md): NEW T075 multi-timeframe
confluence (after T052; volume-delta deferred to SIP) · T076 event-risk calendar guard
(FRED/earnings → pause/scale before FOMC/CPI/NFP) · T077 expected-move distribution
engine (rolling percentile bands, never point forecasts; feeds T055's cost threshold +
T056 exits) · T078 ATR vol-parity sizing (MIN with existing 20% cap — only ever shrinks)
· T079 correlation/overlap guard (engine behind T066's pre-trade correlation check).
EXTENDED: T067 tiers now ENFORCED in the paper loop (25/50/75/100% budget → stricter
R/R / half size / entry pause / breaker), T063 captures regime+targets and calibrates
(human-gated re-weighting), T064 walk-forward = promotion gate, T062 briefs go
voice-first. AGENTS.md gains agent-strengths defaults (Claude math/tests · Gemini UI/web
· ChatGPT ideation-as-data). Already covered: T074, T052, process-over-outcome persona.
Verified: verify.py PASS — 234 passed, 3 skipped (docs/memory session; suite untouched).
Next: T051 support/resistance or T053 breakout detector remain the natural builds;
T077/T078 are strong candidates right after — both are pure deterministic analysis.
Blockers: none.

## 2026-08-13 — T050 done: regime classifier — the doctrine becomes code
The regime pack opener. analysis/regime.py classifies from daily bars, faithful to
docs/research/regime-trading-notes.md: swing-based HH/HL structure (strict local extrema,
SMA-slope fallback since monotone series have no swings), standing 20-bar range + width
percentile across trailing rolling windows (low percentile = the coil), close-escape vs
the prior window with suspected_fakeout when RVOL < 1.0 (the $100→$106→$99 lesson),
RVOL against the symbol's own baseline with volume_feed REQUIRED (D006 label + SIP
caveat in every reading). Decision order matters and is tested: a matured trend outranks
its own escapes. Confidence = fixed 3-signal checklist per label (0.35 + 0.15/pass, cap
0.9 — a daily-bar heuristic never claims certainty); checks dict returned so chat can
say WHY. Shipped reachable: get_regime tool (9 total) + GET /api/regime/{symbol}.
Tests: sawtooth trend fixtures with rising/falling swings, stationary triangle,
coil (13/76 percentile hand-walked), volume-confirmed breakout (15/77), fakeout twin,
plus micro known-answers for rvol/escape/swings/fallback and full validation.
Verified: verify.py PASS — 234 passed, 3 skipped.
Next: T051 support/resistance (feeds the range strategy) or T053 breakout detector;
T054 router wants both. Owner: ask the Orb "what regime is SPY in?" once server restarts.
Blockers: none.

## 2026-08-12 — T073 done: THE KUBERA ORB (Phase 5 opened early)
Owner wants Zoey OS-like experience (fetched zoeyos.com: voice-first workspace, living
visuals, visible agent work). Built the Orb: apps/web/orb.html served at GET / — canvas
orb with state-driven glow (idle/listening/thinking/speaking + audio-amplitude reaction),
browser SpeechRecognition for STT (Chrome/Edge), POST /api/chat(voice=true), streaming
GET /api/tts (edge-tts as lazy SERVER dep — 503 with install hint; text capped 2k),
tool-call chips per reply ("watch the work happen"), typed fallback, and the confirm
checkbox as the deliberate gesture. Tests: root route, tts 503/streaming/empty (fake
edge_tts). Owner setup: pip install edge-tts in the server venv, open localhost:8000.
Zoey's sub-second feel needs a realtime pipeline → T074 filed (LiveKit/Pipecat/OpenAI
Realtime + barge-in; verify landscape at build).
Verified: verify.py PASS — 213 passed, 3 skipped.
Next: owner opens the Orb; T074/T072 for voice polish, or back to T050/T069 substance.
Blockers: none.

## 2026-08-12 — MILESTONE: first spoken conversation (T071 ✔) + naturalness pass
Owner talked to KUBERA and it answered aloud — market snapshot with data-quality
skepticism (flagged DIA's wide spread) and an offer to go deeper. T071 accepted.
Owner feedback: sounds robotic → diagnosis: default SAPI TTS, not the words.
Shipped: KUBERA_VOICE env for edge neural-voice selection (AndrewNeural recommended),
VOICE_STYLE prosody rules (contractions, short varied sentences, natural openers, never
read digit strings — guard-tested), README voice ladder. T072 filed: human-grade TTS
backends (OpenAI TTS, local Kokoro). Also folded in field lint fixes on talk.py.
Verified: verify.py PASS — 209 passed, 3 skipped.
Next: owner flips KUBERA_TTS=edge tonight; T072 or T069/T050 next build.
Blockers: none.

## 2026-08-11 — Gemini (Antigravity) — talk.py CPU device fix & HTTP 503 error reporting
Fixed: (1) `scripts/talk.py` threw `RuntimeError: Library cublas64_12.dll is not found` on Windows when `faster-whisper` defaulted to CUDA. Added `device="cpu"` to `WhisperModel("small", device="cpu", compute_type="int8")` so local STT runs reliably on CPU without CUDA DLL dependencies. (2) Added `'v'` key as an input shortcut alongside `[Enter]` to start push-to-talk recording in `scripts/talk.py`. (3) Added `httpx.HTTPStatusError` exception handling in `scripts/talk.py` so 503/502 server responses print the server's actionable `detail` message (e.g. missing Alpaca or LLM keys in `.env`). (4) `test_llm.py` failed `test_build_provider_allows_keyless_custom_endpoint` when `OPENAI_BASE_URL` was set in `.env` (Ollama setup); added `monkeypatch.delenv("OPENAI_BASE_URL", raising=False)` and explicit `openai_base_url="https://api.openai.com/v1"` parameter to isolate fail-fast testing.
Verified: all 189 tests pass.
Next: T050 (regime pack) or T061 (IPS).
Blockers: none.

## 2026-08-12 — Owner doctrine captured → regime intelligence pack ticketed (T050–T056)
The owner delivered a detailed trading doctrine (day-type classification: trending vs
consolidation vs breakout; range trading at the edges; RVOL + volume-confirmed breakouts
vs fakeouts; VWAP; the no-trade condition as a first-class decision; options theta/IV
caveats). Preserved verbatim-in-spirit at docs/research/regime-trading-notes.md — READ IT
before building T050–T056. Seven tickets seeded: regime classifier, support/resistance,
intraday VWAP/RVOL, breakout detector, range strategy + regime router, no-trade condition
in the paper loop, structured exit_plan ("how long to hold"). Data-honesty constraint
threaded through: IEX feed = relative volume only until SIP upgrade (D006).
"KUBERA decides for me" = already true on paper (T032 loop); live authority stays behind
§7.4 — reaffirmed with the owner.
Next: T050 is the natural opener; T045 (MCP server) still pending in Phase 4.
Blockers: none.

## 2026-08-12 — T061 done (Investment Policy Statement) — KUBERA knows its owner
Built: investment_policy table (migration 08dfc64f8e4b), data/ips.py (partial upserts;
restriction lists replace wholesale; format_ips_for_prompt compact block), IPS injected
into EVERY chat system prompt as hard context ("check every recommendation against it,
state conflicts plainly"). Tools: get_ips (free) + update_ips — the FIRST live
confirmation-gated tool: the owner can set his IPS by talking, KUBERA asks for
confirmation, and only the typed/deliberate confirm flag completes it (T043 gate proven
in production use, not just tests). GET /api/ips for viewing. Registry now 8 tools;
count guards updated; safety guard now asserts gated == {update_ips}.
Verified: verify.py PASS — 209 passed, 3 skipped.
Next: owner should SET his IPS (by voice, fittingly) — then T069 tolerance estimation,
T062 briefs, and the coach all have their foundation. T050 regime pack still open.
Blockers: none.

## 2026-08-12 — T070 done (push-to-talk loop) — KUBERA can be TALKED to
Built: `api/voice_loop.py` — tested orchestration (audio → STT → /api/chat(voice=true) →
TTS): conversation threads across turns, silence never reaches KUBERA, and confirm passes
through ONLY from the typed gesture (all fake-tested). `scripts/talk.py` — Enter-to-talk
capture (sounddevice), STT backends (faster-whisper local default; KUBERA_STT=openai
fallback for py3.14 wheel gaps), TTS backends (pyttsx3/SAPI default; KUBERA_TTS=edge for
neural voices), typing `confirm` is the only confirmed-turn path. requirements-voice.txt
keeps audio deps out of backend CI. README try-it added.
Verified: verify.py PASS — 200 passed, 3 skipped. Spoken round-trip = owner run (T071);
sandbox has no audio hardware.
Next: T071 (owner: talk to it!), then T061 IPS or T050 regime pack.
Blockers: none.

## 2026-08-12 — Voice mode shipped (D015): owner is voice-first
Owner will primarily talk to KUBERA. Shipped now: ChatRequest.voice → run_chat_turn →
build_system_prompt(voice=True) appends VOICE_STYLE — spoken-aloud replies (no markdown/
tables/bullets, ear-rounded numbers, ~120-word default, natural recency phrasing), with
the safety invariant IN the prompt: a spoken "yes" is not the confirm flag. Tests: voice
prompt content, default-off, flag plumbing through the loop. T070 filed: push-to-talk
desktop loop (STT → /api/chat → TTS) — voice lands before Phase 5, not inside it.
Verified: verify.py PASS — 196 passed, 3 skipped.
Next: T070 (hear KUBERA speak) or T061 (IPS). Both high-value; owner's pick.
Blockers: none.

## 2026-08-12 — Time-locked breaker reset (commitment device) + T069
Owner disclosed the pattern: he sets risk limits, passes them, keeps trading. Built the
enforceable half NOW: RiskLimits.cooldown_hours (default 20h) — a trip sets
lockout_until; reset() raises LockoutActiveError until it passes; NO override parameter
exists by design; lockout persists to DB (migration 5b54677a6d1d) so restarts can't
shorten it; risk_reset.py explains the refusal. Tests: refusal with remaining time,
refusal 1 minute before expiry, allowed after, zero-cooldown legacy mode, restart
survival. Honest limits documented in the self-exclusion doctrine (gemini review doc):
KUBERA cannot freeze thinkorswim; friction ≠ cryptography; the structural answer is
KUBERA-managed allocation. T069 filed: adaptive risk-tolerance estimation from account
composition + behavior (owner wants KUBERA's estimate over his in-the-moment one).
Verified: verify.py PASS — 194 passed, 3 skipped. README updated.
Next: T061 IPS (unlocks coach/briefs/T069) or T050 regime pack.
Blockers: none.

## 2026-08-12 — Gemini master-spec reconciled (D014): the coaching layer
Owner supplied Gemini's pre-project master prompt. Review at docs/research/
gemini-master-spec-review.md (companion to D013 — shared rejections not re-argued).
Standout adoption: the Quantitative Trading Coach — process-not-outcome judgment of the
OWNER'S trades, behavioral-pattern detection, and the owner's Decision Quality Score
(risk budget × behavior → graduated advisories; hard stop stays the breaker). Tickets:
T066 coaching pack (needs T016 fills; chat v0 today), T067 DQS + advisories, T068
watchlist/ranking. Upgraded: T061 → full IPS, T062 → +weekly committee review, T064 →
+crisis-window stress tests. Persona: coaching rule + educational mode (guard-tested).
Verified: verify.py PASS — 187 passed, 3 skipped.
Next: T050 regime pack or T061 IPS (unlocks coaching + briefs); T045 MCP still open.
Blockers: none.

## 2026-08-12 — ChatGPT master-spec reconciled (D013); persona upgraded; T060–T065
The owner supplied his original ChatGPT master prompt + Software Factory spec (this was
the abandoned first attempt — its stack matches the .env extras). Full section-by-section
review recorded at docs/research/chatgpt-master-spec-review.md: most of it we already
built leaner (rails, factory-as-repo, modes, explainability); real gaps became T060–T065
(TWR benchmarking, user profile memory, morning/EOD briefs, decision journal, backtest
rigor, risk v2); rejections logged with reasons (microservice stack, nine-agent
bureaucracy, duplicate state files). Persona upgraded in code: strict financial-domain
boundary, KUBERA ANALYSIS answer structure (verdict → confidence with calibration caveat
→ evidence → both cases → what-would-change-my-view → recency), conflicting-signals
honesty, external-content-is-data injection defense — all guard-tested. AGENTS.md gains
the injection-defense rule for coding agents too.
Verified: verify.py PASS — 187 passed, 3 skipped.
Next: T050 (regime pack opener) or T060/T061 (quick wins); T045 MCP still pending.
Blockers: none.

## 2026-08-12 — MILESTONE: claude-sdk live on owner's Max (T047 ✔) + usage-parse fix
Owner activated LLM_PROVIDER=claude-sdk and ran a live turn: KUBERA (Claude brain)
corrected the question's premise via get_portfolio (owner holds 19.46 SPY ≈ $15k — the
paper loop's own first trade!), delivered case-for/against with a falsifiable 200-day
risk level, flagged AAPL/SPY mega-cap overlap, persona disclaimers intact. Side-channel
audit recorded both tool calls correctly.
Fixed: SDK ResultMessage.usage is a DICT in current versions — extraction handled objects
only, reporting 0/0. Now handles both shapes, with a regression test.
Verified: verify.py PASS — 187 passed, 3 skipped.
Next: T045 (KUBERA MCP server) closes Phase 4; then Phase 5 (PWA).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T046 done (chat on the owner's Claude Max)
Built: `api/llm_claude_sdk.py` — LLM_PROVIDER=claude-sdk runs /api/chat on the owner's
Max subscription (personal-use-only per verified Anthropic policy — D012 has citations).
The SDK runs its own agent loop, so: registry bridged as SDK tools (@tool wrappers calling
registry.execute with the request-bound ToolContext — confirmation gate intact), permission
surface locked to mcp__kubera__* (Bash/file tools disallowed, dontAsk, bounded max_turns),
history flattened to a transcript prompt, and every internal tool run captured as a
side-channel event the chat loop persists as tool rows (audit trail complete) + feeds the
recency footer. Lazy optional dependency; ConfigErrors are actionable. Fully mocked tests
(fake claude_agent_sdk module) — 186 passed, 3 skipped.
Owner activation = T047 (install SDK, claude setup-token, flip LLM_PROVIDER).
Next: T045 (KUBERA MCP server) is the last Phase 4 side quest; then Phase 5 (PWA).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T044 done (context budgeting)
Built: `api/context.py` assemble_context — groups history into indivisible blocks (an
assistant tool_call + its results can never split: provider APIs error on orphans, and
the pairing test proves integrity across budgets), drops oldest blocks whole within
KUBERA_CONTEXT_BUDGET_CHARS (default 24k chars), always keeps the newest block, and
elides tool payloads older than the freshest 4 blocks while assistant conclusions
survive. Wired into the chat loop. Long conversations now cost O(budget), not O(history).
Note: "relevant research memory" retrieval deferred to Phase 7 (needs pgvector, D007).
Verified: verify.py PASS — 179 passed, 3 skipped.
Next: T045 (KUBERA MCP server) or T046 (Max/Agent SDK provider). Phase 4 core otherwise
complete — spec §7.4-phase "Done when" needs only real-world conversation mileage.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T043 done (conversation rails as code)
Built: (1) confirmation gate — ToolSpec.requires_confirmation + ConfirmationRequiredError;
ctx.confirmed flows ONLY from ChatRequest.confirm (user's HTTP body — the LLM cannot set
it); chat loop surfaces confirmation_required to the model so it asks the user; guard test
asserts none of the 6 current tools require confirmation (future order tools must flip the
flag consciously). (2) recency post-check — ensure_recency_line appends a deterministic
"Data recency: <tool> asof <ts>" footer from ACTUAL tool timestamps whenever a
data-grounded reply lacks a date (handles str and datetime asof shapes).
Verified: verify.py PASS — 171 passed, 3 skipped. Full two-turn confirm flow tested.
Next: T044 (context budget), T045 (MCP server), or T046 (Max/Agent SDK provider).
Blockers: none.

## 2026-08-11 — Gemini (Antigravity) — terminal environment injection setting
Fixed: enabled `"python.terminal.useEnvFile": true` in `.vscode/settings.json` so integrated terminal sessions automatically inject environment variables from `.env`.
Verified: settings updated cleanly.
Next: T046 (Claude Agent SDK provider) or T043/T044/T045 as planned.
Blockers: none.

## 2026-08-11 — MILESTONE: first live KUBERA conversation (owner-verified)
Owner ran POST /api/chat on his machine with Ollama + nemotron-3.5-lightning (30B MoE,
tools-capable, free/local) via the OPENAI_BASE_URL path. KUBERA called get_latest +
get_symbol_briefing on AAPL and produced a properly hedged, dated, evidence-grounded
answer (verdict, asof-stamped metrics table, assumptions, falsifying risk, no certainty),
correctly noting the owner holds no AAPL. ~5.4k in / 1.3k out tokens per turn.
Environment fact for all agents: local tool-calling models work; nemotron-3.5-lightning
is the validated default for keyless local chat.
Next: unchanged (T043/T044/T045/T046).

## 2026-08-11 — Claude (Cowork) — chat provider options (owner hit API-credits wall)
Context: owner's Anthropic API account has no credits (Max subscription ≠ API billing).
Built: OPENAI_BASE_URL override — the OpenAI adapter now targets any OpenAI-compatible
endpoint (Ollama local = free, Groq, Gemini compat); keyless custom endpoints allowed,
real OpenAI still requires a key. Owner unblock: LLM_PROVIDER=openai +
OPENAI_BASE_URL=http://localhost:11434/v1 + OPENAI_MODEL=<ollama model>.
Filed: T046 — Claude Agent SDK provider to run chat on the owner's Max subscription
(Claude-account auth, registry as SDK tools; verify current subscription terms at build).
Also fixed earlier: conversation_id=0 now means new conversation (Swagger example trap).
Verified: verify.py PASS — 163 passed, 3 skipped.
Next: T046 (high value for owner) or T043/T044/T045 as before.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T042 done — KUBERA CAN TALK
Built: `api/chat.py` run_chat_turn — persona + replayed history → provider.complete →
execute requested registry tools (errors surfaced verbatim, results capped at 6k chars) →
loop until text (bounded by max_tool_rounds=6, honest message on exhaustion). New tables
conversations + chat_messages (migration 7bb8528ec2d3) persist EVERY message, tool call,
tool result, and token count — spec §2.7's "why did KUBERA say that" is a SELECT away.
Endpoints: POST /api/chat (DI: db, alpaca, market, llm provider — each 503s actionably
when unconfigured), GET /api/chat/{id} audit view. README: how to talk to KUBERA via
/docs (needs ANTHROPIC_API_KEY or OPENAI_API_KEY + LLM_PROVIDER).
Verified: verify.py PASS — 161 passed, 3 skipped. First LIVE conversation happens on the
owner's machine (LLM APIs not reachable from sandbox).
Next: T043 (conversation safety post-checks) and T044 (context assembly) polish the loop;
T045 (MCP server) remains the high-leverage side door. Owner: try talking to it!
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T040+T041 done (Phase 4 opened: persona + LLM layer)
Built: `api/persona.py` — build_system_prompt(asof, tools) with 8 CORE_RULES encoding spec
§2 (every number from tools, recency stated, no certainty framing, backtests-are-the-past,
paper clarity, explicit confirmation + risk-engine supremacy for anything order-shaped, no
gap-filling, not-an-advisor) + the analyst voice; guard tests fail if any rule is deleted.
`api/llm.py` — neutral message/tool-call format; AnthropicProvider + OpenAIProvider (thin
httpx, no SDKs) with full both-direction translation (tool_use/tool_result blocks vs
tool_calls/tool role) proven by captured-payload tests; build_provider selects via
LLM_PROVIDER with fail-fast actionable ConfigErrors. Model names are settings with
defaults (claude-sonnet-5 / gpt-5) — verify current names at T042 wiring time.
Verified: verify.py PASS — 154 passed, 3 skipped.
Next: T042 — POST /api/chat: the loop (persona + context → LLM → tool execution via
registry → final answer), conversation persistence, audit trail. Then T043 rails.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T034 done — PHASE 3 CORE COMPLETE
Built: `backtest_runs` table (migration 33592ebf6de6) + `backtest/ledger.py` — every run
recorded with strategy/params/period/metrics; `list_runs` with filters. Shared strategy
TEMPLATES + build_strategy (CLI + API + tools all use one registry). `GET /api/backtests`,
`POST /api/backtests/run`, and `run_backtest` as the 6th registry tool — the future chat
layer can test strategies conversationally, and §7.4 promotion evidence accumulates in the
ledger. Gotcha fixed: in-memory SQLite is per-connection; TestClient threads need
StaticPool (see test_ledger.py comment).
Verified: verify.py PASS — 145 passed, 3 skipped.
Phase 3 status: engine, strategies, risk rails + persistence, paper loop, ledger — DONE.
T036 (fills sync, market-hours guard) remains as optional polish.
Next: Phase 4 (T040 persona → T041 LLM abstraction → T042 /api/chat) or T045 (KUBERA MCP
server — small, high leverage). Owner tasks still open: T005 push, T007 finale.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T035 done (breaker survives restarts)
Built: `risk_state` table (single row, migration 35b6c01bf49b), `risk/persistence.py`
(restore/persist), `RiskEngine.restore()` (persistence-only, documented), paper loop now
restores state before acting and persists after every equity mark. `scripts/risk_reset.py`:
shows state; reset requires --note AND typing RESET. README updated (loop mode now safe;
reset instructions added). Fills-sync + market-hours guard split to T036.
Verified: verify.py PASS — 140 passed, 3 skipped. Killer test: trip → simulated restart
(fresh engine, same DB) → still blocked, zero orders reach the broker.
Next: T034 (results ledger — last Phase 3 ticket) or T036 polish; then Phase 4.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T032 done (paper-trading loop) — KUBERA can trade (paper)
Built: `backtest/paper_loop.py` run_paper_cycle — bars → strategy weight → target value
(weight × allocation × equity) → delta order → RiskEngine pre_trade_check → Alpaca PAPER
order. Every cycle writes a SignalLog row (ordered/rejected/no_action) with the data
snapshot. AlpacaClient.place_order (validates inputs; paper-only by construction).
New table signal_log + migration c09d9671853d. CLI scripts/paper_trade.py (--strategy,
--allocation, --loop). Tests hand-compute the buy qty (15000/179), prove rejected orders
never reach the broker, sells cap at held qty, and the tripped breaker blocks cycle 2.
Verified: verify.py PASS — 136 passed, 3 skipped. README try-it updated per standing rule.
Known gap → T035 filed: risk trip state is per-process; persist to DB so restarts can't
bypass the breaker. Owner should run cycles manually (not --loop) until T035 lands.
Next: T035 (small, safety) then T034 (results ledger) closes Phase 3.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — README testing guide + backtest demo (owner request)
Built: README "Try what's built so far" — every endpoint incl. /docs Swagger explorer,
sync, verify, repair. New `scripts/backtest_demo.py`: compares buy-and-hold / momentum /
SMA-cross / mean-reversion on real history with costs, graceful config/network errors.
NEW STANDING RULE in AGENTS.md session protocol: any session that changes the user-facing
surface updates README's try-it section — the owner tests from it. All agents comply.
Verified: verify.py PASS; demo script degrades cleanly without network (I002).
Next: T032 (paper-trading loop) unchanged.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T031 done (strategy library with regime proofs)
Built: make_momentum(lookback, threshold) and make_mean_reversion(window, band_frac) on the
T030 contract, plus regime test fixtures (BULL +1%/bar, BEAR -1%/bar, CHOP 100/82 range).
Key behavioral proofs: momentum stays 100% flat through the entire synthetic bear (capital
preserved, beats buy-and-hold by construction) and rides the bull after warmup; mean
reversion profits in chop and correctly sits out smooth trends. Hand-tracked equity curves
for both. MR is stateless (no hysteresis) — documented simplification.
Verified: verify.py PASS — 128 passed, 3 skipped.
Next: T032 (paper-trading loop: strategy → risk gate → Alpaca paper orders — the big one)
or T034 (results ledger). T032 recommended; its live pieces will skip in sandbox per I002
and prove out on the owner's machine.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T033 done (risk engine — the hard rails)
Built: `risk/engine.py` — RiskLimits (validated), OrderRequest, RiskDecision (timestamped,
all violated rules with numbers), RiskEngine. Fail-closed: uninitialized engine rejects all
orders. Position cap inclusive at the boundary; sells exempt from cap (they reduce risk).
Circuit breaker: trips at the daily-loss limit exactly, then blocks buys AND sells; neither
recovery nor a new day untrips it — only manual reset(note). Pure logic, no I/O; T032 owns
persistence of trip state and wiring to live equity marks.
Verified: verify.py PASS — 118 passed (22 new risk tests), 3 skipped.
Next: T032 (paper-trading loop through this gate) needs T031 (strategy library) — either
order works; T031 is the smaller bite. T040-T044 (conversation) remain open for any agent.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T030 done; Phase 3+4 backlogs seeded; D010 logged
Built: `backtest/engine.py` — minimal deterministic daily-bar engine (D010: hand-verifiable
over frameworks; revisit triggers logged). No-lookahead enforced by passing the strategy a
prefix slice (tested with a spy). Cost model (bps of shifted equity), weight validation,
flat-strategy Sharpe honestly None. `backtest/strategies.py`: buy_and_hold + make_sma_cross.
Every expected number in the 8 new tests is hand-computed, including a fully hand-tracked
SMA-cross equity curve.
Seeded: Phase 3 tickets T031-T034 (strategy library, risk module, paper loop, results
ledger) and Phase 4 tickets T040-T044 (persona, LLM abstraction, /api/chat, safety rails,
context assembly — unblocked, registry done).
Verified: verify.py PASS — 96 passed, 3 skipped.
Next: T033 (risk module — prereq for the paper loop) or T040/T041 (conversation layer).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T017 done (httpx plumbing unified)
Built: `data/_http.py` — build_client (auth headers, timeout) + checked_get (network-error
wrapping, actionable 401 hints, HTTP>=400 discipline). Both Alpaca clients refactored onto
it; error text preserved byte-for-byte. Pure refactor: same 85 tests pass unchanged.
Remaining Phase 2: T023 (fundamentals/news — owner's machine) and T016 (Schwab read-only —
needs owner's dev-app confirmation). Everything else in Phase 2 is done.
Next: T023 via Antigravity, or begin Phase 4 conversation-layer ticket writing (it can
proceed in parallel — the §3 tool registry it needs is complete).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T025 done (symbol briefing composer)
Built: `analysis/briefing.py` — the deterministic evidence pack behind "should I buy X":
trailing returns (20/60/252 trading days), 60d annualized vol, 252d max drawdown,
distance from 52-week high/low, SMA50/200 trend context (`sma()` added to metrics with
tests), and the owner's current exposure (PositionContext). Degrades gracefully on thin
history (None fields + bars_count, never fake numbers). Registered as tool
`get_symbol_briefing` (registry now 5 tools) + `GET /api/briefing/{symbol}`.
Verified: verify.py PASS — 85 passed, 3 skipped.
Also: owner's venv observed rebuilt on CPython 3.14.7 (I005 nearly closed — needs one
local verify PASS to confirm).
Next: T023 (fundamentals/news — owner's-machine task) or T017 chore. Phase 2 exit then
needs only the Phase 4 narration on top of this briefing.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — IDE config fix (I004)
Fixed: owner's Antigravity showed missing-import errors (Pyrefly) and couldn't bind the
interpreter — no pyrightconfig.json/.vscode existed. Committed pyrightconfig.json (venv
binding, backend extraPaths, alembic versions excluded) and .vscode/settings.json
(defaultInterpreterPath, pytest config). Manual fallback steps in ISSUES I004.
Noted: kubera.sqlite3 exists at repo root — owner has run the migration (T007 nearly done).
Verified: verify.py PASS (unchanged code, config only).
Next: unchanged — T023 via Antigravity, or new "should I buy X" briefing ticket.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T024 done (tool-calling registry)
Built: `api/tools.py` — the spec §3 contract in code. ToolRegistry with @registry.tool
decorator (duplicate names rejected), pydantic argument validation, ToolContext injection
(alpaca/market/db; clear error when missing), error taxonomy (UnknownTool/ToolArgument/
ToolError), and schemas() JSON-schema export consumed directly by LLM function-calling
APIs. Four real tools registered: get_portfolio, get_latest, get_daily_bars,
compare_benchmark. `GET /api/tools` lists them. Adding a Phase-3+ capability is now a
one-decorator registration next to the function it wraps.
Verified: verify.py PASS — 75 passed, 3 skipped.
Next: T023 (fundamentals/news — needs live key checks, best from owner's machine via
Antigravity) or T017 chore; after that Phase 2 needs a "should I buy X" briefing composer
(new ticket to write) to hit the spec §7.2 exit criterion.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T022 done (win/loss breakdown); committed Gemini's fix
Built: `analysis/portfolio.win_loss()` — winners/losers/flat counts, total_gain (>=0) and
total_loss (<=0) with natural signs, net, best/worst position. `/portfolio` now returns a
`win_loss` block ready for the dashboard's green/red chart.
Also: committed Gemini's Windows env fix (ccc5ec4) with attribution — it was left
uncommitted; reminder to all agents: commit before ending a session (AGENTS.md).
Verified: verify.py PASS — 67 passed, 3 skipped (68/68 on Windows per Gemini).
Next: T024 (tool-calling registry — biggest leverage, unblocks Phase 4) or T023
(fundamentals/news). T007 remaining: migrate + sync + open /portfolio once.
Blockers: none.

## 2026-08-11 — Gemini (Antigravity) — Windows subprocess env fix in test_db.py
Fixed: `backend/tests/test_db.py` `test_alembic_migration_matches_models` hardcoded `PATH: /usr/bin:/bin`
when spawning Alembic via `subprocess.run`, overriding `os.environ` completely and breaking Winsock / system DLL loading on Windows (`OSError: [WinError 10106]`). Updated to `{**os.environ, "DATABASE_URL": ...}` so system environment variables (PATH, SystemRoot) are preserved.
Verified: `python scripts/verify.py` passes all tests on Windows (68/68 passed).
Next: T022 (win/loss breakdown) or T024 (tool registry).
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T021 done (benchmark comparison)
Built: `analysis/benchmark.py` — strict inner-join date alignment (ValueError <2 overlaps,
message tells the user history accumulates via sync), normalized curves for charting,
per-series metrics (cum return, ann vol, ann Sharpe, max DD; vol/Sharpe None when <3
points), excess return. `data/history.py` — daily equity: last snapshot per day per
account, summed across accounts. `GET /api/benchmark?symbol=SPY&days=90`; DB DI via lazy
engine; 503 with migrate instructions when DB uninitialized; 409 when insufficient overlap.
Verified: verify.py PASS — 65 passed, 3 skipped.
Note: comparison quality grows with snapshot history — owner should run scripts/sync.py
daily (or --loop / Task Scheduler) once T007 is done.
Next: T022 (win/loss breakdown) — small; or T024 (tool registry) — bigger leverage.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T020 done (metrics library, Phase 2 started)
Built: `analysis/metrics.py` — daily_returns, cumulative_return, cagr, volatility, sharpe,
max_drawdown_frac. Conventions locked in the module docstring: values oldest-first and >0,
252 trading days/year, sqrt-annualization, rf/ppy per-period risk-free, drawdown as
positive magnitude, ValueError on any bad input (no silent garbage in a money pipeline).
Verified: verify.py PASS — 56 passed, 3 skipped. All 16 metric tests are hand-computed
known answers, independent of the implementation.
Next: T021 (benchmark comparison vs SPY — uses these metrics + account_snapshots +
market_data bars) or T022 (win/loss breakdown). T021 recommended first.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T015 done — PHASE 1 CODE-COMPLETE
Built: `analysis/portfolio.py` summarize() — totals, per-position returns, weights, sorted
by market value; duck-typed inputs keep analysis decoupled from broker clients. `GET
/portfolio` fetches account + positions live at request time (no cache presented as
current) and returns computed summary + per-position views + asof + source.
Verified: verify.py PASS — 40 passed, 3 skipped (live tests run on owner's machine).
Phase 1 exit criterion met in code; owner sign-off = T007 (quickstart + sync + /portfolio).
Promoted Phase 2 backlog: T020 metrics, T021 benchmark vs SPY, T022 win/loss, T023
fundamentals/news (evaluate owner's FMP/FRED keys), T024 tool registry, T017 chore.
Next: T020 (time-series metrics) — natural start for any agent.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T014 done (snapshot sync job)
Built: `data/sync.py` — sync_once() fetches live account + positions and writes timestamped
snapshot rows; ensure_account() is idempotent per (broker, external_id) — proven by test
(two syncs → one account row, two snapshots). `scripts/sync.py` CLI: one-shot default,
`--loop N` continuous; Windows Task Scheduler can call one-shot mode. AlpacaClient
AccountSnapshot now carries the broker account_number as external_id. README quickstart
gains migrate + sync commands.
Verified: verify.py PASS — 35 passed, 2 skipped.
Next: T015 — `GET /portfolio` (Phase 1 exit criterion). Owner: T007 quickstart + T005 push.
Blockers: none.

## 2026-08-11 — Claude (Cowork) — T013 done (database schema v1)
Built: SQLAlchemy 2 models — broker_accounts, account_snapshots, position_snapshots,
transactions (deduped per account by broker fill id); UTCDateTime TypeDecorator that
rejects naive datetimes on write and restores UTC on read (SQLite drops tzinfo);
`data/db.py` engine/session factory; settings gain `database_url` (DATABASE_URL env,
default repo-root SQLite per D007). First alembic migration `bee2b4896cdf` with a
migration-parity test (upgrade head must produce exactly the models' tables).
Gotchas fixed: alembic autogenerate emitted `data.models.UTCDateTime` without importing
it (normalized to `sa.DateTime` — identical DDL); ruff per-file-ignores for generated
migrations (style rules off, F-rules kept — they catch real bugs like that import).
Verified: verify.py PASS — 33 passed, 2 skipped.
Next: T014 (scheduled refresh job writing snapshots) then T015 closes Phase 1.
Owner: T007 quickstart + T005 push still open.
Blockers: none.

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
