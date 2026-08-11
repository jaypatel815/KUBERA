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

from settings import ConfigError, KuberaSettings, get_settings

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
        assert s.alpaca_api_secret_key is not None  # guaranteed by require_alpaca()
        self._http = httpx.Client(
            base_url=PAPER_BASE_URL,
            headers={
                "APCA-API-KEY-ID": s.alpaca_api_key_id or "",
                "APCA-API-SECRET-KEY": s.alpaca_api_secret_key.get_secret_value(),
            },
            timeout=15.0,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "AlpacaClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str) -> httpx.Response:
        try:
            resp = self._http.get(path)
        except httpx.HTTPError as e:
            raise AlpacaError(f"Network error calling Alpaca {path}: {e!r}") from e
        if resp.status_code == 401:
            raise AlpacaError(
                "Alpaca rejected the API keys (401). Check ALPACA_API_KEY_ID / "
                "ALPACA_API_SECRET_KEY in .env — paper keys are generated on the "
                "paper dashboard, and regenerate if in doubt."
            )
        if resp.status_code >= 400:
            raise AlpacaError(f"Alpaca {path} failed: HTTP {resp.status_code} — {resp.text[:200]}")
        return resp

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
