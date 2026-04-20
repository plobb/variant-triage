from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from app.classification.base import EvidenceBundle
from app.domain.enums import ConsequenceType

if TYPE_CHECKING:
    from app.classification.evidence.clinvar import ClinVarClient
    from app.classification.evidence.gnomad import GnomadClient
    from app.domain.variant import VCFRecord

_SPLICE_CONSEQUENCES = {
    ConsequenceType.SPLICE_DONOR,
    ConsequenceType.SPLICE_ACCEPTOR,
}


def _get_consequence(variant: VCFRecord) -> ConsequenceType | None:
    raw = variant.info.get("CSQ") or variant.info.get("consequence")
    if isinstance(raw, str):
        try:
            return ConsequenceType(raw)
        except ValueError:
            pass
    return None


def _is_frameshift(variant: VCFRecord, consequence: ConsequenceType | None) -> bool:
    if consequence == ConsequenceType.FRAMESHIFT:
        return True
    if len(variant.ref) != len(variant.alt[0] if variant.alt else variant.ref):
        net = abs(len(variant.alt[0]) - len(variant.ref)) if variant.alt else 0
        return net % 3 != 0
    return False


def _is_splice(consequence: ConsequenceType | None) -> bool:
    return consequence in _SPLICE_CONSEQUENCES


def _protein_length_change(
    variant: VCFRecord, consequence: ConsequenceType | None
) -> bool:
    if consequence in (
        ConsequenceType.FRAMESHIFT,
        ConsequenceType.NONSENSE,
    ):
        return True
    if not variant.alt:
        return False
    ref_len = len(variant.ref)
    alt_len = len(variant.alt[0])
    if ref_len == alt_len:
        return False
    net = abs(alt_len - ref_len)
    return net % 3 == 0  # in-frame indel changes protein length


def _float_from_info(info: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        val = info.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return None


async def assemble_evidence(
    variant: VCFRecord,
    gnomad: GnomadClient,
    clinvar: ClinVarClient,
) -> EvidenceBundle:
    alt = variant.alt[0] if variant.alt else variant.ref

    gnomad_result, clinvar_result = await asyncio.gather(
        gnomad.lookup(variant.chrom, variant.pos, variant.ref, alt),
        clinvar.lookup(variant.chrom, variant.pos, variant.ref, alt),
    )

    consequence = _get_consequence(variant)

    return EvidenceBundle(
        gnomad_af=gnomad_result.get("af"),
        gnomad_pli=gnomad_result.get("pli"),
        gnomad_mis_z=gnomad_result.get("mis_z"),
        clinvar_significances=clinvar_result.get("significances", []),
        clinvar_same_residue=clinvar_result.get("same_residue_pathogenic", []),
        cadd_phred=_float_from_info(variant.info, "CADD_PHRED", "CADD"),
        revel_score=_float_from_info(variant.info, "REVEL"),
        consequence=consequence,
        is_frameshift=_is_frameshift(variant, consequence),
        is_splice=_is_splice(consequence),
        protein_length_change=_protein_length_change(variant, consequence),
    )
