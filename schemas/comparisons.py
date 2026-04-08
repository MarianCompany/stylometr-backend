from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ComparisonResponse(BaseModel):
    profile_id: int
    profile_name: str
    is_public_profile: bool
    candidate_source_type: str
    candidate_text_id: int | None
    candidate_text_length: int
    comparison_metrics: dict[str, float]
    burrows_delta: float
    cosine_similarity: float
    authorship_probability: float
    used_features: dict[str, int]
    analysis_meta: dict[str, Any] | None = None
    warnings: list[str] | None = None
    analyzed_at: datetime
