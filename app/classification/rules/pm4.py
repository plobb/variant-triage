from __future__ import annotations

from typing import ClassVar

from app.classification.base import ACMGRule, EvidenceBundle
from app.domain.enums import ConsequenceType, EvidenceCode
from app.domain.variant import EvidenceItem, VCFRecord


class PM4Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.PM4
    strength: ClassVar[str] = "PM"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        if not evidence.protein_length_change:
            return None
        # Nonsense (stop_gained) is handled by PVS1, not PM4
        if evidence.consequence == ConsequenceType.NONSENSE:
            return None
        return EvidenceItem(
            code=EvidenceCode.PM4,
            description="Protein length change (in-frame indel or stop-loss)",
        )
