from enum import Enum
from typing import NamedTuple
from pydantic import BaseModel, Field

class MatchType(str, Enum):
    EXACT_SKU = "exact_sku"
    EXACT_DESCRIPTION = "exact_description"
    FUZZY_DESCRIPTION = "fuzzy_description"
    UNMATCHED = "unmatched"

class MatchSignal(BaseModel):
    name: str
    score: float  # 0.0 to 1.0

class LineItemMatch(BaseModel):
    score: float
    match_type: MatchType
    signals: list[MatchSignal] = Field(default_factory=list)
    explanation: str

class MatchingResult(BaseModel):
    invoice_to_po: dict[int, LineItemMatch] = Field(default_factory=dict)
    delivery_to_po: dict[int, LineItemMatch] = Field(default_factory=dict)
