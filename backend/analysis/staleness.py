"""Session-aware freshness (T036b, D018 remainder) — "stale" is the wrong word
for a Friday close read on a Saturday.

The wall-clock rule (age > 15 min = stale) is right during a session and
misleading outside one: a quote from Friday's close IS the last real print;
nothing newer exists. Traders need three states, not two:

- "live"          market open, event within MAX_LIVE_AGE
- "stale"         market OPEN but the event is old — the feed is behind, and a
                  recommendation on it is a real hazard
- "last_session"  market closed and the event is from the most recent session —
                  correct and current-as-possible; say when it's from
- "old"           market closed AND the event predates the last session by more
                  than a day — something is wrong with the feed

Pure functions; the caller supplies market state (broker clock) and times.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

MAX_LIVE_AGE_SECONDS = 900.0     # 15 min, matches MAX_DATA_AGE_SECONDS
LAST_SESSION_MAX_HOURS = 96      # Fri close -> Mon pre-open is ~63h; 4 days is generous


@dataclass(frozen=True)
class Freshness:
    state: str        # live | stale | last_session | old
    age_seconds: float
    age_human: str
    market_open: bool
    trustworthy: bool  # False = do not base a trade on this without saying why
    phrase: str        # narration-ready, e.g. "from the last session (2d 1h ago)"


def classify_freshness(exchange_ts: datetime, now: datetime, market_open: bool,
                       age_human: str | None = None) -> Freshness:
    """Three-state freshness. `age_human` lets callers reuse market_data's
    formatter; computed if omitted."""
    if exchange_ts.tzinfo is None or now.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    age = (now - exchange_ts).total_seconds()
    if age < 0:
        raise ValueError("exchange timestamp is in the future")
    if age_human is None:
        from data.market_data import human_age
        age_human = human_age(age)

    if market_open:
        if age <= MAX_LIVE_AGE_SECONDS:
            return Freshness("live", age, age_human, True, True,
                             f"live ({age_human} old)")
        return Freshness(
            "stale", age, age_human, True, False,
            f"STALE — the market is open but this print is {age_human} old; "
            "the feed is behind, do not treat it as the current price")
    if age <= LAST_SESSION_MAX_HOURS * 3600:
        return Freshness(
            "last_session", age, age_human, False, True,
            f"from the last session ({age_human} ago) — the market is closed, "
            "so this is the most recent real print")
    return Freshness(
        "old", age, age_human, False, False,
        f"OLD — {age_human} since the last print, longer than a normal market "
        "closure; check the data feed before relying on this")


def freshness_for(payload_asof: datetime, exchange_ts: datetime,
                  market_open: bool, age_human: str | None = None) -> Freshness:
    """Convenience: judge against the payload's own fetch time."""
    return classify_freshness(exchange_ts, payload_asof, market_open, age_human)


def wallclock_fallback(exchange_ts: datetime, now: datetime,
                       age_human: str | None = None) -> Freshness:
    """No broker clock available (no Alpaca in context): assume open during a
    plausible session window is NOT safe, so fall back to the conservative
    wall-clock rule and SAY the market state is unknown."""
    f = classify_freshness(exchange_ts, now, market_open=True,
                           age_human=age_human)
    unknown = "market state unknown (no broker clock) — "
    return Freshness(f.state, f.age_seconds, f.age_human, False,
                     f.trustworthy, unknown + f.phrase)


def next_session_hint(next_open: datetime, now: datetime) -> str:
    """'the market opens in 14h 20m' — for closed-market narration."""
    delta = next_open - now
    if delta < timedelta(0):
        return "the market should already be open — check the broker clock"
    from data.market_data import human_age
    return f"the market opens in {human_age(delta.total_seconds())}"
