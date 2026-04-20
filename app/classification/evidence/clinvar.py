from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_TOOL = "variant-triage"
_EMAIL = "phil@lobb.co.uk"
_TIMEOUT = 15.0
_EMPTY: dict[str, list[str]] = {
    "significances": [],
    "same_residue_pathogenic": [],
}


class ClinVarClient:
    def __init__(self) -> None:
        self._cache: dict[
            tuple[str, int, str, str], dict[str, list[str]]
        ] = {}

    async def lookup(
        self, chrom: str, pos: int, ref: str, alt: str
    ) -> dict[str, list[str]]:
        key = (chrom, pos, ref, alt)
        if key in self._cache:
            return self._cache[key]

        result = await self._fetch(chrom, pos, ref, alt)
        self._cache[key] = result
        return result

    async def _fetch(
        self, chrom: str, pos: int, ref: str, alt: str
    ) -> dict[str, list[str]]:
        chrom_clean = chrom.removeprefix("chr")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                search_resp = await client.get(
                    f"{_BASE}/esearch.fcgi",
                    params={
                        "db": "clinvar",
                        "term": (
                            f"{chrom_clean}[Chromosome]"
                            f" AND {pos}[Base Position for Assembly Version 38]"
                        ),
                        "retmax": 20,
                        "retmode": "json",
                        "tool": _TOOL,
                        "email": _EMAIL,
                    },
                )
                search_resp.raise_for_status()
                search_data = search_resp.json()

            ids: list[str] = (
                (search_data.get("esearchresult") or {}).get("idlist") or []
            )
            if not ids:
                return dict(_EMPTY)

            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                fetch_resp = await client.get(
                    f"{_BASE}/efetch.fcgi",
                    params={
                        "db": "clinvar",
                        "id": ",".join(ids[:10]),
                        "rettype": "clinvarset",
                        "retmode": "xml",
                        "tool": _TOOL,
                        "email": _EMAIL,
                    },
                )
                fetch_resp.raise_for_status()
                xml_text = fetch_resp.text

        except Exception:
            return dict(_EMPTY)

        return self._parse_xml(chrom_clean, pos, ref, alt, xml_text)

    def _parse_xml(
        self,
        chrom: str,
        pos: int,
        ref: str,
        alt: str,
        xml_text: str,
    ) -> dict[str, list[str]]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return dict(_EMPTY)

        significances: list[str] = []
        same_residue_pathogenic: list[str] = []

        for cv_set in root.iter("ClinVarSet"):
            ref_assertion = cv_set.find("ReferenceClinVarAssertion")
            if ref_assertion is None:
                continue

            # Extract variant position to identify exact vs same-residue match
            is_exact = self._is_exact_match(ref_assertion, chrom, pos, ref, alt)

            sig_el = ref_assertion.find(
                "ClinicalSignificance/Description"
            )
            if sig_el is None or not sig_el.text:
                continue
            sig_text = sig_el.text.strip()

            if is_exact:
                significances.append(sig_text)
            elif "pathogenic" in sig_text.lower():
                # Different variant at nearby position — candidate for PM5
                acc_el = ref_assertion.find("ClinVarAccession")
                acc = (acc_el.get("Acc") if acc_el is not None else None) or sig_text
                same_residue_pathogenic.append(acc)

        return {
            "significances": significances,
            "same_residue_pathogenic": same_residue_pathogenic,
        }

    def _is_exact_match(
        self,
        ref_assertion: ET.Element,
        chrom: str,
        pos: int,
        ref: str,
        alt: str,
    ) -> bool:
        measure_set = ref_assertion.find(
            ".//MeasureSet/Measure"
        )
        if measure_set is None:
            return False

        for seq_loc in measure_set.iter("SequenceLocation"):
            assembly = seq_loc.get("Assembly", "")
            if assembly not in ("GRCh38", "hg38"):
                continue
            loc_chrom = (seq_loc.get("Chr") or "").lstrip("chr")
            start = seq_loc.get("start") or seq_loc.get("positionVCF")
            ref_allele: str = seq_loc.get("referenceAlleleVCF") or seq_loc.get("referenceAllele") or ""
            alt_allele: str = seq_loc.get("alternateAlleleVCF") or seq_loc.get("alternateAllele") or ""
            if (
                loc_chrom == chrom
                and start is not None
                and int(start) == pos
                and ref_allele.upper() == ref.upper()
                and alt_allele.upper() == alt.upper()
            ):
                return True
        return False
