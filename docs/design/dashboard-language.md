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

## Tokens (v4, T157f — THE OWNER'S SCREENSHOT is the source of truth)
The owner posted a screenshot of the exact index36 look he wants — the first
pixel ground truth of this phase — and corrected the record: index36 is the
BLACK + VIOLET variant of the template family, not the blue dark-skin its
generic skin_color.css describes (v3 below was that wrong variant, kept for
the record). From the image:

- Field: `#050507` near-black with faint violet radial glows
- Cards: matte `#0D0D13`, border `rgba(255,255,255,0.07)`, **radius 20**;
  inset sub-boxes `#15151C` radius 12 with corner ↗ buttons
- HERO card: violet gradient `linear-gradient(135deg,#8C7CF8,#5B49C9)` —
  one highlighted stat card per row (Equity)
- Accent: violet `#8C7CF8` / light `#A99BFB` / deep `#6D5BE2`; gradient
  `#A08BFC→#6D5BE2` on logo, avatar, budget bar, active range pill
- Text: `#FFFFFF` values / `#E4E4EC` body / `#8E8E9A` labels / `#5E5E6A` fine
- Semantics: gain `#34C77B` (badge bg 12% alpha) · loss `#FF5063` ·
  stale `#FF7A45`
- Chrome: pill nav in the top bar (rounded container, active pill filled),
  round icon buttons (bell = the T147 notification toggle, relocated),
  user chip with gradient avatar
- Chart: violet line with gradient area fill, gray benchmark, floating
  tooltip; range pills 1M/3M/6M drive the real /api/benchmark days param
- Behaviors mapped to REAL data: three views (Account Overview / Trading
  Overview / Transactions) on the pill nav; status pills from /api/risk and
  /api/monitor; corner ↗ arrows SEND a question to KUBERA in the dock;
  history tables from /api/conversations and /api/household
- Their 3D illustrations: not reproduced (no assets, no CDN) — icon chips
  stand in. Webfonts still not adopted (system stack).

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
