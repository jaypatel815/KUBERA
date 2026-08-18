"""T023b — fundamental ratios, every number hand-computed.

compose_fundamentals is pure; the client methods are exercised in test_fmp.py.
"""

from analysis.fundamentals import STALENESS_NOTE, compose_fundamentals

CASH_ROWS = [
    # newest first, as FMP returns them; reported freeCashFlow present
    {"date": "2025-12-31", "operatingCashFlow": 110_000.0,
     "capitalExpenditure": -30_000.0, "freeCashFlow": 80_000.0},
    {"date": "2024-12-31", "operatingCashFlow": 100_000.0,
     "capitalExpenditure": -25_000.0},          # no reported FCF -> derived
]
BALANCE_ROW = [{"date": "2025-12-31", "totalDebt": 50_000.0,
                "totalStockholdersEquity": 200_000.0, "totalAssets": 400_000.0}]


def test_hand_computed_headline_case():
    """Reported FCF preferred; derived = OCF + (negative) capex; yield =
    80,000 / 1,600,000 = 5%; D/E = 0.25; D/A = 0.125."""
    r = compose_fundamentals("aapl", CASH_ROWS, BALANCE_ROW, market_cap=1_600_000.0)
    assert r.symbol == "AAPL"
    assert [y.fiscal_date for y in r.fcf_years] == ["2025-12-31", "2024-12-31"]
    assert r.fcf_years[0].fcf == 80_000.0 and r.fcf_years[0].source == "reported"
    assert r.fcf_years[1].fcf == 75_000.0                    # 100k + (-25k)
    assert r.fcf_years[1].source == "derived_ocf_plus_capex"
    assert r.fcf_yield == 0.05
    assert r.debt_to_equity == 0.25
    assert r.debt_to_assets == 0.125
    assert r.balance_fiscal_date == "2025-12-31"
    assert r.unparsed == []
    assert STALENESS_NOTE in r.notes


def test_positive_capex_is_reported_never_guessed():
    rows = [{"date": "2025-12-31", "operatingCashFlow": 100.0,
             "capitalExpenditure": 30.0}]                    # unobserved sign
    r = compose_fundamentals("X", rows, None, None)
    assert r.fcf_years == [] and r.fcf_latest is None
    assert any("capex is POSITIVE" in u["why"] for u in r.unparsed)


def test_negative_equity_suppresses_debt_to_equity_with_why():
    """Buyback-heavy names have negative equity; a negative D/E would read as
    'low debt' — the exact wrong conclusion, so it must be None + note."""
    bal = [{"date": "2025-12-31", "totalDebt": 100.0,
            "totalStockholdersEquity": -50.0, "totalAssets": 400.0}]
    r = compose_fundamentals("X", CASH_ROWS, bal, 1_000.0)
    assert r.debt_to_equity is None
    assert any("equity is non-positive" in n for n in r.notes)
    assert r.debt_to_assets == 0.25                          # still computable


def test_missing_market_cap_gives_fcf_but_no_yield():
    r = compose_fundamentals("X", CASH_ROWS, BALANCE_ROW, market_cap=None)
    assert r.fcf_latest == 80_000.0 and r.fcf_yield is None
    assert any("market cap unavailable" in n for n in r.notes)


def test_no_balance_sheet_degrades_with_probe_pointer():
    r = compose_fundamentals("X", CASH_ROWS, None, 1_000.0)
    assert r.debt_to_equity is None and r.debt_to_assets is None
    assert any("fmp_check" in n for n in r.notes)


def test_unparsed_rows_and_missing_dates_reported():
    rows = [
        "not-a-dict",
        {"operatingCashFlow": 5.0, "capitalExpenditure": -1.0},   # no date
        {"date": "2025-12-31"},                                   # nothing usable
    ]
    r = compose_fundamentals("X", rows, None, None)
    assert r.fcf_years == []
    whys = " | ".join(u["why"] for u in r.unparsed)
    assert "not an object" in whys
    assert "missing fiscal date" in whys
    assert "cannot derive" in whys
