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
    ParsedFill,
    ParseReport,
    dedupe_daily_documents,
    dedupe_statement_fills,
    header_trade_date,
    is_us_market_holiday,
    merge,
    parse_confirmation,
    parse_statement_transactions,
    prior_business_day,
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


# ------------------------------------------------------- T108: monthly refusal,
# wrapped option legs, duplicate daily documents

def test_monthly_statement_is_refused_not_double_counted():
    """A monthly statement's transaction rows LOOK like confirmation rows in
    layout extraction, and every trade in it also has a confirmation — parsing
    both counts each fill twice. Detection is content-based ('Statement
    Period' appears in all 5 real statements and none of 86 confirmations)."""
    text = (
        "March 31, 2026\n"
        "Account Number      Statement  Period\n"
        "****-*711           March   1-31, 2026\n"
        "03/25  Purchase   SPY   DESCRIPTION HERE   3   0.45\n"
    )
    rep = parse_confirmation(text, "renamed_download.pdf")
    assert rep.fills == []
    assert "monthly account statement" in rep.unparsed[0]["why"]

    # Filename is the second line of defence, for statements saved without a
    # text layer match.
    rep2 = parse_confirmation("March 31, 2026\nno marker here",
                              "Brokerage Statement_2026-03-31.PDF")
    assert rep2.fills == []
    assert "monthly account statement" in rep2.unparsed[0]["why"]


def test_wrapped_option_leg_is_still_an_option():
    """Long descriptions wrap: '$656' ends the row line and 'Call' lands on the
    next with the expiry column interleaved, so the contiguous pattern misses.
    The broker's own '656.00 C' identity column resolves it. On a real
    confirmation this row was silently misread as 3 SHARES of SPY at $0.45."""
    text = (
        "March 24, 2026\n"
        "03/25  Purchase  SPY  State Street SPDR S&P 500 ETF Trust 03/24/2026 $656   3   0.45\n"
        "                 03/24/2026   Call\n"
        "                 656.00 C     Commission 1.95 / Industry Fee 0.04\n"
    )
    rep = parse_confirmation(text, "wrapped.pdf")
    assert len(rep.fills) == 1
    f = rep.fills[0]
    assert f.asset_type == "option"
    assert f.option_strike == 656.0
    assert f.option_right == "call"
    assert str(f.option_expiry) == "2026-03-24"
    assert f.notional == 135.0            # 3 contracts * 0.45 * 100, not 3 shares


def test_incomplete_option_evidence_fails_closed_not_as_equity():
    """Identity column present but no full expiry date anywhere: booking this
    as equity would be silently 100x wrong, so it must be REPORTED instead."""
    text = (
        "March 24, 2026\n"
        "03/25  Purchase  SPY  State Street SPDR Trust   3   0.45\n"
        "                 656.00 C     Commission 1.95\n"
    )
    rep = parse_confirmation(text, "torn.pdf")
    assert rep.fills == []
    assert any("refusing to classify as equity" in u["why"] for u in rep.unparsed)


def _report_with(fills):
    return ParseReport(fills=list(fills), files_read=1)


def _pf(source, symbol="AAPL", qty=1.0, price=3.0, day=30):
    from datetime import date as _date
    return ParsedFill(
        trade_date=_date(2026, 4, day), settle_date=None, symbol=symbol, side="buy",
        qty=qty, price=price, description="d", asset_type="equity", source_file=source,
    )


def test_identical_daily_documents_are_deduped():
    """Schwab's daily confirmation lists EVERY trade of the day; saving it once
    per trade multi-counts the whole day. On the owner's real folder this
    inflated 250 'fills' to 3x-counted days (47 duplicate files)."""
    a = _report_with([_pf("a.pdf"), _pf("a.pdf", symbol="NVDA", qty=60, price=200.7)])
    b = _report_with([_pf("b.pdf"), _pf("b.pdf", symbol="NVDA", qty=60, price=200.7)])
    out = merge(dedupe_daily_documents([a, b]))
    assert len(out.fills) == 2                       # one day's trades, once
    assert len(out.duplicates) == 1
    assert "duplicate download" in out.duplicates[0]["why"]
    assert out.files_read == 2                       # both files still counted as read


def test_subset_download_is_dropped_for_the_superset():
    early = _report_with([_pf("early.pdf")])                          # intraday download
    late = _report_with([_pf("late.pdf"), _pf("late.pdf", symbol="NVDA")])  # end of day
    out = merge(dedupe_daily_documents([early, late]))
    assert {f.source_file for f in out.fills} == {"late.pdf"}
    assert "partial duplicate (subset)" in out.duplicates[0]["why"]


def test_overlapping_documents_are_kept_and_reported():
    """Overlap without nesting cannot be resolved mechanically — keep both,
    say so loudly, never guess."""
    a = _report_with([_pf("a.pdf"), _pf("a.pdf", symbol="NVDA")])
    b = _report_with([_pf("b.pdf"), _pf("b.pdf", symbol="TSLA")])
    out = merge(dedupe_daily_documents([a, b]))
    assert len(out.fills) == 4                       # nothing dropped
    assert any("OVERLAPPING" in u["why"] for u in out.unparsed)


def test_different_days_are_never_deduped():
    a = _report_with([_pf("a.pdf", day=29)])
    b = _report_with([_pf("b.pdf", day=30)])
    out = merge(dedupe_daily_documents([a, b]))
    assert len(out.fills) == 2
    assert out.duplicates == []


# ------------------------------------------------------- T108b: statement transaction parsing
# and deduplication against confirmations

def test_parse_statement_transactions_equity_and_option():
    text = (
        "Statement Period March 1-31, 2026\n"
        "Transaction Details\n"
        "03/20  Purchase  NVDA  NVIDIA CORP 03/20/2026 $177.5 Call   6.0000   0.1000   60.00\n"
        "                 177.50 C     Commission 1.95  Industry Fee 0.04\n"
        "03/23  Purchase  AAPL  APPLE INC                            100.0000 175.5000 17,550.00\n"
        "Ending Cash\n"
    )
    rep = parse_statement_transactions(text, "Brokerage Statement_2026-03-31_711.PDF")
    assert len(rep.fills) == 2
    assert rep.unparsed == []

    opt = rep.fills[0]
    assert opt.symbol == "NVDA"
    assert opt.side == "buy"
    assert opt.qty == 6.0
    assert opt.price == 0.10
    assert opt.asset_type == "option"
    assert opt.option_strike == 177.5
    assert opt.option_right == "call"
    assert opt.option_expiry == date(2026, 3, 20)
    assert opt.trade_date == date(2026, 3, 19)  # Derived T+1 from settle 03/20 (Fri -> Thu)
    assert opt.settle_date == date(2026, 3, 20)
    assert opt.date_source == "derived_settle_t1"
    assert opt.commission == 1.95
    assert opt.fees == 0.04

    eq = rep.fills[1]
    assert eq.symbol == "AAPL"
    assert eq.side == "buy"
    assert eq.qty == 100.0
    assert eq.price == 175.50
    assert eq.asset_type == "equity"
    assert eq.trade_date == date(2026, 3, 20)  # Derived T+1 from settle 03/23 (Mon -> Fri)
    assert eq.settle_date == date(2026, 3, 23)
    assert eq.date_source == "derived_settle_t1"


def test_parse_statement_transactions_stops_at_section_boundary():
    text = (
        "Statement Period May 1-31, 2026\n"
        "Transaction Details\n"
        "05/08  Purchase  NVDA  NVIDIA CORP 05/08/2026 $217.5 Call   50.0000  0.2000  1000.00\n"
        "Total Transactions\n"
        "05/08  Purchase  NVDA  NVIDIA CORP 05/08/2026 $217.5 Call   50.0000  0.2000  1000.00\n"
    )
    rep = parse_statement_transactions(text, "Brokerage Statement_2026-05-31_711.PDF")
    assert len(rep.fills) == 1


def test_dedupe_statement_fills_preserves_confirmations_and_imports_gaps():
    conf_fill = ParsedFill(
        trade_date=date(2026, 5, 8),
        settle_date=date(2026, 5, 11),
        symbol="NVDA",
        side="buy",
        qty=50.0,
        price=0.20,
        description="NVDA 217.5 Call",
        asset_type="option",
        option_expiry=date(2026, 5, 8),
        option_strike=217.5,
        option_right="call",
        source_file="Confirm - NVDA_2026-05-08.PDF",
    )
    conf_rep = ParseReport(fills=[conf_fill], files_read=1)

    stmt_fill_dup = ParsedFill(
        trade_date=date(2026, 5, 8),
        settle_date=date(2026, 5, 11),
        symbol="NVDA",
        side="buy",
        qty=50.0,
        price=0.20,
        description="NVIDIA CORP 05/08/2026 $217.5 Call",
        asset_type="option",
        option_expiry=date(2026, 5, 8),
        option_strike=217.5,
        option_right="call",
        source_file="Brokerage Statement_2026-05-31.PDF",
    )
    stmt_fill_new = ParsedFill(
        trade_date=date(2026, 5, 8),
        settle_date=date(2026, 5, 11),
        symbol="NVDA",
        side="buy",
        qty=100.0,
        price=0.10,
        description="NVIDIA CORP 05/08/2026 $217.5 Call",
        asset_type="option",
        option_expiry=date(2026, 5, 8),
        option_strike=217.5,
        option_right="call",
        source_file="Brokerage Statement_2026-05-31.PDF",
    )
    stmt_rep = ParseReport(fills=[stmt_fill_dup, stmt_fill_new], files_read=1)

    merged = merge(dedupe_statement_fills([conf_rep], [stmt_rep]))
    assert len(merged.fills) == 2
    assert merged.fills[0].qty == 50.0
    assert merged.fills[0].source_file == "Confirm - NVDA_2026-05-08.PDF"
    assert merged.fills[1].qty == 100.0
    assert merged.fills[1].source_file == "Brokerage Statement_2026-05-31.PDF"
    assert len(merged.duplicates) == 1
    assert "covered by confirmation" in merged.duplicates[0]["why"]


def test_incomplete_statement_row_reported_as_unparsed():
    text = (
        "Statement Period May 1-31, 2026\n"
        "Transaction Details\n"
        "05/08  Purchase  NVDA  Incomplete Option Row $217.5 Call  NOT_NUMERIC  NOT_NUMERIC\n"
    )
    rep = parse_statement_transactions(text, "Brokerage Statement_2026-05-31.PDF")
    assert rep.fills == []
    assert len(rep.unparsed) == 1
    assert "quantity" in rep.unparsed[0]["why"] or "numeric" in rep.unparsed[0]["why"]


def test_us_market_holidays_and_prior_business_day():
    # 2026 Memorial Day: Monday May 25, 2026
    assert is_us_market_holiday(date(2026, 5, 25)) is True
    # Prior business day before Tuesday May 26 is Friday May 22 (skips holiday + weekend)
    assert prior_business_day(date(2026, 5, 26)) == date(2026, 5, 22)

    # 2026 Good Friday: Friday April 3, 2026
    assert is_us_market_holiday(date(2026, 4, 3)) is True
    # Prior business day before Monday April 6 is Thursday April 2 (skips weekend + Good Friday)
    assert prior_business_day(date(2026, 4, 6)) == date(2026, 4, 2)

    # Regular Monday June 1, 2026 -> prior business day is Friday May 29, 2026
    assert prior_business_day(date(2026, 6, 1)) == date(2026, 5, 29)


def test_statement_transaction_derived_t1_trade_date():
    text = (
        "Statement Period June 1-30, 2026\n"
        "Transaction Details\n"
        "06/01  Purchase  DRAM  MICRON TECH INC  475.0000  10.0000\n"
    )
    rep = parse_statement_transactions(text, "Brokerage Statement_2026-06-30.PDF")
    assert len(rep.fills) == 1
    fill = rep.fills[0]
    # Settle date 06/01 -> Trade date derived under T+1 is 2026-05-29
    assert fill.settle_date == date(2026, 6, 1)
    assert fill.trade_date == date(2026, 5, 29)
    assert fill.date_source == "derived_settle_t1"
    assert fill.symbol == "DRAM"
    assert fill.qty == 475.0
    assert fill.price == 10.0


def test_dedupe_statement_cross_statement_copies():
    # Month M statement: pending transaction DRAM 475 shares
    fill_may = ParsedFill(
        trade_date=date(2026, 5, 29),
        settle_date=date(2026, 6, 1),
        symbol="DRAM",
        side="buy",
        qty=475.0,
        price=10.0,
        description="MICRON TECH INC",
        asset_type="equity",
        source_file="Brokerage Statement_2026-05-31.PDF",
        date_source="derived_settle_t1",
    )
    rep_may = ParseReport(fills=[fill_may], files_read=1)

    # Month M+1 statement: settled transaction DRAM 475 shares (same trade)
    fill_june = ParsedFill(
        trade_date=date(2026, 5, 29),
        settle_date=date(2026, 6, 1),
        symbol="DRAM",
        side="buy",
        qty=475.0,
        price=10.0,
        description="MICRON TECH INC",
        asset_type="equity",
        source_file="Brokerage Statement_2026-06-30.PDF",
        date_source="derived_settle_t1",
    )
    rep_june = ParseReport(fills=[fill_june], files_read=1)

    merged = merge(dedupe_statement_fills([], [rep_may, rep_june]))
    assert len(merged.fills) == 1
    assert merged.fills[0].source_file == "Brokerage Statement_2026-05-31.PDF"
    assert len(merged.duplicates) == 1
    assert "already imported from statement" in merged.duplicates[0]["why"]


def test_parse_report_summary_honest_labeling():
    rep = ParseReport(
        fills=[
            ParsedFill(
                trade_date=date(2026, 5, 8),
                settle_date=date(2026, 5, 11),
                symbol="NVDA",
                side="buy",
                qty=1.0,
                price=100.0,
                description="NVDA",
                asset_type="equity",
            )
        ],
        unparsed=[],
        files_read=5,
        duplicates=[
            {"file": "a.pdf", "why": "duplicate download of b.pdf"},
            {"file": "c.pdf", "why": "statement fill covered by confirmation"},
        ],
    )
    summary_text = rep.summary()
    assert "1 duplicate files dropped" in summary_text
    assert "1 duplicate statement fills dropped" in summary_text


