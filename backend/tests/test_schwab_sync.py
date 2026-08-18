"""T016c — Schwab real fills into the daily sync. All MockTransport, no network.

The TRADE fixture is shaped from the owner's March 2026 probe (I029): `time`
carries execution, fee legs are CURRENCY transferItems with a feeType, and one
row exercises the placeholder-tradeDate defect the mapper must survive.
"""

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_alpaca import paper_settings

from analysis.attribution import attributed_fills_from_rows, fifo_attribution
from data.models import Base, CashFlow, Transaction
from data.schwab import SchwabClient, SchwabError
from data.schwab_sync import sync_schwab_fills

TOKEN_JSON = {"access_token": "access-1", "expires_in": 1800, "token_type": "Bearer"}
ACCOUNTS_JSON = [{"accountNumber": "98765432", "hashValue": "HASH-1"}]

OPTION_BUY = {
    "activityId": 111, "type": "TRADE", "status": "VALID",
    "time": "2026-08-14T14:31:00+0000", "tradeDate": "2026-08-14T14:31:00+0000",
    "orderId": 9001, "netAmount": -91.66,
    "transferItems": [
        {"instrument": {"assetType": "CURRENCY", "symbol": "CURRENCY_USD"},
         "amount": 0.65, "cost": -0.65, "feeType": "COMMISSION"},
        {"instrument": {"assetType": "CURRENCY", "symbol": "CURRENCY_USD"},
         "amount": 0.01, "cost": -0.01, "feeType": "OPT_REG_FEE"},
        {"instrument": {"symbol": "SPY   260821P00640000", "assetType": "OPTION"},
         "amount": 1, "price": 0.91},
    ],
}
OPTION_SELL = {
    **OPTION_BUY, "activityId": 112, "orderId": 9002,
    "time": "2026-08-14T15:10:00+0000", "tradeDate": "2026-08-14T15:10:00+0000",
    "netAmount": 129.34,
    "transferItems": [
        {"instrument": {"assetType": "CURRENCY", "symbol": "CURRENCY_USD"},
         "amount": 0.65, "cost": -0.65, "feeType": "COMMISSION"},
        {"instrument": {"symbol": "SPY   260821P00640000", "assetType": "OPTION"},
         "amount": -1, "price": 1.30},
    ],
}
EQUITY_PLACEHOLDER_DATE = {
    "activityId": 113, "type": "TRADE", "status": "VALID",
    "time": "2026-08-14T15:24:20+0000",
    "tradeDate": "2026-08-14T05:00:00+0000",     # the observed midnight placeholder
    "orderId": 9003, "netAmount": 1530.15,
    "transferItems": [
        {"instrument": {"symbol": "GDX", "assetType": "EQUITY"},
         "amount": -15, "price": 102.01},
    ],
}
DEPOSIT = {
    "activityId": 114, "type": "ACH_RECEIPT", "status": "VALID",
    "time": "2026-08-13T10:00:00Z", "netAmount": 500.0,
}
ROWS = [OPTION_BUY, OPTION_SELL, EQUITY_PLACEHOLDER_DATE, DEPOSIT]


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def client_with(rows):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/oauth/token"):
            return httpx.Response(200, json=TOKEN_JSON)
        if path.endswith("/accounts/accountNumbers"):
            return httpx.Response(200, json=ACCOUNTS_JSON)
        if "/transactions" in path:
            return httpx.Response(200, json=rows)
        return httpx.Response(404, json={})

    return SchwabClient(
        settings=paper_settings(schwab_app_key="k", schwab_app_secret="s",
                                schwab_refresh_token="r"),
        transport=httpx.MockTransport(handler),
    )


def test_sync_lands_fills_cash_and_broker_costs(db):
    with client_with(ROWS) as c:
        r = sync_schwab_fills(db, c, days=30)
    assert (r.fills_inserted, r.cash_inserted, r.unmapped) == (3, 1, 0)

    rows = db.execute(select(Transaction).order_by(Transaction.external_id)).scalars().all()
    opt = rows[0]
    assert opt.fill_type == "option"
    assert opt.commission == pytest.approx(0.65)
    assert opt.fees == pytest.approx(0.01)          # OPT_REG_FEE, not commission
    eq = rows[2]
    assert eq.fill_type != "option"
    # I029 regression at the DB layer: execution time, not the placeholder.
    assert eq.occurred_at.hour == 15 and eq.occurred_at.minute == 24
    cash = db.execute(select(CashFlow)).scalars().one()
    assert cash.kind == "deposit" and cash.amount == pytest.approx(500.0)
    assert "fills +3/0 known" in r.summary()


def test_rerun_is_idempotent(db):
    with client_with(ROWS) as c:
        sync_schwab_fills(db, c, days=30)
        r2 = sync_schwab_fills(db, c, days=30)
    assert (r2.fills_inserted, r2.fills_skipped) == (0, 3)
    assert (r2.cash_inserted, r2.cash_skipped) == (0, 1)
    assert len(db.execute(select(Transaction)).scalars().all()) == 3


def test_lapsed_token_raises_the_named_weekly_error(db):
    """sync.py catches this and prints the run-schwab_auth note; the sync
    itself must surface the ALREADY-actionable SchwabError, not a raw 400."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    c = SchwabClient(
        settings=paper_settings(schwab_app_key="k", schwab_app_secret="s",
                                schwab_refresh_token="r"),
        transport=httpx.MockTransport(handler),
    )
    with c, pytest.raises(SchwabError, match="expire roughly weekly"):
        sync_schwab_fills(db, c, days=30)


def test_db_option_round_trip_carries_the_100x_multiplier(db):
    """The reason fill_type is persisted: without it, this trip's P&L reads
    $0.39 instead of $39.00. 1 contract, 0.91 -> 1.30 = 0.39 * 100."""
    with client_with(ROWS) as c:
        sync_schwab_fills(db, c, days=30)
    txns = db.execute(select(Transaction).order_by(Transaction.occurred_at)).scalars().all()
    rep = fifo_attribution(attributed_fills_from_rows(txns, {}))
    opt_trip = [t for t in rep.trips if "260821P" in t["symbol"]]
    assert len(opt_trip) == 1
    assert opt_trip[0]["pnl"] == pytest.approx(39.00)
    assert opt_trip[0]["notional"] == pytest.approx(130.00)  # 1 * 1.30 * 100


def test_days_validated(db):
    with client_with(ROWS) as c:
        with pytest.raises(ValueError, match="days"):
            sync_schwab_fills(db, c, days=0)
