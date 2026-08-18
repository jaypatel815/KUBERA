"""T111 — market-day boundaries (owner-reported).

The founding case is verbatim from the owner: at 11:11 PM Eastern on August
17th, KUBERA said "today" was August 18th — because UTC had already rolled
over. Every test here is a fixed instant, no clocks.
"""

from datetime import date, datetime, timezone

import pytest

from analysis.market_time import MARKET_TZ, market_day_start_utc, market_today


def test_the_owners_exact_instant():
    """2026-08-18T03:11Z is 11:11 PM EDT on the 17th. The market day is the 17th."""
    now = datetime(2026, 8, 18, 3, 11, tzinfo=timezone.utc)
    assert market_today(now) == date(2026, 8, 17)


def test_summer_boundary_is_4am_utc():
    """EDT is UTC-4: the market day flips at exactly 04:00Z."""
    assert market_today(datetime(2026, 8, 18, 3, 59, tzinfo=timezone.utc)) == date(2026, 8, 17)
    assert market_today(datetime(2026, 8, 18, 4, 0, tzinfo=timezone.utc)) == date(2026, 8, 18)


def test_winter_boundary_is_5am_utc():
    """EST is UTC-5 — the ZONE handles the flip; a pinned -4 offset would not."""
    assert market_today(datetime(2026, 1, 16, 4, 59, tzinfo=timezone.utc)) == date(2026, 1, 15)
    assert market_today(datetime(2026, 1, 16, 5, 0, tzinfo=timezone.utc)) == date(2026, 1, 16)


def test_day_start_utc_is_midnight_at_the_market():
    """At the owner's instant, the market day began at 2026-08-17T04:00Z —
    midnight EDT — which is the boundary DB window queries need."""
    now = datetime(2026, 8, 18, 3, 11, tzinfo=timezone.utc)
    start = market_day_start_utc(now)
    assert start == datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc)
    # and it really is midnight on the venue's clock
    local = start.astimezone(MARKET_TZ)
    assert (local.hour, local.minute) == (0, 0)
    assert local.date() == date(2026, 8, 17)


def test_winter_day_start_is_5am_utc():
    now = datetime(2026, 1, 16, 3, 0, tzinfo=timezone.utc)   # 10 PM EST Jan 15
    assert market_day_start_utc(now) == datetime(2026, 1, 15, 5, 0, tzinfo=timezone.utc)


def test_naive_datetime_is_refused():
    """Every KUBERA timestamp is tz-aware; a naive one here would silently
    mean 'whatever zone the host is in', which is the bug class this ends."""
    with pytest.raises(ValueError, match="naive"):
        market_today(datetime(2026, 8, 18, 3, 11))


def test_default_now_agrees_with_explicit_now():
    """The no-argument path uses the same conversion as the explicit path."""
    explicit = market_today(datetime.now(timezone.utc))
    assert market_today() in (explicit, explicit)  # same call, moments apart
