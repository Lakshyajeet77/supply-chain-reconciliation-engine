"""
Deterministic reconciliation engine.

Independent of any LLM provider. Financial arithmetic uses Decimal only.
An invoice alone can never produce MATCHED — a purchase order is required.
"""

from __future__ import annotations

from decimal import Decimal

from app.schemas.common import ReconciliationStatus
from app.schemas.extraction import ExtractedLineItem, InvoiceRecord, PurchaseOrderRecord
from app.schemas.reconciliation import (
    Discrepancy,
    DiscrepancySeverity,
    DiscrepancyType,
    ReconciliationInput,
    ReconciliationResult,
)
from app.services.reconciliation.policies import ReconciliationPolicies


def reconcile(
    payload: ReconciliationInput,
    policies: ReconciliationPolicies | None = None,
) -> ReconciliationResult:
    policies = policies or ReconciliationPolicies()
    discrepancies: list[Discrepancy] = []
    notes: list[str] = []

    # --- Required documents for MATCHED ---
    if payload.invoice is None:
        discrepancies.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_REQUIRED_DOCUMENT,
                severity=DiscrepancySeverity.CRITICAL,
                field="invoice",
                expected="invoice document",
                observed=None,
                explanation="Reconciliation requires an invoice.",
                recommended_action="Upload the supplier invoice and retry.",
            )
        )
    if payload.purchase_order is None:
        discrepancies.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_REQUIRED_DOCUMENT,
                severity=DiscrepancySeverity.CRITICAL,
                field="purchase_order",
                expected="purchase order document",
                observed="missing",
                explanation=(
                    "An invoice cannot be marked MATCHED without a purchase order. "
                    "Document extraction status is independent of reconciliation status."
                ),
                recommended_action="Upload the related purchase order and retry.",
            )
        )

    if payload.invoice is None or payload.purchase_order is None:
        return ReconciliationResult(
            status=ReconciliationStatus.NEEDS_HUMAN_REVIEW,
            discrepancies=discrepancies,
            notes=notes,
        )

    invoice = payload.invoice
    po = payload.purchase_order

    discrepancies.extend(_check_critical_fields(po, invoice))
    discrepancies.extend(_check_currency(po, invoice))
    discrepancies.extend(_check_po_reference(po, invoice))
    discrepancies.extend(_check_line_items(po, invoice, policies))
    discrepancies.extend(_check_invoice_totals(invoice, policies))

    if payload.delivery is not None:
        notes.append("Delivery record supplied; quantity compared against delivered amounts when SKUs align.")
        discrepancies.extend(
            _check_delivery_quantities(payload.delivery.line_items, invoice, policies)
        )

    status = _resolve_status(discrepancies)
    return ReconciliationResult(status=status, discrepancies=discrepancies, notes=notes)


def _resolve_status(discrepancies: list[Discrepancy]) -> ReconciliationStatus:
    if not discrepancies:
        return ReconciliationStatus.MATCHED

    if any(d.severity == DiscrepancySeverity.CRITICAL for d in discrepancies):
        return ReconciliationStatus.NEEDS_HUMAN_REVIEW

    # Concrete mismatches (qty/price/total) → FLAGGED
    flag_types = {
        DiscrepancyType.QUANTITY_MISMATCH,
        DiscrepancyType.PRICE_MISMATCH,
        DiscrepancyType.LINE_ARITHMETIC_MISMATCH,
        DiscrepancyType.TOTAL_MISMATCH,
        DiscrepancyType.REFERENCE_MISMATCH,
        DiscrepancyType.CURRENCY_MISSING_OR_MISMATCH,
    }
    if any(d.discrepancy_type in flag_types for d in discrepancies):
        return ReconciliationStatus.FLAGGED

    return ReconciliationStatus.NEEDS_HUMAN_REVIEW


def _check_critical_fields(
    po: PurchaseOrderRecord,
    invoice: InvoiceRecord,
) -> list[Discrepancy]:
    issues: list[Discrepancy] = []

    if not invoice.invoice_number:
        issues.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                severity=DiscrepancySeverity.CRITICAL,
                field="invoice.invoice_number",
                expected="non-empty invoice number",
                observed=None,
                explanation="Invoice number is missing or empty.",
                recommended_action="Send to human review; do not auto-approve.",
            )
        )

    if not po.po_number:
        issues.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                severity=DiscrepancySeverity.CRITICAL,
                field="purchase_order.po_number",
                expected="non-empty PO number",
                observed=None,
                explanation="Purchase order number is missing or empty.",
                recommended_action="Send to human review.",
            )
        )

    if not invoice.line_items:
        issues.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                severity=DiscrepancySeverity.CRITICAL,
                field="invoice.line_items",
                expected="at least one line item",
                observed="none",
                explanation="Invoice has no line items to reconcile.",
                recommended_action="Send to human review.",
            )
        )

    return issues


def _check_currency(po: PurchaseOrderRecord, invoice: InvoiceRecord) -> list[Discrepancy]:
    issues: list[Discrepancy] = []
    if po.currency is None or invoice.currency is None:
        issues.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.CURRENCY_MISSING_OR_MISMATCH,
                severity=DiscrepancySeverity.CRITICAL,
                field="currency",
                expected=po.currency,
                observed=invoice.currency,
                explanation="Currency must be present on both PO and invoice; never assume a default.",
                recommended_action="Confirm currency with the reviewer.",
            )
        )
    elif po.currency != invoice.currency:
        issues.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.CURRENCY_MISSING_OR_MISMATCH,
                severity=DiscrepancySeverity.ERROR,
                field="currency",
                expected=po.currency,
                observed=invoice.currency,
                explanation="PO and invoice currencies differ.",
                recommended_action="Flag for review before any payment decision.",
            )
        )
    return issues


def _check_po_reference(po: PurchaseOrderRecord, invoice: InvoiceRecord) -> list[Discrepancy]:
    if invoice.po_reference and po.po_number and invoice.po_reference != po.po_number:
        return [
            Discrepancy(
                discrepancy_type=DiscrepancyType.REFERENCE_MISMATCH,
                severity=DiscrepancySeverity.ERROR,
                field="invoice.po_reference",
                expected=po.po_number,
                observed=invoice.po_reference,
                explanation="Invoice PO reference does not match the purchase order number.",
                recommended_action="Verify document linkage.",
            )
        ]
    return []


def _index_by_sku(items: list[ExtractedLineItem]) -> dict[str, ExtractedLineItem]:
    indexed: dict[str, ExtractedLineItem] = {}
    for item in items:
        if item.sku:
            indexed[item.sku.strip().upper()] = item
    return indexed


def _check_line_items(
    po: PurchaseOrderRecord,
    invoice: InvoiceRecord,
    policies: ReconciliationPolicies,
) -> list[Discrepancy]:
    issues: list[Discrepancy] = []
    po_by_sku = _index_by_sku(po.line_items)

    for idx, inv_line in enumerate(invoice.line_items):
        label = inv_line.sku or inv_line.description or f"line[{idx}]"
        po_line = po_by_sku.get(inv_line.sku.strip().upper()) if inv_line.sku else None

        if po_line is None:
            # Milestone 0: SKU-based alignment only; unmatched lines need review.
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                    severity=DiscrepancySeverity.CRITICAL,
                    field=f"invoice.line_items[{idx}]",
                    expected="matching PO line by SKU",
                    observed=label,
                    explanation="Invoice line could not be matched to a PO line by SKU.",
                    recommended_action="Route to human review (fuzzy matching comes later).",
                )
            )
            continue

        if inv_line.quantity is None or po_line.quantity is None:
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                    severity=DiscrepancySeverity.CRITICAL,
                    field=f"quantity:{label}",
                    expected=str(po_line.quantity) if po_line.quantity is not None else None,
                    observed=str(inv_line.quantity) if inv_line.quantity is not None else None,
                    explanation="Quantity missing on PO or invoice line.",
                    recommended_action="Send to human review.",
                )
            )
        elif not policies.within_quantity_tolerance(po_line.quantity, inv_line.quantity):
            diff = inv_line.quantity - po_line.quantity
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                    severity=DiscrepancySeverity.ERROR,
                    field=f"quantity:{label}",
                    expected=str(po_line.quantity),
                    observed=str(inv_line.quantity),
                    difference=str(diff),
                    explanation="Invoiced quantity differs from ordered quantity beyond tolerance.",
                    recommended_action="Flag for quantity review.",
                )
            )

        if inv_line.unit_price is None or po_line.unit_price is None:
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                    severity=DiscrepancySeverity.CRITICAL,
                    field=f"unit_price:{label}",
                    expected=str(po_line.unit_price) if po_line.unit_price is not None else None,
                    observed=str(inv_line.unit_price) if inv_line.unit_price is not None else None,
                    explanation="Unit price missing on PO or invoice line.",
                    recommended_action="Send to human review.",
                )
            )
        elif not policies.within_price_tolerance(po_line.unit_price, inv_line.unit_price):
            diff = policies.round_money(inv_line.unit_price - po_line.unit_price)
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
                    severity=DiscrepancySeverity.ERROR,
                    field=f"unit_price:{label}",
                    expected=str(policies.round_money(po_line.unit_price)),
                    observed=str(policies.round_money(inv_line.unit_price)),
                    difference=str(diff),
                    explanation="Invoice unit price exceeds or differs from approved PO price.",
                    recommended_action="Flag for price review.",
                )
            )

        if (
            inv_line.quantity is not None
            and inv_line.unit_price is not None
            and inv_line.line_total is not None
        ):
            expected_line = policies.round_money(inv_line.quantity * inv_line.unit_price)
            observed_line = policies.round_money(inv_line.line_total)
            if expected_line != observed_line:
                issues.append(
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.LINE_ARITHMETIC_MISMATCH,
                        severity=DiscrepancySeverity.ERROR,
                        field=f"line_total:{label}",
                        expected=str(expected_line),
                        observed=str(observed_line),
                        difference=str(observed_line - expected_line),
                        explanation="Line total does not equal quantity × unit price under configured rounding.",
                        recommended_action="Flag arithmetic discrepancy.",
                    )
                )

    return issues


def _check_delivery_quantities(
    delivery_lines: list[ExtractedLineItem],
    invoice: InvoiceRecord,
    policies: ReconciliationPolicies,
) -> list[Discrepancy]:
    issues: list[Discrepancy] = []
    delivery_by_sku = _index_by_sku(delivery_lines)

    for idx, inv_line in enumerate(invoice.line_items):
        if not inv_line.sku or inv_line.quantity is None:
            continue
        key = inv_line.sku.strip().upper()
        delivered = delivery_by_sku.get(key)
        if delivered is None or delivered.quantity is None:
            continue
        if not policies.within_quantity_tolerance(delivered.quantity, inv_line.quantity):
            # Invoiced more than delivered is a concrete exception.
            if inv_line.quantity > delivered.quantity:
                issues.append(
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                        severity=DiscrepancySeverity.ERROR,
                        field=f"delivered_vs_invoiced:{key}",
                        expected=str(delivered.quantity),
                        observed=str(inv_line.quantity),
                        difference=str(inv_line.quantity - delivered.quantity),
                        explanation="Invoiced quantity exceeds delivered quantity.",
                        recommended_action="Flag over-billing relative to delivery.",
                    )
                )
    return issues


def _check_invoice_totals(
    invoice: InvoiceRecord,
    policies: ReconciliationPolicies,
) -> list[Discrepancy]:
    issues: list[Discrepancy] = []
    if invoice.total is None:
        issues.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                severity=DiscrepancySeverity.CRITICAL,
                field="invoice.total",
                expected="invoice total",
                observed=None,
                explanation="Invoice total is missing.",
                recommended_action="Send to human review.",
            )
        )
        return issues

    if invoice.tax_total is None:
        issues.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                severity=DiscrepancySeverity.CRITICAL,
                field="invoice.tax_total",
                expected="explicit tax amount",
                observed=None,
                explanation=(
                    "Tax amount is missing or ambiguous. "
                    "Invoice total cannot be validated without inventing a tax value."
                ),
                recommended_action="Send to human review; do not assume tax is zero.",
            )
        )
        return issues

    line_sum = Decimal("0")
    for item in invoice.line_items:
        if item.line_total is not None:
            line_sum += item.line_total
        elif item.quantity is not None and item.unit_price is not None:
            line_sum += item.quantity * item.unit_price

    expected_total = policies.round_money(line_sum + invoice.tax_total)
    observed_total = policies.round_money(invoice.total)

    if expected_total != observed_total:
        issues.append(
            Discrepancy(
                discrepancy_type=DiscrepancyType.TOTAL_MISMATCH,
                severity=DiscrepancySeverity.ERROR,
                field="invoice.total",
                expected=str(expected_total),
                observed=str(observed_total),
                difference=str(observed_total - expected_total),
                explanation="Invoice total does not equal sum of line totals plus tax under configured rounding.",
                recommended_action="Flag total mismatch.",
            )
        )
    return issues
