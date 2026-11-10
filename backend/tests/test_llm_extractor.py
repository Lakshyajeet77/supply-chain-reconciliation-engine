"""Mocked tests for the live extraction provider; no external API calls are made."""

import json
from types import SimpleNamespace

import pytest
from google.genai import types

from app.schemas.common import DocumentType
from app.services.extraction.llm_extractor import (
    ExtractionConfigurationError,
    ExtractionError,
    LLMExtractionProvider,
    UnsupportedDocumentError,
)


class FakeModels:
    def __init__(self, response_text=None, error=None):
        self.response_text = response_text
        self.error = error
        self.call = None

    def generate_content(self, **kwargs):
        self.call = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.response_text)


class FakeClient:
    def __init__(self, models):
        self.models = models


def provider(response_text, error=None):
    models = FakeModels(response_text=response_text, error=error)
    return LLMExtractionProvider(
        api_key="test-key-not-real",
        model="test-model",
        client=FakeClient(models),
    ), models


def test_extract_invoice_uses_schema_and_returns_typed_data(monkeypatch):
    monkeypatch.setattr(
        types.Part,
        "from_bytes",
        classmethod(lambda cls, data, mime_type: {"data": data, "mime_type": mime_type}),
    )
    payload = {
        "document_type": "invoice",
        "invoice_number": "INV-42",
        "supplier_name": "Example Supplies",
        "invoice_date": "2026-10-01",
        "po_reference": "PO-9",
        "currency": "inr",
        "line_items": [
            {"description": "Steel bolts", "quantity": "10", "unit_price": "2.50", "line_total": "25.00"}
        ],
        "subtotal": "25.00",
        "tax_total": "4.50",
        "total": "29.50",
    }
    provider_instance, models = provider(json.dumps(payload))
    result = provider_instance.extract(
        document_type=DocumentType.INVOICE,
        file_bytes=b"%PDF-1.7 test pdf bytes",
    )

    assert result.document_type is DocumentType.INVOICE
    assert result.data.invoice_number == "INV-42"
    assert result.data.currency == "INR"
    assert str(result.data.total) == "29.50"
    assert models.call["model"] == "test-model"
    assert models.call["config"].response_mime_type == "application/json"
    assert models.call["contents"][1]["mime_type"] == "application/pdf"


@pytest.mark.parametrize(
    ("document_type", "payload"),
    [
        (DocumentType.PURCHASE_ORDER, {"document_type": "purchase_order", "po_number": "PO-1"}),
        (DocumentType.DELIVERY, {"document_type": "delivery", "delivery_number": "DN-1"}),
        (DocumentType.INVOICE, {"document_type": "invoice", "invoice_number": "INV-1"}),
    ],
)
def test_all_document_types_are_supported(monkeypatch, document_type, payload):
    monkeypatch.setattr(
        types.Part,
        "from_bytes",
        classmethod(lambda cls, data, mime_type: {"data": data, "mime_type": mime_type}),
    )
    instance, _ = provider(json.dumps(payload))
    result = instance.extract(document_type=document_type, file_bytes=b"\x89PNG\r\n\x1a\nfake")
    assert result.document_type is document_type


def test_missing_key_fails_without_creating_client():
    with pytest.raises(ExtractionConfigurationError, match="GEMINI_API_KEY"):
        LLMExtractionProvider(api_key=None, model="test-model")


@pytest.mark.parametrize("data", [b"", b"not a document", b"GIF89a fake"])
def test_unsupported_signatures_fail_before_api_call(data):
    instance, models = provider('{"document_type":"invoice"}')
    with pytest.raises(ExtractionError):
        instance.extract(document_type=DocumentType.INVOICE, file_bytes=data)
    assert models.call is None


def test_provider_error_is_wrapped_without_exposing_provider_message():
    instance, _ = provider(None, error=RuntimeError("sensitive provider internals"))
    with pytest.raises(ExtractionError, match="request failed") as exc:
        instance.extract(document_type=DocumentType.INVOICE, file_bytes=b"%PDF-1.7 test")
    assert "sensitive provider internals" not in str(exc.value)


def test_empty_response_fails():
    instance, _ = provider(" ")
    with pytest.raises(ExtractionError, match="empty response"):
        instance.extract(document_type=DocumentType.INVOICE, file_bytes=b"%PDF-1.7 test")


def test_invalid_schema_response_fails():
    instance, _ = provider('{"document_type":"invoice","currency":"US DOLLAR"}')
    with pytest.raises(ExtractionError, match="invalid structured data"):
        instance.extract(document_type=DocumentType.INVOICE, file_bytes=b"%PDF-1.7 test")


def test_wrong_document_type_fails():
    instance, _ = provider('{"document_type":"delivery","delivery_number":"DN-1"}')
    with pytest.raises(ExtractionError, match="type mismatch"):
        instance.extract(document_type=DocumentType.INVOICE, file_bytes=b"%PDF-1.7 test")
