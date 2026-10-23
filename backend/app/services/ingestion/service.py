"""Document ingestion: validate → hash → duplicate check → store → register."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings
from app.logging_config import get_logger
from app.schemas.common import DocumentProcessingStatus, DocumentType
from app.schemas.documents import DocumentRecord
from app.services.ingestion.hashing import sha256_hex
from app.services.ingestion.storage import FileStorage
from app.services.ingestion.validation import InvalidUploadError, validate_upload
from app.services.registry.store import DocumentRegistry, PersistenceError

logger = get_logger(__name__)


class DuplicateDocumentError(Exception):
    """Exact-file duplicate detected via SHA-256."""

    def __init__(self, existing: DocumentRecord, sha256: str) -> None:
        self.existing = existing
        self.sha256 = sha256
        super().__init__(f"Exact-file duplicate of document {existing.id}")


class IngestionService:
    def __init__(self, settings: Settings, registry: DocumentRegistry) -> None:
        self.settings = settings
        self.registry = registry
        self.storage = FileStorage(settings.upload_dir)

    def ingest(
        self,
        *,
        data: bytes,
        filename: str,
        document_type: DocumentType,
    ) -> DocumentRecord:
        started = time.perf_counter()
        try:
            validated = validate_upload(
                data,
                max_upload_bytes=self.settings.max_upload_bytes,
                declared_filename=filename,
            )
        except InvalidUploadError as exc:
            logger.warning(
                "Upload validation failed filename=%s reason=%s",
                filename,
                str(exc),
            )
            raise

        digest = sha256_hex(data)

        existing = self.registry.get_by_hash(digest)
        if existing is not None:
            logger.info(
                "Exact-file duplicate detected sha256=%s existing_document_id=%s",
                digest,
                existing.id,
            )
            raise DuplicateDocumentError(existing=existing, sha256=digest)

        document_id = uuid4()
        stored_path = self.storage.save(document_id, validated.extension, data)

        record = DocumentRecord(
            id=document_id,
            document_type=document_type,
            original_filename=filename,
            content_type=validated.content_type,
            size_bytes=validated.size_bytes,
            sha256=digest,
            stored_path=str(stored_path),
            processing_status=DocumentProcessingStatus.UPLOADED,
            uploaded_at=datetime.now(timezone.utc),
        )

        try:
            saved = self.registry.register(record)
        except ValueError:
            # Race: another request registered the same hash after our check.
            stored_path.unlink(missing_ok=True)
            existing = self.registry.get_by_hash(digest)
            if existing is not None:
                logger.info(
                    "Exact-file duplicate after race sha256=%s existing_document_id=%s",
                    digest,
                    existing.id,
                )
                raise DuplicateDocumentError(existing=existing, sha256=digest) from None
            raise
        except PersistenceError:
            stored_path.unlink(missing_ok=True)
            logger.error(
                "Upload rejected because persistence failed document_id=%s",
                document_id,
            )
            raise

        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "Upload accepted document_id=%s type=%s status=%s duration_ms=%.1f",
            saved.id,
            saved.document_type.value,
            saved.processing_status.value,
            elapsed_ms,
        )
        return saved
