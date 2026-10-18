"""API schemas for document upload and registry records."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import DocumentProcessingStatus, DocumentType


class DocumentRecord(BaseModel):
    """In-memory document metadata for Milestone 0 (replaced by Postgres later)."""

    id: UUID
    document_type: DocumentType
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    stored_path: str
    processing_status: DocumentProcessingStatus
    uploaded_at: datetime
    extraction_fixture_id: str | None = None
    failure_reason: str | None = None


class UploadResponse(BaseModel):
    document: DocumentRecord
    duplicate: bool = False
    message: str = "Document uploaded successfully."


class DuplicateUploadResponse(BaseModel):
    duplicate: bool = True
    message: str
    existing_document: DocumentRecord
    sha256: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentRecord] = Field(default_factory=list)
    count: int
