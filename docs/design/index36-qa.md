# T157g visual QA — KUBERA vs the index36 reference (owner's screenshot)

Method: structural comparison of the built page against the owner's
2600x1336 screenshot. The agents cannot render a browser in the sandbox —
every ✅ below is verified in code/geometry; items marked 👁 are exactly
what the OWNER must eyeball on refresh. This checklist is the Phase-5
contract from the approved brief.

- [x] Overall layout — header → hero strip → 2 card rows → chat FAB; no
      left sidebar (history is a summoned drawer, as their icon chips imply)
- [x] Header — 64px, logo + name left, 4 amber icon chips, search-shaped
      command box + 4 icon chips right, 24px page padding
- [x] Sidebar/navigation — reference has none fixed; our secondary views
      hang off the two right icon chips (approved deviation, function kept)
- [x] Content width — full-bleed, 24px margins, 20px gutters
- [x] Grid — row 1 = 4 / 2.6 / 1.4 / 3 fr (VISA-card / income stack /
      circles / chart column); row 2 = 4.6 / 2.4 / 2.4 fr
- [x] Card sizes — row 1 ≈ 250px class, row 2 ≈ 330px class (content-driven)
- [x] Spacing — 20px card padding, 14px inset padding, 8-10px stacks
- [x] Typography — IBM Plex Sans body / Rubik headings via local @font-face
      (falls back to system until `python scripts/fetch_fonts.py` runs once);
      root 14px, values 19-24 bold tabular, labels 12 gray, hero 34/25
- [x] Colors — #050505 body, #0B0B0E cards, #14141A insets, #17171B chips,
      amber #FFA800 sole accent, white pills w/ black text, green/red deltas
- [x] Borders — hairlines at rgba(255,255,255,0.05), effectively borderless
- [x] Radii — 18 cards / 14 insets / 12 chips / 999 pills+circles
- [x] Shadows — none on cards (matte, contrast elevation); FAB glow only
- [x] Icons — 40px rounded-square chips, amber glyphs; amber circle buttons
- [x] Charts — amber area sparkline (gradient fill), loss-budget donut,
      nested allocation circles (their Yearly-profits viz), P&L mini bars
- [x] Tables — Conversations + Debts in their Trading-History style
- [x] Responsive — 4→2→1 columns at 1200/760px; hero collapses; drawer
      goes full-width on phones
- [ ] 👁 Pixel judgment — hero type scale, mic-circle proportion, card
      heights against the screenshot: the owner's eyes are the gate
- [ ] 👁 Font fidelity — after fetch_fonts.py, confirm Plex/Rubik render

Known deviations (named, approved or unavoidable):
1. Their 3D illustrations (coins/plant) — no assets to take; icon chips
   and real charts occupy those slots.
2. Their demo right-edge panel switcher — template chrome, excluded.
3. Their Visa masked number — replaced by real equity (a fake mask on a
   money app would be theater).
4. Secondary views (Trading Overview / Transactions) — reference is a
   single page; ours keep T157f functionality behind header icon chips
   (approved).
