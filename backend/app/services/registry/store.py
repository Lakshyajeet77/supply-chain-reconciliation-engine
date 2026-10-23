"""
PostgreSQL-backed document registry (SQLAlchemy session scoped).

Unique sha256 enforces exact-file duplicate detection under concurrency.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.document import Document
from app.schemas.common import DocumentProcessingStatus, DocumentType
from app.schemas.documents import DocumentRecord

logger = get_logger(__name__)


class PersistenceError(RuntimeError):
    """Raised when a required database write fails."""


class DocumentRegistry:
    """Document metadata store backed by the documents table."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def clear(self) -> None:
        """Delete all documents (test isolation only)."""
        self.session.execute(delete(Document))
        self.session.commit()

    def get_by_id(self, document_id: UUID) -> DocumentRecord | None:
        row = self.session.get(Document, document_id)
        return self._to_record(row) if row else None

    def get_by_hash(self, sha256: str) -> DocumentRecord | None:
        row = self.session.scalar(select(Document).where(Document.sha256 == sha256))
        return self._to_record(row) if row else None

    def list_documents(self) -> list[DocumentRecord]:
        rows = self.session.scalars(
            select(Document).order_by(Document.uploaded_at.desc())
        ).all()
        return [self._to_record(row) for row in rows]

    def register(self, record: DocumentRecord) -> DocumentRecord:
        """
        Persist a new document.

        Raises ValueError if sha256 already exists (exact-file duplicate).
        Raises PersistenceError if the database write fails for other reasons.
        """
        existing = self.get_by_hash(record.sha256)
        if existing is not None:
            raise ValueError(f"Document with sha256={record.sha256} already exists")

        row = Document(
            id=record.id,
            document_type=record.document_type.value,
            original_filename=record.original_filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            sha256=record.sha256,
            stored_path=record.stored_path,
            processing_status=record.processing_status.value,
            uploaded_at=record.uploaded_at,
            extraction_fixture_id=record.extraction_fixture_id,
            failure_reason=record.failure_reason,
        )
        self.session.add(row)
        try:
            self.session.commit()
            self.session.refresh(row)
        except IntegrityError:
            self.session.rollback()
            logger.info(
                "Duplicate sha256 rejected by database constraint document_id=%s",
                record.id,
            )
            raise ValueError(f"Document with sha256={record.sha256} already exists") from None
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception(
                "Failed to persist document document_id=%s",
                record.id,
            )
            raise PersistenceError("Failed to persist document metadata") from exc

        logger.info(
            "Document registered document_id=%s type=%s status=%s",
            record.id,
            record.document_type.value,
            record.processing_status.value,
        )
        return self._to_record(row)

    def update(self, record: DocumentRecord) -> DocumentRecord:
        row = self.session.get(Document, record.id)
        if row is None:
            raise KeyError(f"Unknown document id={record.id}")
        if row.sha256 != record.sha256:
            raise ValueError("SHA-256 of an existing document cannot change")

        previous_status = row.processing_status
        row.document_type = record.document_type.value
        row.original_filename = record.original_filename
        row.content_type = record.content_type
        row.size_bytes = record.size_bytes
        row.stored_path = record.stored_path
        row.processing_status = record.processing_status.value
        row.extraction_fixture_id = record.extraction_fixture_id
        row.failure_reason = record.failure_reason

        try:
            self.session.commit()
            self.session.refresh(row)
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception(
                "Failed to update document document_id=%s",
                record.id,
            )
            raise PersistenceError("Failed to update document metadata") from exc

        if previous_status != row.processing_status:
            logger.info(
                "Document status changed document_id=%s from=%s to=%s",
                record.id,
                previous_status,
                row.processing_status,
            )
        return self._to_record(row)

    @staticmethod
    def _to_record(row: Document) -> DocumentRecord:
        return DocumentRecord(
            id=row.id,
            document_type=DocumentType(row.document_type),
            original_filename=row.original_filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            sha256=row.sha256,
            stored_path=row.stored_path,
            processing_status=DocumentProcessingStatus(row.processing_status),
            uploaded_at=row.uploaded_at,
            extraction_fixture_id=row.extraction_fixture_id,
            failure_reason=row.failure_reason,
        )
