"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import documents, health, reconciliation
from app.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
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
        return JSONResponse(
            status_code=422,
            content={"message": "Validation error", "detail": exc.errors()},
        )

    application.include_router(health.router)
    application.include_router(documents.router)
    application.include_router(reconciliation.router)
    return application


app = create_app()
