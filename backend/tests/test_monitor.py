"""T087a — open-trade monitor: every check fires only when it should,
every blind spot is named, and the summary's exit code is schedulable."""

from analysis.monitor import (
    CHURN_CROSSINGS,
    NEAR_INVALIDATION_ATR,
    RVOL_COLLAPSE_BELOW,
    check_position,
    summarize,
)


def _check(price=100.0, **over):
    base = dict(
        daily_regime="trending_up",
        session_rvol=1.2, rvol_sessions_used=5,
        vwap_crossings=1,
        invalidation_level=95.0, invalidation_reason="swing low 95.00",
        atr_value=2.0,
        open_event_windows=[],
    )
    base.update(over)
    return check_position("spy", price, **base)


def test_rvol_collapse_fires_only_under_breakout_thesis():
    quiet = check_position("SPY", 100.0, daily_regime="range_bound",
                           session_rvol=0.3, rvol_sessions_used=5,
                           vwap_crossings=0, invalidation_level=None,
                           invalidation_reason="", atr_value=None,
                           open_event_windows=[])
    assert not any(a.kind == "rvol_collapse" for a in quiet.alerts)

    breakout = check_position("SPY", 100.0, daily_regime="breakout_watch",
                              session_rvol=RVOL_COLLAPSE_BELOW - 0.1,
                              rvol_sessions_used=5, vwap_crossings=0,
                              invalidation_level=None,
                              invalidation_reason="", atr_value=None,
                              open_event_windows=[])
    hits = [a for a in breakout.alerts if a.kind == "rvol_collapse"]
    assert len(hits) == 1 and hits[0].severity == "alert"
    assert "0.60x" in hits[0].detail and "5 prior sessions" in hits[0].detail


def test_churn_watch_at_the_line_and_quiet_below_it():
    churny = _check(vwap_crossings=CHURN_CROSSINGS)
    assert any(a.kind == "vwap_churn" and a.severity == "watch"
               for a in churny.alerts)
    calm = _check(vwap_crossings=CHURN_CROSSINGS - 1)
    assert not any(a.kind == "vwap_churn" for a in calm.alerts)


def test_invalidation_hit_near_and_far():
    # price 94 <= level 95 -> HIT (alert, names the new-decision rule)
    hit = _check(price=94.0)
    kinds = {a.kind: a for a in hit.alerts}
    assert kinds["invalidation_hit"].severity == "alert"
    assert "journal it" in kinds["invalidation_hit"].detail
    # price 95.8, level 95, ATR 2 -> 0.4 ATR above -> NEAR (watch)
    near = _check(price=95.8)
    kinds = {a.kind: a for a in near.alerts}
    assert kinds["invalidation_near"].severity == "watch"
    assert "0.40 ATR" in kinds["invalidation_near"].detail
    # price 100, level 95, ATR 2 -> 2.5 ATR above -> quiet
    far = _check(price=100.0)
    assert not any(a.kind.startswith("invalidation") for a in far.alerts)
    assert NEAR_INVALIDATION_ATR == 0.5  # the tested line IS the shipped line


def test_event_windows_surface_as_watches_never_instructions():
    c = _check(open_event_windows=["FOMC decision 2026-09-16 in 1 day",
                                   "CPI release tomorrow"])
    ev = [a for a in c.alerts if a.kind == "event_window"]
    assert len(ev) == 2 and all(a.severity == "watch" for a in ev)
    assert all("not an instruction" in a.detail for a in ev)


def test_blind_spots_are_named_never_crashes():
    c = check_position("nvda", None, daily_regime="breakout_watch",
                       session_rvol=None, rvol_sessions_used=0,
                       vwap_crossings=None, invalidation_level=None,
                       invalidation_reason="", atr_value=None,
                       open_event_windows=[])
    assert c.symbol == "NVDA" and c.alerts == []
    joined = " ".join(c.notes)
    assert "RVOL unavailable" in joined
    assert "churn check could not run" in joined
    assert "no invalidation level" in joined
    assert len(c.notes) == 3


def test_regime_labels_carry_their_lens_i033():
    """Owner's first live run: 'trending_up' beside a -1.58% week read like
    a wrong prediction. Labels now carry their timeframe, always."""
    from analysis.monitor import describe_regime
    assert describe_regime("trending_up") == \
        "trending_up (daily structure - a weeks-to-months lens)"
    assert "SESSION lines" in describe_regime("breakout_watch")
    assert describe_regime(None) == \
        "unknown (thin history - no structural read)"
    # and the short lens rides on the check itself, next to the label
    c = _check(week_change_frac=-0.0158)
    assert c.week_change_frac == -0.0158
    assert _check().week_change_frac is None          # absent stays honest


def test_summary_exit_code_is_schedulable():
    burning = _check(price=94.0)                       # invalidation_hit
    watchy = _check(vwap_crossings=CHURN_CROSSINGS)    # watch only
    s = summarize([burning, watchy])
    assert (s.positions, s.alerts, s.exit_code) == (2, 1, 1)
    assert s.watches >= 1 and "advisory only" in s.note
    calm = summarize([_check()])
    assert calm.exit_code == 0 and calm.alerts == 0
