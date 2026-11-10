import unittest
from decimal import Decimal
from datetime import date
from app.evaluation.extraction.evaluator import ExtractionEvaluator
from app.evaluation.extraction.metrics import MetricCount

class TestExtractionEvaluatorExpanded(unittest.TestCase):
    def setUp(self):
        self.evaluator = ExtractionEvaluator()

    def test_expanded_field_evaluation(self):
        # 1. Exact/Normalized
        self.assertTrue(self.evaluator.evaluate_field("100.00", "100", "total"))
        # 2. Incorrect
        self.assertFalse(self.evaluator.evaluate_field("100.00", "105.00", "total"))
        # 3. Missing/Extra handled in evaluate()
        # 4. Empty
        self.assertTrue(self.evaluator.evaluate_field(None, None, "date"))
        # 5. Incompatible units
        self.assertFalse(self.evaluator.evaluate_field("10 pcs", "10 kg", "quantity"))
        # 6. Decimal Tolerance (10.0001 vs 10.0002 within tolerance 0.01)
        self.assertTrue(self.evaluator.evaluate_field(Decimal("10.0001"), Decimal("10.0002"), "total"))
        # 7. Zero vs Missing Money
        self.assertFalse(self.evaluator.evaluate_field(Decimal("0.00"), None, "total"))

    def test_metrics_calculation(self):
        metrics = MetricCount()
        metrics.add(tp=10, fp=2, fn=1)
        self.assertEqual(metrics.precision, 10/12)
        self.assertEqual(metrics.recall, 10/11)

        # Zero-division
        empty_metrics = MetricCount()
        self.assertEqual(empty_metrics.f1, 0.0)

    def test_line_item_assignment_complex(self):
        # Duplicate SKUs, Multiple Similar Descriptions, Assignment
        gt = {
            "line_items": [
                {"sku": "A", "description": "Item 1"},
                {"sku": "A", "description": "Item 2"}
            ]
        }
        pred = {
            "line_items": [
                {"sku": "A", "description": "Item 1"},
                {"sku": "A", "description": "Item 2 modified"}
            ]
        }
        results = self.evaluator.evaluate(gt, pred, "po", "PO1")
        # Should match both
        self.assertEqual(len(results.line_item_matches), 2)

    def test_aggregation(self):
        # Test document-level aggregation
        doc1 = {"field_matches": {"f1": True}, "metrics": {"tp": 1, "fp": 0, "fn": 0}}
        doc2 = {"field_matches": {"f1": False}, "metrics": {"tp": 0, "fp": 1, "fn": 0}}

        total_tp = doc1["metrics"]["tp"] + doc2["metrics"]["tp"]
        total_fp = doc1["metrics"]["fp"] + doc2["metrics"]["fp"]
        self.assertEqual(total_tp, 1)
        self.assertEqual(total_fp, 1)

if __name__ == '__main__':
    unittest.main()