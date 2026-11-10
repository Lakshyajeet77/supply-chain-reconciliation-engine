"""Extraction orchestration for ingestion pipeline."""
from __future__ import annotations
from dataclasses import dataclass
from app.schemas.common import DocumentType
from app.schemas.extraction_confidence import ConfidenceAssessment
from app.services.extraction.confidence_builder import baseline_confidence_for_extracted_doc
from app.services.extraction.protocol import ExtractionProvider, ExtractionResult, ExtractedDocument
@dataclass(frozen=True)
class ExtractionArtifacts:
    extracted: ExtractedDocument
    confidence: ConfidenceAssessment
    provider_metadata: dict[str, str | int | float | None] | None = None

class ExtractionWorkflowError(RuntimeError):
    pass

class ExtractionWorkflow:
    def __init__(self, *, provider: ExtractionProvider) -> None:
        self.provider = provider

    def extract(self, *, document_type: DocumentType, file_bytes: bytes, fixture_id: str | None) -> ExtractionArtifacts:
        try:
            result: ExtractionResult = self.provider.extract(document_type=document_type, file_bytes=file_bytes, fixture_id=fixture_id)
        except Exception as exc:
            raise ExtractionWorkflowError("Extraction provider failed") from exc

        confidence = baseline_confidence_for_extracted_doc(document_type=document_type.value, extracted=result.data)

        return ExtractionArtifacts(
            extracted=result.data,
            confidence=confidence,
            provider_metadata=result.provider_metadata
        )
