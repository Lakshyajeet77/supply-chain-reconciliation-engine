"""End-to-end extraction integration tests for Milestone 1."""
from pathlib import Path
from app.schemas.common import DocumentType
from app.services.extraction.orchestrator import ExtractionWorkflow
from app.services.extraction.fixture_provider import FixtureExtractionProvider
def test_upload_with_fixture_extraction_produces_extracted_data_and_confidence(client, sample_png_bytes):
    resp = client.post("/documents/upload", data={"document_type": "invoice", "fixture_id": "invoice_matched"}, files={"file": ("a.png", sample_png_bytes, "image/png")})
    assert resp.status_code == 201
    body = resp.json()
    doc = body["document"]
    assert doc["processing_status"] == "extracted"
    assert doc["extraction_fixture_id"] == "invoice_matched"
    extracted = doc["extracted_data"]
    assert extracted is not None
    assert extracted["document_type"] == "invoice"
    assert "extracted" in extracted
    assert "confidence" in extracted
    data = extracted["extracted"]
    assert data["invoice_number"] == "INV-9001"
    conf = extracted["confidence"]
    assert conf["schema_version"] == "1"
    assert conf["overall_score"] is not None
    assert "fields" in conf
def test_extraction_failure_marks_processing_failed(client, sample_png_bytes):
    resp = client.post("/documents/upload", data={"document_type": "invoice", "fixture_id": "does_not_exist"}, files={"file": ("a.png", sample_png_bytes, "image/png")})
    assert resp.status_code == 201
    doc = resp.json()["document"]
    assert doc["processing_status"] == "processing_failed"
    assert doc["failure_reason"] == "extraction_failed"
def test_extraction_provider_interface_and_confidence(sample_png_bytes):
    fixtures_dir = Path(__file__).parent.parent / "app" / "fixtures" / "extraction"
    provider = FixtureExtractionProvider(fixtures_dir=fixtures_dir)
    workflow = ExtractionWorkflow(provider=provider)
    artifacts = workflow.extract(document_type=DocumentType.INVOICE, file_bytes=sample_png_bytes, fixture_id="invoice_matched")
    assert artifacts.extracted.invoice_number == "INV-9001"
    assert artifacts.confidence.schema_version == "1"
    assert artifacts.confidence.overall_score is not None
    assert isinstance(artifacts.confidence.overall_score, float)
