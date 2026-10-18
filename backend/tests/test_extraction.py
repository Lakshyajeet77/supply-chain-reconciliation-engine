"""Fixture-based extraction provider tests (no external API keys)."""

from decimal import Decimal

from app.schemas.common import DocumentType
from app.services.extraction.fixture_provider import FixtureExtractionError


def test_extract_invoice_fixture(extraction_provider):
    result = extraction_provider.extract(
        document_type=DocumentType.INVOICE,
        file_bytes=b"",
        fixture_id="invoice_matched",
    )
    invoice = result.data
    assert invoice.invoice_number == "INV-9001"
    assert invoice.currency == "INR"
    assert invoice.line_items[0].unit_price == Decimal("2500.00")
    assert isinstance(invoice.line_items[0].quantity, Decimal)


def test_extract_po_fixture(extraction_provider):
    result = extraction_provider.extract(
        document_type=DocumentType.PURCHASE_ORDER,
        file_bytes=b"",
        fixture_id="po_matched",
    )
    assert result.data.po_number == "PO-1001"
    assert result.data.currency == "INR"


def test_missing_fixture_raises(extraction_provider):
    try:
        extraction_provider.extract(
            document_type=DocumentType.INVOICE,
            file_bytes=b"",
            fixture_id="does_not_exist",
        )
        assert False, "expected FixtureExtractionError"
    except FixtureExtractionError as exc:
        assert "not found" in str(exc)


def test_fixture_id_required(extraction_provider):
    try:
        extraction_provider.extract(
            document_type=DocumentType.INVOICE,
            file_bytes=b"",
            fixture_id=None,
        )
        assert False, "expected FixtureExtractionError"
    except FixtureExtractionError as exc:
        assert "fixture_id" in str(exc)
