"""Pydantic schemas for document relationships."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentRelationshipCreate(BaseModel):
    po_id: UUID
    invoice_id: UUID
    delivery_id: Optional[UUID] = None
    status: str = Field(default="SUGGESTED")


class DocumentRelationshipUpdate(BaseModel):
    status: Optional[str] = None
    delivery_id: Optional[UUID] = None


class DocumentRelationshipResponse(BaseModel):
    id: UUID
    po_id: UUID
    invoice_id: UUID
    delivery_id: Optional[UUID] = None
    status: str
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
