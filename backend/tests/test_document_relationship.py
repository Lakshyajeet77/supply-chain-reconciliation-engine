"""Tests for DocumentRelationshipService and related validation rules."""

from __future__ import annotations

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.document import Document
from app.models.document_relationship import DocumentRelationship
from app.schemas.common import DocumentType
from app.services.document_relationship import DocumentRelationshipService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_test_doc(session, doc_type: DocumentType, extracted_data: dict) -> Document:
    """Helper to create a test document."""
    doc = Document(
        id=uuid4(),
        document_type=doc_type.value,
        original_filename=f"test_{doc_type.value}.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        sha256=uuid4().hex,
        stored_path=f"/tmp/{uuid4().hex}.pdf",
        processing_status="COMPLETED",
        uploaded_at=datetime.now(timezone.utc),
        extracted_data=extracted_data,
    )
    session.add(doc)
    session.commit()
    return doc


def test_create_relationship_success(db_session):
    """Test successful creation of a document relationship."""
    po = create_test_doc(
        db_session,
        DocumentType.PURCHASE_ORDER,
        {"po_number": "PO-1001", "supplier_name": "Acme Corp", "total_amount": 1000.0}
    )
    invoice = create_test_doc(
        db_session,
        DocumentType.INVOICE,
        {"invoice_number": "INV-1001", "po_reference": "PO-1001", "total_amount": 1000.0}
    )

    service = DocumentRelationshipService(db_session)
    rel = service.create_relationship(po.id, invoice.id)

    assert rel is not None
    assert rel.po_id == po.id
    assert rel.invoice_id == invoice.id
    assert rel.status == "SUGGESTED"
    assert rel.created_at is not None


def test_create_relationship_idempotent(db_session):
    """Test that creating the same relationship twice is idempotent."""
    po = create_test_doc(
        db_session,
        DocumentType.PURCHASE_ORDER,
        {"po_number": "PO-1002", "supplier_name": "Acme Corp", "total_amount": 500.0}
    )
    invoice = create_test_doc(
        db_session,
        DocumentType.INVOICE,
        {"invoice_number": "INV-1002", "po_reference": "PO-1002", "total_amount": 500.0}
    )

    service = DocumentRelationshipService(db_session)
    rel1 = service.create_relationship(po.id, invoice.id)
    rel2 = service.create_relationship(po.id, invoice.id)

    assert rel1.id == rel2.id


def test_reference_mismatch_validation(db_session):
    """Test that reference mismatch between PO and Invoice raises ValueError."""
    po = create_test_doc(
        db_session,
        DocumentType.PURCHASE_ORDER,
        {"po_number": "PO-1003", "supplier_name": "Acme Corp", "total_amount": 500.0}
    )
    invoice = create_test_doc(
        db_session,
        DocumentType.INVOICE,
        {"invoice_number": "INV-1003", "po_reference": "PO-WRONG", "total_amount": 500.0}
    )

    service = DocumentRelationshipService(db_session)
    with pytest.raises(ValueError, match="does not match PO number"):
        service.create_relationship(po.id, invoice.id)


def test_document_type_validation(db_session):
    """Test that incorrect document types raise ValueError."""
    doc1 = create_test_doc(
        db_session,
        DocumentType.INVOICE,
        {"invoice_number": "INV-1004", "po_reference": "PO-1004", "total_amount": 100.0}
    )
    doc2 = create_test_doc(
        db_session,
        DocumentType.INVOICE,
        {"invoice_number": "INV-1005", "po_reference": "PO-1004", "total_amount": 100.0}
    )

    service = DocumentRelationshipService(db_session)
    with pytest.raises(ValueError, match="expected 'purchase_order'"):
        service.create_relationship(doc1.id, doc2.id)


def test_confirm_relationship(db_session):
    """Test confirming a relationship sets audit metadata correctly."""
    po = create_test_doc(
        db_session,
        DocumentType.PURCHASE_ORDER,
        {"po_number": "PO-1006", "supplier_name": "Acme Corp", "total_amount": 250.0}
    )
    invoice = create_test_doc(
        db_session,
        DocumentType.INVOICE,
        {"invoice_number": "INV-1006", "po_reference": "PO-1006", "total_amount": 250.0}
    )

    service = DocumentRelationshipService(db_session)
    rel = service.create_relationship(po.id, invoice.id)
    confirmed_rel = service.confirm_relationship(rel.id, confirmed_by="auditor-1")

    assert confirmed_rel.status == "CONFIRMED"
    assert confirmed_rel.confirmed_at is not None
    assert confirmed_rel.confirmed_by == "auditor-1"


def test_protect_confirmed_relationship(db_session):
    """Test that confirmed relationships cannot be deleted or modified."""
    po = create_test_doc(
        db_session,
        DocumentType.PURCHASE_ORDER,
        {"po_number": "PO-1007", "supplier_name": "Acme Corp", "total_amount": 300.0}
    )
    invoice = create_test_doc(
        db_session,
        DocumentType.INVOICE,
        {"invoice_number": "INV-1007", "po_reference": "PO-1007", "total_amount": 300.0}
    )

    service = DocumentRelationshipService(db_session)
    rel = service.create_relationship(po.id, invoice.id)
    service.confirm_relationship(rel.id, confirmed_by="auditor-1")

    with pytest.raises(ValueError, match="Cannot delete a confirmed relationship"):
        service.delete_relationship(rel.id)
