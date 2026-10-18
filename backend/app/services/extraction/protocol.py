"""Replaceable extraction provider interface (fixture stub now; live LLM later)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas.common import DocumentType
from app.schemas.extraction import DeliveryRecord, InvoiceRecord, PurchaseOrderRecord


ExtractedDocument = PurchaseOrderRecord | DeliveryRecord | InvoiceRecord


@dataclass(frozen=True)
class ExtractionResult:
    document_type: DocumentType
    data: ExtractedDocument
    source_fixture_id: str | None = None


class ExtractionProvider(Protocol):
    def extract(
        self,
        *,
        document_type: DocumentType,
        file_bytes: bytes,
        fixture_id: str | None = None,
    ) -> ExtractionResult:
        """
        Extract structured fields from a document.

        Implementations must not invent missing values to satisfy a schema.
        """
        ...
