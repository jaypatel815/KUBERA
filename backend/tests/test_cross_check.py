"""T016b — API-vs-statement cross-check, every case hand-computed.

The fixtures replay the owner's real March 2026 verification shapes: the
71+29=100 per-order aggregation that landed to the penny, options as OCC
symbols on one side and underlying+fields on the other, and UTC evening
timestamps that must stay on their Eastern trading day.
"""

from datetime import date, datetime, timezone

import pytest

from analysis.cross_check import (
    api_order_lines,
    cross_check,
    parse_occ,
)
from data.alpaca import Fill
from data.statements import ParsedFill

ASOF = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def api_fill(external_id: str, symbol: str, side: str, qty: float, price: float,
             occurred_at: datetime, order_id: str, fill_type: str = "fill",
             commission: float = 0.0, fees: float = 0.0) -> Fill:
    return Fill(external_id=external_id, symbol=symbol, side=side, qty=qty,
                price=price, occurred_at=occurred_at, order_id=order_id,
                fill_type=fill_type, asof=ASOF, commission=commission,
                fees=fees, source="schwab")


def stmt_fill(symbol: str, side: str, qty: float, price: float, trade: date,
              asset_type: str = "equity", expiry: date | None = None,
              strike: float | None = None, right: str | None = None,
              commission: float = 0.0, fees: float = 0.0) -> ParsedFill:
    return ParsedFill(trade_date=trade, settle_date=None, symbol=symbol,
                      side=side, qty=qty, price=price, description="",
                      asset_type=asset_type, commission=commission, fees=fees,
                      option_expiry=expiry, option_strike=strike,
                      option_right=right, source_file="stmt-2026-03.pdf")


# ---------------------------------------------------------------- parse_occ

def test_parse_occ_round_trips_the_march_contract():
    assert parse_occ("NVDA  260320C00177500") == ("NVDA", date(2026, 3, 20), "call", 177.5)
    assert parse_occ("SPY   260821P00640000") == ("SPY", date(2026, 8, 21), "put", 640.0)


def test_parse_occ_fails_closed():
    assert parse_occ("NVDA") is None                      # bare equity symbol
    assert parse_occ("NVDA  269999C00177500") is None     # month 99: invalid date


# ------------------------------------------------- per-order aggregation

def test_owner_march_case_71_plus_29_equals_one_statement_line():
    """The exact case the owner verified by hand: two executions on one order
    (71 + 29 @ 0.21) must aggregate to the statement's single 100-lot line."""
    t = datetime(2026, 3, 13, 14, 30, tzinfo=timezone.utc)
    api = [
        api_fill("e1", "USO   260417P00068000", "buy", 71, 0.21, t, "ord-1",
                 fill_type="option"),
        api_fill("e2", "USO   260417P00068000", "buy", 29, 0.21, t, "ord-1",
                 fill_type="option"),
    ]
    stmt = [stmt_fill("USO", "buy", 100, 0.21, date(2026, 3, 13),
                      asset_type="option", expiry=date(2026, 4, 17),
                      strike=68.0, right="put")]
    report = cross_check(api, stmt)
    assert report.clean
    assert len(report.matched) == 1
    a, s, _ = report.matched[0]
    assert a.qty == 100 and a.price == pytest.approx(0.21)
    assert a.label.endswith("2 execution(s)")


def test_weighted_average_price_within_tolerance_matches():
    """Mixed-price executions: 60 @ 0.20 + 40 @ 0.215 -> 0.206; the statement
    prints the rounded 0.21. |0.206 - 0.21| = 0.004 <= tol 0.01 -> match."""
    t = datetime(2026, 3, 5, 15, 0, tzinfo=timezone.utc)
    api = [
        api_fill("e1", "GDX", "sell", 60, 0.20, t, "ord-2"),
        api_fill("e2", "GDX", "sell", 40, 0.215, t, "ord-2"),
    ]
    stmt = [stmt_fill("GDX", "sell", 100, 0.21, date(2026, 3, 5))]
    report = cross_check(api, stmt)
    assert report.clean and len(report.matched) == 1


def test_utc_evening_stays_on_its_eastern_trading_day():
    """23:30 UTC on 3/12 is 19:30 ET on 3/12 (EDT) — the I029 lesson at the
    diff layer: the join must use the Eastern date, not the UTC date."""
    t = datetime(2026, 3, 12, 23, 30, tzinfo=timezone.utc)
    api = [api_fill("e1", "NVDA", "buy", 15, 102.01, t, "ord-3")]
    stmt = [stmt_fill("NVDA", "buy", 15, 102.01, date(2026, 3, 12))]
    assert cross_check(api, stmt).clean


# ---------------------------------------------------------------- buckets

def test_api_only_and_statement_only_never_absorbed():
    t = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
    api = [api_fill("e1", "AAPL", "buy", 10, 175.0, t, "ord-4")]
    stmt = [stmt_fill("MSFT", "sell", 5, 400.0, date(2026, 3, 10))]
    report = cross_check(api, stmt)
    assert not report.clean
    assert len(report.api_only) == 1 and len(report.statement_only) == 1
    assert report.near_misses == []          # different instruments: not near


def test_price_out_of_tolerance_is_unmatched_with_a_near_miss_label():
    t = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
    api = [api_fill("e1", "AAPL", "buy", 10, 175.00, t, "ord-5")]
    stmt = [stmt_fill("AAPL", "buy", 10, 175.50, date(2026, 3, 10))]
    report = cross_check(api, stmt)
    assert not report.clean                  # NOT silently reconciled
    assert len(report.api_only) == 1 and len(report.statement_only) == 1
    assert len(report.near_misses) == 1
    assert "price differs by 0.5000" in report.near_misses[0]


def test_date_off_by_one_is_unmatched_with_a_near_miss_label():
    t = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
    api = [api_fill("e1", "AAPL", "buy", 10, 175.0, t, "ord-6")]
    stmt = [stmt_fill("AAPL", "buy", 10, 175.0, date(2026, 3, 11))]
    report = cross_check(api, stmt)
    assert not report.clean
    assert len(report.near_misses) == 1
    assert "1 day(s) apart" in report.near_misses[0]


def test_both_date_and_price_off_gets_no_false_label():
    """D028 catch: a pair differing in date AND price must not be labelled
    'all else equal' — it is genuinely different, buckets only."""
    t = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
    api = [api_fill("e1", "AAPL", "buy", 10, 175.00, t, "ord-6b")]
    stmt = [stmt_fill("AAPL", "buy", 10, 176.00, date(2026, 3, 11))]
    report = cross_check(api, stmt)
    assert not report.clean
    assert report.near_misses == []


def test_two_identical_orders_need_two_statement_lines():
    """Greedy 1:1 — one statement line cannot satisfy two same-key orders."""
    t = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
    api = [
        api_fill("e1", "AAPL", "buy", 10, 175.0, t, "ord-7"),
        api_fill("e2", "AAPL", "buy", 10, 175.0, t, "ord-8"),
    ]
    stmt = [stmt_fill("AAPL", "buy", 10, 175.0, date(2026, 3, 10))]
    report = cross_check(api, stmt)
    assert len(report.matched) == 1
    assert len(report.api_only) == 1
    assert not report.clean


def test_unparseable_occ_is_reported_not_guessed():
    t = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
    api = [api_fill("e1", "BROKEN-OCC", "buy", 1, 0.5, t, "ord-9",
                    fill_type="option")]
    report = cross_check(api, [])
    assert report.unparseable and not report.clean
    assert "unparseable OCC" in report.unparseable[0]["why"]
    assert report.api_only == []             # not matched under a wrong key


def test_fee_note_flags_disagreement_and_blesses_agreement():
    t = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
    api = [
        api_fill("e1", "AAPL", "buy", 10, 175.0, t, "ord-10",
                 commission=0.65, fees=0.01),
        api_fill("e2", "MSFT", "sell", 5, 400.0, t, "ord-11",
                 commission=0.65, fees=0.01),
    ]
    stmt = [
        stmt_fill("AAPL", "buy", 10, 175.0, date(2026, 3, 10),
                  commission=0.65, fees=0.01),
        stmt_fill("MSFT", "sell", 5, 400.0, date(2026, 3, 10),
                  commission=1.95, fees=0.04),
    ]
    report = cross_check(api, stmt)
    assert report.clean                      # fee notes never affect matching
    notes = {a.key[1]: note for a, _, note in report.matched}
    assert notes["AAPL"] == "fees agree"
    assert "FEE NOTE" in notes["MSFT"]


def test_aggregation_rejects_non_positive_qty():
    t = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
    lines, bad = api_order_lines(
        [api_fill("e1", "AAPL", "buy", 0.0, 175.0, t, "ord-12")])
    assert lines == [] and bad[0]["why"] == "non-positive aggregated qty"


def test_price_tol_validated():
    with pytest.raises(ValueError, match="price_tol"):
        cross_check([], [], price_tol=-0.01)
