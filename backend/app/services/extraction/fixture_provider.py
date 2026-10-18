"""
Fixture-based extraction provider for Milestone 0.

Loads validated structured JSON from disk. No external API keys required.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from app.schemas.common import DocumentType
from app.schemas.extraction import DeliveryRecord, InvoiceRecord, PurchaseOrderRecord
from app.services.extraction.protocol import ExtractionResult

_SCHEMA_BY_TYPE = {
    DocumentType.PURCHASE_ORDER: PurchaseOrderRecord,
    DocumentType.DELIVERY: DeliveryRecord,
    DocumentType.INVOICE: InvoiceRecord,
}


class FixtureExtractionError(ValueError):
    """Fixture missing or does not validate against the extraction schema."""


class FixtureExtractionProvider:
    def __init__(self, fixtures_dir: Path) -> None:
        self.fixtures_dir = fixtures_dir

    def extract(
        self,
        *,
        document_type: DocumentType,
        file_bytes: bytes,
        fixture_id: str | None = None,
    ) -> ExtractionResult:
        # file_bytes reserved for future providers; fixtures ignore image/PDF content.
        _ = file_bytes
        if not fixture_id:
            raise FixtureExtractionError(
                "fixture_id is required for FixtureExtractionProvider."
            )

        path = self.fixtures_dir / f"{fixture_id}.json"
        if not path.is_file():
            raise FixtureExtractionError(f"Extraction fixture not found: {fixture_id}")

        raw = json.loads(path.read_text(encoding="utf-8"))
        schema = _SCHEMA_BY_TYPE[document_type]
        try:
            data = schema.model_validate(raw)
        except ValidationError as exc:
            raise FixtureExtractionError(
                f"Fixture '{fixture_id}' failed schema validation: {exc}"
            ) from exc

        return ExtractionResult(
            document_type=document_type,
            data=data,
            source_fixture_id=fixture_id,
        )
