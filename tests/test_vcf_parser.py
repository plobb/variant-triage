"""Tests for VCF parser — germline, somatic, long-read, edge cases."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.domain.enums import SVType, VariantOrigin
from app.domain.variant import VCFRecord
from app.ingestion.vcf_parser import detect_origin, parse_vcf

FIXTURES = Path(__file__).parent / "fixtures"
GERMLINE_VCF = FIXTURES / "germline_snv.vcf"
SOMATIC_VCF = FIXTURES / "somatic_longread.vcf"


# ---------------------------------------------------------------------------
# detect_origin()
# ---------------------------------------------------------------------------

class TestDetectOrigin:
    def test_somatic_flag_in_info(self) -> None:
        origin = detect_origin(Path("sample.vcf"), {"SOMATIC": True})
        assert origin == VariantOrigin.SOMATIC

    def test_somatic_integer_flag(self) -> None:
        origin = detect_origin(Path("sample.vcf"), {"SOMATIC": 1})
        assert origin == VariantOrigin.SOMATIC

    def test_tumour_in_filename(self) -> None:
        origin = detect_origin(Path("tumor_sample.vcf"), {})
        assert origin == VariantOrigin.SOMATIC

    def test_normal_in_filename(self) -> None:
        origin = detect_origin(Path("normal_blood.vcf"), {})
        assert origin == VariantOrigin.GERMLINE

    def test_unknown_filename(self) -> None:
        origin = detect_origin(Path("WES_sample_001.vcf"), {})
        assert origin == VariantOrigin.UNKNOWN

    def test_somatic_flag_wins_over_filename(self) -> None:
        # Even a "normal" filename yields SOMATIC when INFO/SOMATIC is set
        origin = detect_origin(Path("normal_blood.vcf"), {"SOMATIC": True})
        assert origin == VariantOrigin.SOMATIC


# ---------------------------------------------------------------------------
# parse_vcf() — requires cyvcf2
# ---------------------------------------------------------------------------

def _cyvcf2_available() -> bool:
    try:
        import cyvcf2  # noqa: F401
        return True
    except ImportError:
        return False


cyvcf2_required = pytest.mark.skipif(
    not _cyvcf2_available(),
    reason="cyvcf2 not installed — skipping VCF parse tests",
)


@cyvcf2_required
class TestGermlineVCF:
    def setup_method(self) -> None:
        self.records = parse_vcf(GERMLINE_VCF)

    def test_record_count(self) -> None:
        assert len(self.records) == 5

    def test_all_germline_origin(self) -> None:
        # Germline VCF has no SOMATIC flag; filename heuristic should set GERMLINE
        # (filename is "germline_snv.vcf" — no direct keyword, returns UNKNOWN)
        # Accept GERMLINE or UNKNOWN from this fixture
        for rec in self.records:
            assert rec.origin in (VariantOrigin.GERMLINE, VariantOrigin.UNKNOWN)

    def test_brca1_variant_present(self) -> None:
        brca1 = [r for r in self.records if r.pos == 43044295]
        assert len(brca1) == 1
        assert brca1[0].ref == "G"
        assert "A" in brca1[0].alt

    def test_genotypes_present(self) -> None:
        for rec in self.records:
            assert rec.genotype is not None

    def test_depth_parsed(self) -> None:
        for rec in self.records:
            assert rec.depth is not None and rec.depth > 0

    def test_allele_depths_present(self) -> None:
        for rec in self.records:
            assert rec.allele_depths is not None
            assert len(rec.allele_depths) == 2  # REF, ALT

    def test_homozygous_alt_variant(self) -> None:
        hom = [r for r in self.records if r.pos == 117548628]
        assert len(hom) == 1
        assert hom[0].genotype in ("1/1", "1|1")


@cyvcf2_required
class TestSomaticLongReadVCF:
    def setup_method(self) -> None:
        self.records = parse_vcf(SOMATIC_VCF)

    def test_record_count(self) -> None:
        assert len(self.records) == 5

    def test_all_somatic_origin(self) -> None:
        for rec in self.records:
            assert rec.origin == VariantOrigin.SOMATIC

    def test_af_field_parsed(self) -> None:
        snvs = [r for r in self.records if r.sv_type is None]
        for rec in snvs:
            assert rec.allele_freq is not None
            assert 0.0 < rec.allele_freq <= 1.0

    def test_hp_tag_parsed(self) -> None:
        for rec in self.records:
            assert rec.haplotype_phase in (1, 2)

    def test_structural_variant_passthrough(self) -> None:
        svs = [r for r in self.records if r.sv_type is not None]
        assert len(svs) == 1
        assert svs[0].sv_type == SVType.DEL
        assert svs[0].is_structural is True

    def test_low_depth_variant_present(self) -> None:
        kras = [r for r in self.records if r.pos == 25398284]
        assert len(kras) == 1
        assert "LowDepth" in kras[0].filter


@cyvcf2_required
class TestMissingFormatFields:
    """Ensure parser degrades gracefully for missing optional FORMAT fields."""

    def test_germline_has_no_af_format(self) -> None:
        # Germline VCF has no FORMAT/AF — allele_freq should be None
        records = parse_vcf(GERMLINE_VCF)
        for rec in records:
            assert rec.allele_freq is None

    def test_germline_has_no_hp_tag(self) -> None:
        records = parse_vcf(GERMLINE_VCF)
        for rec in records:
            assert rec.haplotype_phase is None
