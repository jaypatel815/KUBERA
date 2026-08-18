"""Alpaca paper-trading client (T011).

Thin, auditable layer over Alpaca's REST API using httpx — no SDK dependency.
Every payload is timestamped (`asof`) and sourced (`source`), per AGENTS.md.

SAFETY RAIL (code, not prompt): this client refuses to construct against the
live-money endpoint. Live trading requires the PROJECT_SPEC §7.4 promotion gate,
which does not exist yet — so there is deliberately no code path to real capital.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from data._http import build_client, checked_get
from data.market_data import parse_rfc3339
from settings import ConfigError, KuberaSettings, get_settings

# Deliberately hardcoded (D028): PAPER_BASE_URL is a safety rail against live money.
# Configurable would mean pointable at live capital before spec §7.4 promotion.
PAPER_BASE_URL = "https://paper-api.alpaca.markets"
SOURCE = "alpaca-paper"


class AlpacaError(RuntimeError):
    """Alpaca API returned an error; message includes status code and hint."""


@dataclass(frozen=True)
class AccountSnapshot:
    external_id: str  # broker's account number — identifies the account across syncs
    status: str
    currency: str
    cash: float
    equity: float
    buying_power: float
    asof: datetime
    source: str = SOURCE


@dataclass(frozen=True)
class OrderResult:
    external_id: str
    symbol: str
    side: str
    qty: float
    status: str  # e.g. "accepted", "new", "filled"
    asof: datetime
    source: str = SOURCE


@dataclass(frozen=True)
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    asof: datetime
    source: str = SOURCE




@dataclass(frozen=True)
class Fill:
    """One executed fill from the activities feed (T036) — the ground truth that
    slippage/attribution (T088/T091) are built on."""

    external_id: str
    symbol: str
    side: str
    qty: float
    price: float
    occurred_at: datetime
    order_id: str
    fill_type: str  # "fill" | "partial_fill" | "option" (Schwab, T016c)
    asof: datetime
    # T016c: per-trade costs where the broker reports them (Schwab transferItems
    # carry COMMISSION and regulatory-fee legs; Alpaca fills default to 0).
    commission: float = 0.0
    fees: float = 0.0
    source: str = SOURCE


def _as_utc(dt: datetime) -> datetime:
    """Date-only broker fields parse naive; every KUBERA timestamp is tz-aware."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class CashActivity:
    """A deposit or withdrawal (T060). `amount` is signed: + in, − out."""

    external_id: str
    kind: str          # deposit | withdrawal
    amount: float
    occurred_at: datetime
    asof: datetime
    source: str = SOURCE


@dataclass(frozen=True)
class Clock:
    """The broker's own market clock — no local timezone guessing."""

    is_open: bool
    timestamp: datetime
    next_open: datetime
    next_close: datetime
    asof: datetime
    source: str = SOURCE



class AlpacaClient:
    """Paper-account client. `AlpacaClient()` for real use; inject settings/transport in tests."""

    def __init__(
        self,
        settings: KuberaSettings | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        s = (settings or get_settings()).require_alpaca()
        if not s.alpaca_paper:
            # §7.4 gate does not exist yet; there is no live code path on purpose.
            raise ConfigError(
                "ALPACA_PAPER=false is not supported: live trading is gated by "
                "PROJECT_SPEC.md §7.4, which is not implemented. Set ALPACA_PAPER=true."
            )
        self._http = build_client(PAPER_BASE_URL, s, transport)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "AlpacaClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        return checked_get(
            self._http,
            path,
            params=params,
            error_cls=AlpacaError,
            label="Alpaca",
            unauthorized_hint=(
                "Alpaca rejected the API keys (401). Check ALPACA_API_KEY_ID / "
                "ALPACA_API_SECRET_KEY in .env — paper keys are generated on the "
                "paper dashboard, and regenerate if in doubt."
            ),
        )

    def get_account(self) -> AccountSnapshot:
        d = self._get("/v2/account").json()
        return AccountSnapshot(
            external_id=str(d.get("account_number") or d["id"]),
            status=d["status"],
            currency=d["currency"],
            cash=float(d["cash"]),
            equity=float(d["equity"]),
            buying_power=float(d["buying_power"]),
            asof=datetime.now(timezone.utc),
        )


    def get_fills(self, after: datetime | None = None) -> list[Fill]:
        """Executed fills (activities API), oldest first. `after` filters server-side."""
        params: dict = {"direction": "asc", "page_size": 100}
        if after is not None:
            params["after"] = after.isoformat()
        rows = self._get("/v2/account/activities/FILL", params=params).json()
        out = []
        for r in rows:
            out.append(Fill(
                external_id=str(r["id"]),
                symbol=str(r["symbol"]).upper(),
                side=str(r["side"]),
                qty=float(r["qty"]),
                price=float(r["price"]),
                occurred_at=parse_rfc3339(r["transaction_time"]),
                order_id=str(r.get("order_id") or ""),
                fill_type=str(r.get("type") or "fill"),
                asof=datetime.now(timezone.utc),
            ))
        return out

    def get_cash_activities(self, after: datetime | None = None) -> list[CashActivity]:
        """External cash movements (T060): CSD deposits, CSW withdrawals. These
        are what make a naive return figure lie — a deposit is not performance."""
        out: list[CashActivity] = []
        for kind, activity_type in (("deposit", "CSD"), ("withdrawal", "CSW")):
            params: dict = {"direction": "asc", "page_size": 100}
            if after is not None:
                params["after"] = after.isoformat()
            rows = self._get(f"/v2/account/activities/{activity_type}",
                             params=params).json()
            for r in rows:
                amount = float(r["net_amount"])
                out.append(CashActivity(
                    external_id=str(r["id"]),
                    kind=kind,
                    # Alpaca reports withdrawals negative already; normalize
                    # defensively so the sign always means direction.
                    amount=amount if kind == "deposit" else -abs(amount),
                    # CSD/CSW rows carry a DATE-ONLY "date" (naive when parsed);
                    # KUBERA timestamps are always tz-aware, so anchor to UTC
                    # midnight rather than letting a naive value reach the DB.
                    occurred_at=_as_utc(
                        parse_rfc3339(r.get("date") or r["transaction_time"])),
                    asof=datetime.now(timezone.utc),
                ))
        return sorted(out, key=lambda a: a.occurred_at)

    def get_clock(self) -> Clock:
        """Market open/closed per the BROKER — the loop's market-hours guard (T036)."""
        d = self._get("/v2/clock").json()
        return Clock(
            is_open=bool(d["is_open"]),
            timestamp=parse_rfc3339(d["timestamp"]),
            next_open=parse_rfc3339(d["next_open"]),
            next_close=parse_rfc3339(d["next_close"]),
            asof=datetime.now(timezone.utc),
        )

    def place_order(self, symbol: str, side: str, qty: float) -> OrderResult:
        """Market day order on the PAPER account (the only account this client can reach).

        This method must only ever be called with a RiskDecision.approved order —
        the paper loop enforces that; nothing else in the codebase places orders.
        """
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
        if qty <= 0:
            raise ValueError(f"qty must be > 0, got {qty}")
        try:
            resp = self._http.post(
                "/v2/orders",
                json={
                    "symbol": symbol.upper(),
                    "qty": str(qty),
                    "side": side,
                    "type": "market",
                    "time_in_force": "day",
                },
            )
        except httpx.HTTPError as e:
            raise AlpacaError(f"Network error placing order for {symbol}: {e!r}") from e
        if resp.status_code >= 400:
            raise AlpacaError(
                f"Alpaca order for {symbol} failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )
        d = resp.json()
        return OrderResult(
            external_id=str(d["id"]),
            symbol=d["symbol"],
            side=d["side"],
            qty=float(d["qty"]),
            status=d["status"],
            asof=datetime.now(timezone.utc),
        )

    def get_positions(self) -> list[Position]:
        items = self._get("/v2/positions").json()
        asof = datetime.now(timezone.utc)
        return [
            Position(
                symbol=p["symbol"],
                qty=float(p["qty"]),
                avg_entry_price=float(p["avg_entry_price"]),
                current_price=float(p["current_price"]),
                market_value=float(p["market_value"]),
                cost_basis=float(p["cost_basis"]),
                unrealized_pl=float(p["unrealized_pl"]),
                unrealized_plpc=float(p["unrealized_plpc"]),
                asof=asof,
            )
            for p in items
        ]
