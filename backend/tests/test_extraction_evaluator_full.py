import unittest
import json
from decimal import Decimal
from app.evaluation.extraction.evaluator import ExtractionEvaluator, DocumentEvaluationResult, EvaluationReport
from app.evaluation.extraction.metrics import MetricCount

class TestExtractionEvaluatorFull(unittest.TestCase):
    def setUp(self):
        self.evaluator = ExtractionEvaluator()

    def test_single_document_evaluation(self):
        # Exact match
        gt = {"po_number": "PO-123", "line_items": [{"sku": "A", "quantity": 10}]}
        pred = {"po_number": "PO-123", "line_items": [{"sku": "A", "quantity": 10}]}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")
        # po_number (header) + line item identification (SKU match) + quantity field match = 3 TP
        self.assertEqual(result.tp, 3)
        self.assertEqual(result.fp, 0)
        self.assertEqual(result.fn, 0)
        self.assertEqual(len(result.line_item_matches), 1)

    def test_field_normalization(self):
        # Money normalization
        self.assertTrue(self.evaluator.evaluate_field("100.00", "100", "total"))
        # Quantity normalization
        self.assertTrue(self.evaluator.evaluate_field("10.0", "10", "quantity"))

    def test_field_mismatch(self):
        # Incorrect value where both exist -> returns False
        self.assertFalse(self.evaluator.evaluate_field("100", "200", "total"))

    def test_missing_fields(self):
        # GT has field, pred does not
        self.assertFalse(self.evaluator.evaluate_field("PO-123", None, "po_number"))
        # Pred has field, GT does not
        self.assertFalse(self.evaluator.evaluate_field(None, "PO-123", "po_number"))

    def test_line_item_assignment(self):
        gt = {"line_items": [{"sku": "A", "description": "Widget"}]}
        pred = {"line_items": [{"sku": "A", "description": "Widget"}]}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")
        self.assertEqual(len(result.line_item_matches), 1)

    def test_incompatible_units(self):
        self.assertFalse(self.evaluator.evaluate_field("10 pcs", "10 kg", "quantity"))

    def test_dataset_aggregation(self):
        # Two perfect documents
        dataset = [
            ("po", "PO1", {"po_number": "PO-1"}, {"po_number": "PO-1"}),
            ("invoice", "INV1", {"invoice_number": "INV-1"}, {"invoice_number": "INV-1"})
        ]
        report = self.evaluator.evaluate_dataset(dataset)
        self.assertEqual(report.aggregate_dataset_metrics()["tp"], 2)
        self.assertEqual(report.aggregate_dataset_metrics()["fp"], 0)
        self.assertEqual(report.aggregate_dataset_metrics()["fn"], 0)

    def test_json_serialization(self):
        report = EvaluationReport()
        result = DocumentEvaluationResult(
            doc_id="PO1", doc_type="po",
            field_matches={"po_number": True}, line_item_matches=[],
            tp=1, fp=0, fn=0,
            line_items_total=0, line_items_matched=0
        )
        report.add_document(result)
        json_str = report.to_json()
        json_data = json.loads(json_str)
        self.assertEqual(json_data["metadata"]["dataset_id"], "synthetic_baseline_v1")

    def test_decimal_handling(self):
        gt = {"total": Decimal("100.00")}
        pred = {"total": "100.00"}
        self.assertTrue(self.evaluator.evaluate_field(gt["total"], pred["total"], "total"))

    def test_fuzzy_description_match(self):
        gt = {"line_items": [{"description": "Red Widget"}]}
        pred = {"line_items": [{"description": "Widget Red"}]}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")
        self.assertEqual(len(result.line_item_matches), 1)

    # --- Hand-calculated verification tests ---

    def test_header_field_correct_value(self):
        gt = {"po_number": "PO-123"}
        pred = {"po_number": "PO-123"}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")
        self.assertEqual(result.tp, 1)
        self.assertEqual(result.fp, 0)
        self.assertEqual(result.fn, 0)

    def test_header_field_incorrect_value(self):
        gt = {"po_number": "PO-123"}
        pred = {"po_number": "PO-456"}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")
        # Both exist but incorrect -> FP + FN
        self.assertEqual(result.tp, 0)
        self.assertEqual(result.fp, 1)
        self.assertEqual(result.fn, 1)

    def test_header_field_missing_required(self):
        gt = {"po_number": "PO-123"}
        pred = {}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")
        # GT exists, pred missing -> FN
        self.assertEqual(result.tp, 0)
        self.assertEqual(result.fp, 0)
        self.assertEqual(result.fn, 1)

    def test_header_field_unexpected_predicted(self):
        gt = {}
        pred = {"po_number": "PO-123"}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")
        # Pred exists, GT doesn't -> FP
        self.assertEqual(result.tp, 0)
        self.assertEqual(result.fp, 1)
        self.assertEqual(result.fn, 0)

    def test_line_item_identification_hand_calculated(self):
        # GT: 5 items, Pred: 4 items, Matches: 3
        gt = {"line_items": [{"sku": str(i), "description": f"Item {i}"} for i in range(5)]}
        pred = {"line_items": [{"sku": str(i), "description": f"Item {i}"} for i in range(3)] + [{"sku": "extra", "description": "Extra Item"}]}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")

        # Line items: TP=3 (matched), FP=1 (unmatched pred), FN=2 (unmatched GT)
        # Header fields: none
        # Plus field-level evaluation for matched items (description matches = TP for each)
        # 3 matches * 1 description field each = 3 additional TP
        # Total TP = 3 (identification) + 3 (description fields) = 6
        self.assertEqual(result.tp, 6)
        self.assertEqual(result.fp, 1)
        self.assertEqual(result.fn, 2)

        # Verify through dataset metrics
        report = EvaluationReport()
        report.add_document(result)
        self.assertAlmostEqual(report.aggregate_dataset_metrics()["precision"], 0.857, places=2)  # 6/(6+1)

    def test_correct_sku_incorrect_quantity(self):
        # SKU matches, but quantity differs
        gt = {"line_items": [{"sku": "A", "quantity": 100}]}
        pred = {"line_items": [{"sku": "A", "quantity": 90}]}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")

        # Line item identification: TP=1 (SKU match)
        # Line item field (quantity): FP=1, FN=1 (both exist, incorrect)
        # Total: TP=1 (id) + 0 (qty) = 1
        # Total FP: 0 (id) + 1 (qty) = 1
        # Total FN: 0 (id) + 1 (qty) = 1
        self.assertEqual(result.tp, 1)  # Only identification TP
        self.assertEqual(result.fp, 1)  # Quantity FP
        self.assertEqual(result.fn, 1)  # Quantity FN

    def test_both_missing_optional_excluded(self):
        # Both None for optional field -> should be excluded from metrics
        gt = {"po_number": "PO-123", "supplier_name": None}
        pred = {"po_number": "PO-123", "supplier_name": None}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")

        # po_number: TP=1
        # supplier_name: both None -> excluded (evaluate_field returns True but gt/pred are None so no TP counted)
        self.assertEqual(result.tp, 1)
        self.assertEqual(result.fp, 0)
        self.assertEqual(result.fn, 0)

    def test_dataset_aggregate_equals_sum(self):
        # Verify dataset-level TP/FP/FN equals sum of document-level TP/FP/FN
        dataset = [
            ("po", "PO1", {"po_number": "PO-1", "line_items": [{"sku": "A"}]},
                     {"po_number": "PO-1", "line_items": [{"sku": "A"}]}),
            ("po", "PO2", {"po_number": "PO-2", "line_items": [{"sku": "B"}]},
                     {"po_number": "PO-2", "line_items": [{"sku": "B"}]}),
            ("invoice", "INV1", {"invoice_number": "INV-1", "line_items": [{"sku": "C"}]},
                      {"invoice_number": "INV-1", "line_items": [{"sku": "C"}]}),
        ]
        report = self.evaluator.evaluate_dataset(dataset)

        # Sum of individual document metrics
        sum_tp = sum(doc.tp for doc in report.documents)
        sum_fp = sum(doc.fp for doc in report.documents)
        sum_fn = sum(doc.fn for doc in report.documents)

        # Dataset aggregates
        agg = report.aggregate_dataset_metrics()

        self.assertEqual(agg["tp"], sum_tp)
        self.assertEqual(agg["fp"], sum_fp)
        self.assertEqual(agg["fn"], sum_fn)

if __name__ == '__main__':
    unittest.main()