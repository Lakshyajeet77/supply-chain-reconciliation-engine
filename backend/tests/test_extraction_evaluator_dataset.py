import unittest
from decimal import Decimal
from app.evaluation.extraction.evaluator import ExtractionEvaluator, EvaluationReport, DocumentEvaluationResult

class TestExtractionEvaluatorDataset(unittest.TestCase):
    def setUp(self):
        self.evaluator = ExtractionEvaluator()

    def test_dataset_aggregation(self):
        # Simulate two documents
        dataset = [
            ("po", "PO1", {"po_number": "PO-1", "line_items": []}, {"po_number": "PO-1", "line_items": []}),
            ("invoice", "INV1", {"invoice_number": "INV-1"}, {"invoice_number": "INV-1"})
        ]
        report = self.evaluator.evaluate_dataset(dataset)
        # Verify document-type metrics
        self.assertEqual(report.document_type_metrics["po"].tp, 1)
        self.assertEqual(report.document_type_metrics["invoice"].tp, 1)
        # Verify dataset-level metrics
        self.assertEqual(report.to_dict()["dataset_metrics"]["tp"], 2)

    def test_document_type_metrics(self):
        dataset = [
            ("po", "PO1", {"po_number": "PO-1"}, {"po_number": "PO-1"}),
            ("po", "PO2", {"po_number": "PO-2"}, {"po_number": "PO-X"})
        ]
        report = self.evaluator.evaluate_dataset(dataset)
        po_metrics = report.document_type_metrics["po"]
        # PO1: correct (tp=1)
        # PO2: incorrect value (fp=1, fn=1)
        # Total: tp=1, fp=1, fn=1
        self.assertEqual(po_metrics.tp, 1)
        self.assertEqual(po_metrics.fp, 1)
        self.assertEqual(po_metrics.fn, 1)

    def test_line_item_identification(self):
        gt = {"line_items": [{"sku": "A", "description": "Widget"}]}
        pred = {"line_items": [{"sku": "A", "description": "Widget"}]}
        result = self.evaluator.evaluate(gt, pred, "po", "PO1")
        self.assertEqual(len(result.line_item_matches), 1)

    def test_json_serialization(self):
        report = EvaluationReport()
        result = DocumentEvaluationResult(
            doc_id="PO1", doc_type="po",
            field_matches={"po_number": True}, line_item_matches=[],
            tp=1, fp=0, fn=0,
            line_items_total=0, line_items_matched=0
        )
        report.add_document(result)
        json_report = report.to_json()
        self.assertIn("dataset_id", json_report)

if __name__ == '__main__':
    unittest.main()