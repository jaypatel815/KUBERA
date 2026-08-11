"""KUBERA API entrypoint.

Run locally:  uvicorn --app-dir backend api.main:app --reload
"""

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException

from data.alpaca import AlpacaClient, AlpacaError
from settings import ConfigError, KuberaSettings, get_settings

VERSION = "0.1.0"

app = FastAPI(title="KUBERA API", version=VERSION)


def get_alpaca_client(s: KuberaSettings = Depends(get_settings)):
    """Yield a paper-account client, or 503 with an actionable message if unconfigured."""
    try:
        client = AlpacaClient(settings=s)
    except ConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    try:
        yield client
    finally:
        client.close()


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


@app.get("/api/account")
def account(client: AlpacaClient = Depends(get_alpaca_client)) -> dict:
    """Live paper-account snapshot — equity, cash, buying power, timestamped."""
    try:
        return asdict(client.get_account())
    except AlpacaError as e:
        raise HTTPException(status_code=502, detail=str(e))
