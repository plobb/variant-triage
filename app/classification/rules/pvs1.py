from __future__ import annotations

from typing import ClassVar

from app.classification.base import ACMGRule, EvidenceBundle
from app.domain.enums import EvidenceCode
from app.domain.variant import EvidenceItem, VCFRecord

_PLI_THRESHOLD = 0.9


class PVS1Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.PVS1
    strength: ClassVar[str] = "PVS"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        if not (evidence.is_frameshift or evidence.is_splice):
            return None
        pli = evidence.gnomad_pli
        if pli is None or pli < _PLI_THRESHOLD:
            return None
        return EvidenceItem(
            code=EvidenceCode.PVS1,
            description=f"LoF variant in pLI≥0.9 gene (pLI={pli:.3f})",
        )
