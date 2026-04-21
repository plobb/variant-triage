from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.variants.schemas import (
    AnyVariantResult,
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
from app.db.models import User

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