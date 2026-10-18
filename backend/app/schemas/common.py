"""Shared enums — document processing vs reconciliation stay separate."""

from enum import Enum


class DocumentType(str, Enum):
    PURCHASE_ORDER = "purchase_order"
    DELIVERY = "delivery"
    INVOICE = "invoice"


class DocumentProcessingStatus(str, Enum):
    """Lifecycle of a single uploaded file. Never used as payment authorization."""

    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    PROCESSING_FAILED = "processing_failed"


class ReconciliationStatus(str, Enum):
    """
    Outcome of comparing related documents.

    MATCHED is not payment authorization. An extracted invoice alone
    must never receive MATCHED without the documents required to reconcile.
    """

    MATCHED = "matched"
    FLAGGED = "flagged"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
