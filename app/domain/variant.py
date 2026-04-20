from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import (
    ClassificationTier,
    ConsequenceType,
    EvidenceCode,
    SVType,
    VariantOrigin,
    Zygosity,
)


class VCFRecord(BaseModel):
    """Raw parsed record from a VCF file before domain enrichment."""

    chrom: str
    pos: int
    id: str | None = None
    ref: str
    alt: list[str]
    qual: float | None = None
    filter: list[str] = Field(default_factory=list)

    # FORMAT fields (may be absent in short-read or long-read VCFs)
    genotype: str | None = None      # GT field, e.g. "0/1"
    depth: int | None = None         # DP
    allele_depths: list[int] | None = None  # AD
    allele_freq: float | None = None  # AF (somatic callers)

    # Long-read specific
    haplotype_phase: int | None = None  # HP tag (ONT/PacBio phasing)

    # INFO fields
    info: dict[str, Any] = Field(default_factory=dict)

    # Derived
    sv_type: SVType | None = None
    origin: VariantOrigin = VariantOrigin.UNKNOWN
    sample_id: str | None = None

    @field_validator("pos")
    @classmethod
    def pos_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("VCF position must be ≥ 1 (1-based coordinate)")
        return v

    @field_validator("ref", "alt", mode="before")
    @classmethod
    def bases_uppercase(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        if isinstance(v, list):
            return [a.upper() if isinstance(a, str) else a for a in v]
        return v

    @property
    def is_snv(self) -> bool:
        return len(self.ref) == 1 and all(len(a) == 1 for a in self.alt)

    @property
    def is_indel(self) -> bool:
        return not self.is_snv and self.sv_type is None

    @property
    def is_structural(self) -> bool:
        return self.sv_type is not None


class Variant(BaseModel):
    """Enriched domain variant with annotation."""

    vcf_record: VCFRecord
    gene_symbol: str | None = None
    transcript_id: str | None = None
    hgvs_c: str | None = None
    hgvs_p: str | None = None
    consequence: ConsequenceType = ConsequenceType.UNKNOWN
    zygosity: Zygosity = Zygosity.UNKNOWN
    gnomad_af: float | None = None
    clinvar_id: str | None = None

    @model_validator(mode="after")
    def derive_zygosity(self) -> Variant:
        gt = self.vcf_record.genotype
        if gt is not None and self.zygosity == Zygosity.UNKNOWN:
            sep = "/" if "/" in gt else "|"
            alleles = gt.split(sep)
            unique = set(alleles) - {"."}
            if len(unique) == 0:
                pass  # no-call, leave UNKNOWN
            elif len(unique) == 1:
                if "0" in unique:
                    self.zygosity = Zygosity.HOMOZYGOUS_REF
                else:
                    self.zygosity = Zygosity.HOMOZYGOUS_ALT
            else:
                self.zygosity = Zygosity.HETEROZYGOUS
        return self


class EvidenceItem(BaseModel):
    """Single piece of ACMG/AMP evidence supporting a classification."""

    code: EvidenceCode
    description: str
    source: str | None = None
    strength_modifier: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Multiplier for evidence strength (1.0 = standard weight)",
    )


class ClassificationResult(BaseModel):
    """Final ACMG/AMP classification for a variant."""

    variant: Variant
    tier: ClassificationTier
    evidence: list[EvidenceItem] = Field(default_factory=list)
    pathogenic_score: float = Field(ge=0.0, le=1.0)
    reviewer_notes: str | None = None
    classified_by: str | None = None
    is_automated: bool = True

    @field_validator("pathogenic_score")
    @classmethod
    def score_precision(cls, v: float) -> float:
        return round(v, 4)

    @property
    def pathogenic_codes(self) -> list[str]:
        return [
            e.code.value
            for e in self.evidence
            if e.code.value.startswith(("PVS", "PS", "PM", "PP"))
        ]

    @property
    def benign_codes(self) -> list[str]:
        return [
            e.code.value
            for e in self.evidence
            if e.code.value.startswith(("BA", "BS", "BP"))
        ]
