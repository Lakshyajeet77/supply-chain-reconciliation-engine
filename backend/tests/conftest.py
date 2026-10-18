"""Shared pytest fixtures. Ground-truth fixtures live under tests/fixtures/."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.extraction.fixture_provider import FixtureExtractionProvider
from app.services.registry.memory import get_registry

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXTRACTION_FIXTURES_DIR = FIXTURES_DIR / "extraction"


@pytest.fixture(autouse=True)
def _reset_registry_and_settings(tmp_path, monkeypatch):
    """Isolate uploads and in-memory registry per test."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "10485760")
    get_settings.cache_clear()
    get_registry().clear()
    yield
    get_registry().clear()
    get_settings.cache_clear()


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
    # SOI + APP0 (JFIF) + EOI — enough for our structural checks.
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
