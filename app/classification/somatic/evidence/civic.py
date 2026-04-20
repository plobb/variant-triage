from __future__ import annotations

import logging
from typing import Any

import httpx

from app.classification.somatic.base import TherapyImplication

logger = logging.getLogger(__name__)

_BASE = "https://civicdb.org/api"
_TIMEOUT = 10.0

APPROVED_THERAPIES: set[str] = {
    "vemurafenib",
    "dabrafenib",
    "trametinib",
    "erlotinib",
    "gefitinib",
    "osimertinib",
    "imatinib",
    "crizotinib",
    "pembrolizumab",
    "nivolumab",
    "olaparib",
    "trastuzumab",
    "cetuximab",
    "bevacizumab",
    "sorafenib",
    "sunitinib",
    "ibrutinib",
    "venetoclax",
    "palbociclib",
    "ribociclib",
}

_EMPTY: dict[str, Any] = {
    "evidence_levels": [],
    "has_approved_therapy": False,
    "has_investigational_therapy": False,
    "therapy_implications": [],
}


class CivicClient:
    def __init__(self) -> None:
        self._cache: dict[
            tuple[str, str, int, str, str], dict[str, Any]
        ] = {}

    async def lookup(
        self, chrom: str, pos: int, ref: str, alt: str, gene: str
    ) -> dict[str, Any]:
        key = (gene, chrom, pos, ref, alt)
        if key in self._cache:
            return self._cache[key]

        result = await self._fetch(chrom, pos, ref, alt, gene)
        self._cache[key] = result
        return result

    async def _fetch(
        self, chrom: str, pos: int, ref: str, alt: str, gene: str
    ) -> dict[str, Any]:
        if not gene:
            return dict(_EMPTY)

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                gene_resp = await client.get(
                    f"{_BASE}/genes/{gene}",
                    params={"include_status": "accepted"},
                )
                if gene_resp.status_code == 404:
                    return dict(_EMPTY)
                gene_resp.raise_for_status()
                gene_data = gene_resp.json()
        except Exception as exc:
            logger.warning("CIViC gene lookup failed for %s: %s", gene, exc)
            return dict(_EMPTY)

        variants: list[dict[str, Any]] = gene_data.get("variants") or []
        matching_ids = self._find_matching_variants(variants, chrom, pos, ref, alt)

        if not matching_ids:
            return dict(_EMPTY)

        return await self._fetch_evidence(matching_ids)

    @staticmethod
    def _find_matching_variants(
        variants: list[dict[str, Any]],
        chrom: str,
        pos: int,
        ref: str,
        alt: str,
    ) -> list[int]:
        chrom_clean = chrom.removeprefix("chr")
        matched: list[int] = []
        for v in variants:
            coords: dict[str, Any] = v.get("coordinates") or {}
            v_chrom = str(coords.get("chromosome") or "").removeprefix("chr")
            v_start = coords.get("start")
            v_ref = str(coords.get("reference_bases") or "").upper()
            v_alt = str(coords.get("variant_bases") or "").upper()
            if (
                v_chrom == chrom_clean
                and v_start is not None
                and int(v_start) == pos
                and v_ref == ref.upper()
                and v_alt == alt.upper()
            ):
                vid = v.get("id")
                if isinstance(vid, int):
                    matched.append(vid)
        return matched

    async def _fetch_evidence(self, variant_ids: list[int]) -> dict[str, Any]:
        evidence_levels: list[str] = []
        therapy_implications: list[TherapyImplication] = []
        has_approved = False
        has_investigational = False

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                for vid in variant_ids[:5]:
                    resp = await client.get(f"{_BASE}/variants/{vid}/evidence_items")
                    resp.raise_for_status()
                    raw = resp.json()
                    items: list[dict[str, Any]] = (
                        raw if isinstance(raw, list) else raw.get("records") or []
                    )
                    for item in items:
                        level: str = (
                            item.get("evidence_level")
                            or item.get("evidenceLevel")
                            or ""
                        )
                        if level and level not in evidence_levels:
                            evidence_levels.append(level)

                        is_predictive = item.get("evidence_type") in (
                            "Predictive",
                            "PREDICTIVE",
                        )
                        is_sensitive = item.get("clinical_significance") in (
                            "Sensitivity/Response",
                            "SENSITIVITY",
                        )
                        if not (is_predictive and is_sensitive):
                            continue

                        disease: str = (item.get("disease") or {}).get("name") or ""
                        drugs: list[Any] = (
                            item.get("drugs") or item.get("therapies") or []
                        )
                        for drug_obj in drugs:
                            drug_name = (
                                drug_obj.get("name", "")
                                if isinstance(drug_obj, dict)
                                else str(drug_obj)
                            ).lower()
                            if drug_name in APPROVED_THERAPIES:
                                has_approved = True
                            else:
                                has_investigational = True
                            therapy_implications.append(
                                TherapyImplication(
                                    drug=drug_name,
                                    disease=disease,
                                    evidence_level=level,
                                    source="CIViC",
                                )
                            )
        except Exception as exc:
            logger.warning("CIViC evidence fetch failed: %s", exc)

        return {
            "evidence_levels": evidence_levels,
            "has_approved_therapy": has_approved,
            "has_investigational_therapy": has_investigational,
            "therapy_implications": therapy_implications,
        }
