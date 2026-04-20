"""VCF parser supporting short-read and long-read (PacBio/ONT) FORMAT fields.

Two-layer design:
  _parse_record()  — raw VCF row → VCFRecord (no side-effects, testable)
  parse_vcf()      — file path → List[VCFRecord] (orchestrates cyvcf2 iteration)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.domain.enums import SVType, VariantOrigin
from app.domain.variant import VCFRecord

# Tumour/normal sample name patterns used by common somatic callers
_TUMOUR_PATTERNS = re.compile(r"(tumor|tumour|somatic|cancer|sample[_-]?t)", re.I)
_NORMAL_PATTERNS = re.compile(r"(normal|germline|blood|sample[_-]?n)", re.I)


def detect_origin(vcf_path: Path, info: dict[str, Any]) -> VariantOrigin:
    """Heuristic: SOMATIC INFO flag or tumour/normal sample name in filename."""
    if info.get("SOMATIC") is True or info.get("SOMATIC") == 1:
        return VariantOrigin.SOMATIC

    stem = vcf_path.stem.lower()
    if _TUMOUR_PATTERNS.search(stem):
        return VariantOrigin.SOMATIC
    if _NORMAL_PATTERNS.search(stem):
        return VariantOrigin.GERMLINE

    return VariantOrigin.UNKNOWN


def _sv_type_from_info(info: dict[str, Any]) -> SVType | None:
    raw = info.get("SVTYPE")
    if raw is None:
        return None
    try:
        return SVType(str(raw).upper())
    except ValueError:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_record(
    variant: Any,  # cyvcf2.Variant
    sample_names: list[str],
    origin: VariantOrigin,
) -> list[VCFRecord]:
    """Convert one cyvcf2 variant row into one VCFRecord per ALT allele.

    Returns a list because multi-allelic sites have multiple ALTs.
    """
    info: dict[str, Any] = {}
    for item in variant.INFO:
        try:
            # cyvcf2 INFO iterator yields (key, value) tuples
            if isinstance(item, tuple):
                k, v_val = item
                info[str(k)] = v_val
            else:
                info[str(item)] = variant.INFO[item]
        except Exception:
            pass

    sv_type = _sv_type_from_info(info)

    filter_list: list[str] = list(variant.FILTER.split(";")) if variant.FILTER else []

    records: list[VCFRecord] = []
    alts = list(variant.ALT) if variant.ALT else ["."]

    for sample_idx, sample_name in enumerate(sample_names):
        try:
            gt_tuple = variant.genotypes[sample_idx]
            # cyvcf2 returns e.g. [0, 1, True] where last element is phased flag
            phased = gt_tuple[-1] if len(gt_tuple) > 0 else False
            allele_ints = [a for a in gt_tuple[:-1] if a is not None]
            sep = "|" if phased else "/"
            gt_str: str | None = sep.join(
                "." if a == -1 else str(a) for a in allele_ints
            )
        except Exception:
            gt_str = None

        # DP
        dp: int | None = None
        try:
            dp_val = variant.format("DP")
            if dp_val is not None:
                dp = _safe_int(dp_val[sample_idx][0])
        except Exception:
            pass

        # AD
        ad: list[int] | None = None
        try:
            ad_val = variant.format("AD")
            if ad_val is not None:
                ad = [int(x) for x in ad_val[sample_idx] if x != -1]
        except Exception:
            pass

        # AF (somatic callers like Mutect2 emit per-sample AF)
        af: float | None = None
        try:
            af_val = variant.format("AF")
            if af_val is not None:
                af = _safe_float(af_val[sample_idx][0])
        except Exception:
            pass

        # HP — haplotype phasing tag (ONT / PacBio)
        hp: int | None = None
        try:
            hp_val = variant.format("HP")
            if hp_val is not None:
                hp = _safe_int(hp_val[sample_idx][0])
        except Exception:
            pass

        qual: float | None = _safe_float(variant.QUAL)

        records.append(
            VCFRecord(
                chrom=variant.CHROM,
                pos=variant.POS,
                id=variant.ID or None,
                ref=variant.REF,
                alt=alts,
                qual=qual,
                filter=filter_list,
                genotype=gt_str,
                depth=dp,
                allele_depths=ad,
                allele_freq=af,
                haplotype_phase=hp,
                info=info,
                sv_type=sv_type,
                origin=origin,
                sample_id=sample_name,
            )
        )

    return records


def parse_vcf(vcf_path: Path | str, sample_name: str | None = None) -> list[VCFRecord]:
    """Parse a VCF file and return a list of VCFRecord domain objects.

    Args:
        vcf_path: Path to the VCF file (plain or bgzipped).
        sample_name: Override the sample name (defaults to first sample in VCF).

    Returns:
        List of VCFRecord, one per variant (multi-sample: one per sample×variant).
    """
    import cyvcf2  # deferred import so unit-tests can mock/skip

    path = Path(vcf_path)
    vcf = cyvcf2.VCF(str(path))
    sample_names: list[str] = list(vcf.samples) if vcf.samples else ["UNKNOWN"]
    if sample_name is not None:
        sample_names = [sample_name]

    origin = detect_origin(path, {})
    records: list[VCFRecord] = []

    for variant in vcf:
        # Re-derive origin per-record so INFO/SOMATIC flag wins over filename
        per_record_info: dict[str, Any] = {}
        for item in variant.INFO:
            try:
                if isinstance(item, tuple):
                    k, v_val = item
                    per_record_info[str(k)] = v_val
                else:
                    per_record_info[str(item)] = variant.INFO[item]
            except Exception:
                pass
        per_record_origin = detect_origin(path, per_record_info)

        records.extend(_parse_record(variant, sample_names, per_record_origin))

    vcf.close()
    return records
