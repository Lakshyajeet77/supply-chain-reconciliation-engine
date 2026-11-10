"""
Deterministic reconciliation engine with intelligent matching.

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
from app.schemas.matching import MatchType, MatchingResult
from app.services.matching.matcher import IntelligentMatcher
from app.services.reconciliation.policies import ReconciliationPolicies


def reconcile(
    payload: ReconciliationInput,
    policies: ReconciliationPolicies | None = None,
) -> ReconciliationResult:
    policies = policies or ReconciliationPolicies()
    discrepancies: list[Discrepancy] = []
    notes: list[str] = []
    matching_metadata: dict = {}  # Will store match explanations per line

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

    # --- Intelligent Matching Integration ---
    matcher = IntelligentMatcher()

    # Match Invoice lines to PO lines
    inv_to_po_matches = matcher.match_line_items(invoice.line_items, po.line_items)

    # Match Delivery lines to PO lines (if delivery provided)
    delivery_to_po_matches = {}
    if payload.delivery is not None:
        delivery_to_po_matches = matcher.match_line_items(payload.delivery.line_items, po.line_items)

    # Prepare matching details
    matching_details = MatchingResult(
        invoice_to_po=inv_to_po_matches,
        delivery_to_po=delivery_to_po_matches
    )

    # Check line items using matched pairs
    discrepancies.extend(
        _check_line_items_matched(po, invoice, payload.delivery, inv_to_po_matches, delivery_to_po_matches, policies)
    )
    discrepancies.extend(_check_invoice_totals(invoice, policies))

    if payload.delivery is not None:
        notes.append("Delivery record supplied; quantity compared against delivered amounts when SKUs align.")

    status = _resolve_status(discrepancies)
    return ReconciliationResult(
        status=status,
        discrepancies=discrepancies,
        notes=notes,
        matching_details=matching_details
    )


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


def _check_line_items_matched(
    po: PurchaseOrderRecord,
    invoice: InvoiceRecord,
    delivery,
    inv_to_po_matches: dict,
    delivery_to_po_matches: dict,
    policies: ReconciliationPolicies,
) -> list[Discrepancy]:
    """Check line items using intelligent matching results."""
    issues: list[Discrepancy] = []

    # Build reverse lookup: PO index -> list of invoice indices that matched it
    po_to_inv: dict[int, list[int]] = {}
    for inv_idx, match in inv_to_po_matches.items():
        # Find which PO line this matched to
        # Since we match against target items list, we need to find the target index
        # The matcher returns matches by source index, but we need to find target
        pass  # We'll use the match object directly

    for inv_idx, inv_line in enumerate(invoice.line_items):
        match = inv_to_po_matches.get(inv_idx)

        # Determine the matched PO line
        matched_po_line = None
        matched_po_idx = -1

        if match and match.match_type != MatchType.UNMATCHED:
            # Find which PO line was matched by comparing descriptions/SKU
            # The matcher only returns the match result, not the target index
            # For now, we find the best matching PO line using same logic
            # In a more robust implementation, matcher would return target index
            for po_idx, po_line in enumerate(po.line_items):
                if match.match_type == MatchType.EXACT_SKU:
                    from app.services.matching.normalization import normalize_sku
                    if normalize_sku(po_line.sku) == normalize_sku(inv_line.sku):
                        matched_po_line = po_line
                        matched_po_idx = po_idx
                        break
                elif match.match_type == MatchType.FUZZY_DESCRIPTION:
                    from app.services.matching.normalization import normalize_description
                    if normalize_description(po_line.description) == normalize_description(match.explanation.split(": ")[-1].split(" (score")[0]):
                        matched_po_line = po_line
                        matched_po_idx = po_idx
                        break

        if matched_po_line is None:
            # No match found - line item doesn't correspond to any PO line
            label = inv_line.sku or inv_line.description or f"line[{inv_idx}]"
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                    severity=DiscrepancySeverity.CRITICAL,
                    field=f"invoice.line_items[{inv_idx}]",
                    expected="matching PO line",
                    observed=label,
                    explanation="Invoice line could not be matched to any PO line (SKU or fuzzy description).",
                    recommended_action="Route to human review - unmatched product.",
                )
            )
            continue

        # We have a matched PO line - now check financials
        label = inv_line.sku or inv_line.description or f"line[{inv_idx}]"

        # Check quantity
        if inv_line.quantity is None or matched_po_line.quantity is None:
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                    severity=DiscrepancySeverity.CRITICAL,
                    field=f"quantity:{label}",
                    expected=str(matched_po_line.quantity) if matched_po_line.quantity is not None else None,
                    observed=str(inv_line.quantity) if inv_line.quantity is not None else None,
                    explanation="Quantity missing on PO or invoice line.",
                    recommended_action="Send to human review.",
                )
            )
        elif not policies.within_quantity_tolerance(matched_po_line.quantity, inv_line.quantity):
            diff = inv_line.quantity - matched_po_line.quantity
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                    severity=DiscrepancySeverity.ERROR,
                    field=f"quantity:{label}",
                    expected=str(matched_po_line.quantity),
                    observed=str(inv_line.quantity),
                    difference=str(diff),
                    explanation="Invoiced quantity differs from ordered quantity beyond tolerance.",
                    recommended_action="Flag for quantity review.",
                )
            )

        # Check unit price
        if inv_line.unit_price is None or matched_po_line.unit_price is None:
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_CRITICAL_FIELD,
                    severity=DiscrepancySeverity.CRITICAL,
                    field=f"unit_price:{label}",
                    expected=str(matched_po_line.unit_price) if matched_po_line.unit_price is not None else None,
                    observed=str(inv_line.unit_price) if inv_line.unit_price is not None else None,
                    explanation="Unit price missing on PO or invoice line.",
                    recommended_action="Send to human review.",
                )
            )
        elif not policies.within_price_tolerance(matched_po_line.unit_price, inv_line.unit_price):
            diff = policies.round_money(inv_line.unit_price - matched_po_line.unit_price)
            issues.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
                    severity=DiscrepancySeverity.ERROR,
                    field=f"unit_price:{label}",
                    expected=str(policies.round_money(matched_po_line.unit_price)),
                    observed=str(policies.round_money(inv_line.unit_price)),
                    difference=str(diff),
                    explanation="Invoice unit price exceeds or differs from approved PO price.",
                    recommended_action="Flag for price review.",
                )
            )

        # Check line arithmetic
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

    # Check delivery quantities against invoice using matched PO lines as bridge
    if delivery is not None:
        issues.extend(
            _check_delivery_quantities_matched(delivery.line_items, invoice.line_items, po.line_items,
                                             delivery_to_po_matches, inv_to_po_matches, policies)
        )

    return issues


def _check_delivery_quantities_matched(
    delivery_lines: list[ExtractedLineItem],
    invoice_lines: list[ExtractedLineItem],
    po_lines: list[ExtractedLineItem],
    delivery_to_po_matches: dict,
    inv_to_po_matches: dict,
    policies: ReconciliationPolicies,
) -> list[Discrepancy]:
    """Check delivery quantities against invoice using PO as reference bridge."""
    issues: list[Discrepancy] = []

    # For each delivery line, find its matched PO line
    # Then find which invoice line matched the same PO line
    po_idx_to_delivery: dict[int, list[int]] = {}
    for del_idx, match in delivery_to_po_matches.items():
        if match.match_type != MatchType.UNMATCHED:
            # Find PO index
            for po_idx, po_line in enumerate(po_lines):
                if match.match_type == MatchType.EXACT_SKU:
                    from app.services.matching.normalization import normalize_sku
                    if normalize_sku(po_line.sku) == normalize_sku(delivery_lines[del_idx].sku):
                        po_idx_to_delivery.setdefault(po_idx, []).append(del_idx)
                        break
                elif match.match_type == MatchType.FUZZY_DESCRIPTION:
                    from app.services.matching.normalization import normalize_description
                    if normalize_description(po_line.description) == normalize_description(match.explanation.split(": ")[-1].split(" (score")[0]):
                        po_idx_to_delivery.setdefault(po_idx, []).append(del_idx)
                        break

    po_idx_to_invoice: dict[int, list[int]] = {}
    for inv_idx, match in inv_to_po_matches.items():
        if match.match_type != MatchType.UNMATCHED:
            for po_idx, po_line in enumerate(po_lines):
                if match.match_type == MatchType.EXACT_SKU:
                    from app.services.matching.normalization import normalize_sku
                    if normalize_sku(po_line.sku) == normalize_sku(invoice_lines[inv_idx].sku):
                        po_idx_to_invoice.setdefault(po_idx, []).append(inv_idx)
                        break
                elif match.match_type == MatchType.FUZZY_DESCRIPTION:
                    from app.services.matching.normalization import normalize_description
                    if normalize_description(po_line.description) == normalize_description(match.explanation.split(": ")[-1].split(" (score")[0]):
                        po_idx_to_invoice.setdefault(po_idx, []).append(inv_idx)
                        break

    # Now compare delivery vs invoice for each PO line
    for po_idx, del_indices in po_idx_to_delivery.items():
        inv_indices = po_idx_to_invoice.get(po_idx, [])
        if not inv_indices:
            continue  # No invoice line for this PO line

        # Sum delivery quantities
        total_delivered = sum(
            delivery_lines[i].quantity for i in del_indices
            if delivery_lines[i].quantity is not None
        )

        # Sum invoiced quantities
        total_invoiced = sum(
            invoice_lines[i].quantity for i in inv_indices
            if invoice_lines[i].quantity is not None
        )

        if total_delivered > 0 and total_invoiced > 0:
            if not policies.within_quantity_tolerance(total_delivered, total_invoiced):
                if total_invoiced > total_delivered:
                    po_line = po_lines[po_idx]
                    label = po_line.sku or po_line.description or f"line[{po_idx}]"
                    issues.append(
                        Discrepancy(
                            discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                            severity=DiscrepancySeverity.ERROR,
                            field=f"delivered_vs_invoiced:{label}",
                            expected=str(total_delivered),
                            observed=str(total_invoiced),
                            difference=str(total_invoiced - total_delivered),
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