from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import VariantOrigin


class VCFSubmission(BaseModel):
    vcf_content: str = Field(max_length=1_000_000, description="Raw VCF text, max 1 MB")
    sample_name: str
    origin: VariantOrigin
    notes: str | None = None


class VariantResult(BaseModel):
    id: int
    chrom: str
    pos: int
    ref: str
    alt: str
    gene: str | None
    consequence: str | None


class GermlineVariantResult(VariantResult):
    result_type: Literal["germline"] = "germline"
    classification_tier: str
    acmg_points: int
    evidence_codes: list[str]
    summary: str


class SomaticVariantResult(VariantResult):
    result_type: Literal["somatic"] = "somatic"
    amp_tier: str
    confidence: str
    therapy_implications: list[dict[str, Any]]
    oncokb_oncogenicity: str | None
    summary: str


class GermlineClassificationResponse(BaseModel):
    sample_id: int
    sample_name: str
    variants_processed: int
    results: list[GermlineVariantResult]
    classified_at: datetime


class SomaticClassificationResponse(BaseModel):
    sample_id: int
    sample_name: str
    variants_processed: int
    results: list[SomaticVariantResult]
    classified_at: datetime


AnyVariantResult = Annotated[
    GermlineVariantResult | SomaticVariantResult,
    Field(discriminator="result_type"),
]


class BatchInterpretationBody(BaseModel):
    variant_ids: list[int]

    @field_validator("variant_ids")
    @classmethod
    def max_ten(cls, v: list[int]) -> list[int]:
        if len(v) > 10:
            raise ValueError("Maximum 10 variant IDs per batch")
        return v
