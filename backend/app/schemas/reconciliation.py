"""Reconciliation request/result schemas. Status is independent of document processing."""

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.common import ReconciliationStatus
from app.schemas.extraction import DeliveryRecord, InvoiceRecord, PurchaseOrderRecord


class DiscrepancyType(str, Enum):
    MISSING_REQUIRED_DOCUMENT = "missing_required_document"
    MISSING_CRITICAL_FIELD = "missing_critical_field"
    CURRENCY_MISSING_OR_MISMATCH = "currency_missing_or_mismatch"
    QUANTITY_MISMATCH = "quantity_mismatch"
    PRICE_MISMATCH = "price_mismatch"
    LINE_ARITHMETIC_MISMATCH = "line_arithmetic_mismatch"
    TOTAL_MISMATCH = "total_mismatch"
    REFERENCE_MISMATCH = "reference_mismatch"


class DiscrepancySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Discrepancy(BaseModel):
    discrepancy_type: DiscrepancyType
    severity: DiscrepancySeverity
    field: str
    expected: str | None = None
    observed: str | None = None
    difference: str | None = None
    explanation: str
    recommended_action: str


class ReconciliationInput(BaseModel):
    """
    Documents required for a reconciliation run.

    Invoice alone is insufficient for MATCHED. Purchase order is required
    in Milestone 0; delivery is optional and used when present.
    """

    purchase_order: PurchaseOrderRecord | None = None
    delivery: DeliveryRecord | None = None
    invoice: InvoiceRecord | None = None


class ReconciliationResult(BaseModel):
    status: ReconciliationStatus
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def is_matched(self) -> bool:
        return self.status == ReconciliationStatus.MATCHED
