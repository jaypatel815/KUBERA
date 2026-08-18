"""T016 — Schwab read-only client and transaction mapping (D026).

No network: every test drives httpx.MockTransport. The live smoke test lives on
the owner's machine (I002 — the sandbox cannot reach api.schwabapi.com).

The mapping fixtures below were originally built from Schwab's published
response shapes. AS OF 2026-08-17 the key shapes are checked against a LIVE
pull (the owner's March 2026 probe, I029): `time` is the real execution
instant on every observed row, while `tradeDate` sometimes degrades to a
date-only placeholder at midnight ET (05:00:00Z) — the placeholder fixture
below is a faithful copy of that observed defect. Expirations produce NO
transaction row at all in this endpoint; the reconcile script surfaces them
as expected-expirations instead (T108 closes them at $0).
"""

from datetime import datetime, timezone

import httpx
import pytest

from data.schwab import (
    BASE_URL,
    ImportReport,
    SchwabClient,
    SchwabError,
    map_transactions,
)
from settings import ConfigError, KuberaSettings

T0 = datetime(2026, 3, 2, 14, 31, tzinfo=timezone.utc)


def schwab_settings(**over) -> KuberaSettings:
    base = dict(
        _env_file=None,
        schwab_app_key="app-key",
        schwab_app_secret="app-secret",
        schwab_refresh_token="refresh-token",
    )
    base.update(over)
    return KuberaSettings(**base)


TOKEN_JSON = {"access_token": "access-1", "expires_in": 1800, "token_type": "Bearer"}

TRADE_ROW = {
    "activityId": 1001,
    "type": "TRADE",
    "status": "VALID",
    "time": "2026-03-02T14:31:00+0000",
    "orderId": "ORD-77",
    "netAmount": -1234.50,
    "transferItems": [
        {"instrument": {"assetType": "CURRENCY"}, "amount": -1234.50},
        {"instrument": {"symbol": "aapl", "assetType": "EQUITY"},
         "amount": 10, "price": 123.45, "positionEffect": "OPENING"},
        {"instrument": {"assetType": "FEE"}, "amount": -0.02, "feeType": "SEC"},
    ],
}

SELL_ROW = {
    **TRADE_ROW,
    "activityId": 1002,
    "transferItems": [
        {"instrument": {"symbol": "AAPL"}, "amount": -10, "price": 130.00},
    ],
}

DEPOSIT_ROW = {
    "activityId": 2001, "type": "ACH_RECEIPT", "status": "VALID",
    "time": "2026-03-03T10:00:00Z", "netAmount": 500.0,
}


# ------------------------------------------------------------------ config

def test_missing_config_explains_all_three_pieces():
    with pytest.raises(ConfigError) as e:
        KuberaSettings(_env_file=None).require_schwab()
    msg = str(e.value)
    for name in ("SCHWAB_APP_KEY", "SCHWAB_APP_SECRET", "SCHWAB_REFRESH_TOKEN"):
        assert name in msg
    assert "READ-ONLY" in msg          # the constraint travels with the error


def test_secrets_never_appear_in_repr():
    s = schwab_settings()
    assert "app-secret" not in repr(s)
    assert "refresh-token" not in repr(s)


# ------------------------------------------------------------------ auth

def _transport(handler):
    return httpx.MockTransport(handler)


def test_token_is_minted_once_and_reused():
    """A 30-minute token must not be re-minted per request."""
    calls = {"token": 0, "get": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            calls["token"] += 1
            return httpx.Response(200, json=TOKEN_JSON)
        calls["get"] += 1
        assert request.headers["Authorization"] == "Bearer access-1"
        return httpx.Response(200, json=[{"accountNumber": "12345678", "hashValue": "H"}])

    with SchwabClient(schwab_settings(), transport=_transport(handler)) as c:
        c.list_accounts()
        c.list_accounts()

    assert calls["token"] == 1
    assert calls["get"] == 2


def test_expired_token_is_refreshed_on_a_fake_clock():
    # Clock call order: _bearer() short-circuits on token-is-None (no call), so
    # the FIRST tick is consumed inside _refresh_token setting the expiry. The
    # SECOND is _bearer()'s expiry comparison on the next request — that is the
    # one that has to be past 1740 (1800s lifetime minus the 60s skew).
    ticks = iter([0.0, 5000.0, 5000.0, 5000.0])
    calls = {"token": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            calls["token"] += 1
            return httpx.Response(200, json=TOKEN_JSON)
        return httpx.Response(200, json=[{"accountNumber": "1", "hashValue": "H"}])

    c = SchwabClient(schwab_settings(), transport=_transport(handler),
                     clock=lambda: next(ticks))
    c.list_accounts()
    c.list_accounts()      # clock has moved past expiry -> second mint
    c.close()
    assert calls["token"] == 2


def test_a_401_triggers_one_refresh_then_succeeds():
    state = {"gets": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json=TOKEN_JSON)
        state["gets"] += 1
        if state["gets"] == 1:
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(200, json=[{"accountNumber": "1", "hashValue": "H"}])

    with SchwabClient(schwab_settings(), transport=_transport(handler)) as c:
        assert c.list_accounts()[0].hash_value == "H"
    assert state["gets"] == 2


def test_dead_refresh_token_says_what_to_do():
    """The common failure is time-based, not a typo. The message must say so."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    with SchwabClient(schwab_settings(), transport=_transport(handler)) as c:
        with pytest.raises(SchwabError, match="expire roughly weekly"):
            c.list_accounts()


def test_persistent_401_blames_approval_not_the_token():
    """A 401 on a token minted seconds ago is not an expiry problem.

    Writing this test found the client had no branch for it — the second 401
    fell through to a bare "HTTP 401", which is the message most likely to send
    someone re-authorising for an hour when the real cause is app scopes.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json=TOKEN_JSON)
        return httpx.Response(401, json={"error": "nope"})

    with SchwabClient(schwab_settings(), transport=_transport(handler)) as c:
        with pytest.raises(SchwabError, match="re-authorising will not help"):
            c.list_accounts()


# ------------------------------------------------------------------ reads

def test_account_numbers_are_masked_in_memory():
    """A full account number should not be carried around; the hash addresses it."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json=TOKEN_JSON)
        return httpx.Response(200, json=[{"accountNumber": "98765432", "hashValue": "HASH"}])

    with SchwabClient(schwab_settings(), transport=_transport(handler)) as c:
        acct = c.list_accounts()[0]
    assert acct.number_masked == "***5432"
    assert "98765432" not in repr(acct)
    assert acct.hash_value == "HASH"


def test_no_accounts_is_an_actionable_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json=TOKEN_JSON)
        return httpx.Response(200, json=[])

    with SchwabClient(schwab_settings(), transport=_transport(handler)) as c:
        with pytest.raises(SchwabError, match="no accounts"):
            c.list_accounts()


def test_transactions_send_the_window_schwab_expects():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json=TOKEN_JSON)
        seen.update(dict(request.url.params))
        return httpx.Response(200, json=[TRADE_ROW])

    with SchwabClient(schwab_settings(), transport=_transport(handler)) as c:
        rows = c.get_transactions("HASH", datetime(2026, 3, 1, tzinfo=timezone.utc), T0)

    assert rows == [TRADE_ROW]
    assert seen["startDate"] == "2026-03-01T00:00:00.000Z"
    assert seen["types"] == "TRADE"


def test_client_exposes_no_order_methods():
    """D026: read-only is a constraint, not an omission. Assert it."""
    forbidden = {"place_order", "submit_order", "cancel_order", "replace_order", "post"}
    assert forbidden.isdisjoint(dir(SchwabClient))


# ------------------------------------------------------------------ mapping

def test_trade_maps_to_a_fill_from_the_priced_equity_leg():
    """The cash and fee legs must be ignored; only the priced symbol leg is the fill."""
    report = map_transactions([TRADE_ROW])
    assert len(report.fills) == 1
    f = report.fills[0]
    assert f.symbol == "AAPL"          # normalised from "aapl"
    assert f.side == "buy" and f.qty == 10 and f.price == 123.45
    assert f.order_id == "ORD-77"
    assert f.source == "schwab"
    assert f.occurred_at == T0         # "+0000" parsed, not dropped
    assert not report.unmapped


def test_negative_amount_is_a_sell_with_positive_quantity():
    f = map_transactions([SELL_ROW]).fills[0]
    assert f.side == "sell" and f.qty == 10 and f.price == 130.00


def test_cash_movements_map_with_a_signed_amount():
    report = map_transactions([DEPOSIT_ROW])
    assert len(report.cash) == 1
    assert report.cash[0].kind == "deposit" and report.cash[0].amount == 500.0
    withdrawal = map_transactions([{**DEPOSIT_ROW, "activityId": 2002,
                                    "type": "ACH_DISBURSEMENT", "netAmount": -200.0}])
    assert withdrawal.cash[0].kind == "withdrawal"


def test_unmappable_rows_are_reported_never_dropped():
    """The discipline that makes reconciliation possible."""
    rows = [
        {"activityId": 3001, "type": "TRADE", "status": "VALID", "time": "2026-03-02T14:31:00Z",
         "transferItems": [{"instrument": {"assetType": "OPTION"}, "amount": 1}]},
        {"activityId": 3002, "type": "DIVIDEND_OR_INTEREST", "status": "VALID",
         "time": "2026-03-02T14:31:00Z", "netAmount": 12.0},
        {"activityId": 3003, "type": "TRADE", "status": "INVALID",
         "time": "2026-03-02T14:31:00Z", "transferItems": []},
        {"type": "TRADE", "time": "2026-03-02T14:31:00Z"},          # no id at all
    ]
    report = map_transactions(rows)
    assert report.fills == [] and report.cash == []
    assert len(report.unmapped) == 4
    whys = " ".join(u["why"] for u in report.unmapped)
    assert "no priced security leg" in whys
    assert "unhandled type" in whys
    assert "not VALID" in whys
    assert "no activityId" in whys


def test_report_summary_states_the_counts_that_reconcile():
    report = map_transactions([TRADE_ROW, DEPOSIT_ROW, {"activityId": 9, "type": "WEIRD",
                                                        "time": "2026-03-02T14:31:00Z"}])
    assert report.raw_count == 3
    assert report.mapped_count == 2
    s = report.summary()
    assert "3 transactions in" in s and "2 mapped" in s and "1 unmapped" in s


def test_unparseable_timestamp_is_reported_not_guessed():
    report = map_transactions([{**TRADE_ROW, "activityId": 4001, "time": "not-a-date",
                                "tradeDate": None, "settlementDate": None}])
    assert report.fills == []
    assert report.unmapped[0]["why"] == "no parseable timestamp"


def test_empty_input_is_an_empty_report_not_an_error():
    report = map_transactions([])
    assert isinstance(report, ImportReport)
    assert report.raw_count == 0 and report.mapped_count == 0


def test_base_url_is_the_documented_host():
    assert BASE_URL == "https://api.schwabapi.com"


# ------------------------------------------------- the auth helper (scripts/schwab_auth.py)

def _auth_module():
    """Import the script by path — scripts/ is not a package."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "schwab_auth.py"
    spec = importlib.util.spec_from_file_location("schwab_auth", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_auth_url_encodes_the_callback():
    """An unencoded redirect_uri silently produces a mismatch Schwab rejects."""
    url = _auth_module().build_auth_url("KEY 1", "https://127.0.0.1")
    assert "client_id=KEY%201" in url
    assert "redirect_uri=https%3A%2F%2F127.0.0.1" in url


def test_code_survives_schwab_url_encoding():
    """Schwab's code is URL-encoded and ends with '@'. Splitting on '=' mangles it."""
    m = _auth_module()
    pasted = "https://127.0.0.1/?code=C0.abc%2Bdef%3D%3D%40&session=xyz"
    assert m.extract_code(pasted) == "C0.abc+def==@"


def test_paste_errors_say_what_was_wrong():
    m = _auth_module()
    with pytest.raises(ValueError, match="Nothing pasted"):
        m.extract_code("   ")
    with pytest.raises(ValueError, match="ENTIRE address"):
        m.extract_code("https://127.0.0.1/")
    with pytest.raises(ValueError, match="Parameters found: error, session"):
        m.extract_code("https://127.0.0.1/?error=access_denied&session=z")


def test_write_env_replaces_the_line_and_keeps_the_rest(tmp_path, monkeypatch):
    m = _auth_module()
    env = tmp_path / ".env"
    env.write_text("ALPACA_API_KEY_ID=keep-me\nSCHWAB_REFRESH_TOKEN=old\nFRED_API_KEY=also\n",
                   encoding="utf-8")
    monkeypatch.setattr(m, "ROOT", tmp_path)
    m.write_env("brand-new")
    text = env.read_text(encoding="utf-8")
    assert "SCHWAB_REFRESH_TOKEN=brand-new" in text
    assert "ALPACA_API_KEY_ID=keep-me" in text and "FRED_API_KEY=also" in text
    assert "old" not in text


def test_write_env_appends_when_the_key_is_absent(tmp_path, monkeypatch):
    m = _auth_module()
    env = tmp_path / ".env"
    env.write_text("ALPACA_API_KEY_ID=keep-me\n", encoding="utf-8")
    monkeypatch.setattr(m, "ROOT", tmp_path)
    m.write_env("fresh")
    assert "SCHWAB_REFRESH_TOKEN=fresh" in env.read_text(encoding="utf-8")


# --- T105 / I020: options are the majority of this account -------------------

OPTION_ROW = {
    "activityId": 5001,
    "type": "TRADE",
    "status": "VALID",
    "time": "2026-03-13T14:31:00+0000",
    "orderId": "ORD-OPT",
    "transferItems": [
        {"instrument": {"assetType": "CURRENCY"}, "amount": -89.0},
        {"instrument": {"symbol": "NVDA  260313P00180000", "assetType": "OPTION",
                        "underlyingSymbol": "NVDA", "putCall": "PUT",
                        "strikePrice": 180.0, "expirationDate": "2026-03-13"},
         "amount": 8, "price": 0.89},
        {"instrument": {"assetType": "FEE"}, "amount": -0.01, "feeType": "OCC"},
    ],
}


def test_option_trades_map_instead_of_being_discarded():
    """I020: the first mapper reported options as unmapped BY DESIGN.

    The owner's real confirmations are 147 option fills out of 250, and 62% of
    those are 0DTE. Discarding them would have left every behavioural conclusion
    describing the leftover 41% of his trading.
    """
    report = map_transactions([OPTION_ROW])
    assert report.unmapped == []
    assert len(report.fills) == 1
    f = report.fills[0]
    assert f.side == "buy" and f.qty == 8 and f.price == 0.89
    assert f.fill_type == "option"          # what tells attribution to apply 100x


def test_option_fill_is_marked_so_the_multiplier_can_be_applied():
    """One contract at $0.89 is $89 of exposure. Counting it as one share
    understates the position by 100x — across 147 fills."""
    f = map_transactions([OPTION_ROW]).fills[0]
    equity = map_transactions([TRADE_ROW]).fills[0]
    assert f.fill_type == "option"
    assert equity.fill_type == "fill"


def test_cash_and_fee_legs_are_never_mistaken_for_the_fill():
    """Both legs precede the security leg in this payload; a naive 'first priced
    item' rule would pick the wrong one."""
    row = {
        **OPTION_ROW, "activityId": 5002,
        "transferItems": [
            {"instrument": {"assetType": "CURRENCY"}, "amount": -89.0, "price": 1.0},
            {"instrument": {"assetType": "FEE"}, "amount": -0.01, "price": 0.01},
            {"instrument": {"symbol": "SPY", "assetType": "OPTION"},
             "amount": 1, "price": 7.15},
        ],
    }
    f = map_transactions([row]).fills[0]
    assert f.symbol == "SPY" and f.price == 7.15


def test_underlying_symbol_is_used_when_the_occ_symbol_is_absent():
    row = {
        **OPTION_ROW, "activityId": 5003,
        "transferItems": [
            {"instrument": {"assetType": "OPTION", "underlyingSymbol": "AMD"},
             "amount": 2, "price": 1.25},
        ],
    }
    assert map_transactions([row]).fills[0].symbol == "AMD"


# ------------------------------------------------ I029: observed-row regressions

PLACEHOLDER_DATE_ROW = {
    # Faithful shape of observed row ...468374 (owner's March 2026 probe):
    # real execution in `time`, date-only placeholder (midnight ET) in
    # `tradeDate`. The mapper must trust `time`.
    "activityId": 468374,
    "time": "2026-03-06T15:24:20+0000",
    "tradeDate": "2026-03-06T05:00:00+0000",
    "type": "TRADE",
    "status": "VALID",
    "orderId": 1005629000000,
    "netAmount": 1530.15,
    "transferItems": [
        {"instrument": {"assetType": "CURRENCY", "symbol": "CURRENCY_USD"},
         "amount": 0.0, "cost": 0.0, "feeType": "SEC_FEE"},
        {"instrument": {"symbol": "GDX", "assetType": "EQUITY"},
         "amount": -15, "price": 102.01},
    ],
}


def test_execution_time_beats_the_placeholder_trade_date():
    """I029: the owner read '05:00:00' on his reconcile printout and correctly
    said that is not when he traded. `time` carries 15:24:20Z (11:24 ET);
    `tradeDate` carries the midnight placeholder. `time` wins."""
    rep = map_transactions([PLACEHOLDER_DATE_ROW])
    assert len(rep.fills) == 1
    f = rep.fills[0]
    assert f.occurred_at == datetime(2026, 3, 6, 15, 24, 20, tzinfo=timezone.utc)
    assert f.side == "sell" and f.symbol == "GDX"


def test_normal_rows_unchanged_by_the_preference_swap():
    """Rows where time == tradeDate (50 of the 51 observed) map identically."""
    rep = map_transactions([TRADE_ROW])
    assert rep.fills[0].occurred_at == T0
