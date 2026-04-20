from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from app.domain.enums import ClassificationTier, ConsequenceType, EvidenceCode
from app.domain.variant import ClassificationResult, EvidenceItem, Variant, VCFRecord


@dataclass
class EvidenceBundle:
    gnomad_af: float | None = None
    gnomad_pli: float | None = None
    gnomad_mis_z: float | None = None
    clinvar_significances: list[str] = field(default_factory=list)
    clinvar_same_residue: list[str] = field(default_factory=list)
    cadd_phred: float | None = None
    revel_score: float | None = None
    consequence: ConsequenceType | None = None
    is_frameshift: bool = False
    is_splice: bool = False
    protein_length_change: bool = False


STRENGTH_POINTS: dict[str, int] = {
    "PVS": 8,
    "PS": 4,
    "PM": 2,
    "PP": 1,
    "BA": -100,
    "BS": -4,
    "BP": -1,
}


class ACMGRule(ABC):
    code: ClassVar[EvidenceCode]
    strength: ClassVar[str]

    @abstractmethod
    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None: ...


def _code_prefix(code: EvidenceCode) -> str:
    v = code.value
    for prefix in ("PVS", "PS", "PM", "PP", "BA", "BS", "BP"):
        if v.startswith(prefix):
            return prefix
    return "PP"


_TIER_SCORE: dict[ClassificationTier, float] = {
    ClassificationTier.PATHOGENIC: 0.99,
    ClassificationTier.LIKELY_PATHOGENIC: 0.80,
    ClassificationTier.VUS: 0.50,
    ClassificationTier.LIKELY_BENIGN: 0.20,
    ClassificationTier.BENIGN: 0.01,
}


def _points_to_tier(points: int) -> ClassificationTier:
    if points >= 10:
        return ClassificationTier.PATHOGENIC
    if points >= 6:
        return ClassificationTier.LIKELY_PATHOGENIC
    if points >= 0:
        return ClassificationTier.VUS
    if points >= -5:
        return ClassificationTier.LIKELY_BENIGN
    return ClassificationTier.BENIGN


class RuleEngine:
    def __init__(self, rules: list[ACMGRule]) -> None:
        self._rules = rules

    def classify(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> ClassificationResult:
        items: list[EvidenceItem] = []
        for rule in self._rules:
            item = rule.evaluate(variant, evidence)
            if item is not None:
                items.append(item)

        points = 0
        has_ba = False
        for item in items:
            prefix = _code_prefix(item.code)
            base = STRENGTH_POINTS.get(prefix, 0)
            points += int(base * item.strength_modifier)
            if prefix == "BA":
                has_ba = True

        tier = ClassificationTier.BENIGN if has_ba else _points_to_tier(points)

        wrapped = Variant(
            vcf_record=variant,
            consequence=evidence.consequence or ConsequenceType.UNKNOWN,
        )
        return ClassificationResult(
            variant=wrapped,
            tier=tier,
            evidence=items,
            pathogenic_score=_TIER_SCORE[tier],
            is_automated=True,
        )
