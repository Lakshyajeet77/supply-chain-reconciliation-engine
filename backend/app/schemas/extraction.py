"""Structured extraction DTOs. Financial fields use Decimal, never float."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=4)]
Quantity = Annotated[Decimal, Field(max_digits=18, decimal_places=6)]


class ExtractedLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_number: int | None = None
    description: str | None = None
    sku: str | None = None
    quantity: Quantity | None = None
    unit_of_measure: str | None = None
    unit_price: Money | None = None
    line_total: Money | None = None


class PurchaseOrderRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str = "purchase_order"
    po_number: str | None = None
    supplier_name: str | None = None
    order_date: date | None = None
    currency: str | None = None
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    subtotal: Money | None = None
    tax_total: Money | None = None
    total: Money | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be an ISO 4217 alphabetic code")
        return normalized


class DeliveryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str = "delivery"
    delivery_number: str | None = None
    po_reference: str | None = None
    supplier_name: str | None = None
    delivery_date: date | None = None
    line_items: list[ExtractedLineItem] = Field(default_factory=list)


class InvoiceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str = "invoice"
    invoice_number: str | None = None
    supplier_name: str | None = None
    invoice_date: date | None = None
    po_reference: str | None = None
    currency: str | None = None
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    subtotal: Money | None = None
    tax_total: Money | None = None
    total: Money | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be an ISO 4217 alphabetic code")
        return normalized
