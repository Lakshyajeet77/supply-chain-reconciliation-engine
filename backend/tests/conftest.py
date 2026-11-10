"""Shared pytest fixtures. Ground-truth fixtures live under tests/fixtures/."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import Base, get_engine, get_session_factory, reset_db_state
from app.main import create_app
from app.models import Document  # noqa: F401 — register metadata
from app.services.extraction.fixture_provider import FixtureExtractionProvider
from app.services.registry.store import DocumentRegistry

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXTRACTION_FIXTURES_DIR = FIXTURES_DIR / "extraction"


@pytest.fixture(autouse=True)
def _isolate_db_and_uploads(tmp_path, monkeypatch):
    """
    Isolate each test with a fresh SQLite database and upload directory.

    Does not touch development PostgreSQL data.
    """
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    db_path = tmp_path / "test.db"

    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "10485760")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("EXTRACTION_PROVIDER_MODE", "fixture")

    get_settings.cache_clear()
    reset_db_state()

    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    yield

    reset_db_state()
    get_settings.cache_clear()


@pytest.fixture
def db_session():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def registry(db_session) -> DocumentRegistry:
    return DocumentRegistry(db_session)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def extraction_provider() -> FixtureExtractionProvider:
    return FixtureExtractionProvider(EXTRACTION_FIXTURES_DIR)


def make_minimal_png() -> bytes:
    """Valid 1x1 PNG (signature + IHDR + IDAT + IEND)."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00\xff\x00\x00")
    idat = chunk(b"IDAT", raw)
    iend = chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def make_minimal_jpeg() -> bytes:
    """Minimal JPEG with SOI, APP0-ish short body, and EOI."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xd9"
    )


def make_minimal_pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def make_corrupt_pdf() -> bytes:
    return b"%PDF-1.4\nthis is not a complete pdf"


@pytest.fixture
def sample_png_bytes() -> bytes:
    return make_minimal_png()


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    return make_minimal_jpeg()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return make_minimal_pdf()
