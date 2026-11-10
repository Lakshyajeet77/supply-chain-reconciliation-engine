from __future__ import annotations
from typing import Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

class CorrectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_path: str = Field(..., description="Field path e.g. po_number or line_items.0.quantity")
    original_value: Any = None
    corrected_value: Any = None
    reviewer_id: str = Field(default="system-reviewer")

class CorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    review_request_id: UUID
    field_path: str
    original_value: Any
    corrected_value: Any
    version: int
    corrected_by: str
    corrected_at: datetime

class ReviewActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(..., description="APPROVED, REJECTED, or IN_REVIEW")
    reviewer_id: str = Field(default="system-reviewer")
    notes: str | None = None

class ReviewActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    review_request_id: UUID
    action: str
    reviewer_id: str
    notes: str | None
    performed_at: datetime

class ReviewRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID
    status: str
    original_extraction: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    corrections: list[CorrectionResponse] = Field(default_factory=list)
    actions: list[ReviewActionResponse] = Field(default_factory=list)
