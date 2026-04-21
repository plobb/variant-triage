from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, get_db
from app.api.variants.schemas import (
    AnyVariantResult,
    BatchInterpretationBody,
    GermlineClassificationResponse,
    SomaticClassificationResponse,
    VCFSubmission,
)
from app.api.variants.service import (
    get_variant_result,
    list_variant_results,
    process_germline_submission,
    process_somatic_submission,
)
from app.core.config import settings
from app.db.models import Classification, Sample, User, VariantModel
from app.interpretation.assistant import VariantInterpretationAssistant
from app.interpretation.schemas import (
    InterpretationError,
    InterpretationRequest,
    InterpretationResponse,
)

router = APIRouter()


@router.post(
    "/germline",
    response_model=GermlineClassificationResponse,
    description="Submit a VCF for germline ACMG/AMP classification.",
)
async def submit_germline(
    submission: VCFSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GermlineClassificationResponse:
    return await process_germline_submission(submission, current_user, db)


@router.post(
    "/somatic",
    response_model=SomaticClassificationResponse,
    description="Submit a VCF for somatic AMP-tier classification.",
)
async def submit_somatic(
    submission: VCFSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SomaticClassificationResponse:
    return await process_somatic_submission(submission, current_user, db)


@router.get(
    "/",
    response_model=list[AnyVariantResult],
    description="List all classifications for the authenticated user (newest first, max 100).",
)
async def list_variants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnyVariantResult]:
    return await list_variant_results(current_user, db)

@router.get(
    "/{variant_id}",
    response_model=AnyVariantResult,
    description="Fetch a single classification by ID. Returns 404 if not owned by caller.",
)
async def get_variant(
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnyVariantResult:
    return await get_variant_result(variant_id, current_user, db)


def _build_interpretation_request(
    clf: Classification, variant: VariantModel
) -> InterpretationRequest:
    raw: Any = clf.evidence_codes
    data: dict[str, Any] = raw if isinstance(raw, dict) else {}

    therapy_impls: list[str] = []
    for t in data.get("therapy_implications") or []:
        if isinstance(t, dict):
            drug = t.get("drug") or t.get("therapy_name") or ""
            if drug:
                therapy_impls.append(str(drug))
        elif isinstance(t, str):
            therapy_impls.append(t)

    return InterpretationRequest(
        variant_id=str(clf.id),
        chrom=variant.chrom,
        pos=variant.pos,
        ref=variant.ref,
        alt=variant.alt,
        gene=variant.gene_symbol,
        classification_tier=clf.tier,
        evidence_codes=data.get("codes") or [],
        amp_tier=data.get("amp_tier"),
        therapy_implications=therapy_impls,
        oncokb_oncogenicity=data.get("oncokb_oncogenicity"),
        acmg_points=data.get("acmg_points"),
        origin=variant.origin,
        notes=clf.reviewer_notes,
    )


async def _fetch_clf_for_user(
    variant_id: int, user: User, db: AsyncSession
) -> tuple[Classification, VariantModel]:
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
    return clf, clf.variant


@router.post(
    "/interpret/batch",
    response_model=list[InterpretationResponse | InterpretationError],
    description="Draft LLM interpretations for up to 10 classifications at once.",
)
async def interpret_batch(
    body: BatchInterpretationBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InterpretationResponse | InterpretationError]:
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="Interpretation service not configured")
    assistant = VariantInterpretationAssistant(api_key=settings.ANTHROPIC_API_KEY)
    interp_requests: list[InterpretationRequest] = []
    for vid in body.variant_ids:
        clf, variant = await _fetch_clf_for_user(vid, current_user, db)
        interp_requests.append(_build_interpretation_request(clf, variant))
    return await assistant.interpret_batch(interp_requests)


@router.post(
    "/{variant_id}/interpret",
    response_model=InterpretationResponse,
    description="Draft an LLM interpretation for a single classification.",
)
async def interpret_variant(
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterpretationResponse:
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="Interpretation service not configured")
    clf, variant = await _fetch_clf_for_user(variant_id, current_user, db)
    request = _build_interpretation_request(clf, variant)
    assistant = VariantInterpretationAssistant(api_key=settings.ANTHROPIC_API_KEY)
    result = await assistant.interpret(request)
    if isinstance(result, InterpretationError):
        raise HTTPException(status_code=500, detail=result.error)
    return result