"""Document ingestion: validate → hash → duplicate check → store → register → optional extract."""
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
from app.services.extraction.orchestrator import ExtractionWorkflow, ExtractionWorkflowError
from app.schemas.extraction_storage import StoredExtractionData
from app.schemas.extraction_storage import ExtractionSource
from app.models.document import Document
logger = get_logger(__name__)
class DuplicateDocumentError(Exception):
    def __init__(self, existing: DocumentRecord, sha256: str) -> None:
        self.existing = existing
        self.sha256 = sha256
        super().__init__(f"Exact-file duplicate of document {existing.id}")
class IngestionService:
    def __init__(self, settings: Settings, registry: DocumentRegistry) -> None:
        self.settings = settings
        self.registry = registry
        self.storage = FileStorage(settings.upload_dir)
        from app.services.extraction.fixture_provider import FixtureExtractionProvider
        from app.services.extraction.llm_extractor import LLMExtractionProvider

        if settings.extraction_provider_mode == "fixture":
            provider = FixtureExtractionProvider(fixtures_dir=settings.extraction_fixtures_dir)
        elif settings.extraction_provider_mode == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY must be set for live extraction")
            provider = LLMExtractionProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        else:
            raise ValueError(f"Unsupported extraction provider mode: {settings.extraction_provider_mode}")
        self.extraction_workflow = ExtractionWorkflow(provider=provider)
    def ingest(self, *, data: bytes, filename: str, document_type: DocumentType, fixture_id: str | None = None) -> DocumentRecord:
        started = time.perf_counter()
        try:
            validated = validate_upload(data, max_upload_bytes=self.settings.max_upload_bytes, declared_filename=filename)
        except InvalidUploadError as exc:
            logger.warning("Upload validation failed filename=%s reason=%s", filename, str(exc))
            raise
        digest = sha256_hex(data)
        existing = self.registry.get_by_hash(digest)
        if existing is not None:
            logger.info("Exact-file duplicate detected sha256=%s existing_document_id=%s", digest, existing.id)
            raise DuplicateDocumentError(existing=existing, sha256=digest)
        document_id = uuid4()
        stored_path = self.storage.save(document_id, validated.extension, data)
        record = DocumentRecord(id=document_id, document_type=document_type, original_filename=filename, content_type=validated.content_type, size_bytes=validated.size_bytes, sha256=digest, stored_path=str(stored_path), processing_status=DocumentProcessingStatus.UPLOADED, uploaded_at=datetime.now(timezone.utc), extraction_fixture_id=fixture_id)
        try:
            saved = self.registry.register(record)
        except ValueError:
            stored_path.unlink(missing_ok=True)
            existing = self.registry.get_by_hash(digest)
            if existing is not None:
                logger.info("Exact-file duplicate after race sha256=%s existing_document_id=%s", digest, existing.id)
                raise DuplicateDocumentError(existing=existing, sha256=digest) from None
            raise
        except PersistenceError:
            stored_path.unlink(missing_ok=True)
            logger.error("Upload rejected because persistence failed document_id=%s", document_id)
            raise
        # Perform extraction if we're in live extraction mode or if a fixture_id is provided
        if self.settings.extraction_provider_mode == "gemini" or fixture_id:
            try:
                saved.processing_status = DocumentProcessingStatus.EXTRACTING
                saved.failure_reason = None
                saved = self.registry.update(saved)

                # If fixture_id is provided, force fixture extraction provider or pass fixture_id to workflow
                if fixture_id and self.settings.extraction_provider_mode == "gemini":
                    from app.services.extraction.fixture_provider import FixtureExtractionProvider
                    fixture_provider = FixtureExtractionProvider(fixtures_dir=self.settings.extraction_fixtures_dir)
                    workflow_to_use = ExtractionWorkflow(provider=fixture_provider)
                else:
                    workflow_to_use = self.extraction_workflow

                artifacts = workflow_to_use.extract(document_type=document_type, file_bytes=data, fixture_id=fixture_id)

                # Determine extraction source based on provider mode
                if self.settings.extraction_provider_mode == "gemini":
                    source = ExtractionSource(provider="gemini", fixture_id=None, modality="vision")
                else:
                    source = ExtractionSource(provider="fixture", fixture_id=fixture_id, modality="text")
                # Include provider metadata in the extraction summary
                extraction_summary = {
                    "provider": source.provider,
                    "modality": source.modality,
                }

                # Add metadata from the extraction result if available
                if artifacts.provider_metadata:
                    extraction_summary.update({
                        "latency_ms": artifacts.provider_metadata.get("latency_ms"),
                        "model": artifacts.provider_metadata.get("model"),
                        "prompt_version": artifacts.provider_metadata.get("prompt_version"),
                    })

                stored_extraction = StoredExtractionData(
                    schema_version="1",
                    document_type=document_type,
                    extracted=artifacts.extracted,
                    confidence=artifacts.confidence,
                    source=source,
                    provider_metadata=artifacts.provider_metadata,
                    extracted_summary=extraction_summary
                )
                saved.processing_status = DocumentProcessingStatus.EXTRACTED
                saved.extracted_data = stored_extraction.model_dump(mode="json")
                saved.failure_reason = None
                saved = self.registry.update(saved)

                # Create ReviewRequest automatically upon successful extraction
                from app.services.review import ReviewService
                review_service = ReviewService(self.registry.session)
                doc_model = self.registry.session.get(Document, saved.id)
                if doc_model:
                    review_service.create_review_request_if_needed(doc_model)
            except ExtractionWorkflowError as exc:
                logger.warning("Extraction failed document_id=%s type=%s reason=%s", saved.id, document_type.value, str(exc))
                saved.processing_status = DocumentProcessingStatus.PROCESSING_FAILED
                saved.failure_reason = "extraction_failed"
                saved = self.registry.update(saved)
            except Exception:
                logger.exception("Unexpected extraction error document_id=%s type=%s", saved.id, document_type.value)
                saved.processing_status = DocumentProcessingStatus.PROCESSING_FAILED
                saved.failure_reason = "extraction_failed"
                saved = self.registry.update(saved)
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info("Upload%s extraction completed document_id=%s type=%s status=%s duration_ms=%.1f", " + extraction" if fixture_id else "", saved.id, saved.document_type.value, saved.processing_status.value, elapsed_ms)
        return saved
