"""Build confidence metadata for extracted Pydantic data."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from app.schemas.extraction_confidence import ConfidenceAssessment, ConfidenceStatus, FieldConfidence
from app.services.extraction.protocol import ExtractedDocument
@dataclass(frozen=True)
class BaselineConfidenceConfig:
    present_score: float = 0.95
    uncertain_score: float = 0.55
def _status_for_value(value: Any) -> ConfidenceStatus:
    if value is None:
        return ConfidenceStatus.MISSING
    if isinstance(value, str) and value.strip() == "":
        return ConfidenceStatus.UNCERTAIN
    return ConfidenceStatus.PRESENT
def _score_for_status(status: ConfidenceStatus, config: BaselineConfidenceConfig) -> float | None:
    if status == ConfidenceStatus.PRESENT:
        return config.present_score
    if status == ConfidenceStatus.MISSING:
        return None
    return config.uncertain_score
def _walk_and_collect(obj: Any, path: str, out: dict[str, FieldConfidence], config: BaselineConfidenceConfig) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            child_path = f"{path}.{k}" if path else str(k)
            _walk_and_collect(v, child_path, out, config)
        return
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            child_path = f"{path}[{i}]" if path else f"[{i}]"
            _walk_and_collect(v, child_path, out, config)
        return
    status = _status_for_value(obj)
    out[path] = FieldConfidence(status=status, score=_score_for_status(status, config))
def baseline_confidence_for_extracted_doc(*, document_type: str, extracted: ExtractedDocument, config: BaselineConfidenceConfig | None = None) -> ConfidenceAssessment:
    config = config or BaselineConfidenceConfig()
    data_dict = extracted.model_dump(mode="python", exclude_none=False)
    data_dict.pop("document_type", None)
    fields: dict[str, FieldConfidence] = {}
    _walk_and_collect(data_dict, "", fields, config)
    total = 0
    presentish = 0
    for fc in fields.values():
        total += 1
        if fc.status != ConfidenceStatus.MISSING:
            presentish += 1
    overall = None
    if total > 0:
        overall = max(0.0, min(1.0, float(presentish / total)))
    return ConfidenceAssessment(schema_version="1", source=f"baseline-heuristic::{document_type}", overall_score=overall, fields=fields)
