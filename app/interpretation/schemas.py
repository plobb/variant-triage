from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class InterpretationRequest(BaseModel):
    variant_id: str
    chrom: str
    pos: int
    ref: str
    alt: str
    gene: str | None = None
    classification_tier: str
    evidence_codes: list[str] = []
    amp_tier: str | None = None
    therapy_implications: list[str] = []
    oncokb_oncogenicity: str | None = None
    acmg_points: int | None = None
    origin: str
    notes: str | None = None


class InterpretationResponse(BaseModel):
    variant_id: str
    interpretation: str
    confidence: str
    guardrail_flags: list[str]
    disclaimer: str
    model_used: str
    generated_at: datetime


class InterpretationError(BaseModel):
    variant_id: str
    error: str
    generated_at: datetime
