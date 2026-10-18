"""Upload validation and document API tests."""

from tests.conftest import make_corrupt_pdf


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_valid_png(client, sample_png_bytes):
    response = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("invoice.png", sample_png_bytes, "image/png")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["duplicate"] is False
    doc = body["document"]
    assert doc["processing_status"] == "uploaded"
    assert doc["content_type"] == "image/png"
    assert len(doc["sha256"]) == 64
    # Processing status is not reconciliation status
    assert "matched" not in doc["processing_status"]


def test_upload_valid_pdf(client, sample_pdf_bytes):
    response = client.post(
        "/documents/upload",
        data={"document_type": "purchase_order"},
        files={"file": ("po.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["document"]["document_type"] == "purchase_order"


def test_reject_empty_file(client):
    response = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400
    assert "Empty" in response.json()["detail"]["message"]


def test_reject_unsupported_bytes(client):
    response = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]["message"]


def test_reject_corrupt_pdf(client):
    response = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("bad.pdf", make_corrupt_pdf(), "application/pdf")},
    )
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]["message"].lower() or "EOF" in response.json()["detail"]["message"]


def test_reject_extension_mismatch(client, sample_png_bytes):
    response = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("invoice.pdf", sample_png_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    assert "extension" in response.json()["detail"]["message"].lower()


def test_list_and_get_document(client, sample_jpeg_bytes):
    upload = client.post(
        "/documents/upload",
        data={"document_type": "delivery"},
        files={"file": ("delivery.jpg", sample_jpeg_bytes, "image/jpeg")},
    )
    doc_id = upload.json()["document"]["id"]

    listed = client.get("/documents")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    detail = client.get(f"/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == doc_id
