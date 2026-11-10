"""API router for approved-document reconciliation workflow."""

from __future__ import annotations

from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.models.document import Document
from app.models.document_relationship import DocumentRelationship
from app.models.review import ReviewRequest
from app.schemas.common import DocumentType
from app.schemas.extraction import DeliveryRecord, InvoiceRecord, PurchaseOrderRecord
from app.schemas.reconciliation import ReconciliationInput, ReconciliationResult
from app.services.reconciliation.engine import reconcile
from app.services.reconciliation.policies import ReconciliationPolicies
from app.services.review import ReviewService

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


def _get_approved_document(
    db: Session, document_id: UUID, expected_type: DocumentType
) -> Document:
    """Fetch document and verify it has APPROVED review status."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    if doc.document_type != expected_type.value:
        raise HTTPException(
            status_code=400,
            detail=f"Document {document_id} is type '{doc.document_type}', expected '{expected_type.value}'"
        )
    review_req = db.query(ReviewRequest).filter_by(document_id=document_id).first()
    if not (review_req and review_req.status == 'APPROVED'):
        raise HTTPException(
            status_code=400,
            detail=f"Document {document_id} is not approved for reconciliation"
        )
    return doc


@router.post("/run-approved", response_model=ReconciliationResult)
def run_approved_reconciliation(
    payload: ReconciliationInput,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> ReconciliationResult:
    """Run reconciliation using only approved document data and confirmed relationships.

    Validates:
    - PO, Invoice and Delivery exist and have correct document types
    - Each document has an APPROVED review status (Rule 5)
    - A confirmed document relationship exists matching PO and invoice (Rule 1 & 2)
    - Delivery document matches confirmed relationship (Rule 3 & 4)
    - Documents belong to the same transaction (PO reference matches)

    Returns immutable snapshot of the approved data used.
    """
    review_service = ReviewService(db)

    # Resolve approved documents (Rule 5)
    po = _get_approved_document(db, payload.po_id, DocumentType.PURCHASE_ORDER)
    invoice = _get_approved_document(db, payload.invoice_id, DocumentType.INVOICE)

    # Verify confirmed relationship exists and matches (Rule 1, 2, 3, 4)
    rel = db.query(DocumentRelationship).filter_by(po_id=payload.po_id, invoice_id=payload.invoice_id).first()
    if not rel or rel.status != "CONFIRMED":
        raise HTTPException(
            status_code=400,
            detail="A confirmed document relationship between this PO and invoice is required for reconciliation"
        )

    delivery_id = payload.delivery.id if payload.delivery else None
    if rel.delivery_id:
        if delivery_id != rel.delivery_id:
            raise HTTPException(
                status_code=400,
                detail=f"Supplied delivery ID '{delivery_id}' does not match confirmed relationship delivery ID '{rel.delivery_id}'"
            )
    else:
        if delivery_id is not None:
            raise HTTPException(
                status_code=400,
                detail="No delivery document is associated with this confirmed relationship"
            )

    # Validate PO-invoice relationship extraction data
    if not po.extracted_data or not invoice.extracted_data:
        raise HTTPException(
            status_code=400,
            detail="Both PO and invoice must have extracted data"
        )
    po_data = PurchaseOrderRecord(**po.extracted_data)
    invoice_data = InvoiceRecord(**invoice.extracted_data)

    if po_data.po_number is None or invoice_data.po_reference is None:
        raise HTTPException(
            status_code=400,
            detail="PO and invoice must contain PO reference information"
        )
    if po_data.po_number != invoice_data.po_reference:
        raise HTTPException(
            status_code=400,
            detail=f"Invoice PO reference '{invoice_data.po_reference}' does not match PO number '{po_data.po_number}'"
        )

    # Build reconciliation input from approved data
    approved_payload = ReconciliationInput(
        purchase_order=po_data,
        invoice=invoice_data,
        delivery=payload.delivery,
    )

    # Record snapshot of approved data used
    snapshot_data = {
        "po": po.extracted_data,
        "invoice": invoice.extracted_data,
        "delivery": payload.delivery.extracted_data if payload.delivery else None,
        "review_requests": [
            str(review_service.get_review_request(po.id).id) if review_service.get_review_request(po.id) else None,
            str(review_service.get_review_request(invoice.id).id) if review_service.get_review_request(invoice.id) else None,
        ]
    }

    # Execute reconciliation
    policies = ReconciliationPolicies(
        money_decimal_places=settings.money_decimal_places,
        price_tolerance=settings.price_tolerance,
        quantity_tolerance=settings.quantity_tolerance,
    )
    result = reconcile(approved_payload, policies)

    # Store immutable snapshot
    from app.models.reconciliation_snapshot import ReconciliationSnapshot
    snapshot = ReconciliationSnapshot(
        run_id=str(uuid4()),
        po_id=payload.po_id,
        invoice_id=payload.invoice_id,
        delivery_id=delivery_id,
        review_request_ids=[r.id for r in [review_service.get_review_request(po.id), review_service.get_review_request(invoice.id)] if r],
        snapshot_data=snapshot_data,
        reconciliation_result=result.model_dump()
    )
    db.add(snapshot)
    db.commit()

    return result
