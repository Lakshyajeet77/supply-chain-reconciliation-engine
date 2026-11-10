"""Upload validation and document API tests."""
from tests.conftest import make_corrupt_pdf
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
def test_upload_valid_png_without_extraction(client, sample_png_bytes):
    response = client.post("/documents/upload", data={"document_type": "invoice"}, files={"file": ("invoice.png", sample_png_bytes, "image/png")})
    assert response.status_code == 201
    body = response.json()
    assert body["duplicate"] is False
    doc = body["document"]
    assert doc["processing_status"] == "uploaded"
    assert doc["content_type"] == "image/png"
    assert len(doc["sha256"]) == 64
def test_upload_valid_png_with_extraction(client, sample_png_bytes):
    response = client.post("/documents/upload", data={"document_type": "invoice", "fixture_id": "invoice_matched"}, files={"file": ("invoice.png", sample_png_bytes, "image/png")})
    assert response.status_code == 201
    doc = response.json()["document"]
    assert doc["processing_status"] == "extracted"
    assert doc["extraction_fixture_id"] == "invoice_matched"
    assert doc["extracted_data"] is not None
def test_upload_valid_pdf(client, sample_pdf_bytes):
    response = client.post("/documents/upload", data={"document_type": "purchase_order"}, files={"file": ("po.pdf", sample_pdf_bytes, "application/pdf")})
    assert response.status_code == 201
    assert response.json()["document"]["document_type"] == "purchase_order"
def test_reject_empty_file(client):
    response = client.post("/documents/upload", data={"document_type": "invoice"}, files={"file": ("empty.png", b"", "image/png")})
    assert response.status_code == 400
    assert "Empty" in response.json()["detail"]["message"]
def test_reject_unsupported_bytes(client):
    response = client.post("/documents/upload", data={"document_type": "invoice"}, files={"file": ("notes.txt", b"hello world", "text/plain")})
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]["message"]
def test_reject_corrupt_pdf(client):
    response = client.post("/documents/upload", data={"document_type": "invoice"}, files={"file": ("bad.pdf", make_corrupt_pdf(), "application/pdf")})
    assert response.status_code == 400
    msg = response.json()["detail"]["message"]
    assert "corrupted" in msg.lower() or "EOF" in msg
def test_reject_extension_mismatch(client, sample_png_bytes):
    response = client.post("/documents/upload", data={"document_type": "invoice"}, files={"file": ("invoice.pdf", sample_png_bytes, "application/pdf")})
    assert response.status_code == 400
    assert "extension" in response.json()["detail"]["message"].lower()
def test_list_and_get_document(client, sample_jpeg_bytes):
    upload = client.post("/documents/upload", data={"document_type": "delivery"}, files={"file": ("delivery.jpg", sample_jpeg_bytes, "image/jpeg")})
    doc_id = upload.json()["document"]["id"]
    listed = client.get("/documents")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    detail = client.get(f"/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == doc_id


def test_get_document_file_serves_original_bytes(client, sample_png_bytes):
    upload = client.post("/documents/upload", data={"document_type": "invoice"}, files={"file": ("invoice.png", sample_png_bytes, "image/png")})
    doc_id = upload.json()["document"]["id"]
    response = client.get(f"/documents/{doc_id}/file")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert "inline" in response.headers["content-disposition"]
    assert response.content == sample_png_bytes


def test_get_document_file_unknown_id_404(client):
    import uuid
    response = client.get(f"/documents/{uuid.uuid4()}/file")
    assert response.status_code == 404
