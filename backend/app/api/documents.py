"""Document upload and listing endpoints."""
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.config import Settings, get_settings
from app.db.session import get_db
from app.logging_config import get_logger
from app.schemas.common import DocumentType
from app.schemas.documents import DocumentListResponse, DocumentRecord, DuplicateUploadResponse, UploadResponse
from app.services.ingestion.service import DuplicateDocumentError, IngestionService
from app.services.ingestion.validation import InvalidUploadError
from app.services.registry.store import DocumentRegistry, PersistenceError
router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)
def get_registry(db: Session = Depends(get_db)) -> DocumentRegistry:
    return DocumentRegistry(db)
def get_ingestion_service(settings: Settings = Depends(get_settings), registry: DocumentRegistry = Depends(get_registry)) -> IngestionService:
    return IngestionService(settings=settings, registry=registry)
@router.post("/upload", response_model=UploadResponse | DuplicateUploadResponse, status_code=status.HTTP_201_CREATED, responses={409: {"model": DuplicateUploadResponse, "description": "Exact-file duplicate"}, 400: {"description": "Invalid upload"}, 503: {"description": "Persistence unavailable"}})
async def upload_document(document_type: DocumentType = Form(...), file: UploadFile = File(...), fixture_id: str | None = Form(None), ingestion: IngestionService = Depends(get_ingestion_service)) -> UploadResponse | DuplicateUploadResponse:
    data = await file.read()
    filename = file.filename or "upload.bin"
    try:
        record = ingestion.ingest(data=data, filename=filename, document_type=document_type, fixture_id=fixture_id)
    except DuplicateDocumentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"duplicate": True, "message": "Exact-file duplicate detected via SHA-256. Extraction was skipped; existing document is referenced.", "sha256": exc.sha256, "existing_document": exc.existing.model_dump(mode="json")}) from exc
    except InvalidUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(exc)}) from exc
    except PersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"message": "Document could not be persisted. Upload was not accepted."}) from exc
    return UploadResponse(document=record, duplicate=False)
@router.get("", response_model=DocumentListResponse)
def list_documents(registry: DocumentRegistry = Depends(get_registry)) -> DocumentListResponse:
    documents = registry.list_documents()
    return DocumentListResponse(documents=documents, count=len(documents))
@router.get("/{document_id}", response_model=DocumentRecord)
def get_document(document_id: UUID, registry: DocumentRegistry = Depends(get_registry)) -> DocumentRecord:
    record = registry.get_by_id(document_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": f"Document {document_id} not found"})
    return record

_CONTENT_TYPES = {"pdf": "application/pdf", "png": "image/png", "jpeg": "image/jpeg"}

@router.get("/{document_id}/file")
def get_document_file(document_id: UUID, registry: DocumentRegistry = Depends(get_registry), settings: Settings = Depends(get_settings)) -> FileResponse:
    """Serve the original uploaded bytes for preview. Path is validated against the registry."""
    record = registry.get_by_id(document_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": f"Document {document_id} not found"})
    stored = Path(record.stored_path)
    if not stored.is_absolute():
        stored = (settings.upload_dir / stored.name).resolve()
    upload_root = settings.upload_dir.resolve()
    try:
        stored.resolve().relative_to(upload_root)
    except ValueError as exc:
        logger.warning("Blocked file access outside upload dir document_id=%s", document_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Stored file unavailable"}) from exc
    if not stored.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Stored file missing on disk"})
    kind = record.content_type.split("/")[0]
    media_type = _CONTENT_TYPES.get(stored.suffix.lstrip(".").lower(), record.content_type)
    if media_type not in _CONTENT_TYPES.values():
        media_type = record.content_type
    logger.info("Serving stored file document_id=%s", document_id)
    return FileResponse(
        stored,
        media_type=media_type,
        filename=record.original_filename,
        content_disposition_type="inline",
    )
