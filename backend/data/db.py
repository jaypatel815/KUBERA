"""Engine and session factory. One place decides the database URL (settings, D007)."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from settings import get_settings


def make_engine(url: str | None = None) -> Engine:
    """Engine for the given URL (or the configured one). SQLite needs the thread flag."""
    url = url or get_settings().database_url
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
