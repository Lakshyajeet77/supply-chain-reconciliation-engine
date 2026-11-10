"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import documents, health, reconciliation, reviews, reconciliation_approved, document_relationships
from app.config import get_settings
from app.db.session import get_engine
from app.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Application starting name=%s env=%s",
        settings.app_name,
        settings.app_env,
    )
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception:
        logger.exception(
            "Database connection failed at startup; "
            "API will return errors until the database is reachable"
        )

    yield

    logger.info("Application shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description=(
            "Supply-chain document reconciliation support system. "
            "MATCHED is not payment authorization. "
            "Local MVP has no authentication — do not expose publicly."
        ),
        lifespan=lifespan,
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("Request validation error detail=%s", exc.errors())
        return JSONResponse(
            status_code=422,
            content={"message": "Validation error", "detail": exc.errors()},
        )

    application.include_router(health.router)
    application.include_router(documents.router)
    application.include_router(reconciliation.router)
    application.include_router(reviews.router)
    application.include_router(reconciliation_approved.router)
    application.include_router(document_relationships.router)

    # Local MVP has no authentication; restrict CORS to the configured dev origins.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    return application


app = create_app()
