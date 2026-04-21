from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.variants.schemas import (
    GermlineClassificationResponse,
    GermlineVariantResult,
    SomaticClassificationResponse,
    SomaticVariantResult,
    VCFSubmission,
)
from app.classification.base import STRENGTH_POINTS, EvidenceBundle, RuleEngine
from app.classification.rules import DEFAULT_RULES
from app.classification.rules.pm1 import HOTSPOT_DOMAINS
from app.classification.somatic.base import SomaticClassifier, SomaticEvidenceBundle
from app.db.models import Classification, Sample, User, VariantModel
from app.domain.enums import ConsequenceType
from app.domain.variant import ClassificationResult, VCFRecord
from app.ingestion.vcf_parser import parse_vcf


def _code_prefix(code_value: str) -> str:
    for prefix in ("PVS", "PS", "PM", "PP", "BA", "BS", "BP"):
        if code_value.startswith(prefix):
            return prefix
    return "PP"


def _compute_acmg_points(result: ClassificationResult) -> int:
    points = 0
    for item in result.evidence:
        prefix = _code_prefix(item.code.value)
        base = STRENGTH_POINTS.get(prefix, 0)
        points += int(base * item.strength_modifier)
    return points


def _derive_consequence(record: VCFRecord) -> ConsequenceType:
    alt0 = record.alt[0] if record.alt else record.ref
    len_diff = abs(len(record.ref) - len(alt0))
    if len_diff == 0:
        return ConsequenceType.MISSENSE
    if len_diff % 3 != 0:
        return ConsequenceType.FRAMESHIFT
    return ConsequenceType.MISSENSE


def _check_is_hotspot(chrom: str, pos: int) -> bool:
    for dom_chrom, dom_start, dom_end, _ in HOTSPOT_DOMAINS:
        if chrom == dom_chrom and dom_start <= pos <= dom_end:
            return True
    return False


def _parse_vcf_content(vcf_content: str, sample_name: str) -> list[VCFRecord]:
    if not vcf_content.strip().startswith("##fileformat"):
        raise HTTPException(
            status_code=422,
            detail="Invalid VCF: content must start with ##fileformat header",
        )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".vcf", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(vcf_content)
        tmp_path = tmp.name
    try:
        return parse_vcf(Path(tmp_path), sample_name)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid VCF content: {exc}"
        ) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _evidence_data(clf: Classification) -> dict[str, Any]:
    raw: Any = clf.evidence_codes
    if isinstance(raw, dict):
        return raw
    return {}


def _build_germline_result(clf: Classification, variant: VariantModel) -> GermlineVariantResult:
    data = _evidence_data(clf)
    codes: list[str] = data.get("codes", [])
    acmg_points: int = data.get("acmg_points", 0)
    summary: str = data.get("summary", "")
    return GermlineVariantResult(
        id=clf.id,
        chrom=variant.chrom,
        pos=variant.pos,
        ref=variant.ref,
        alt=variant.alt,
        gene=variant.gene_symbol,
        consequence=variant.consequence,
        classification_tier=clf.tier,
        acmg_points=acmg_points,
        evidence_codes=codes,
        summary=summary,
    )


def _build_somatic_result(clf: Classification, variant: VariantModel) -> SomaticVariantResult:
    data = _evidence_data(clf)
    return SomaticVariantResult(
        id=clf.id,
        chrom=variant.chrom,
        pos=variant.pos,
        ref=variant.ref,
        alt=variant.alt,
        gene=variant.gene_symbol,
        consequence=variant.consequence,
        amp_tier=data.get("amp_tier", clf.tier),
        confidence=data.get("confidence", "low"),
        therapy_implications=data.get("therapy_implications", []),
        oncokb_oncogenicity=data.get("oncokb_oncogenicity"),
        summary=data.get("summary", ""),
    )


async def process_germline_submission(
    submission: VCFSubmission,
    user: User,
    db: AsyncSession,
) -> GermlineClassificationResponse:
    """Parse VCF, classify each variant with mock ACMG evidence, persist, and return results."""
    records = _parse_vcf_content(submission.vcf_content, submission.sample_name)

    sample = Sample(
        external_id=str(uuid4()),
        patient_pseudonym=submission.sample_name,
        user_id=user.id,
    )
    db.add(sample)
    await db.flush()

    engine = RuleEngine(DEFAULT_RULES)
    results: list[GermlineVariantResult] = []

    for record in records:
        alt0 = record.alt[0] if record.alt else record.ref
        len_diff = abs(len(record.ref) - len(alt0))
        is_frameshift = len_diff > 0 and len_diff % 3 != 0
        consequence = _derive_consequence(record)

        # TODO Phase 6: wire real evidence clients
        evidence = EvidenceBundle(
            gnomad_af=0.0001,
            gnomad_pli=0.95,
            gnomad_mis_z=3.5,
            clinvar_significances=[],
            cadd_phred=25.0,
            revel_score=0.75,
            is_frameshift=is_frameshift,
            is_splice=False,
            protein_length_change=False,
            consequence=consequence,
        )

        clf_result = engine.classify(record, evidence)
        acmg_points = _compute_acmg_points(clf_result)
        codes = [item.code.value for item in clf_result.evidence]
        summary = (
            f"Classified as {clf_result.tier.value} "
            f"(score={clf_result.pathogenic_score:.2f}) with "
            f"{len(codes)} evidence item(s): {', '.join(codes) or 'none'}"
        )

        variant_row = VariantModel(
            sample_id=sample.id,
            chrom=record.chrom,
            pos=record.pos,
            ref=record.ref,
            alt=",".join(record.alt),
            gene_symbol=record.info.get("GENE"),
            consequence=consequence.value,
            origin=record.origin.value,
        )
        db.add(variant_row)
        await db.flush()

        clf_row = Classification(
            variant_id=variant_row.id,
            tier=clf_result.tier.value,
            pathogenic_score=clf_result.pathogenic_score,
            evidence_codes={
                "type": "germline",
                "codes": codes,
                "acmg_points": acmg_points,
                "summary": summary,
            },
            classified_by="automated",
            is_automated=True,
        )
        db.add(clf_row)
        await db.flush()

        results.append(
            GermlineVariantResult(
                id=clf_row.id,
                chrom=record.chrom,
                pos=record.pos,
                ref=record.ref,
                alt=",".join(record.alt),
                gene=record.info.get("GENE"),
                consequence=consequence.value,
                classification_tier=clf_result.tier.value,
                acmg_points=acmg_points,
                evidence_codes=codes,
                summary=summary,
            )
        )

    return GermlineClassificationResponse(
        sample_id=sample.id,
        sample_name=submission.sample_name,
        variants_processed=len(results),
        results=results,
        classified_at=datetime.now(UTC),
    )


async def process_somatic_submission(
    submission: VCFSubmission,
    user: User,
    db: AsyncSession,
) -> SomaticClassificationResponse:
    """Parse VCF, classify each variant with mock somatic evidence, persist, and return results."""
    records = _parse_vcf_content(submission.vcf_content, submission.sample_name)

    sample = Sample(
        external_id=str(uuid4()),
        patient_pseudonym=submission.sample_name,
        user_id=user.id,
    )
    db.add(sample)
    await db.flush()

    classifier = SomaticClassifier()
    results: list[SomaticVariantResult] = []

    for record in records:
        is_hotspot = _check_is_hotspot(record.chrom, record.pos)
        consequence = _derive_consequence(record)

        # TODO Phase 6: wire real evidence clients
        evidence = SomaticEvidenceBundle(
            civic_evidence_levels=[],
            civic_has_approved_therapy=False,
            civic_has_investigational_therapy=False,
            civic_therapy_implications=[],
            oncokb_oncogenicity=None,
            oncokb_highest_sensitive_level=None,
            oncokb_highest_resistance_level=None,
            oncokb_therapy_implications=[],
            gnomad_af=0.0001,
            is_synonymous=False,
            is_hotspot=is_hotspot,
        )

        clf_result = classifier.classify(record, evidence)
        therapy_dicts: list[dict[str, Any]] = [
            json.loads(t.model_dump_json()) for t in clf_result.therapy_implications
        ]

        variant_row = VariantModel(
            sample_id=sample.id,
            chrom=record.chrom,
            pos=record.pos,
            ref=record.ref,
            alt=",".join(record.alt),
            gene_symbol=record.info.get("GENE"),
            consequence=consequence.value,
            origin=record.origin.value,
        )
        db.add(variant_row)
        await db.flush()

        clf_row = Classification(
            variant_id=variant_row.id,
            tier=clf_result.amp_tier.value,
            pathogenic_score=0.5,
            evidence_codes={
                "type": "somatic",
                "amp_tier": clf_result.amp_tier.value,
                "confidence": clf_result.confidence,
                "therapy_implications": therapy_dicts,
                "oncokb_oncogenicity": clf_result.oncokb_oncogenicity,
                "summary": clf_result.summary,
            },
            classified_by="automated",
            is_automated=True,
        )
        db.add(clf_row)
        await db.flush()

        results.append(
            SomaticVariantResult(
                id=clf_row.id,
                chrom=record.chrom,
                pos=record.pos,
                ref=record.ref,
                alt=",".join(record.alt),
                gene=record.info.get("GENE"),
                consequence=consequence.value,
                amp_tier=clf_result.amp_tier.value,
                confidence=clf_result.confidence,
                therapy_implications=therapy_dicts,
                oncokb_oncogenicity=clf_result.oncokb_oncogenicity,
                summary=clf_result.summary,
            )
        )

    return SomaticClassificationResponse(
        sample_id=sample.id,
        sample_name=submission.sample_name,
        variants_processed=len(results),
        results=results,
        classified_at=datetime.now(UTC),
    )


async def get_variant_result(
    variant_id: int,
    user: User,
    db: AsyncSession,
) -> GermlineVariantResult | SomaticVariantResult:
    """Fetch a single classification, ensuring it belongs to the current user."""
    stmt = (
        select(Classification)
        .options(joinedload(Classification.variant).joinedload(VariantModel.sample))
        .join(VariantModel, Classification.variant_id == VariantModel.id)
        .join(Sample, VariantModel.sample_id == Sample.id)
        .where(Classification.id == variant_id)
        .where(Sample.user_id == user.id)
    )
    result = await db.execute(stmt)
    clf = result.scalar_one_or_none()
    if clf is None:
        raise HTTPException(status_code=404, detail="Classification not found")
    variant = clf.variant
    data = _evidence_data(clf)
    if data.get("type") == "somatic":
        return _build_somatic_result(clf, variant)
    return _build_germline_result(clf, variant)


async def list_variant_results(
    user: User,
    db: AsyncSession,
) -> list[GermlineVariantResult | SomaticVariantResult]:
    """Return all classifications for the current user, newest first, limit 100."""
    stmt = (
        select(Classification)
        .options(joinedload(Classification.variant).joinedload(VariantModel.sample))
        .join(VariantModel, Classification.variant_id == VariantModel.id)
        .join(Sample, VariantModel.sample_id == Sample.id)
        .where(Sample.user_id == user.id)
        .order_by(Classification.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    clfs = result.scalars().all()
    out: list[GermlineVariantResult | SomaticVariantResult] = []
    for clf in clfs:
        variant = clf.variant
        data = _evidence_data(clf)
        if data.get("type") == "somatic":
            out.append(_build_somatic_result(clf, variant))
        else:
            out.append(_build_germline_result(clf, variant))
    return out
