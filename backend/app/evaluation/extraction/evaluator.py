from __future__ import annotations
import json
from decimal import Decimal
from typing import Any, Dict, List, Tuple
from rapidfuzz import fuzz

from app.evaluation.extraction.normalizer import (
    normalize_sku, normalize_description, normalize_money, normalize_quantity, normalize_date
)
from app.evaluation.extraction.metrics import MetricCount


class DocumentEvaluationResult:
    """
    Represents the evaluation result for a single document.
    Encapsulates all TP/FP/FN counts, field matches, and line-item metrics.
    """
    def __init__(
        self,
        doc_id: str,
        doc_type: str,
        field_matches: Dict[str, bool],
        line_item_matches: List[Dict[str, Any]],
        tp: int,
        fp: int,
        fn: int,
        line_items_total: int,
        line_items_matched: int
    ):
        self.doc_id = doc_id
        self.doc_type = doc_type
        self.field_matches = field_matches
        self.line_item_matches = line_item_matches
        self.tp = tp
        self.fp = fp
        self.fn = fn
        self.line_items_total = line_items_total
        self.line_items_matched = line_items_matched

    def to_dict(self) -> Dict:
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "field_matches": self.field_matches,
            "line_item_matches": self.line_item_matches,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "line_items_total": self.line_items_total,
            "line_items_matched": self.line_items_matched
        }


class EvaluationReport:
    """
    Consolidates evaluation results across a dataset of documents.
    Aggregates TP/FP/FN before calculating precision, recall, and F1.
    """
    def __init__(self):
        self.dataset_id: str = "synthetic_baseline_v1"
        self.evaluator_version: str = "1.0"
        self.documents: List[DocumentEvaluationResult] = []
        self.document_type_metrics: Dict[str, MetricCount] = {
            "po": MetricCount(),
            "invoice": MetricCount(),
            "delivery": MetricCount()
        }
        self.line_item_identification_total: int = 0
        self.line_item_identification_matches: int = 0

    def add_document(self, result: DocumentEvaluationResult):
        """
        Adds a single document's evaluation result and updates aggregates.
        Each document is counted exactly once.
        """
        self.documents.append(result)
        # Aggregate document-type metrics
        if result.doc_type in self.document_type_metrics:
            self.document_type_metrics[result.doc_type].add(
                tp=result.tp, fp=result.fp, fn=result.fn
            )
        else:
            # Fallback for unknown types
            self.document_type_metrics[result.doc_type] = MetricCount(
                tp=result.tp, fp=result.fp, fn=result.fn
            )
        # Aggregate line item identification metrics
        self.line_item_identification_total += result.line_items_total
        self.line_item_identification_matches += result.line_items_matched

    def aggregate_dataset_metrics(self) -> Dict[str, Any]:
        """
        Calculates dataset-level precision, recall, and F1
        by aggregating TP/FP/FN across all documents first.
        """
        total_tp = sum(mc.tp for mc in self.document_type_metrics.values())
        total_fp = sum(mc.fp for mc in self.document_type_metrics.values())
        total_fn = sum(mc.fn for mc in self.document_type_metrics.values())

        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "line_item_identification_accuracy": round(
                self.line_item_identification_matches / self.line_item_identification_total, 4
            ) if self.line_item_identification_total > 0 else 0.0
        }

    def to_dict(self) -> Dict:
        return {
            "metadata": {
                "dataset_id": self.dataset_id,
                "evaluator_version": self.evaluator_version,
            },
            "documents": [doc.to_dict() for doc in self.documents],
            "document_type_metrics": {dt: vars(mc) for dt, mc in self.document_type_metrics.items()},
            "dataset_metrics": self.aggregate_dataset_metrics()
        }

    def to_json(self) -> str:
        # Ensure all numeric values are float-compatible for JSON
        def sanitize(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize(v) for v in obj]
            return obj

        raw = self.to_dict()
        return json.dumps(sanitize(raw), indent=2, ensure_ascii=False)


class ExtractionEvaluator:
    """
    Core evaluator for AI extraction performance against ground truth.
    """

    def __init__(self, tolerance_money: Decimal = Decimal("0.01"), tolerance_qty: Decimal = Decimal("0.0001")):
        self.tolerance_money = tolerance_money
        self.tolerance_qty = tolerance_qty

    def evaluate_field(self, gt_val: Any, pred_val: Any, field_name: str) -> bool:
        """
        Evaluates a single field between ground truth and prediction.
        Returns True if the values match after normalization.
        """
        if gt_val is None and pred_val is None: return True  # Both missing
        if gt_val is None or pred_val is None: return False  # One missing

        # Normalize based on field type
        if "sku" in field_name:
            return normalize_sku(str(gt_val)) == normalize_sku(str(pred_val))
        elif "description" in field_name:
            return normalize_description(str(gt_val)) == normalize_description(str(pred_val))
        elif any(f in field_name for f in ["price", "total", "subtotal", "tax", "unit_price"]):
            gt = normalize_money(gt_val)
            pred = normalize_money(pred_val)
            if gt is None or pred is None: return False
            return abs(gt - pred) <= self.tolerance_money
        elif "quantity" in field_name:
            gt = normalize_quantity(gt_val)
            pred = normalize_quantity(pred_val)
            if gt is None or pred is None: return False
            # Check for unit incompatibility
            if str(gt_val) != str(pred_val) and (
                ("pcs" in str(gt_val).lower() and "kg" in str(pred_val).lower()) or
                ("kg" in str(gt_val).lower() and "pcs" in str(pred_val).lower())
            ):
                return False
            return abs(gt - pred) <= self.tolerance_qty
        elif "date" in field_name:
            return normalize_date(gt_val) == normalize_date(pred_val)
        elif "unit_of_measure" in field_name:
            return normalize_description(str(gt_val)) == normalize_description(str(pred_val))
        # Default string comparison
        return str(gt_val) == str(pred_val)

    def evaluate(self, gt_doc: dict, pred_doc: dict, doc_id: str, doc_type: str) -> DocumentEvaluationResult:
        """
        Full evaluation of a single document pair.

        Returns:
            DocumentEvaluationResult containing all metrics and matches.
        """
        field_matches: Dict[str, bool] = {}
        line_item_matches: List[Dict[str, Any]] = []
        tp_total = 0
        fp_total = 0
        fn_total = 0

        # 1. Header field evaluation
        all_keys = set(gt_doc.keys()) | set(pred_doc.keys())
        all_keys.discard("line_items")  # Skip line items for now; evaluated separately

        for key in all_keys:
            gt_val = gt_doc.get(key)
            pred_val = pred_doc.get(key)
            is_match = self.evaluate_field(gt_val, pred_val, key)
            field_matches[key] = is_match

            # Metric logic
            if is_match:
                # Both None -> exclude (already handled by evaluate_field returning True for both None)
                # But we must not count this as TP
                if gt_val is not None and pred_val is not None:
                    tp_total += 1
                # else: both None -> exclude from metrics
            else:
                # Both exist but incorrect -> FP + FN
                if gt_val is not None and pred_val is not None:
                    fp_total += 1
                    fn_total += 1
                # Prediction exists, ground truth doesn't -> FP (unexpected field)
                elif pred_val is not None:
                    fp_total += 1
                # Ground truth exists, prediction doesn't -> FN (missing field)
                elif gt_val is not None:
                    fn_total += 1

        # 2. Line item assignment (One-to-one)
        gt_items = gt_doc.get("line_items", [])
        pred_items = pred_doc.get("line_items", [])

        matched_gt_indices = set()
        matched_pred_indices = set()

        # A. Exact SKU Matching
        for p_idx, p_item in enumerate(pred_items):
            for g_idx, g_item in enumerate(gt_items):
                if g_idx in matched_gt_indices or p_idx in matched_pred_indices:
                    continue
                sku_match = (
                    normalize_sku(p_item.get("sku")) == normalize_sku(g_item.get("sku"))
                    and p_item.get("sku") is not None
                )
                if sku_match:
                    line_item_matches.append({
                        "method": "sku",
                        "pred_index": p_idx,
                        "gt_index": g_idx
                    })
                    matched_gt_indices.add(g_idx)
                    matched_pred_indices.add(p_idx)
                    break  # Move to next predicted item

        # B. Fuzzy Description Matching (remaining)
        for p_idx, p_item in enumerate(pred_items):
            if p_idx in matched_pred_indices:
                continue
            best_score = 0.0
            best_g_idx = -1
            for g_idx, g_item in enumerate(gt_items):
                if g_idx in matched_gt_indices:
                    continue
                score = fuzz.token_sort_ratio(
                    normalize_description(p_item.get("description", "")),
                    normalize_description(g_item.get("description", ""))
                )
                if score > best_score and score > 80:
                    best_score = score
                    best_g_idx = g_idx

            if best_g_idx != -1:
                # Ensure we don't match on empty descriptions
                pred_desc = normalize_description(p_item.get("description", ""))
                gt_desc = normalize_description(gt_items[best_g_idx].get("description", ""))
                if pred_desc and gt_desc:  # Both non-empty
                    line_item_matches.append({
                        "method": "fuzzy",
                        "pred_index": p_idx,
                        "gt_index": best_g_idx
                    })
                    matched_gt_indices.add(best_g_idx)
                    matched_pred_indices.add(p_idx)

        # Calculate line-item identification metrics
        line_items_total = len(gt_items) + len(pred_items)
        line_items_matched = len(line_item_matches)

        # Calculate unmatched items for TP/FP/FN
        unmatched_gt = len(gt_items) - len(matched_gt_indices)
        unmatched_pred = len(pred_items) - len(matched_pred_indices)

        # Line-item identification TP/FP/FN
        # TP = matched items
        # FP = unmatched predicted items
        # FN = unmatched ground-truth items
        line_item_tp = line_items_matched
        line_item_fp = unmatched_pred
        line_item_fn = unmatched_gt

        # 3. Line-item field-level evaluation for matched pairs
        # Evaluate quantity, unit, description, unit_price, tax for matched items
        for match in line_item_matches:
            gt_item = gt_items[match["gt_index"]]
            pred_item = pred_items[match["pred_index"]]

            # Evaluate fields for matched line items
            item_fields = ["quantity", "unit_of_measure", "unit_price", "description", "tax"]
            for field in item_fields:
                gt_val = gt_item.get(field)
                pred_val = pred_item.get(field)
                is_match = self.evaluate_field(gt_val, pred_val, field)

                if is_match:
                    if gt_val is not None and pred_val is not None:
                        tp_total += 1
                    # Both None -> exclude
                else:
                    if gt_val is not None and pred_val is not None:
                        fp_total += 1
                        fn_total += 1
                    elif pred_val is not None:
                        fp_total += 1
                    elif gt_val is not None:
                        fn_total += 1

        # Aggregate all metrics (header + line item identification + line item fields)
        total_tp = tp_total + line_item_tp
        total_fp = fp_total + line_item_fp
        total_fn = fn_total + line_item_fn

        return DocumentEvaluationResult(
            doc_id=doc_id,
            doc_type=doc_type,
            field_matches=field_matches,
            line_item_matches=line_item_matches,
            tp=total_tp,
            fp=total_fp,
            fn=total_fn,
            line_items_total=line_items_total,
            line_items_matched=line_items_matched
        )

    def evaluate_dataset(self, dataset: List[Tuple[str, str, dict, dict]]) -> EvaluationReport:
        """
        Evaluates a dataset of document pairs.

        Args:
            dataset: List of (doc_type, doc_id, ground_truth_doc, predicted_doc) tuples.

        Returns:
            EvaluationReport containing consolidated results.
        """
        report = EvaluationReport()

        for doc_type, doc_id, gt_doc, pred_doc in dataset:
            result = self.evaluate(gt_doc, pred_doc, doc_id, doc_type)
            report.add_document(result)

        return report