"""Exact-file SHA-256 duplicate detection tests."""


def test_exact_file_duplicate_returns_409(client, sample_png_bytes):
    first = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("invoice-a.png", sample_png_bytes, "image/png")},
    )
    assert first.status_code == 201
    first_id = first.json()["document"]["id"]
    digest = first.json()["document"]["sha256"]

    second = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("invoice-b.png", sample_png_bytes, "image/png")},
    )
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["duplicate"] is True
    assert detail["sha256"] == digest
    assert detail["existing_document"]["id"] == first_id
    assert "Extraction was skipped" in detail["message"]

    # Registry still has exactly one document
    listed = client.get("/documents")
    assert listed.json()["count"] == 1


def test_different_bytes_are_not_duplicates(client, sample_png_bytes, sample_jpeg_bytes):
    first = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("a.png", sample_png_bytes, "image/png")},
    )
    second = client.post(
        "/documents/upload",
        data={"document_type": "invoice"},
        files={"file": ("b.jpg", sample_jpeg_bytes, "image/jpeg")},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["document"]["sha256"] != second.json()["document"]["sha256"]
    assert client.get("/documents").json()["count"] == 2
