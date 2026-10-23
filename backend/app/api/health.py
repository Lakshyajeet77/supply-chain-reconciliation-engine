from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.db.session import get_engine
from app.logging_config import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — process is up."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    """Readiness probe — database is reachable."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed: database unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Database unavailable"},
        ) from None
    return {"status": "ready"}
