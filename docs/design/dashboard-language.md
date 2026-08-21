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

## Tokens (v3, T157e — crypto-admin's skin_color.css owns the final word)
The owner said "more like the crypto-admin page" — and this time its CSS was
fetchable: `bs5/main/css/skin_color.css` gave the dark-skin palette verbatim.
Field `#0c1a32`, surfaces `#112547`/`#162f5b`/`#1b3a70`/`#254f99`/`#2a5aad`,
hairlines `rgba(255,255,255,0.12)`, text `#b5b5c3`/headings `#bdd1f8`/icons
`#8cade4`/muted `#566f9e` — and THE accent is amber `#ffa800` (their skin even
forces chart series to it: `.chart g [fill] {fill:#ffa800!important}`).
Applied: blue-navy glass field with amber/blue glows; ramp mapped to
`#E9EEF9`/`#BDD1F8`/`#8CADE4`/`#566F9E`/`#4C6390`; amber `#FFA800` = brand,
watch, days lens, the "you" chart line, budget bar (`→#FFD166`); their link
blue `#4F80D5` = interaction (focus, utilization, speaking state); orb states
amber/light-blue/deep-blue/bright-blue. buck-net's greens/reds stay for
gain/loss (`#02C751`/`#F52C38` — crypto-admin leaves semantics to Bootstrap).
Their IBM Plex/Rubik webfonts are NOT adopted (no CDN, D039) — system stack.

## Tokens (v2, T157d — superseded by v3 above, kept for the record)
Round two of references was minable: **buck-net's tailwind.config.js**
(github.com/jbrz0/buck-net — the shot the owner called "what I was looking
for") gave its literal palette; ha-component-kit supplied the glass-card
language; trading-vault the widget anatomy. The crypto-admin template page
and the glasshome blog are client-rendered (empty fetch) — noted, not
guessed at.

- Field: `#05050F` base with fixed radial glows (purple `#7517F8` @16%,
  blue `#007DF1` @13%, teal `#00F1E7` @7%) — glass needs light to refract
- Glass cards: `rgba(20,20,43,0.55)` + `backdrop-filter: blur(14px)` +
  border `rgba(146,146,193,0.16)` + inset top highlight; radius 14px
- Solids: `#0D0D1E` (sidebar), translucent `rgba(13,13,30,0.72)` (topbar)
- Text: `#EDEDF7` primary / `#C7C9E2` values / `#9292C1` labels /
  `#5A5A89` muted / `#565677` asof lines  (buck-net's gray ramp)
- Roles — one hue per JOB: **amber `#FFB524` = brand** (wordmark, orb idle,
  active row, checkbox) · **teal `#00F1E7` = data** (the "you" chart line,
  days lens, listening state) · **blue `#007DF1` = interaction** (focus,
  utilization, budget-bar gradient start, speaking state) · purple
  `#7517F8` = thinking state
- Semantics: gain `#02C751` · loss `#F52C38` · watch `#FFB524` ·
  stale `#FF5924` · benchmark/neutral `#5A5A89`
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
