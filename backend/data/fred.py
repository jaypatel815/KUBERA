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

# T076: release calendars for the event-risk guard. FRED release ids are stable
# and documented; include_release_dates_with_no_data returns SCHEDULED future
# dates. FOMC meetings are not a FRED release — that source decision is T076b.
RELEASES = {
    "CPI": 10,                      # Consumer Price Index
    "Employment Situation": 50,     # the NFP report
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
        assert s.fred_api_key is not None  # require_fred() guarantees
        self._api_key = s.fred_api_key.get_secret_value()
        self._http = httpx.Client(
            base_url=s.fred_base_url, timeout=10.0, transport=transport
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

    def release_dates(self, release_id: int, limit: int = 40) -> list[str]:
        """Release dates (newest first), INCLUDING scheduled future dates."""
        r = self._http.get(
            "/fred/release/dates",
            params={
                "release_id": release_id,
                "api_key": self._api_key,
                "file_type": "json",
                "include_release_dates_with_no_data": "true",
                "sort_order": "desc",
                "limit": limit,
            },
        )
        if r.status_code == 400:
            raise FredError(
                f"FRED rejected release_dates for id {release_id} (400) — check "
                "the release id and that FRED_API_KEY is valid"
            )
        if r.status_code != 200:
            raise FredError(
                f"FRED error {r.status_code} for release {release_id}: {r.text[:200]}"
            )
        return [d["date"] for d in r.json().get("release_dates", []) if d.get("date")]

    def release_calendar(self) -> dict[str, list[str]]:
        """All guarded releases -> their dates. Feeds analysis/events.py."""
        return {name: self.release_dates(rid) for name, rid in RELEASES.items()}
