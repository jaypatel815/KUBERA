"""T117 — TLH scan, hand-computed. Measurement only; every limitation named."""

from datetime import date

from analysis.tlh import LONG_TERM_DAYS, NOT_TAX_ADVICE, scan_tlh

TODAY = date(2026, 8, 20)


def _lot(sym, qty, price, ts, mult=1):
    return {"symbol": sym, "qty": qty, "price": price, "ts": ts, "mult": mult,
            "regime": None, "sub_strategy": None, "bucket": None}


def test_hand_computed_losses_terms_and_ordering():
    lots = [
        _lot("AAA", 10, 100.0, "2026-08-01T14:00:00Z"),   # short-term
        _lot("BBB", 5, 200.0, "2025-01-10T14:00:00Z"),    # long-term (>365d)
        _lot("CCC", 3, 50.0, "2026-07-01T14:00:00Z"),     # a GAIN — skipped
    ]
    prices = {"AAA": 90.0, "BBB": 150.0, "CCC": 60.0}
    scan = scan_tlh(lots, prices, recent_buys=[], today=TODAY)

    # AAA: 10 * (90-100) = -100 ; BBB: 5 * (150-200) = -250
    assert scan.total_harvestable_loss == -350.0
    assert scan.n_gains_skipped == 1 and scan.n_unpriced == 0
    # largest loss first (their checklist's prioritization)
    assert [c.symbol for c in scan.candidates] == ["BBB", "AAA"]
    bbb, aaa = scan.candidates
    assert bbb.unrealized_pnl == -250.0 and bbb.term == "long"
    assert aaa.unrealized_pnl == -100.0 and aaa.term == "short"
    # forward window: sold today -> first safe repurchase = today + 31
    assert aaa.no_rebuy_until == "2026-09-20"
    assert "NOT TAX ADVICE" in scan.limitations


def test_wash_lookback_flags_only_recent_same_symbol_buys():
    lots = [_lot("AAA", 10, 100.0, "2026-06-01T14:00:00Z")]
    prices = {"AAA": 80.0}
    scan = scan_tlh(lots, prices,
                    recent_buys=[("AAA", "2026-08-05"),     # inside 30d — WASH
                                 ("AAA", "2026-06-01"),     # too old — clean
                                 ("ZZZ", "2026-08-10")],    # other symbol
                    today=TODAY)
    c = scan.candidates[0]
    assert c.wash_lookback_flag is not None
    assert "2026-08-05" in c.wash_lookback_flag and "WASH" in c.wash_lookback_flag

    clean = scan_tlh(lots, prices, recent_buys=[("AAA", "2026-07-01")],
                     today=TODAY)
    assert clean.candidates[0].wash_lookback_flag is None  # 50 days ago


def test_options_multiplier_and_unpriced_lots_are_named():
    lots = [
        _lot("SPY260918P00650000", 2, 3.50, "2026-08-10T14:00:00Z", mult=100),
        _lot("AAA", 1, 100.0, "2026-08-01T14:00:00Z"),
    ]
    # option symbol has no price on this feed -> unpriced, listed, not guessed
    scan = scan_tlh(lots, {"AAA": 90.0, "SPY260918P00650000": None},
                    recent_buys=[], today=TODAY)
    assert scan.n_unpriced == 1
    unpriced = [c for c in scan.candidates if c.last_price is None][0]
    assert unpriced.unrealized_pnl is None
    assert "NOT assumed" in unpriced.note
    assert unpriced.contract_multiplier == 100
    # the priced equity loss still counts
    assert scan.total_harvestable_loss == -10.0


def test_missing_entry_clock_reads_unknown_never_guessed():
    lots = [_lot("AAA", 1, 100.0, None)]
    scan = scan_tlh(lots, {"AAA": 50.0}, recent_buys=[], today=TODAY)
    assert scan.candidates[0].term == "unknown"
    assert LONG_TERM_DAYS == 365 and "tax professional" in NOT_TAX_ADVICE
