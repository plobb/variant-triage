"""Tests for domain Pydantic models and enums."""

import pytest
from pydantic import ValidationError

from app.domain.enums import (
    ClassificationTier,
    ConsequenceType,
    EvidenceCode,
    VariantOrigin,
    Zygosity,
)
from app.domain.variant import (
    ClassificationResult,
    EvidenceItem,
    Variant,
    VCFRecord,
)


class TestVCFRecord:
    def test_basic_construction(self) -> None:
        rec = VCFRecord(chrom="chr1", pos=12345, ref="A", alt=["T"])
        assert rec.chrom == "chr1"
        assert rec.is_snv is True
        assert rec.is_structural is False

    def test_ref_alt_uppercased(self) -> None:
        rec = VCFRecord(chrom="chr1", pos=1, ref="a", alt=["t"])
        assert rec.ref == "A"
        assert rec.alt == ["T"]

    def test_invalid_pos_raises(self) -> None:
        with pytest.raises(ValidationError):
            VCFRecord(chrom="chr1", pos=0, ref="A", alt=["T"])

    def test_indel_classification(self) -> None:
        rec = VCFRecord(chrom="chr1", pos=100, ref="AT", alt=["A"])
        assert rec.is_indel is True
        assert rec.is_snv is False

    def test_multi_alt(self) -> None:
        rec = VCFRecord(chrom="chr1", pos=100, ref="A", alt=["T", "G"])
        assert len(rec.alt) == 2

    def test_missing_optional_fields_default(self) -> None:
        rec = VCFRecord(chrom="chr2", pos=500, ref="C", alt=["G"])
        assert rec.qual is None
        assert rec.depth is None
        assert rec.allele_depths is None
        assert rec.filter == []
        assert rec.origin == VariantOrigin.UNKNOWN


class TestVariant:
    def _make_vcf_record(self, gt: str | None = "0/1") -> VCFRecord:
        return VCFRecord(
            chrom="chr17",
            pos=43044295,
            ref="G",
            alt=["A"],
            genotype=gt,
            depth=60,
        )

    def test_heterozygous_gt(self) -> None:
        v = Variant(vcf_record=self._make_vcf_record("0/1"))
        assert v.zygosity == Zygosity.HETEROZYGOUS

    def test_homozygous_alt_gt(self) -> None:
        v = Variant(vcf_record=self._make_vcf_record("1/1"))
        assert v.zygosity == Zygosity.HOMOZYGOUS_ALT

    def test_homozygous_ref_gt(self) -> None:
        v = Variant(vcf_record=self._make_vcf_record("0/0"))
        assert v.zygosity == Zygosity.HOMOZYGOUS_REF

    def test_phased_gt(self) -> None:
        v = Variant(vcf_record=self._make_vcf_record("0|1"))
        assert v.zygosity == Zygosity.HETEROZYGOUS

    def test_no_call_gt(self) -> None:
        v = Variant(vcf_record=self._make_vcf_record("./."))
        assert v.zygosity == Zygosity.UNKNOWN

    def test_missing_gt(self) -> None:
        v = Variant(vcf_record=self._make_vcf_record(None))
        assert v.zygosity == Zygosity.UNKNOWN

    def test_explicit_zygosity_not_overridden(self) -> None:
        rec = self._make_vcf_record("0/1")
        v = Variant(vcf_record=rec, zygosity=Zygosity.HEMIZYGOUS)
        # Model validator only fires when zygosity is still UNKNOWN
        assert v.zygosity == Zygosity.HEMIZYGOUS


class TestEnums:
    def test_variant_origin_values(self) -> None:
        assert VariantOrigin.GERMLINE == "GERMLINE"
        assert VariantOrigin.SOMATIC == "SOMATIC"

    def test_classification_tier_values(self) -> None:
        assert ClassificationTier.PATHOGENIC == "Pathogenic"
        assert ClassificationTier.VUS == "Variant_of_uncertain_significance"

    def test_evidence_code_pvs1(self) -> None:
        assert EvidenceCode.PVS1 == "PVS1"

    def test_consequence_type_str(self) -> None:
        assert ConsequenceType.MISSENSE == "missense_variant"


class TestClassificationResult:
    def _make_variant(self) -> Variant:
        rec = VCFRecord(chrom="chr17", pos=43044295, ref="G", alt=["A"], genotype="0/1")
        return Variant(
            vcf_record=rec,
            gene_symbol="BRCA1",
            consequence=ConsequenceType.NONSENSE,
        )

    def test_pathogenic_construction(self) -> None:
        v = self._make_variant()
        evidence = [
            EvidenceItem(code=EvidenceCode.PVS1, description="Null variant in BRCA1"),
            EvidenceItem(code=EvidenceCode.PM2, description="Absent from gnomAD"),
        ]
        result = ClassificationResult(
            variant=v,
            tier=ClassificationTier.PATHOGENIC,
            evidence=evidence,
            pathogenic_score=0.97,
        )
        assert result.tier == ClassificationTier.PATHOGENIC
        assert "PVS1" in result.pathogenic_codes
        assert "PM2" in result.pathogenic_codes
        assert result.benign_codes == []

    def test_score_clamped_to_range(self) -> None:
        v = self._make_variant()
        with pytest.raises(ValidationError):
            ClassificationResult(
                variant=v,
                tier=ClassificationTier.PATHOGENIC,
                pathogenic_score=1.5,
            )

    def test_score_precision(self) -> None:
        v = self._make_variant()
        result = ClassificationResult(
            variant=v,
            tier=ClassificationTier.VUS,
            pathogenic_score=0.499999,
        )
        assert result.pathogenic_score == 0.5

    def test_benign_evidence_codes(self) -> None:
        v = self._make_variant()
        evidence = [
            EvidenceItem(code=EvidenceCode.BA1, description="High MAF in gnomAD"),
            EvidenceItem(code=EvidenceCode.BS1, description="MAF too high for disease"),
        ]
        result = ClassificationResult(
            variant=v,
            tier=ClassificationTier.BENIGN,
            evidence=evidence,
            pathogenic_score=0.02,
        )
        assert "BA1" in result.benign_codes
        assert result.pathogenic_codes == []

    def test_is_automated_default(self) -> None:
        v = self._make_variant()
        result = ClassificationResult(
            variant=v,
            tier=ClassificationTier.VUS,
            pathogenic_score=0.5,
        )
        assert result.is_automated is True
