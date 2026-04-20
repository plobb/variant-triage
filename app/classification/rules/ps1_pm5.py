from __future__ import annotations

from typing import ClassVar

from app.classification.base import ACMGRule, EvidenceBundle
from app.domain.enums import EvidenceCode
from app.domain.variant import EvidenceItem, VCFRecord

_PATHOGENIC = "Pathogenic"


class PS1Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.PS1
    strength: ClassVar[str] = "PS"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        if _PATHOGENIC in evidence.clinvar_significances:
            return EvidenceItem(
                code=EvidenceCode.PS1,
                description="Same variant classified Pathogenic in ClinVar",
                source="ClinVar",
            )
        return None


class PM5Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.PM5
    strength: ClassVar[str] = "PM"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        # PM5 only fires when PS1 does not
        if _PATHOGENIC in evidence.clinvar_significances:
            return None
        if evidence.clinvar_same_residue:
            return EvidenceItem(
                code=EvidenceCode.PM5,
                description=(
                    "Different pathogenic missense at same residue in ClinVar"
                ),
                source="ClinVar",
            )
        return None
