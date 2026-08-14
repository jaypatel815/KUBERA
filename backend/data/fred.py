"""FRED client (T080) — the macro tape, four series, free tier.

Series (documented so nobody guesses):
- T10Y2Y  10-year minus 2-year Treasury spread (negative = inverted curve)
- VIXCLS  CBOE VIX daily close
- DFII10  10-year TIPS yield (a real-rate proxy)
- DFF     effective federal funds rate

FRED publishes each series on its own calendar and marks missing days with a "."
value — the client skips those and returns the latest REAL observation with its
own date. Consumers must show per-series dates (a Friday VIX next to a Wednesday
spread is normal and must be visible).
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from settings import KuberaSettings, get_settings

FRED_BASE_URL = "https://api.stlouisfed.org"
SOURCE = "fred"

SERIES = {
    "yield_curve_10y2y": "T10Y2Y",
    "vix": "VIXCLS",
    "real_rate_10y": "DFII10",
    "fed_funds": "DFF",
}


class FredError(RuntimeError):
    """FRED API failure; message includes status and hint."""


@dataclass(frozen=True)
class Observation:
    series_id: str
    date: str      # the observation's own date — series differ, always show it
    value: float
    asof: datetime  # when KUBERA fetched it
    source: str = SOURCE


class FredClient:
    def __init__(
        self,
        settings: KuberaSettings | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        s = (settings or get_settings()).require_fred()
        self._api_key = s.fred_api_key.get_secret_value()
        self._http = httpx.Client(
            base_url=FRED_BASE_URL, timeout=10.0, transport=transport
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "FredClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def latest(self, series_id: str) -> Observation:
        """Most recent non-missing observation for a series."""
        r = self._http.get(
            "/fred/series/observations",
            params={
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 10,  # enough to skip weekend/holiday "." placeholders
            },
        )
        if r.status_code == 400:
            raise FredError(
                f"FRED rejected the request for '{series_id}' (400) — check the "
                "series id and that FRED_API_KEY is valid"
            )
        if r.status_code != 200:
            raise FredError(f"FRED error {r.status_code} for '{series_id}': {r.text[:200]}")
        for obs in r.json().get("observations", []):
            if obs.get("value") not in (None, "", "."):
                return Observation(
                    series_id=series_id,
                    date=obs["date"],
                    value=float(obs["value"]),
                    asof=datetime.now(timezone.utc),
                )
        raise FredError(f"no usable observations returned for '{series_id}'")
