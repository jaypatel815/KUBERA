"""T108 — expiry reconciliation against monthly statements (I026).

The synthetic statement texts below replicate, shape for shape, the three row
variants found on the owner's five REAL monthly statements (Jan–May 2026,
twelve expiration events): expiry date on the action line; expiry pushed to the
continuation line by a long description; and the quantity always in accounting
parentheses. The "Short" token is the tax-lot term (short-TERM), not a short
position — the purchases sit directly above each removal on the real documents.
"""

from datetime import date, datetime, timezone

from analysis.autopsy import AutopsyRoundTrip
from analysis.expiry_reconcile import (
    StatementExpiry,
    parse_statement_expirations,
    reconcile,
)

# Variant 1 (most common): expiry + PUT/CALL on the action line, strike on +1.
VARIANT_LINE1 = (
    "        Other         Expired  Short       SPY   05/11/2026    PUT   STATE   "
    "STREET     SPDR   S&$733                (135.0000)\n"
    "        Activity                           733.00  P           EXP   05/11/26\n"
)

# Variant 2: posting date leads the line; expiry still on the action line.
VARIANT_DATED = (
    "05/18  Other          Expired  Short        AMD   05/15/2026     CALL   ADVANCED"
    "       MICRO    DEVI$490                    (1.0000)\n"
    "       Activity                             490.00   C           EXP   05/15/26\n"
)

# Variant 3: long description pushes the expiry to the continuation lines.
VARIANT_WRAPPED = (
    "05/26  Other          Expired  Short        NVDA                 CALL   NVIDIA   "
    "CORP          $285       EXP               (1.0000)\n"
    "       Activity                             05/22/2026           05/22/26\n"
    "                                            285.00   C\n"
)

# The continuation hazard: the next TRANSACTION's line carries a different
# contract's date and must never be read as this row's expiry.
VARIANT_TRUNCATED = (
    "        Other         Expired  Short       QQQ                 CALL   INVESCO   "
    "QQQ   TR        $713                  (2.0000)\n"
    "02/04  Purchase                             SPY   02/03/2026     CALL   SPDR    "
    "S&P  500       $696           1.0000    0.40\n"
)


def _trip(key: str, symbol: str, qty: float, pnl: float,
          closed_by: str = "expiry_assumed") -> AutopsyRoundTrip:
    return AutopsyRoundTrip(
        symbol=symbol, contract_key=key, asset_type="option", qty=qty,
        entry_price=abs(pnl) / (qty * 100), exit_price=0.0, pnl=pnl,
        held_days=0.0, entry_ts=datetime(2026, 5, 11, tzinfo=timezone.utc),
        exit_ts=datetime(2026, 5, 11, tzinfo=timezone.utc), is_0dte=True,
        time_known=False, contract_multiplier=100, closed_by=closed_by,
    )


# ------------------------------------------------------------------ parsing

def test_variant_expiry_on_the_action_line():
    found, unparsed = parse_statement_expirations(VARIANT_LINE1, "may.pdf")
    assert unparsed == []
    assert len(found) == 1
    e = found[0]
    assert (e.symbol, e.expiry, e.right, e.strike, e.qty, e.action) == (
        "SPY", date(2026, 5, 11), "put", 733.0, 135.0, "expired",
    )
    assert e.contract_key == "SPY_2026-05-11_733.0_PUT"


def test_variant_with_posting_date_prefix():
    found, unparsed = parse_statement_expirations(VARIANT_DATED, "may.pdf")
    assert unparsed == []
    assert found[0].symbol == "AMD"
    assert found[0].expiry == date(2026, 5, 15)
    assert found[0].strike == 490.0
    assert found[0].right == "call"
    assert found[0].qty == 1.0


def test_variant_wrapped_description():
    """Expiry lives on the continuation line, strike two lines down."""
    found, unparsed = parse_statement_expirations(VARIANT_WRAPPED, "may.pdf")
    assert unparsed == []
    assert found[0].symbol == "NVDA"
    assert found[0].expiry == date(2026, 5, 22)
    assert found[0].strike == 285.0


def test_next_transactions_date_is_never_stolen():
    """The row is missing its own expiry and the next line starts a Purchase —
    grabbing 02/03/2026 from it would attribute a DIFFERENT contract's date.
    The row must be reported unparsed instead."""
    found, unparsed = parse_statement_expirations(VARIANT_TRUNCATED, "feb.pdf")
    assert found == []
    assert len(unparsed) == 1
    assert "missing" in unparsed[0]["why"]
    assert "refusing to guess" in unparsed[0]["why"]


def test_prose_mentioning_expiry_is_not_a_row():
    text = "Options positions that reach expiration may be Exercised or Expired.\n"
    found, unparsed = parse_statement_expirations(text, "x.pdf")
    assert found == [] and unparsed == []   # no parenthesised quantity: prose


# ------------------------------------------------------------------ joining

STMT_SPY = StatementExpiry(symbol="SPY", expiry=date(2026, 5, 11), right="put",
                           strike=733.0, qty=135.0, action="expired")


def test_confirmed_when_quantities_agree():
    trips = [_trip("SPY_2026-05-11_733.0_PUT", "SPY", 135.0, -3459.0)]
    r = reconcile(trips, [STMT_SPY], statements_read=1)
    assert r.confirmed == 1 and r.clean
    assert r.entries[0].status == "confirmed_expired"


def test_quantity_mismatch_is_flagged_as_understated_losses():
    """The owner's real case: 100 contracts in confirmations, 135 on the
    statement — a missing confirmation PDF, and losses UNDERSTATED even
    after the expiry fix."""
    trips = [_trip("SPY_2026-05-11_733.0_PUT", "SPY", 100.0, -2900.0)]
    r = reconcile(trips, [STMT_SPY], statements_read=1)
    assert r.quantity_mismatches == 1 and not r.clean
    assert "UNDERSTATED" in r.entries[0].detail


def test_assumed_trip_with_no_statement_row_is_unverified():
    trips = [_trip("SPY_2026-06-08_735.0_PUT", "SPY", 12.0, -240.0)]
    r = reconcile(trips, [], statements_read=0)
    assert r.not_in_statements == 1 and not r.clean
    assert "UNVERIFIED" in r.entries[0].detail


def test_statement_expiry_invisible_to_confirmations_is_reported():
    r = reconcile([], [STMT_SPY], statements_read=1)
    assert r.no_confirmation_coverage == 1 and not r.clean
    assert "invisible" in r.entries[0].detail


def test_assignment_makes_exit_zero_wrong_and_says_so():
    """No assignment has occurred on the real statements yet, but the first one
    must not be silently treated as a worthless expiry."""
    assigned = StatementExpiry(symbol="SPY", expiry=date(2026, 5, 11), right="put",
                               strike=733.0, qty=135.0, action="assigned")
    trips = [_trip("SPY_2026-05-11_733.0_PUT", "SPY", 135.0, -3459.0)]
    r = reconcile(trips, [assigned], statements_read=1)
    assert r.assigned_or_exercised == 1 and not r.clean
    assert "exit 0 is WRONG" in r.entries[0].detail


def test_sold_trips_are_ignored_by_reconciliation():
    """Only assumption-closed trips need statement verification."""
    trips = [_trip("SPY_2026-05-11_733.0_PUT", "SPY", 135.0, 500.0, closed_by="sell")]
    r = reconcile(trips, [STMT_SPY], statements_read=1)
    # The sold trip is not an assumption; the statement row has no counterpart.
    assert r.confirmed == 0
    assert r.no_confirmation_coverage == 1
