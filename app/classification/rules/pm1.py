from __future__ import annotations

from typing import ClassVar

from app.classification.base import ACMGRule, EvidenceBundle
from app.domain.enums import EvidenceCode
from app.domain.variant import EvidenceItem, VCFRecord

# (chrom, start, end, label) — GRCh38 coordinates
_HOTSPOT_DOMAINS: list[tuple[str, int, int, str]] = [
    ("chr17", 43044295, 43125483, "BRCA1 RING domain"),
    ("chr17", 7669609, 7676594, "TP53 DNA-binding domain"),
    ("chr12", 25227343, 25227348, "KRAS G12/G13 hotspot"),
    ("chr7", 55019021, 55211628, "EGFR kinase domain"),
    ("chr3", 179148114, 179240952, "PIK3CA helical/kinase domain"),
    ("chr13", 32315474, 32400266, "BRCA2 DNA-binding domain"),
    ("chr17", 37844167, 37884915, "ERBB2 kinase domain"),
    ("chr9", 107545975, 107551675, "TSC1 coiled-coil domain"),
    ("chr16", 2097895, 2138721, "TSC2 GAP domain"),
    ("chr5", 112707498, 112846239, "APC ARM repeat domain"),
    ("chr10", 89623195, 89728532, "PTEN phosphatase domain"),
    ("chr11", 108098940, 108236624, "ATM FAT domain"),
    ("chr2", 212240509, 212248068, "STK11 kinase domain"),
    ("chr1", 226061851, 226120285, "MUTYH DNA glycosylase domain"),
]


class PM1Rule(ACMGRule):
    code: ClassVar[EvidenceCode] = EvidenceCode.PM1
    strength: ClassVar[str] = "PM"

    def evaluate(
        self, variant: VCFRecord, evidence: EvidenceBundle
    ) -> EvidenceItem | None:
        chrom = variant.chrom
        pos = variant.pos
        for dom_chrom, dom_start, dom_end, label in _HOTSPOT_DOMAINS:
            if chrom == dom_chrom and dom_start <= pos <= dom_end:
                return EvidenceItem(
                    code=EvidenceCode.PM1,
                    description=f"Variant in functional domain: {label}",
                )
        return None
