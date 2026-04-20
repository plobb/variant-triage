"""Tests for SomaticClassifier using mock SomaticEvidenceBundles — no network calls."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.classification.somatic.base import (
    AMPTier,
    SomaticClassificationResult,
    SomaticClassifier,
    SomaticEvidenceBundle,
)
from app.domain.variant import VCFRecord
from tests.fixtures.mock_somatic_evidence import (
    tier1_bundle,
    tier2_civic_bundle,
    tier2_hotspot_bundle,
    tier3_bundle,
    tier4_af_bundle,
    tier4_synonymous_bundle,
)

clf = SomaticClassifier()


def _vcf(
    chrom: str = "chr7",
    pos: int = 140453136,
    ref: str = "A",
    alt: str = "T",
) -> VCFRecord:
    return VCFRecord(chrom=chrom, pos=pos, ref=ref, alt=[alt])


# ---------------------------------------------------------------------------
# Tier assignment
# ---------------------------------------------------------------------------


def test_tier1_from_approved_therapy_and_civic_a() -> None:
    result = clf.classify(_vcf(), tier1_bundle())
    assert result.amp_tier == AMPTier.TIER_I


def test_tier1_from_oncokb_level1() -> None:
    bundle = SomaticEvidenceBundle(
        oncokb_highest_sensitive_level="LEVEL_1",
        gnomad_af=0.0001,
    )
    assert clf.classify(_vcf(), bundle).amp_tier == AMPTier.TIER_I


def test_tier1_from_oncokb_level2() -> None:
    bundle = SomaticEvidenceBundle(
        oncokb_highest_sensitive_level="LEVEL_2",
        gnomad_af=0.0001,
    )
    assert clf.classify(_vcf(), bundle).amp_tier == AMPTier.TIER_I


def test_tier2_from_civic_c_level() -> None:
    # level C + no approved therapy → Tier II, not Tier I
    bundle = SomaticEvidenceBundle(
        civic_evidence_levels=["C"],
        civic_has_approved_therapy=False,
        gnomad_af=0.0001,
    )
    assert clf.classify(_vcf(), bundle).amp_tier == AMPTier.TIER_II


def test_tier2_civic_bundle() -> None:
    assert clf.classify(_vcf(), tier2_civic_bundle()).amp_tier == AMPTier.TIER_II


def test_tier2_from_hotspot() -> None:
    assert clf.classify(_vcf(), tier2_hotspot_bundle()).amp_tier == AMPTier.TIER_II


def test_tier2_from_oncokb_level3a() -> None:
    bundle = SomaticEvidenceBundle(
        oncokb_highest_sensitive_level="LEVEL_3A",
        gnomad_af=0.0001,
    )
    assert clf.classify(_vcf(), bundle).amp_tier == AMPTier.TIER_II


def test_tier2_from_oncokb_level3b() -> None:
    bundle = SomaticEvidenceBundle(
        oncokb_highest_sensitive_level="LEVEL_3B",
        gnomad_af=0.0001,
    )
    assert clf.classify(_vcf(), bundle).amp_tier == AMPTier.TIER_II


def test_tier3_default() -> None:
    assert clf.classify(_vcf(), tier3_bundle()).amp_tier == AMPTier.TIER_III


def test_tier4_common_af() -> None:
    assert clf.classify(_vcf(), tier4_af_bundle()).amp_tier == AMPTier.TIER_IV


def test_tier4_synonymous() -> None:
    assert clf.classify(_vcf(), tier4_synonymous_bundle()).amp_tier == AMPTier.TIER_IV


def test_tier4_overrides_hotspot() -> None:
    bundle = SomaticEvidenceBundle(
        is_hotspot=True,
        gnomad_af=0.05,
        civic_evidence_levels=["A"],
        civic_has_approved_therapy=True,
    )
    result = clf.classify(_vcf(), bundle)
    assert result.amp_tier == AMPTier.TIER_IV


def test_tier4_overrides_oncokb_level1() -> None:
    bundle = SomaticEvidenceBundle(
        oncokb_highest_sensitive_level="LEVEL_1",
        gnomad_af=0.02,
    )
    assert clf.classify(_vcf(), bundle).amp_tier == AMPTier.TIER_IV


# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------


def test_confidence_high_tier1() -> None:
    assert clf.classify(_vcf(), tier1_bundle()).confidence == "high"


def test_confidence_high_tier2_ab_evidence() -> None:
    bundle = SomaticEvidenceBundle(
        civic_evidence_levels=["B"],
        civic_has_approved_therapy=False,
        gnomad_af=0.0001,
    )
    result = clf.classify(_vcf(), bundle)
    assert result.amp_tier == AMPTier.TIER_II
    assert result.confidence == "high"


def test_confidence_medium_tier2_c() -> None:
    result = clf.classify(_vcf(), tier2_civic_bundle())
    assert result.amp_tier == AMPTier.TIER_II
    assert result.confidence == "medium"


def test_confidence_medium_tier2_hotspot_only() -> None:
    result = clf.classify(_vcf(), tier2_hotspot_bundle())
    assert result.amp_tier == AMPTier.TIER_II
    assert result.confidence == "medium"


def test_confidence_low_tier3_no_evidence() -> None:
    assert clf.classify(_vcf(), tier3_bundle()).confidence == "low"


def test_confidence_medium_tier3_with_civic() -> None:
    bundle = SomaticEvidenceBundle(
        civic_evidence_levels=["D"],
        is_hotspot=False,
        gnomad_af=0.001,
    )
    result = clf.classify(_vcf(), bundle)
    assert result.amp_tier == AMPTier.TIER_III
    assert result.confidence == "medium"


def test_confidence_low_tier4() -> None:
    assert clf.classify(_vcf(), tier4_af_bundle()).confidence == "low"


# ---------------------------------------------------------------------------
# Summary strings
# ---------------------------------------------------------------------------


def test_summary_nonempty_all_tiers() -> None:
    for bundle in (
        tier1_bundle(),
        tier2_civic_bundle(),
        tier2_hotspot_bundle(),
        tier3_bundle(),
        tier4_af_bundle(),
        tier4_synonymous_bundle(),
    ):
        result = clf.classify(_vcf(), bundle)
        assert result.summary


def test_summary_contains_tier_label() -> None:
    assert "Tier I" in clf.classify(_vcf(), tier1_bundle()).summary
    assert "Tier II" in clf.classify(_vcf(), tier2_hotspot_bundle()).summary
    assert "Tier III" in clf.classify(_vcf(), tier3_bundle()).summary
    assert "Tier IV" in clf.classify(_vcf(), tier4_af_bundle()).summary


def test_summary_tier1_mentions_drug() -> None:
    summary = clf.classify(_vcf(), tier1_bundle()).summary
    assert "vemurafenib" in summary


def test_summary_tier4_synonymous_mentions_synonymous() -> None:
    summary = clf.classify(_vcf(), tier4_synonymous_bundle()).summary
    assert "synonymous" in summary.lower()


# ---------------------------------------------------------------------------
# Therapy implications
# ---------------------------------------------------------------------------


def test_therapy_implications_populated_tier1() -> None:
    result = clf.classify(_vcf(), tier1_bundle())
    assert len(result.therapy_implications) >= 1
    assert result.therapy_implications[0].drug == "vemurafenib"
    assert result.therapy_implications[0].source == "CIViC"


def test_therapy_implications_populated_tier2() -> None:
    result = clf.classify(_vcf(), tier2_civic_bundle())
    assert len(result.therapy_implications) >= 1
    assert result.therapy_implications[0].evidence_level == "C"


def test_therapy_implications_empty_tier3() -> None:
    result = clf.classify(_vcf(), tier3_bundle())
    assert result.therapy_implications == []


def test_therapy_implication_fields_complete() -> None:
    result = clf.classify(_vcf(), tier1_bundle())
    impl = result.therapy_implications[0]
    assert impl.drug
    assert impl.disease
    assert impl.evidence_level
    assert impl.source


# ---------------------------------------------------------------------------
# OncoKB / CIViC propagation
# ---------------------------------------------------------------------------


def test_oncokb_oncogenicity_propagated() -> None:
    result = clf.classify(_vcf(), tier1_bundle())
    assert result.oncokb_oncogenicity == "Oncogenic"


def test_civic_evidence_levels_propagated() -> None:
    result = clf.classify(_vcf(), tier1_bundle())
    assert "A" in result.civic_evidence_levels


def test_oncokb_none_when_no_oncokb_data() -> None:
    result = clf.classify(_vcf(), tier3_bundle())
    assert result.oncokb_oncogenicity is None


# ---------------------------------------------------------------------------
# Result metadata
# ---------------------------------------------------------------------------


def test_variant_id_format() -> None:
    vcf = _vcf(chrom="chr7", pos=140453136, ref="A", alt="T")
    result = clf.classify(vcf, tier1_bundle())
    assert result.variant_id == "chr7:140453136:A>T"


def test_classified_at_is_recent() -> None:
    result = clf.classify(_vcf(), tier3_bundle())
    now = datetime.now(UTC)
    assert result.classified_at <= now
    assert result.classified_at >= now - timedelta(seconds=5)


def test_result_is_pydantic_model() -> None:
    result = clf.classify(_vcf(), tier1_bundle())
    assert isinstance(result, SomaticClassificationResult)


# ---------------------------------------------------------------------------
# Edge cases / robustness
# ---------------------------------------------------------------------------


def test_empty_bundle_gives_tier3() -> None:
    bundle = SomaticEvidenceBundle()
    result = clf.classify(_vcf(), bundle)
    assert result.amp_tier == AMPTier.TIER_III


def test_all_bundles_no_exception() -> None:
    for bundle in (
        tier1_bundle(),
        tier2_civic_bundle(),
        tier2_hotspot_bundle(),
        tier3_bundle(),
        tier4_af_bundle(),
        tier4_synonymous_bundle(),
        SomaticEvidenceBundle(),
    ):
        clf.classify(_vcf(), bundle)  # must not raise


def test_none_gnomad_af_not_tier4() -> None:
    bundle = SomaticEvidenceBundle(gnomad_af=None, is_synonymous=False)
    result = clf.classify(_vcf(), bundle)
    assert result.amp_tier != AMPTier.TIER_IV


def test_af_exactly_threshold_not_tier4() -> None:
    # AF == 0.01 is not > 0.01, so should NOT be Tier IV
    bundle = SomaticEvidenceBundle(gnomad_af=0.01, is_synonymous=False)
    result = clf.classify(_vcf(), bundle)
    assert result.amp_tier != AMPTier.TIER_IV


def test_oncokb_disabled_classifier_still_works() -> None:
    # Simulate disabled OncoKB: bundle with all oncokb fields None
    bundle = SomaticEvidenceBundle(
        oncokb_oncogenicity=None,
        oncokb_highest_sensitive_level=None,
        is_hotspot=True,
        gnomad_af=0.0001,
    )
    result = clf.classify(_vcf(), bundle)
    assert result.amp_tier == AMPTier.TIER_II
