from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.domain.variant import VCFRecord


class AMPTier(StrEnum):
    TIER_I = "Tier_I"
    TIER_II = "Tier_II"
    TIER_III = "Tier_III"
    TIER_IV = "Tier_IV"


class TherapyImplication(BaseModel):
    drug: str
    disease: str
    evidence_level: str
    source: str


@dataclass
class SomaticEvidenceBundle:
    civic_evidence_levels: list[str] = field(default_factory=list)
    civic_has_approved_therapy: bool = False
    civic_has_investigational_therapy: bool = False
    civic_therapy_implications: list[TherapyImplication] = field(default_factory=list)
    oncokb_oncogenicity: str | None = None
    oncokb_highest_sensitive_level: str | None = None
    oncokb_highest_resistance_level: str | None = None
    oncokb_therapy_implications: list[TherapyImplication] = field(default_factory=list)
    gnomad_af: float | None = None
    is_synonymous: bool = False
    is_hotspot: bool = False


class SomaticEvidenceSource(Protocol):
    async def lookup(
        self, chrom: str, pos: int, ref: str, alt: str, gene: str
    ) -> dict[str, Any]: ...


class SomaticClassificationResult(BaseModel):
    variant_id: str
    amp_tier: AMPTier
    confidence: str
    therapy_implications: list[TherapyImplication] = Field(default_factory=list)
    oncokb_oncogenicity: str | None = None
    civic_evidence_levels: list[str] = Field(default_factory=list)
    summary: str
    classified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


_TIER_I_ONCOKB = {"LEVEL_1", "LEVEL_2"}
_TIER_II_ONCOKB = {"LEVEL_3A", "LEVEL_3B"}
_TIER_I_CIVIC = {"A", "B"}
_TIER_II_CIVIC = {"A", "B", "C"}


class SomaticClassifier:
    def classify(
        self, variant: VCFRecord, evidence: SomaticEvidenceBundle
    ) -> SomaticClassificationResult:
        alt = variant.alt[0] if variant.alt else variant.ref
        variant_id = f"{variant.chrom}:{variant.pos}:{variant.ref}>{alt}"

        tier = self._assign_tier(evidence)
        confidence = self._assign_confidence(tier, evidence)
        therapy = (
            evidence.civic_therapy_implications + evidence.oncokb_therapy_implications
        )
        summary = self._make_summary(variant_id, tier, evidence)

        return SomaticClassificationResult(
            variant_id=variant_id,
            amp_tier=tier,
            confidence=confidence,
            therapy_implications=therapy,
            oncokb_oncogenicity=evidence.oncokb_oncogenicity,
            civic_evidence_levels=evidence.civic_evidence_levels,
            summary=summary,
        )

    @staticmethod
    def _assign_tier(ev: SomaticEvidenceBundle) -> AMPTier:
        # Tier IV first — benign evidence overrides therapeutic evidence
        if (ev.gnomad_af is not None and ev.gnomad_af > 0.01) or ev.is_synonymous:
            return AMPTier.TIER_IV

        civic_levels = set(ev.civic_evidence_levels)

        # Tier I
        if (ev.civic_has_approved_therapy and bool(civic_levels & _TIER_I_CIVIC)) or (
            ev.oncokb_highest_sensitive_level in _TIER_I_ONCOKB
        ):
            return AMPTier.TIER_I

        # Tier II
        if (
            bool(civic_levels & _TIER_II_CIVIC)
            or ev.oncokb_highest_sensitive_level in _TIER_II_ONCOKB
            or ev.is_hotspot
        ):
            return AMPTier.TIER_II

        return AMPTier.TIER_III

    @staticmethod
    def _assign_confidence(tier: AMPTier, ev: SomaticEvidenceBundle) -> str:
        if tier == AMPTier.TIER_I:
            return "high"
        if tier == AMPTier.TIER_II:
            civic_levels = set(ev.civic_evidence_levels)
            if civic_levels & _TIER_I_CIVIC:
                return "high"
            return "medium"
        if tier == AMPTier.TIER_III:
            return "medium" if ev.civic_evidence_levels else "low"
        return "low"  # Tier IV

    @staticmethod
    def _make_summary(
        variant_id: str, tier: AMPTier, ev: SomaticEvidenceBundle
    ) -> str:
        tier_label = tier.value.replace("_", " ")

        if tier == AMPTier.TIER_I:
            impl = ev.civic_therapy_implications or ev.oncokb_therapy_implications
            if impl:
                t = impl[0]
                levels = ", ".join(ev.civic_evidence_levels) or (
                    ev.oncokb_highest_sensitive_level or ""
                )
                return (
                    f"{variant_id}: {tier_label} — approved therapy available"
                    f" ({t.drug}, {t.disease}) [{t.source} level {levels}]"
                )
            return f"{variant_id}: {tier_label} — FDA-approved therapy available"

        if tier == AMPTier.TIER_II:
            parts: list[str] = []
            if ev.is_hotspot:
                parts.append("hotspot")
            if ev.civic_has_investigational_therapy or ev.civic_therapy_implications:
                parts.append("investigational therapies available")
            if ev.civic_evidence_levels:
                levels = ", ".join(ev.civic_evidence_levels)
                parts.append(f"CIViC level {levels}")
            detail = "; ".join(parts) if parts else "therapeutic evidence available"
            return f"{variant_id}: {tier_label} — {detail}"

        if tier == AMPTier.TIER_III:
            return f"{variant_id}: {tier_label} — variant of unknown significance"

        # Tier IV
        if ev.is_synonymous:
            return f"{variant_id}: {tier_label} — synonymous variant (likely benign)"
        af_str = f"{ev.gnomad_af:.4f}" if ev.gnomad_af is not None else "unknown"
        return f"{variant_id}: {tier_label} — common in gnomAD (AF={af_str})"
