"""Service for managing document relationships between purchase orders, invoices, and deliveries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_relationship import DocumentRelationship
from app.schemas.common import DocumentType
from app.schemas.extraction import InvoiceRecord, PurchaseOrderRecord
from app.schemas.reconciliation import ReconciliationInput
from app.services.reconciliation.engine import reconcile


class DocumentRelationshipService:
    """Service for creating, validating, and managing document relationships."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _validate_document_exists(self, document_id: UUID, expected_type: DocumentType) -> Document:
        """Validate that a document exists and matches the expected type."""
        document = self.db.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        if document.document_type != expected_type.value:
            raise ValueError(
                f"Document {document_id} is type '{document.document_type}', expected '{expected_type.value}'"
            )
        return document

    def _validate_relationship_exists(self, po_id: UUID, invoice_id: UUID) -> Optional[DocumentRelationship]:
        """Check if a relationship already exists between the given PO and invoice."""
        return (
            self.db.query(DocumentRelationship)
            .filter_by(po_id=po_id, invoice_id=invoice_id)
            .first()
        )

    def _validate_relationship_status(self, relationship: DocumentRelationship) -> None:
        """Validate that a relationship is not already confirmed."""
        if relationship.status == "CONFIRMED":
            raise ValueError("Cannot modify a confirmed relationship")

    def _validate_reference_consistency(self, po: Document, invoice: Document) -> None:
        """Validate that PO and invoice reference information is consistent."""
        if not po.extracted_data or not invoice.extracted_data:
            raise ValueError("Both PO and invoice must have extracted data")

        po_data = po.extracted_data
        invoice_data = invoice.extracted_data

        po_number = po_data.get("po_number")
        po_reference = invoice_data.get("po_reference")

        if po_number is None or po_reference is None:
            raise ValueError("PO and invoice must contain PO reference information")

        if po_number != po_reference:
            raise ValueError(
                f"Invoice PO reference '{po_reference}' does not match PO number '{po_number}'"
            )

    def _validate_delivery_consistency(
        self, delivery: Optional[Document], relationship: Optional[DocumentRelationship]
    ) -> None:
        """Validate that delivery document is consistent with existing relationship."""
        if delivery:
            if not delivery.extracted_data:
                raise ValueError("Delivery document must have extracted data")
            if relationship and relationship.delivery_id and relationship.delivery_id != delivery.id:
                raise ValueError("A delivery relationship already exists and differs")

    def create_relationship(
        self,
        po_id: UUID,
        invoice_id: UUID,
        delivery_id: Optional[UUID] = None,
        status: str = "SUGGESTED",
    ) -> DocumentRelationship:
        """Create a new document relationship.

        This method is idempotent: if an identical relationship already exists, it returns it.
        """
        po = self._validate_document_exists(po_id, DocumentType.PURCHASE_ORDER)
        invoice = self._validate_document_exists(invoice_id, DocumentType.INVOICE)

        existing_relationship = self._validate_relationship_exists(po_id, invoice_id)
        if existing_relationship:
            # If a delivery ID is supplied and not set, update it idempotently
            if delivery_id and not existing_relationship.delivery_id:
                delivery = self._validate_document_exists(delivery_id, DocumentType.DELIVERY)
                self._validate_delivery_consistency(delivery, existing_relationship)
                existing_relationship.delivery_id = delivery_id
                self.db.commit()
                self.db.refresh(existing_relationship)
            return existing_relationship

        self._validate_reference_consistency(po, invoice)

        delivery = None
        if delivery_id:
            delivery = self._validate_document_exists(delivery_id, DocumentType.DELIVERY)
            self._validate_delivery_consistency(delivery, None)

        relationship = DocumentRelationship(
            po_id=po_id,
            invoice_id=invoice_id,
            delivery_id=delivery_id,
            status=status,
        )
        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)
        return relationship

    def confirm_relationship(
        self,
        relationship_id: UUID,
        confirmed_by: str = "system",
    ) -> DocumentRelationship:
        """Confirm an existing relationship with audit metadata."""
        relationship = self.db.get(DocumentRelationship, relationship_id)
        if not relationship:
            raise ValueError(f"Relationship {relationship_id} not found")

        self._validate_relationship_status(relationship)

        relationship.status = "CONFIRMED"
        relationship.confirmed_at = datetime.now(timezone.utc)
        relationship.confirmed_by = confirmed_by
        self.db.commit()
        self.db.refresh(relationship)
        return relationship

    def get_relationships(self, po_id: UUID, invoice_id: Optional[UUID] = None) -> List[DocumentRelationship]:
        """Get all relationships for a given PO."""
        query = self.db.query(DocumentRelationship).filter_by(po_id=po_id)
        if invoice_id:
            query = query.filter_by(invoice_id=invoice_id)
        return query.all()

    def get_relationship_by_id(self, relationship_id: UUID) -> Optional[DocumentRelationship]:
        """Get a specific relationship by ID."""
        return self.db.get(DocumentRelationship, relationship_id)

    def validate_documents_for_reconciliation(
        self,
        po_id: UUID,
        invoice_id: UUID,
        delivery_id: Optional[UUID] = None,
    ) -> Dict[str, Union[bool, Optional[str]]]:
        """Validate documents and their cross-references for reconciliation."""
        results: Dict[str, Union[bool, Optional[str]]] = {}

        try:
            po = self._validate_document_exists(po_id, DocumentType.PURCHASE_ORDER)
            results["po_validated"] = True
            results["po_error"] = None
        except ValueError as e:
            results["po_validated"] = False
            results["po_error"] = str(e)

        try:
            invoice = self._validate_document_exists(invoice_id, DocumentType.INVOICE)
            results["invoice_validated"] = True
            results["invoice_error"] = None
        except ValueError as e:
            results["invoice_validated"] = False
            results["invoice_error"] = str(e)

        if delivery_id:
            try:
                self._validate_document_exists(delivery_id, DocumentType.DELIVERY)
                results["delivery_validated"] = True
                results["delivery_error"] = None
            except ValueError as e:
                results["delivery_validated"] = False
                results["delivery_error"] = str(e)
        else:
            results["delivery_validated"] = True
            results["delivery_error"] = None

        if results.get("po_validated") and results.get("invoice_validated"):
            try:
                po_doc = self.db.get(Document, po_id)
                invoice_doc = self.db.get(Document, invoice_id)
                if po_doc and invoice_doc:
                    self._validate_reference_consistency(po_doc, invoice_doc)
                    results["reference_consistency_validated"] = True
                    results["reference_consistency_error"] = None
                else:
                    results["reference_consistency_validated"] = False
                    results["reference_consistency_error"] = "Documents not found for reference check"
            except ValueError as e:
                results["reference_consistency_validated"] = False
                results["reference_consistency_error"] = str(e)
        else:
            results["reference_consistency_validated"] = False
            results["reference_consistency_error"] = "Prerequisite documents failed validation"

        return results

    def delete_relationship(self, relationship_id: UUID) -> bool:
        """Delete a relationship if not confirmed."""
        relationship = self.db.get(DocumentRelationship, relationship_id)
        if not relationship:
            return False

        if relationship.status == "CONFIRMED":
            raise ValueError("Cannot delete a confirmed relationship")

        self.db.delete(relationship)
        self.db.commit()
        return True
