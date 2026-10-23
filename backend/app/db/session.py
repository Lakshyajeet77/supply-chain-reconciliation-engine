"""SQLAlchemy 2.x engine and session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        connect_args: dict = {}
        url = settings.database_url
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        try:
            _engine = create_engine(
                url,
                pool_pre_ping=True,
                connect_args=connect_args,
            )
            _session_factory = sessionmaker(
                bind=_engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
            logger.info("Database engine created")
        except Exception:
            logger.exception("Failed to create database engine")
            raise
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a session and close it afterward."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_db_state() -> None:
    """Dispose engine/session factory (used by tests when DATABASE_URL changes)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
