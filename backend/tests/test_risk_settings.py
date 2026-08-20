"""T115 — risk limits from settings: the T033 promise, validated loudly."""

import pytest

from risk.engine import RiskLimits
from settings import KuberaSettings


def test_defaults_cannot_drift_apart():
    """Settings defaults MUST mirror RiskLimits defaults — pinned here so a
    change to one without the other fails a test instead of surprising the
    owner's rails."""
    s = KuberaSettings(_env_file=None)
    from_settings = RiskLimits.from_settings(s)
    assert from_settings == RiskLimits()


def test_env_values_flow_through(monkeypatch):
    monkeypatch.setenv("KUBERA_MAX_BUYS_PER_DAY", "2")
    monkeypatch.setenv("KUBERA_DAILY_LOSS_LIMIT_FRAC", "0.02")
    monkeypatch.setenv("KUBERA_COOLDOWN_HOURS", "48")
    limits = RiskLimits.from_settings(KuberaSettings(_env_file=None))
    assert limits.max_buys_per_day == 2
    assert limits.daily_loss_limit_frac == pytest.approx(0.02)
    assert limits.cooldown_hours == pytest.approx(48.0)
    assert limits.max_position_frac == pytest.approx(0.20)  # untouched default


def test_bad_env_values_refuse_loudly_with_the_range():
    s = KuberaSettings(_env_file=None, risk_max_buys_per_day=0)
    with pytest.raises(ValueError, match=r"max_buys_per_day must be in \[1, 100\]"):
        RiskLimits.from_settings(s)
    s = KuberaSettings(_env_file=None, risk_daily_loss_limit_frac=1.5)
    with pytest.raises(ValueError, match="daily_loss_limit_frac"):
        RiskLimits.from_settings(s)
    s = KuberaSettings(_env_file=None, risk_per_trade_frac=0.5)
    with pytest.raises(ValueError, match="risk_per_trade_frac"):
        RiskLimits.from_settings(s)  # >5% per trade isn't sizing, it's gambling
