"""KUBERA API entrypoint.

Run locally:  uvicorn --app-dir backend api.main:app --reload
"""

from datetime import datetime, timezone

from fastapi import FastAPI

from settings import get_settings

VERSION = "0.1.0"

app = FastAPI(title="KUBERA API", version=VERSION)


@app.get("/health")
def health() -> dict:
    """Liveness check. Every KUBERA payload is timestamped (AGENTS.md: no undated data)."""
    s = get_settings()
    return {
        "status": "ok",
        "service": "kubera-api",
        "version": VERSION,
        "time": datetime.now(timezone.utc).isoformat(),
        # Config state only — never config values.
        "alpaca_configured": s.alpaca_configured,
        "paper_mode": s.alpaca_paper,
    }
