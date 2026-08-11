"""Sync job tests — in-memory DB + MockTransport client; idempotency is the key property."""

import httpx
import pytest
from sqlalchemy import func, select
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings

from data.alpaca import AlpacaClient
from data.db import make_engine, make_session_factory
from data.models import AccountSnapshot, Base, BrokerAccount, PositionSnapshot
from data.sync import sync_once


@pytest.fixture()
def session():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def make_client() -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        if "/v2/positions" in request.url.path:
            return httpx.Response(200, json=POSITIONS_JSON)
        return httpx.Response(404, json={})

    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_sync_writes_snapshots(session):
    with make_client() as client:
        result = sync_once(session, client)

    assert result.account_external_id == "PA1TEST23"
    assert result.positions == 1
    assert result.asof.tzinfo is not None

    acct = session.execute(select(BrokerAccount)).scalar_one()
    assert acct.broker == "alpaca-paper"
    snap = session.execute(select(AccountSnapshot)).scalar_one()
    assert snap.equity == pytest.approx(100000.75)
    pos = session.execute(select(PositionSnapshot)).scalar_one()
    assert pos.symbol == "AAPL"
    assert pos.account_id == acct.id


def test_sync_is_idempotent_on_account(session):
    """Two syncs → ONE account row, TWO snapshot rows each. Never duplicate accounts."""
    with make_client() as client:
        sync_once(session, client)
        sync_once(session, client)

    n_accounts = session.execute(select(func.count()).select_from(BrokerAccount)).scalar_one()
    n_snaps = session.execute(select(func.count()).select_from(AccountSnapshot)).scalar_one()
    n_pos = session.execute(select(func.count()).select_from(PositionSnapshot)).scalar_one()
    assert n_accounts == 1
    assert n_snaps == 2
    assert n_pos == 2
