from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

from app.classification.rules.pm1 import HOTSPOT_DOMAINS
from app.classification.somatic.base import SomaticEvidenceBundle
from app.domain.enums import ConsequenceType

if TYPE_CHECKING:
    from app.classification.evidence.gnomad import GnomadClient
    from app.classification.somatic.evidence.civic import CivicClient
    from app.classification.somatic.evidence.oncokb import OncoKbClient
    from app.domain.variant import VCFRecord


def _is_hotspot(chrom: str, pos: int) -> bool:
    for dom_chrom, dom_start, dom_end, _ in HOTSPOT_DOMAINS:
        if chrom == dom_chrom and dom_start <= pos <= dom_end:
            return True
    return False


def _get_gene(variant: VCFRecord) -> str:
    info: dict[str, Any] = variant.info
    return str(info.get("GENE") or info.get("gene") or info.get("ANN_gene") or "")


async def assemble_somatic_evidence(
    variant: VCFRecord,
    civic: CivicClient,
    oncokb: OncoKbClient,
    gnomad: GnomadClient,
) -> SomaticEvidenceBundle:
    alt = variant.alt[0] if variant.alt else variant.ref
    gene = _get_gene(variant)

    civic_result, oncokb_result, gnomad_result = await asyncio.gather(
        civic.lookup(variant.chrom, variant.pos, variant.ref, alt, gene),
        oncokb.lookup(variant.chrom, variant.pos, variant.ref, alt, gene),
        gnomad.lookup(variant.chrom, variant.pos, variant.ref, alt),
    )

    raw_consequence = variant.info.get("CSQ") or variant.info.get("consequence")
    is_synonymous = False
    if isinstance(raw_consequence, str):
        with contextlib.suppress(ValueError):
            is_synonymous = ConsequenceType(raw_consequence) == ConsequenceType.SYNONYMOUS

    return SomaticEvidenceBundle(
        civic_evidence_levels=civic_result.get("evidence_levels") or [],
        civic_has_approved_therapy=bool(
            civic_result.get("has_approved_therapy")
        ),
        civic_has_investigational_therapy=bool(
            civic_result.get("has_investigational_therapy")
        ),
        civic_therapy_implications=civic_result.get("therapy_implications") or [],
        oncokb_oncogenicity=oncokb_result.get("oncogenicity"),
        oncokb_highest_sensitive_level=oncokb_result.get("highestSensitiveLevel"),
        oncokb_highest_resistance_level=oncokb_result.get("highestResistanceLevel"),
        oncokb_therapy_implications=oncokb_result.get("therapy_implications") or [],
        gnomad_af=gnomad_result.get("af"),
        is_synonymous=is_synonymous,
        is_hotspot=_is_hotspot(variant.chrom, variant.pos),
    )
