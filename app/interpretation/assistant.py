from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from app.interpretation.guardrails import DISCLAIMER, GuardrailChecker
from app.interpretation.prompts import GERMLINE_TEMPLATE, SOMATIC_TEMPLATE, SYSTEM_PROMPT
from app.interpretation.schemas import (
    InterpretationError,
    InterpretationRequest,
    InterpretationResponse,
)


class VariantInterpretationAssistant:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key: str = (
            api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self._guardrails = GuardrailChecker()
        self.model = "claude-3-5-haiku-20241022"
        self.max_tokens = 512

    def _build_user_message(self, request: InterpretationRequest) -> str:
        gene = request.gene or "unknown"
        notes = request.notes or "None"
        if request.origin.upper() == "GERMLINE":
            return GERMLINE_TEMPLATE.format(
                chrom=request.chrom,
                pos=request.pos,
                ref=request.ref,
                alt=request.alt,
                gene=gene,
                classification_tier=request.classification_tier,
                acmg_points=request.acmg_points,
                evidence_codes=", ".join(request.evidence_codes) or "none",
                notes=notes,
            )
        return SOMATIC_TEMPLATE.format(
            chrom=request.chrom,
            pos=request.pos,
            ref=request.ref,
            alt=request.alt,
            gene=gene,
            amp_tier=request.amp_tier or "Unknown",
            oncokb_oncogenicity=request.oncokb_oncogenicity or "Unknown",
            therapy_implications=", ".join(request.therapy_implications) or "None",
            notes=notes,
        )

    def _determine_confidence(self, tier: str, flags: list[str]) -> str:
        if flags:
            return "low"
        if tier in {"Pathogenic", "Tier_I", "Tier_II"}:
            return "high"
        if tier in {"VUS", "Tier_III", "Likely_Pathogenic"}:
            return "medium"
        return "low"

    async def interpret(
        self,
        request: InterpretationRequest,
    ) -> InterpretationResponse | InterpretationError:
        try:
            user_message = self._build_user_message(request)
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": self.max_tokens,
                        "system": SYSTEM_PROMPT,
                        "messages": [{"role": "user", "content": user_message}],
                    },
                )
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()

            text: str = data["content"][0]["text"]
            flags = self._guardrails.check(text)
            sanitized = self._guardrails.sanitize(text)
            confidence = self._determine_confidence(request.classification_tier, flags)

            return InterpretationResponse(
                variant_id=request.variant_id,
                interpretation=sanitized,
                confidence=confidence,
                guardrail_flags=flags,
                disclaimer=DISCLAIMER,
                model_used=self.model,
                generated_at=datetime.now(UTC),
            )
        except Exception as exc:
            return InterpretationError(
                variant_id=request.variant_id,
                error=str(exc),
                generated_at=datetime.now(UTC),
            )

    async def interpret_batch(
        self,
        requests: list[InterpretationRequest],
    ) -> list[InterpretationResponse | InterpretationError]:
        semaphore = asyncio.Semaphore(3)

        async def _sem(
            req: InterpretationRequest,
        ) -> InterpretationResponse | InterpretationError:
            async with semaphore:
                return await self.interpret(req)

        results: list[InterpretationResponse | InterpretationError] = list(
            await asyncio.gather(*[_sem(r) for r in requests])
        )
        return results
