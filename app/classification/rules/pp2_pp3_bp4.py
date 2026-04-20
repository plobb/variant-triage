from __future__ import annotations

from typing import ClassVar

from app.classification.base import ACMGRule, EvidenceBundle
from app.domain.enums import EvidenceCode
from app.domain.variant import EvidenceItem, VCFRecord

_MIS_Z_THRESHOLD = 3.09
_CADD_PP3 = 20.0
_REVEL_PP3 = 0.7
_CADD_BP4 = 10.0
_REVEL_BP4 = 0.3


class PP2Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.PP2
    strength: ClassVar[str] = "PP"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        mis_z = evidence.gnomad_mis_z
        if mis_z is not None and mis_z >= _MIS_Z_THRESHOLD:
            return EvidenceItem(
                code=EvidenceCode.PP2,
                description=(
                    f"Missense in gene intolerant to benign variation (mis_z={mis_z:.2f})"
                ),
                source="gnomAD",
            )
        return None


class PP3Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.PP3
    strength: ClassVar[str] = "PP"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        cadd = evidence.cadd_phred
        revel = evidence.revel_score
        if (cadd is not None and cadd >= _CADD_PP3) or (
            revel is not None and revel >= _REVEL_PP3
        ):
            parts: list[str] = []
            if cadd is not None:
                parts.append(f"CADD={cadd:.1f}")
            if revel is not None:
                parts.append(f"REVEL={revel:.3f}")
            return EvidenceItem(
                code=EvidenceCode.PP3,
                description=f"Computational evidence supports pathogenicity ({', '.join(parts)})",
            )
        return None


class BP4Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.BP4
    strength: ClassVar[str] = "BP"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        cadd = evidence.cadd_phred
        revel = evidence.revel_score
        if revel is None:
            return None
        if cadd is not None and cadd < _CADD_BP4 and revel < _REVEL_BP4:
            return EvidenceItem(
                code=EvidenceCode.BP4,
                description=(
                    f"Computational evidence suggests benign impact "
                    f"(CADD={cadd:.1f}, REVEL={revel:.3f})"
                ),
            )
        return None
