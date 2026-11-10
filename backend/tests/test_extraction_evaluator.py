import unittest
from decimal import Decimal
from app.evaluation.extraction.evaluator import ExtractionEvaluator

class TestExtractionEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = ExtractionEvaluator()

    def test_field_evaluation(self):
        # Test exact match
        self.assertTrue(self.evaluator.evaluate_field("PO-123", "PO-123", "po_number"))
        # Test normalized match (money)
        self.assertTrue(self.evaluator.evaluate_field("100.00", "100.0", "line_total"))
        # Test mismatch
        self.assertFalse(self.evaluator.evaluate_field("100.00", "101.00", "line_total"))

    def test_line_item_assignment_sku(self):
        gt = {"line_items": [{"sku": "A1", "description": "Widget A"}]}
        pred = {"line_items": [{"sku": "A1", "description": "Widget A"}]}
        results = self.evaluator.evaluate(gt, pred, "doc-1", "po")
        self.assertEqual(len(results.line_item_matches), 1)
        self.assertEqual(results.line_item_matches[0]["method"], "sku")

    def test_line_item_assignment_fuzzy(self):
        gt = {"line_items": [{"sku": None, "description": "Widget Apple"}]}
        pred = {"line_items": [{"sku": None, "description": "Apple Widget"}]}
        results = self.evaluator.evaluate(gt, pred, "doc-2", "po")
        self.assertEqual(len(results.line_item_matches), 1)
        self.assertEqual(results.line_item_matches[0]["method"], "fuzzy")

if __name__ == '__main__':
    unittest.main()
