"""Confidence metadata for extracted document fields."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
class ConfidenceStatus(str, Enum):
    PRESENT = "present"
    MISSING = "missing"
    UNCERTAIN = "uncertain"
class FieldConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ConfidenceStatus
    score: float | None = Field(default=None, ge=0.0, le=1.0, description="Non-calibrated score (0..1) provided by the extraction provider.")
    note: str | None = None
class ConfidenceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1"
    source: str | None = None
    overall_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Non-calibrated overall score for the extraction result.")
    fields: dict[str, FieldConfidence] = Field(default_factory=dict)
