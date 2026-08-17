"""T102 — Schwab confirmation parser (D026).

The fixtures are the owner's REAL confirmations, put through `redact()` and
audited for account numbers, long digit runs and address-shaped lines before
being committed. The repo is public, so the rule is: the parser is tested
against his true layout, never against his true identity.

`multi_trade_day.txt` is a regression fixture with a purpose. The first version
of this parser used a fixed 4-line lookahead to find an option's expiry and
strike. These are DAILY confirmations carrying every trade of the day, so that
window reached into the NEXT trade and tagged a SCHD equity purchase at $30.81
as a 180-strike put. Nothing complained — 0 unparsed, plausible totals — and it
only surfaced when the per-file fills were read one by one. That is the whole
argument for reconciliation over "it ran".
"""

from datetime import date
from pathlib import Path

import pytest

from data.statements import (
    OPTION_MULTIPLIER,
    header_trade_date,
    merge,
    parse_confirmation,
    redact,
)

FIXTURES = Path(__file__).parent / "fixtures" / "schwab"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ------------------------------------------------------- the trade-date trap

def test_trade_date_comes_from_the_header_not_the_row():
    """The row shows 03/03 for a trade executed 03/02 — that is the SETTLE date.

    Taking the row date would shift every fill forward a day or two and quietly
    corrupt holding periods, day-of-week patterns and post-loss timing.
    """
    report = parse_confirmation(load("equity_single.txt"), "equity_single.txt")
    fill = report.fills[0]
    assert fill.trade_date == date(2026, 3, 2)     # header
    assert fill.settle_date == date(2026, 3, 3)    # row
    assert fill.settle_date > fill.trade_date


def test_no_header_date_is_refused_not_defaulted():
    report = parse_confirmation("Purchase XLE  SOMETHING   25   56.59", "x.txt")
    assert report.fills == []
    assert "refusing to fall back" in report.unparsed[0]["why"]


def test_header_date_parses_the_long_form():
    assert header_trade_date("blah March 2, 2026 blah") == date(2026, 3, 2)
    assert header_trade_date("no date here") is None


# ------------------------------------------------------- equity vs option

def test_equity_row_is_read_exactly():
    fill = parse_confirmation(load("equity_single.txt")).fills[0]
    assert fill.symbol == "XLE"
    assert fill.side == "buy"
    assert fill.qty == 25
    assert fill.price == 56.59
    assert fill.asset_type == "equity"
    assert fill.option_strike is None
    assert fill.notional == pytest.approx(25 * 56.59)   # no multiplier


def test_option_rows_carry_expiry_strike_and_right():
    fills = parse_confirmation(load("multi_trade_day.txt")).fills
    opts = [f for f in fills if f.asset_type == "option"]
    assert opts, "fixture must contain option rows"
    for o in opts:
        assert o.option_expiry is not None
        assert o.option_strike is not None
        assert o.option_right in {"put", "call"}


def test_option_notional_applies_the_contract_multiplier():
    """One contract at $0.89 is $89 of exposure, not $0.89. Forgetting this
    understates every option position by 100x — and 147 of 250 fills are options."""
    o = next(f for f in parse_confirmation(load("multi_trade_day.txt")).fills
             if f.asset_type == "option")
    assert o.notional == pytest.approx(o.qty * o.price * OPTION_MULTIPLIER)
    assert OPTION_MULTIPLIER == 100


# ------------------------------------------------------- the regression

def test_equity_row_is_not_contaminated_by_a_later_option(monkeypatch):
    """THE BUG THIS FIXTURE EXISTS FOR.

    A daily confirmation holds several unrelated trades. An unbounded lookahead
    stole the next trade's option details and labelled an equity ETF purchase a
    put. Assert on the shape that made it obvious: nothing priced like a share
    may be classified as an option.
    """
    fills = parse_confirmation(load("multi_trade_day.txt")).fills
    equities = [f for f in fills if f.asset_type == "equity"]
    assert equities, "fixture must contain at least one equity row"
    for f in equities:
        assert f.option_strike is None and f.option_right is None

    # And the converse: no "option" with an equity-sized quantity AND price.
    for f in fills:
        if f.asset_type == "option":
            assert not (f.qty > 50 and f.price > 25), (
                f"{f.symbol} {f.qty}@{f.price} looks like shares, tagged as an option"
            )


def test_several_fills_per_document():
    """Same-day round trips arrive as separate rows on one document; a parser
    returning 'the' trade per file loses half of them."""
    report = parse_confirmation(load("multi_trade_day.txt"))
    assert len(report.fills) >= 5
    assert {f.side for f in report.fills} == {"buy", "sell"}


def test_nothing_is_dropped_silently():
    for name in ("equity_single.txt", "multi_trade_day.txt"):
        assert parse_confirmation(load(name), name).unparsed == []


# ------------------------------------------------------- merge + privacy

def test_merge_orders_by_trade_date():
    a = parse_confirmation(load("equity_single.txt"), "a")
    b = parse_confirmation(load("multi_trade_day.txt"), "b")
    m = merge([b, a])
    assert m.files_read == 2
    dates = [f.trade_date for f in m.fills]
    assert dates == sorted(dates)
    assert "2 files" in m.summary()


def test_redact_removes_identity():
    dirty = (
        "Schwab One® Account of JOHN Q PUBLIC\n"
        "  1234 EXAMPLE LOOP APT 5678\n"
        "Account Number 1234-5678\n"
        "78245-5243\n"
        "Purchase XLE  DESC   25   56.59\n"
    )
    clean = redact(dirty)
    assert "1234-5678" not in clean
    assert "JOHN Q PUBLIC" not in clean
    assert "78245-5243" not in clean
    assert "Purchase XLE" in clean            # the trade data survives


def test_committed_fixtures_contain_no_identity():
    """A guard on the repository itself, not just on the function."""
    import re

    for f in FIXTURES.glob("*.txt"):
        text = f.read_text(encoding="utf-8")
        assert not [h for h in re.findall(r"\b\d{4}-\d{4}\b", text) if h != "0000-0000"]
        assert not [h for h in re.findall(r"\b\d{6,}\b", text) if h != "000000"]
