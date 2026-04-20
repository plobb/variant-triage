from __future__ import annotations

import logging
from typing import Any

import httpx

from app.classification.somatic.base import TherapyImplication

logger = logging.getLogger(__name__)

_BASE = "https://www.oncokb.org/api/v1"
_TIMEOUT = 10.0
_EMPTY: dict[str, Any] = {
    "oncogenicity": None,
    "highestSensitiveLevel": None,
    "highestResistanceLevel": None,
    "therapy_implications": [],
}


class OncoKbClient:
    def __init__(self, token: str | None = None) -> None:
        if token is None:
            from app.core.config import settings

            token = settings.ONCOKB_API_TOKEN
        if not token:
            logger.warning(
                "ONCOKB_API_TOKEN not configured — OncoKB lookups disabled"
            )
            self._enabled = False
            self._token = ""
        else:
            self._enabled = True
            self._token = token

        self._cache: dict[tuple[str, int, str, str], dict[str, Any]] = {}

    async def lookup(
        self, chrom: str, pos: int, ref: str, alt: str, gene: str
    ) -> dict[str, Any]:
        if not self._enabled:
            return dict(_EMPTY)

        key = (chrom, pos, ref, alt)
        if key in self._cache:
            return self._cache[key]

        result = await self._fetch(chrom, pos, ref, alt)
        self._cache[key] = result
        return result

    async def _fetch(
        self, chrom: str, pos: int, ref: str, alt: str
    ) -> dict[str, Any]:
        chrom_clean = chrom.removeprefix("chr")
        hgvsg = f"{chrom_clean}:g.{pos}{ref}>{alt}"

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE}/annotate/mutations/byHGVSg",
                    params={"hgvsg": hgvsg, "referenceGenome": "GRCh38"},
                    headers={"Authorization": f"Bearer {self._token}"},
                )
                if resp.status_code in (401, 403):
                    logger.warning("OncoKB token invalid or expired")
                    self._enabled = False
                    return dict(_EMPTY)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except Exception as exc:
            logger.warning("OncoKB lookup failed for %s: %s", hgvsg, exc)
            return dict(_EMPTY)

        therapy_implications = self._extract_treatments(data)

        return {
            "oncogenicity": data.get("oncogenic"),
            "highestSensitiveLevel": data.get("highestSensitiveLevel"),
            "highestResistanceLevel": data.get("highestResistanceLevel"),
            "therapy_implications": therapy_implications,
        }

    @staticmethod
    def _extract_treatments(data: dict[str, Any]) -> list[TherapyImplication]:
        implications: list[TherapyImplication] = []
        treatments: list[dict[str, Any]] = data.get("treatments") or []
        for t in treatments:
            level: str = t.get("level") or ""
            indication: str = t.get("indication") or t.get("levelAssociatedCancerType", {}).get(
                "mainType", {}).get("name", "") or ""
            drugs: list[Any] = t.get("drugs") or []
            for drug_obj in drugs:
                drug_name = (
                    drug_obj.get("drugName") or drug_obj.get("name") or ""
                    if isinstance(drug_obj, dict)
                    else str(drug_obj)
                ).lower()
                if drug_name:
                    implications.append(
                        TherapyImplication(
                            drug=drug_name,
                            disease=indication,
                            evidence_level=level,
                            source="OncoKB",
                        )
                    )
        return implications
