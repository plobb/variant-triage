"""Integration tests for RuleEngine using DEFAULT_RULES and mock EvidenceBundles."""
from __future__ import annotations

import pytest

from app.classification.base import EvidenceBundle, RuleEngine
from app.classification.rules import DEFAULT_RULES
from app.domain.enums import ClassificationTier, ConsequenceType
from app.domain.variant import VCFRecord
from tests.fixtures.mock_evidence import (
    benign_bundle,
    lof_intolerant_bundle,
    pathogenic_bundle,
    vus_bundle,
)


def _vcf(
    chrom: str = "chr17",
    pos: int = 43044300,
    ref: str = "C",
    alt: str = "T",
) -> VCFRecord:
    return VCFRecord(chrom=chrom, pos=pos, ref=ref, alt=[alt])


engine = RuleEngine(DEFAULT_RULES)


def test_pathogenic_bundle_classifies_pathogenic() -> None:
    result = engine.classify(_vcf(), pathogenic_bundle())
    assert result.tier == ClassificationTier.PATHOGENIC


def test_benign_bundle_classifies_benign() -> None:
    result = engine.classify(_vcf(), benign_bundle())
    assert result.tier == ClassificationTier.BENIGN


def test_vus_bundle_classifies_vus() -> None:
    result = engine.classify(_vcf(), vus_bundle())
    assert result.tier == ClassificationTier.VUS


def test_lof_intolerant_bundle_classifies_pathogenic_or_likely() -> None:
    result = engine.classify(_vcf(), lof_intolerant_bundle())
    assert result.tier in (
        ClassificationTier.PATHOGENIC,
        ClassificationTier.LIKELY_PATHOGENIC,
    )


def test_ba1_alone_forces_benign_overriding_positive_evidence() -> None:
    # Combine common AF with pathogenic-looking ClinVar + high CADD
    bundle = EvidenceBundle(
        gnomad_af=0.10,
        gnomad_pli=0.99,
        clinvar_significances=["Pathogenic"],
        cadd_phred=35.0,
        revel_score=0.9,
        is_frameshift=True,
    )
    result = engine.classify(_vcf(), bundle)
    assert result.tier == ClassificationTier.BENIGN


def test_result_contains_evidence_items() -> None:
    result = engine.classify(_vcf(), pathogenic_bundle())
    assert len(result.evidence) > 0
    codes = [e.code.value for e in result.evidence]
    assert "PVS1" in codes


def test_pathogenic_score_range() -> None:
    for bundle in (pathogenic_bundle(), benign_bundle(), vus_bundle()):
        result = engine.classify(_vcf(), bundle)
        assert 0.0 <= result.pathogenic_score <= 1.0


def test_pathogenic_score_ordering() -> None:
    path_score = engine.classify(_vcf(), pathogenic_bundle()).pathogenic_score
    vus_score = engine.classify(_vcf(), vus_bundle()).pathogenic_score
    benign_score = engine.classify(_vcf(), benign_bundle()).pathogenic_score
    assert path_score > vus_score > benign_score


def test_ba1_not_present_in_pathogenic_result() -> None:
    result = engine.classify(_vcf(), pathogenic_bundle())
    ba_codes = [e.code.value for e in result.evidence if e.code.value.startswith("BA")]
    assert ba_codes == []


def test_result_is_automated() -> None:
    result = engine.classify(_vcf(), vus_bundle())
    assert result.is_automated is True


def test_empty_evidence_bundle_gives_vus() -> None:
    # No evidence at all: 0 points → VUS
    bundle = EvidenceBundle()
    result = engine.classify(_vcf(), bundle)
    assert result.tier == ClassificationTier.VUS


def test_pm2_fires_when_af_absent() -> None:
    bundle = EvidenceBundle(gnomad_af=None)
    result = engine.classify(_vcf(), bundle)
    pm2_items = [e for e in result.evidence if e.code.value == "PM2"]
    assert len(pm2_items) == 1


def test_splice_variant_in_pli_gene_triggers_pvs1() -> None:
    bundle = EvidenceBundle(is_splice=True, gnomad_pli=0.98, gnomad_af=0.00001)
    result = engine.classify(_vcf(), bundle)
    pvs1_items = [e for e in result.evidence if e.code.value == "PVS1"]
    assert len(pvs1_items) == 1
    assert result.tier in (
        ClassificationTier.LIKELY_PATHOGENIC,
        ClassificationTier.PATHOGENIC,
    )
