"""JSON structure persisted into Document.extracted_data."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import DocumentType
from app.schemas.extraction import DeliveryRecord, InvoiceRecord, PurchaseOrderRecord
from app.schemas.extraction_confidence import ConfidenceAssessment
ExtractedDocument = PurchaseOrderRecord | DeliveryRecord | InvoiceRecord
ExtractionModalityValue = Literal["text", "vision"]
class ExtractionSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    fixture_id: str | None = None
    modality: ExtractionModalityValue = "text"
class StoredExtractionData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1"
    document_type: DocumentType
    extracted: ExtractedDocument
    confidence: ConfidenceAssessment
    source: ExtractionSource
    provider_metadata: dict[str, str | int | float | None] | None = None
    extracted_summary: dict[str, str | None] = Field(default_factory=dict)
