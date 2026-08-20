"""T085b — fractional-Kelly ADVISORY view. Hand-computed; D017 respected."""

import pytest

from risk.sizing import (
    KELLY_ADVISORY_CAP,
    KELLY_MIN_SAMPLES,
    fractional_kelly_view,
)


def test_hand_computed_kelly():
    # w=0.54, R=1.8  ->  f* = 0.54 - 0.46/1.8 = 0.284444...
    # quarter-Kelly  = 0.0711..., under the 10% cap.
    v = fractional_kelly_view(0.54, 1.8, 120)
    assert v.available and v.why is None
    assert v.full_kelly_frac == pytest.approx(0.54 - 0.46 / 1.8)
    assert v.advisory_frac == pytest.approx((0.54 - 0.46 / 1.8) / 4)
    assert "advisory" in v.note and "unchanged" in v.note


def test_negative_kelly_is_reported_not_hidden():
    # w=0.40, R=1.0 -> f* = 0.40 - 0.60 = -0.20: the distribution argues
    # for NO position. The full number stays visible; advisory floors at 0.
    v = fractional_kelly_view(0.40, 1.0, 200)
    assert v.available
    assert v.full_kelly_frac == pytest.approx(-0.20)
    assert v.advisory_frac == 0.0


def test_cap_binds_on_extreme_numbers():
    # w=0.80, R=4 -> f* = 0.80 - 0.05 = 0.75; quarter = 0.1875 -> capped 0.10.
    v = fractional_kelly_view(0.80, 4.0, 500)
    assert v.full_kelly_frac == pytest.approx(0.75)
    assert v.advisory_frac == pytest.approx(KELLY_ADVISORY_CAP)


def test_refusals_are_named():
    thin = fractional_kelly_view(0.6, 2.0, KELLY_MIN_SAMPLES - 1)
    assert not thin.available and "thin history" in thin.why
    one_sided = fractional_kelly_view(0.6, None, 100)
    assert not one_sided.available and "one-sided" in one_sided.why
    bad_w = fractional_kelly_view(1.0, 2.0, 100)
    assert not bad_w.available and "outside (0, 1)" in bad_w.why
    empty = fractional_kelly_view(None, None, None)
    assert not empty.available and "0 samples" in empty.why
