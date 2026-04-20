from __future__ import annotations

import httpx

_EMPTY: dict[str, float | None] = {"af": None, "pli": None, "mis_z": None}

_VARIANT_QUERY = """
query VariantData($variantId: String!, $dataset: DatasetId!) {
  variant(variantId: $variantId, dataset: $dataset) {
    exome { af }
    genome { af }
    transcript_consequences {
      gene_id
      is_canonical
    }
  }
}
"""

_GENE_QUERY = """
query GeneConstraint($geneId: String!, $referenceGenome: ReferenceGenomeId!) {
  gene(gene_id: $geneId, reference_genome: $referenceGenome) {
    gnomad_constraint {
      pli
      mis_z
    }
  }
}
"""


class GnomadClient:
    _URL = "https://gnomad.broadinstitute.org/api"
    _TIMEOUT = 10.0

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int, str, str], dict[str, float | None]] = {}

    async def lookup(
        self, chrom: str, pos: int, ref: str, alt: str
    ) -> dict[str, float | None]:
        key = (chrom, pos, ref, alt)
        if key in self._cache:
            return self._cache[key]

        result = await self._fetch(chrom, pos, ref, alt)
        self._cache[key] = result
        return result

    async def _fetch(
        self, chrom: str, pos: int, ref: str, alt: str
    ) -> dict[str, float | None]:
        chrom_clean = chrom.removeprefix("chr")
        variant_id = f"{chrom_clean}-{pos}-{ref}-{alt}"

        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                v_resp = await client.post(
                    self._URL,
                    json={
                        "query": _VARIANT_QUERY,
                        "variables": {
                            "variantId": variant_id,
                            "dataset": "gnomad_r4",
                        },
                    },
                )
                v_resp.raise_for_status()
                v_data = v_resp.json()

            variant = (v_data.get("data") or {}).get("variant")
            if not variant:
                return dict(_EMPTY)

            exome_af: float | None = (variant.get("exome") or {}).get("af")
            genome_af: float | None = (variant.get("genome") or {}).get("af")
            af: float | None = None
            if exome_af is not None and genome_af is not None:
                af = min(exome_af, genome_af)
            elif exome_af is not None:
                af = exome_af
            elif genome_af is not None:
                af = genome_af

            gene_id: str | None = None
            for tc in variant.get("transcript_consequences") or []:
                if tc.get("is_canonical"):
                    gene_id = tc.get("gene_id")
                    break
            if gene_id is None:
                consequences = variant.get("transcript_consequences") or []
                if consequences:
                    gene_id = consequences[0].get("gene_id")

            pli: float | None = None
            mis_z: float | None = None

            if gene_id:
                async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                    g_resp = await client.post(
                        self._URL,
                        json={
                            "query": _GENE_QUERY,
                            "variables": {
                                "geneId": gene_id,
                                "referenceGenome": "GRCh38",
                            },
                        },
                    )
                    g_resp.raise_for_status()
                    g_data = g_resp.json()

                constraint = (
                    ((g_data.get("data") or {}).get("gene") or {}).get(
                        "gnomad_constraint"
                    )
                    or {}
                )
                pli = constraint.get("pli")
                mis_z = constraint.get("mis_z")

        except Exception:
            return dict(_EMPTY)

        return {"af": af, "pli": pli, "mis_z": mis_z}
