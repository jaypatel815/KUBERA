# Owner's trading doctrine: regimes, ranges, and the no-trade condition

*Source: product owner (Chotu), 2026-08-12. This is domain spec for tickets T050–T056.
Agents implementing those tickets: read this first — the acceptance criteria live here.*

## Vocabulary (day/market types KUBERA must recognize)

- **Consolidation** — price in a relatively narrow range while the market waits for a catalyst.
- **Sideways / range-bound** — oscillation around the same price rather than a clear trend.
- **Low-volume consolidation** — low trading volume + narrow range + no major catalyst (the key regime).
- **Market equilibrium** — buying/selling pressure balanced.
- **Quiet / low-volatility environment** — the broad-market version of the above.

## The framework: first determine what kind of day it is

| Day type | Signals | Playbook |
|---|---|---|
| **Trending** | higher highs/lows (or lower/lower), rising volume, price holding above/below VWAP, strong momentum | momentum / trend-following |
| **Consolidation** | repeated rejection at the same upper/lower levels, lower volume, oscillation around VWAP, no catalyst, narrowing range | range strategy — or wait |
| **Breakout** | price escapes the established range, volume suddenly expands, price HOLDS outside the prior range | breakout strategy |

## Range trading

- Identify the range: repeated rejections define support and resistance.
- Trade the edges, not the middle: support → long → resistance; (resistance → short → support).
- The middle of the range is where risk/reward is worst.

## Volume is the referee

- **RVOL (relative volume)**: today's volume at this point vs the stock's own typical volume
  by the same point. Low RVOL = market not interested.
- **False breakouts**: `$100 → $106 → $99` on weak volume is a fakeout, not a breakout.
  Never trust a range escape without volume confirmation.
- The pattern that matters: low volume → consolidation → **volume expansion** → breakout.

## VWAP

- Rough session "fair price" weighted by volume.
- Price repeatedly crossing VWAP without holding a side = no trend = be selective.

## The no-trade condition (as important as any strategy)

Low volume + tiny range + no catalyst + poor risk/reward ⇒ **"There isn't a trade today."**
Preserving capital is a legitimate trading decision. Overtrading — taking setups whose
expected move doesn't clear spreads/fees/slippage — is the biggest enemy.

## Options caveat (recorded, deliberately out of scope for now)

Sideways markets: stock range-trading can work; LONG options usually lose (theta decay,
IV crush, no movement) even when the price thesis is right; SHORT options can suit low-vol
regimes but carry categorically different risk. KUBERA must at minimum WARN about
theta/IV when options come up in low-vol regimes. Full options analytics = future phase.

## Data-honesty constraint (D006)

Our free IEX feed samples a small fraction of consolidated volume. RVOL computed against
the stock's own IEX history is valid as a relative measure; absolute volume statements and
precise VWAP require the paid SIP feed. Every regime/volume output must label its feed.
