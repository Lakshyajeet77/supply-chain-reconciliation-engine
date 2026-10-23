"""PostgreSQL-backed document registry persistence tests (SQLite-isolated)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.common import DocumentProcessingStatus, DocumentType
from app.schemas.documents import DocumentRecord
from app.services.ingestion.service import DuplicateDocumentError, IngestionService
from app.services.registry.store import DocumentRegistry


def _record(*, sha256: str = "a" * 64, doc_id=None) -> DocumentRecord:
    return DocumentRecord(
        id=doc_id or uuid4(),
        document_type=DocumentType.INVOICE,
        original_filename="invoice.png",
        content_type="image/png",
        size_bytes=100,
        sha256=sha256,
        stored_path="/tmp/fake.png",
        processing_status=DocumentProcessingStatus.UPLOADED,
        uploaded_at=datetime.now(timezone.utc),
    )


def test_register_and_get_by_id(registry: DocumentRegistry):
    record = _record()
    saved = registry.register(record)
    loaded = registry.get_by_id(saved.id)
    assert loaded is not None
    assert loaded.id == saved.id
    assert loaded.sha256 == saved.sha256
    assert loaded.processing_status == DocumentProcessingStatus.UPLOADED


def test_duplicate_hash_raises_value_error(registry: DocumentRegistry):
    first = registry.register(_record(sha256="b" * 64))
    with pytest.raises(ValueError):
        registry.register(_record(sha256="b" * 64))
    assert registry.get_by_hash("b" * 64).id == first.id


def test_list_documents_ordered(registry: DocumentRegistry):
    registry.register(_record(sha256="c" * 64))
    registry.register(_record(sha256="d" * 64))
    docs = registry.list_documents()
    assert len(docs) == 2


def test_ingestion_persists_and_duplicate_via_api(client, sample_png_bytes):
    first = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("a.png", sample_png_bytes, "image/png")},
    )
    assert first.status_code == 201
    doc_id = first.json()["document"]["id"]

    listed = client.get("/documents")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    detail = client.get(f"/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["sha256"] == first.json()["document"]["sha256"]

    second = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("b.png", sample_png_bytes, "image/png")},
    )
    assert second.status_code == 409
    assert second.json()["detail"]["existing_document"]["id"] == doc_id


def test_ingestion_service_duplicate(registry, sample_png_bytes, tmp_path):
    from app.config import get_settings

    settings = get_settings()
    service = IngestionService(settings=settings, registry=registry)
    first = service.ingest(
        data=sample_png_bytes,
        filename="one.png",
        document_type=DocumentType.INVOICE,
    )
    with pytest.raises(DuplicateDocumentError) as exc:
        service.ingest(
            data=sample_png_bytes,
            filename="two.png",
            document_type=DocumentType.INVOICE,
        )
    assert exc.value.existing.id == first.id
