"""API router for document relationship management."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document_relationship import (
    DocumentRelationshipCreate,
    DocumentRelationshipResponse,
)
from app.services.document_relationship import DocumentRelationshipService

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.post("", response_model=DocumentRelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_relationship(
    payload: DocumentRelationshipCreate,
    db: Session = Depends(get_db),
) -> DocumentRelationshipResponse:
    """Create or suggest a document relationship between PO, Invoice, and optional Delivery."""
    service = DocumentRelationshipService(db)
    try:
        rel = service.create_relationship(
            po_id=payload.po_id,
            invoice_id=payload.invoice_id,
            delivery_id=payload.delivery_id,
            status=payload.status,
        )
        return DocumentRelationshipResponse.model_validate(rel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[DocumentRelationshipResponse])
def list_relationships(
    po_id: Optional[UUID] = None,
    invoice_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
) -> List[DocumentRelationshipResponse]:
    """List document relationships, optionally filtered by PO ID or Invoice ID."""
    service = DocumentRelationshipService(db)
    if po_id:
        rels = service.get_relationships(po_id=po_id, invoice_id=invoice_id)
    else:
        from app.models.document_relationship import DocumentRelationship
        query = db.query(DocumentRelationship)
        if invoice_id:
            query = query.filter_by(invoice_id=invoice_id)
        rels = query.all()
    return [DocumentRelationshipResponse.model_validate(r) for r in rels]


@router.post("/{relationship_id}/confirm", response_model=DocumentRelationshipResponse)
def confirm_relationship(
    relationship_id: UUID,
    confirmed_by: Optional[str] = "system",
    db: Session = Depends(get_db),
) -> DocumentRelationshipResponse:
    """Confirm a suggested document relationship."""
    service = DocumentRelationshipService(db)
    try:
        rel = service.confirm_relationship(relationship_id, confirmed_by=confirmed_by or "system")
        return DocumentRelationshipResponse.model_validate(rel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_relationship(
    relationship_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """Delete an unconfirmed document relationship."""
    service = DocumentRelationshipService(db)
    try:
        success = service.delete_relationship(relationship_id)
        if not success:
            raise HTTPException(status_code=404, detail="Relationship not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
