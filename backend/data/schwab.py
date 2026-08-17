"""T016 — Schwab Trader API, READ-ONLY (D026, D009).

Why this exists: every behavioural module in KUBERA — holding periods (T091b),
sizing drift and post-loss tempo (T069), slippage by hour (T088), give-back
(T089) — currently reads Alpaca PAPER fills. Those are trades KUBERA's own loop
made. They say nothing about how the owner actually trades. This module is the
adapter that lets the same analysis read his real record.

THREE THINGS THAT ARE NOT LIKE ALPACA, and each one has bitten somebody:

1. AUTH IS OAUTH, NOT A KEY PAIR. Requests carry `Authorization: Bearer <access
   token>`; the access token is short-lived and is minted from a refresh token
   that the owner authorises in a browser. So the client refreshes on demand and
   on a 401, and a dead refresh token produces an actionable message rather than
   a wall of 401s.

2. THE ACCOUNT NUMBER IS NOT THE URL KEY. Schwab addresses accounts by an
   encrypted hash obtained from `/accounts/accountNumbers`; the plain number is
   only for recognising which account is which. This is why "just type your
   account number" was never going to be the whole story.

3. TRANSACTIONS ARE NOT FILLS. A Schwab transaction is a container: one TRADE
   carries `transferItems` — an equity leg, a cash leg, sometimes fees. The fill
   lives in the equity leg. Mapping is therefore lossy in both directions if done
   carelessly, which is exactly why D026 makes RECONCILIATION the acceptance
   criterion for this ticket rather than "it ran".

HONESTY ABOUT THE SHAPES BELOW: the response structures are written from Schwab's
published documentation and have NOT yet been checked against a live pull — the
sandbox cannot reach api.schwabapi.com, same as Alpaca (I002). Every mapper here
therefore REPORTS what it could not interpret instead of dropping it silently.
A row KUBERA cannot explain must never disappear quietly; that is how an import
becomes wrong without anyone noticing, and a wrong import does not crash, it just
changes every conclusion downstream (I018's lesson, applied before the fact).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

# The canonical broker-neutral shapes. They live in data.alpaca today because it
# was the first broker; when a third arrives they should move to a shared
# data/broker_types.py. Reusing them is deliberate — it is what lets every
# existing analysis module read Schwab history with no changes at all.
from data.alpaca import CashActivity, Fill
from settings import ConfigError, KuberaSettings, get_settings

BASE_URL = "https://api.schwabapi.com"
TRADER = "/trader/v1"
TOKEN_PATH = "/v1/oauth/token"
SOURCE = "schwab"

# Refresh a little before expiry so a long request cannot straddle the boundary.
TOKEN_SKEW_SECONDS = 60.0
TIMEOUT_SECONDS = 30.0


class SchwabError(RuntimeError):
    """Schwab API problem. Messages are actionable and never contain secrets."""


@dataclass(frozen=True)
class SchwabAccount:
    """One account. `hash_value` is what URLs use; `number_masked` is for humans."""

    number_masked: str
    hash_value: str


@dataclass(frozen=True)
class ImportReport:
    """What came back, and — more importantly — what did not map.

    `unmapped` is the honest half. Every entry names the activity id and why it
    was skipped, so reconciliation against a statement can account for the gap
    instead of quietly tolerating it.
    """

    fills: list[Fill] = field(default_factory=list)
    cash: list[CashActivity] = field(default_factory=list)
    unmapped: list[dict] = field(default_factory=list)
    raw_count: int = 0

    @property
    def mapped_count(self) -> int:
        return len(self.fills) + len(self.cash)

    def summary(self) -> str:
        return (
            f"{self.raw_count} transactions in, {self.mapped_count} mapped "
            f"({len(self.fills)} fills, {len(self.cash)} cash), "
            f"{len(self.unmapped)} unmapped"
        )


def _utc(value: str | None) -> datetime | None:
    """Schwab timestamps arrive in several ISO flavours. None on anything unparseable."""
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    # "+0000" (no colon) appears in some Schwab payloads; fromisoformat wants "+00:00".
    if len(text) >= 5 and (text[-5] in "+-") and text[-3] != ":":
        text = text[:-2] + ":" + text[-2:]
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class SchwabClient:
    """Read-only Schwab client.

    There are no order methods on this class, and that is a design constraint
    rather than an omission (D026): read-only until the PROJECT_SPEC §7.4 gate
    passes. A bug in fresh import code must not be able to reach an order.
    """

    def __init__(
        self,
        settings: KuberaSettings | None = None,
        transport: httpx.BaseTransport | None = None,
        clock=time.monotonic,
    ):
        self._s = (settings or get_settings()).require_schwab()
        self._clock = clock
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._http = httpx.Client(
            base_url=self._s.schwab_base_url, timeout=TIMEOUT_SECONDS, transport=transport
        )

    # ---------------------------------------------------------------- lifecycle

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "SchwabClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ---------------------------------------------------------------- auth

    def _refresh_token(self) -> str:
        """Mint an access token from the refresh token. Never logs either."""
        assert self._s.schwab_app_secret is not None      # require_schwab() guarantees
        assert self._s.schwab_refresh_token is not None
        try:
            resp = self._http.post(
                self._s.schwab_token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._s.schwab_refresh_token.get_secret_value(),
                },
                auth=(self._s.schwab_app_key or "",
                      self._s.schwab_app_secret.get_secret_value()),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as e:
            raise SchwabError(f"Network error refreshing the Schwab token: {e!r}") from e

        if resp.status_code >= 400:
            # The overwhelmingly common cause, and it is time-based rather than
            # a typo — say so, because "401" alone sends people hunting the wrong bug.
            raise SchwabError(
                "Schwab token refresh failed "
                f"(HTTP {resp.status_code}). Refresh tokens expire roughly weekly — "
                "re-authorise in a browser and update SCHWAB_REFRESH_TOKEN in .env. "
                "Run: python scripts/schwab_auth.py"
            )

        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise SchwabError("Schwab token response contained no access_token.")
        self._token = token
        self._token_expires_at = (
            self._clock() + float(payload.get("expires_in", 1800)) - TOKEN_SKEW_SECONDS
        )
        return token

    def _bearer(self) -> str:
        if self._token is None or self._clock() >= self._token_expires_at:
            return self._refresh_token()
        return self._token

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        """GET with one automatic retry after a token refresh on 401."""
        for attempt in (1, 2):
            try:
                resp = self._http.get(
                    f"{TRADER}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {self._bearer()}"},
                )
            except httpx.HTTPError as e:
                raise SchwabError(f"Network error calling schwab {path}: {e!r}") from e

            if resp.status_code == 401:
                if attempt == 1:
                    self._token = None      # force a refresh, then try once more
                    continue
                # Second 401 with a token minted seconds ago is not an expiry
                # problem, so saying "HTTP 401" would send the reader hunting the
                # wrong bug. Name the two causes that actually produce this.
                raise SchwabError(
                    f"schwab {path}: still unauthorised after a fresh token. Either the "
                    "app is not approved for this account, or its scopes do not cover "
                    "this endpoint. Check the app's status at developer.schwab.com — "
                    "re-authorising will not help."
                )
            if resp.status_code >= 400:
                raise SchwabError(
                    f"schwab {path} failed: HTTP {resp.status_code} — {resp.text[:200]}"
                )
            return resp
        raise SchwabError(f"schwab {path}: retry loop exhausted.")  # unreachable

    # ---------------------------------------------------------------- reads

    def list_accounts(self) -> list[SchwabAccount]:
        """Account numbers with their URL hashes. The first call any flow makes."""
        rows = self._get("/accounts/accountNumbers").json()
        out = []
        for r in rows if isinstance(rows, list) else []:
            number, hashed = r.get("accountNumber"), r.get("hashValue")
            if number and hashed:
                out.append(SchwabAccount(number_masked=_mask(str(number)), hash_value=hashed))
        if not out:
            raise SchwabError(
                "Schwab returned no accounts. Confirm the app is approved for this "
                "account and that the refresh token belongs to the same login."
            )
        return out

    def get_transactions(
        self, account_hash: str, start: datetime, end: datetime, types: str = "TRADE"
    ) -> list[dict]:
        """Raw transactions for a window. Returned unmapped on purpose — the
        caller maps them, so the raw payload stays available for reconciliation."""
        resp = self._get(
            f"/accounts/{account_hash}/transactions",
            params={
                "startDate": _api_date(start),
                "endDate": _api_date(end),
                "types": types,
            },
        )
        body = resp.json()
        return body if isinstance(body, list) else []


def _mask(number: str) -> str:
    """Never carry a full account number around in memory or logs."""
    return f"***{number[-4:]}" if len(number) > 4 else "***"


def _api_date(dt: datetime) -> str:
    """Schwab wants ISO-8601 with milliseconds and a Z."""
    aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# -------------------------------------------------------------------- mapping

def map_transactions(rows: list[dict]) -> ImportReport:
    """Turn Schwab transactions into the Fill/CashActivity shapes KUBERA already reads.

    Every row that cannot be interpreted lands in `unmapped` WITH A REASON. That
    is the whole discipline here: a statement reconciliation can only account for
    a discrepancy if the importer admits what it skipped.
    """
    report = ImportReport(raw_count=len(rows))
    now = datetime.now(timezone.utc)

    for row in rows:
        activity_id = str(row.get("activityId") or row.get("transactionId") or "")
        kind = str(row.get("type") or "").upper()
        occurred = _utc(row.get("tradeDate") or row.get("time") or row.get("settlementDate"))

        if not activity_id:
            report.unmapped.append({"row": _brief(row), "why": "no activityId"})
            continue
        if occurred is None:
            report.unmapped.append({"id": activity_id, "why": "no parseable timestamp"})
            continue
        if str(row.get("status", "VALID")).upper() not in {"VALID", ""}:
            report.unmapped.append(
                {"id": activity_id, "why": f"status={row.get('status')} (not VALID)"})
            continue

        if kind == "TRADE":
            leg = _security_leg(row)
            if leg is None:
                report.unmapped.append(
                    {"id": activity_id, "why": "TRADE with no priced security leg "
                                               "(multi-leg spread or corporate action)"})
                continue
            qty, price, symbol, asset_type = leg
            report.fills.append(Fill(
                external_id=activity_id,
                symbol=symbol,
                side="buy" if qty > 0 else "sell",
                qty=abs(qty),
                price=price,
                occurred_at=occurred,
                order_id=str(row.get("orderId") or ""),
                # An option fill is per CONTRACT. Recording the type here is what
                # lets attribution apply the 100x multiplier instead of treating
                # one contract as one share (I020).
                fill_type="option" if asset_type == "option" else "fill",
                asof=now,
                source=SOURCE,
            ))
        elif kind in {"ACH_RECEIPT", "ACH_DISBURSEMENT", "CASH_RECEIPT",
                      "CASH_DISBURSEMENT", "WIRE_IN", "WIRE_OUT", "JOURNAL"}:
            amount = row.get("netAmount")
            if amount is None:
                report.unmapped.append({"id": activity_id, "why": f"{kind} with no netAmount"})
                continue
            report.cash.append(CashActivity(
                external_id=activity_id,
                kind="deposit" if float(amount) > 0 else "withdrawal",
                amount=float(amount),
                occurred_at=occurred,
                asof=now,
                source=SOURCE,
            ))
        else:
            report.unmapped.append({"id": activity_id, "why": f"unhandled type {kind!r}"})

    return report


OPTION_MULTIPLIER = 100


def _security_leg(row: dict) -> tuple[float, float, str, str] | None:
    """Find the (qty, price, symbol, asset_type) leg of a TRADE.

    A Schwab TRADE carries several transferItems — the security, the cash side,
    and sometimes fees. Only the one with a symbol AND a price is the fill.

    I020 — WHY THIS IS NO LONGER EQUITY-ONLY. The first version accepted the
    priced symbol leg and reported everything else as "no priced equity leg",
    which classified options as unmapped BY DESIGN. That was defensible while we
    believed this was an equity account. Parsing the owner's real confirmations
    (T102) showed 147 of 250 fills are options and 62% of those are 0DTE — so the
    original mapper would have silently discarded the majority of his trading and
    every behavioural conclusion would have described the leftover 41%.
    """
    for item in row.get("transferItems") or []:
        instrument = item.get("instrument") or {}
        symbol = instrument.get("symbol") or instrument.get("underlyingSymbol")
        price = item.get("price")
        amount = item.get("amount")
        if not (symbol and price is not None and amount is not None):
            continue
        asset = str(instrument.get("assetType") or "").upper()
        if asset in {"CURRENCY", "FEE"}:      # never the fill, even if priced
            continue
        kind = "option" if asset == "OPTION" else "equity"
        try:
            return float(amount), float(price), str(symbol).upper(), kind
        except (TypeError, ValueError):
            return None
    return None


def _brief(row: dict) -> dict:
    """A small, non-sensitive excerpt of a row for an unmapped report."""
    return {k: row.get(k) for k in ("type", "status", "time", "tradeDate") if k in row}


def require_schwab_or_explain(settings: KuberaSettings | None = None) -> str | None:
    """Return None if configured, else a message the owner can act on."""
    try:
        (settings or get_settings()).require_schwab()
        return None
    except ConfigError as e:
        return str(e)
