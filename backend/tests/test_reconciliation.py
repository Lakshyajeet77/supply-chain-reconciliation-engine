"""Deterministic reconciliation tests using structured fixtures (no LLM)."""

from decimal import Decimal

from app.schemas.common import DocumentType, ReconciliationStatus
from app.schemas.reconciliation import DiscrepancyType, ReconciliationInput
from app.services.reconciliation.engine import reconcile
from app.services.reconciliation.policies import ReconciliationPolicies


def _load(provider, doc_type: DocumentType, fixture_id: str):
    return provider.extract(
        document_type=doc_type,
        file_bytes=b"",
        fixture_id=fixture_id,
    ).data


def test_fully_matched_po_delivery_invoice(extraction_provider):
    payload = ReconciliationInput(
        purchase_order=_load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched"),
        delivery=_load(extraction_provider, DocumentType.DELIVERY, "delivery_matched"),
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_matched"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.MATCHED
    assert result.discrepancies == []


def test_invoice_alone_never_matched(extraction_provider):
    payload = ReconciliationInput(
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_matched"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.NEEDS_HUMAN_REVIEW
    assert any(
        d.discrepancy_type == DiscrepancyType.MISSING_REQUIRED_DOCUMENT
        and d.field == "purchase_order"
        for d in result.discrepancies
    )


def test_invoice_quantity_exceeds_ordered(extraction_provider):
    payload = ReconciliationInput(
        purchase_order=_load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched"),
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_over_qty"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.FLAGGED
    assert any(d.discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH for d in result.discrepancies)


def test_invoice_quantity_exceeds_delivered(extraction_provider):
    payload = ReconciliationInput(
        purchase_order=_load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched"),
        delivery=_load(extraction_provider, DocumentType.DELIVERY, "delivery_partial"),
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_matched"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.FLAGGED
    assert any(
        d.discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH
        and "delivered_vs_invoiced" in d.field
        for d in result.discrepancies
    )


def test_invoice_unit_price_exceeds_po(extraction_provider):
    payload = ReconciliationInput(
        purchase_order=_load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched"),
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_over_price"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.FLAGGED
    price_issues = [
        d for d in result.discrepancies if d.discrepancy_type == DiscrepancyType.PRICE_MISMATCH
    ]
    assert price_issues
    assert price_issues[0].expected == "2500.00"
    assert price_issues[0].observed == "2750.00"


def test_missing_invoice_number_needs_review(extraction_provider):
    payload = ReconciliationInput(
        purchase_order=_load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched"),
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_missing_number"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.NEEDS_HUMAN_REVIEW
    assert any(
        d.discrepancy_type == DiscrepancyType.MISSING_CRITICAL_FIELD
        and d.field == "invoice.invoice_number"
        for d in result.discrepancies
    )


def test_incorrect_line_arithmetic(extraction_provider):
    payload = ReconciliationInput(
        purchase_order=_load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched"),
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_bad_line_math"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.FLAGGED
    assert any(
        d.discrepancy_type == DiscrepancyType.LINE_ARITHMETIC_MISMATCH for d in result.discrepancies
    )


def test_incorrect_invoice_total(extraction_provider):
    payload = ReconciliationInput(
        purchase_order=_load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched"),
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_bad_total"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.FLAGGED
    assert any(d.discrepancy_type == DiscrepancyType.TOTAL_MISMATCH for d in result.discrepancies)


def test_missing_tax_total_needs_review_not_matched(extraction_provider):
    """Missing tax must not be treated as zero; otherwise-matching docs stay unmatched."""
    payload = ReconciliationInput(
        purchase_order=_load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched"),
        invoice=_load(extraction_provider, DocumentType.INVOICE, "invoice_missing_tax"),
    )
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.NEEDS_HUMAN_REVIEW
    assert result.status != ReconciliationStatus.MATCHED
    assert any(
        d.discrepancy_type == DiscrepancyType.MISSING_CRITICAL_FIELD
        and d.field == "invoice.tax_total"
        and d.severity.value == "critical"
        for d in result.discrepancies
    )
    assert not any(
        d.discrepancy_type == DiscrepancyType.TOTAL_MISMATCH for d in result.discrepancies
    )


def test_missing_currency_prevents_matched(extraction_provider):
    po = _load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched")
    invoice = _load(extraction_provider, DocumentType.INVOICE, "invoice_matched")
    invoice = invoice.model_copy(update={"currency": None})
    payload = ReconciliationInput(purchase_order=po, invoice=invoice)
    result = reconcile(payload, ReconciliationPolicies())
    assert result.status == ReconciliationStatus.NEEDS_HUMAN_REVIEW
    assert result.status != ReconciliationStatus.MATCHED
    assert any(
        d.discrepancy_type == DiscrepancyType.CURRENCY_MISSING_OR_MISMATCH
        for d in result.discrepancies
    )


def test_money_uses_decimal_not_float(extraction_provider):
    invoice = _load(extraction_provider, DocumentType.INVOICE, "invoice_matched")
    assert type(invoice.total) is Decimal
    assert type(invoice.line_items[0].unit_price) is Decimal


def test_reconciliation_api_matched(client, extraction_provider):
    po = _load(extraction_provider, DocumentType.PURCHASE_ORDER, "po_matched")
    inv = _load(extraction_provider, DocumentType.INVOICE, "invoice_matched")
    response = client.post(
        "/reconciliation/run",
        json={
            "purchase_order": po.model_dump(mode="json"),
            "invoice": inv.model_dump(mode="json"),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "matched"


def test_reconciliation_api_invoice_alone(client, extraction_provider):
    inv = _load(extraction_provider, DocumentType.INVOICE, "invoice_matched")
    response = client.post(
        "/reconciliation/run",
        json={"invoice": inv.model_dump(mode="json")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_human_review"
