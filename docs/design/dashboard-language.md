# KUBERA dashboard design language (T157a, D039)

## Provenance — read this first
The owner sent six references and the direction "neat, and not just an Orb":

1. dribbble.com/shots/27667139 — FundNova Prop Trading Firm Dashboard
2. dribbble.com/shots/27649056 — Prop Trading Dashboard / Fintech Platform UI
3. dribbble.com/shots/25178389 — Fundcy Finance Dashboard
4. dribbble.com/shots/27130049 — Personal Finance Landing Page
5. dribbble.com/shots/25063010 — ASTX Investment App
6. dribbble.com/shots/22297284 — Personal AI Buddy App / AI Chatbot

Dribbble pages are client-rendered; a text fetch returns an empty shell, and
the owner's Chrome extension was not connected when this was written — so
NOBODY pixel-inspected these shots from the sandbox. This language is derived
from the genre these six titles name (dark fintech/prop-trading dashboards +
AI-companion chat) plus KUBERA's existing brand. **The acceptance gate is the
owner's eyes**: he renders v1 against his references and corrects; this doc
updates with each correction rather than pretending it was right first.

## The genre, distilled
Dark near-black canvas; content lives on **cards** (soft radius, hairline
border, faint inner glow) not on the page; ONE accent color doing all the
talking; big-number KPIs with small delta chips; charts as thin-line areas
with gradient fills; navigation quiet and monochrome; the AI presence is a
**docked companion**, not the centerpiece.

## Tokens
- Canvas: `#07070c` (page) / `#0d0d14` (card base) / `#12121c` (card hover)
- Hairlines: `#1a1a24`; inset dividers `#14141c`
- Text: `#e8e4d8` (primary) / `#c8c4b4` (values) / `#8a815f` (labels,
  uppercase 10px tracked) / `#55503e` (fine print) / `#3a3830` (asof lines)
- Accent — **KUBERA gold `#c9a227`**, kept from the Orb (brand continuity
  beats the genre's neon lime; one accent, used sparingly: active states,
  the "you" line in charts, the wordmark)
- Semantics: gain `#5aaa88` · loss `#b07070` · watch `#a89050` ·
  benchmark/neutral `#8b8fa3` — all pre-existing, unchanged
- Radius 12px cards / 999px chips; card padding 14–16px
- Type: system stack (no webfonts — no CDN, D039); KPI values 22–26px
  tabular; labels 10px uppercase +1px tracking

## Card anatomy (every card, no exceptions)
label (uppercase, quiet) → value (big) → delta/context chip → **asof line**.
The asof line is not decoration: a number without its timestamp does not ship
(AGENTS.md priority 1). Stale manual data says "as you told me on DATE".

## Layout
Top bar (wordmark + paper-account tag + date) · left: existing conversation
history drawer (toggle) · center: KPI row (auto-fit grid) then card grid
(performance, open-trade monitor, household, positions) · right: the
**conversation dock** — the Orb shrunk to a companion (canvas CSS-scaled,
voice loop byte-identical), log, input, confirm-this-turn.

## Hard rules carried from doctrine
- No CDN, single self-contained file, hand-drawn canvas charts (pinned by
  test since T143).
- All API text through `esc()` before innerHTML.
- Money endpoints never cached (sw.js, pinned).
- Degradations render as NAMED text in the card, never blank space.
