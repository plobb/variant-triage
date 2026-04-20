from __future__ import annotations

from typing import ClassVar

from app.classification.base import ACMGRule, EvidenceBundle
from app.domain.enums import EvidenceCode
from app.domain.variant import EvidenceItem, VCFRecord

_BA1_THRESHOLD = 0.05
_PM2_THRESHOLD = 0.001


class BA1Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.BA1
    strength: ClassVar[str] = "BA"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        af = evidence.gnomad_af
        if af is not None and af > _BA1_THRESHOLD:
            return EvidenceItem(
                code=EvidenceCode.BA1,
                description=f"Common variant in gnomAD (AF={af:.4f} > {_BA1_THRESHOLD})",
                source="gnomAD",
            )
        return None


class PM2Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.PM2
    strength: ClassVar[str] = "PM"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        af = evidence.gnomad_af
        # BA1 takes priority — if AF > 0.05, PM2 should not fire
        if af is not None and af > _BA1_THRESHOLD:
            return None
        if af is None or af < _PM2_THRESHOLD:
            af_str = "absent" if af is None else f"{af:.6f}"
            return EvidenceItem(
                code=EvidenceCode.PM2,
                description=f"Absent/rare in gnomAD (AF={af_str})",
                source="gnomAD",
            )
        return None
