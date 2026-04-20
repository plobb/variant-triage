"""Unit tests for individual ACMG rules — no network calls."""
from __future__ import annotations

import pytest

from app.classification.base import EvidenceBundle
from app.classification.rules.pm1 import PM1Rule
from app.classification.rules.pm2_ba1 import BA1Rule, PM2Rule
from app.classification.rules.pm4 import PM4Rule
from app.classification.rules.pp2_pp3_bp4 import BP4Rule, PP2Rule, PP3Rule
from app.classification.rules.ps1_pm5 import PM5Rule, PS1Rule
from app.classification.rules.pvs1 import PVS1Rule
from app.domain.enums import ConsequenceType, EvidenceCode
from app.domain.variant import VCFRecord


def _vcf(
    chrom: str = "chr17",
    pos: int = 43044300,
    ref: str = "C",
    alt: str = "T",
) -> VCFRecord:
    return VCFRecord(chrom=chrom, pos=pos, ref=ref, alt=[alt])


# ---------------------------------------------------------------------------
# PVS1
# ---------------------------------------------------------------------------


def test_pvs1_fires_frameshift_high_pli() -> None:
    rule = PVS1Rule()
    bundle = EvidenceBundle(is_frameshift=True, gnomad_pli=0.99)
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.PVS1
    assert "0.990" in item.description


def test_pvs1_fires_splice_high_pli() -> None:
    rule = PVS1Rule()
    bundle = EvidenceBundle(is_splice=True, gnomad_pli=0.95)
    assert rule.evaluate(_vcf(), bundle) is not None


def test_pvs1_no_fire_low_pli() -> None:
    rule = PVS1Rule()
    bundle = EvidenceBundle(is_frameshift=True, gnomad_pli=0.5)
    assert rule.evaluate(_vcf(), bundle) is None


def test_pvs1_no_fire_not_lof() -> None:
    rule = PVS1Rule()
    bundle = EvidenceBundle(is_frameshift=False, is_splice=False, gnomad_pli=0.99)
    assert rule.evaluate(_vcf(), bundle) is None


def test_pvs1_handles_none_pli() -> None:
    rule = PVS1Rule()
    bundle = EvidenceBundle(is_frameshift=True, gnomad_pli=None)
    assert rule.evaluate(_vcf(), bundle) is None


# ---------------------------------------------------------------------------
# PS1
# ---------------------------------------------------------------------------


def test_ps1_fires_on_pathogenic_clinvar() -> None:
    rule = PS1Rule()
    bundle = EvidenceBundle(clinvar_significances=["Pathogenic"])
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.PS1


def test_ps1_no_fire_benign_clinvar() -> None:
    rule = PS1Rule()
    bundle = EvidenceBundle(clinvar_significances=["Benign"])
    assert rule.evaluate(_vcf(), bundle) is None


def test_ps1_no_fire_empty_clinvar() -> None:
    rule = PS1Rule()
    bundle = EvidenceBundle(clinvar_significances=[])
    assert rule.evaluate(_vcf(), bundle) is None


# ---------------------------------------------------------------------------
# PM5
# ---------------------------------------------------------------------------


def test_pm5_fires_same_residue_no_exact_match() -> None:
    rule = PM5Rule()
    bundle = EvidenceBundle(
        clinvar_significances=[],
        clinvar_same_residue=["RCV000123456"],
    )
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.PM5


def test_pm5_no_fire_when_ps1_active() -> None:
    rule = PM5Rule()
    bundle = EvidenceBundle(
        clinvar_significances=["Pathogenic"],
        clinvar_same_residue=["RCV000123456"],
    )
    assert rule.evaluate(_vcf(), bundle) is None


def test_pm5_no_fire_empty_same_residue() -> None:
    rule = PM5Rule()
    bundle = EvidenceBundle(clinvar_significances=[], clinvar_same_residue=[])
    assert rule.evaluate(_vcf(), bundle) is None


# ---------------------------------------------------------------------------
# PM1
# ---------------------------------------------------------------------------


def test_pm1_fires_in_brca1_ring_domain() -> None:
    rule = PM1Rule()
    vcf = _vcf(chrom="chr17", pos=43080000)
    assert rule.evaluate(vcf, EvidenceBundle()) is not None


def test_pm1_fires_in_kras_hotspot() -> None:
    rule = PM1Rule()
    vcf = _vcf(chrom="chr12", pos=25227345)
    item = rule.evaluate(vcf, EvidenceBundle())
    assert item is not None
    assert item.code == EvidenceCode.PM1


def test_pm1_no_fire_outside_all_domains() -> None:
    rule = PM1Rule()
    vcf = _vcf(chrom="chr1", pos=1000000)
    assert rule.evaluate(vcf, EvidenceBundle()) is None


def test_pm1_handles_none_evidence_fields() -> None:
    rule = PM1Rule()
    vcf = _vcf(chrom="chr17", pos=7670000)
    bundle = EvidenceBundle(gnomad_af=None, gnomad_pli=None)
    assert rule.evaluate(vcf, bundle) is not None


# ---------------------------------------------------------------------------
# BA1
# ---------------------------------------------------------------------------


def test_ba1_fires_common_variant() -> None:
    rule = BA1Rule()
    bundle = EvidenceBundle(gnomad_af=0.10)
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.BA1


def test_ba1_no_fire_rare_variant() -> None:
    rule = BA1Rule()
    bundle = EvidenceBundle(gnomad_af=0.001)
    assert rule.evaluate(_vcf(), bundle) is None


def test_ba1_no_fire_none_af() -> None:
    rule = BA1Rule()
    bundle = EvidenceBundle(gnomad_af=None)
    assert rule.evaluate(_vcf(), bundle) is None


# ---------------------------------------------------------------------------
# PM2
# ---------------------------------------------------------------------------


def test_pm2_fires_absent_variant() -> None:
    rule = PM2Rule()
    bundle = EvidenceBundle(gnomad_af=None)
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.PM2


def test_pm2_fires_ultra_rare() -> None:
    rule = PM2Rule()
    bundle = EvidenceBundle(gnomad_af=0.00005)
    assert rule.evaluate(_vcf(), bundle) is not None


def test_pm2_no_fire_moderate_af() -> None:
    rule = PM2Rule()
    bundle = EvidenceBundle(gnomad_af=0.005)
    assert rule.evaluate(_vcf(), bundle) is None


def test_pm2_no_fire_when_ba1_territory() -> None:
    rule = PM2Rule()
    bundle = EvidenceBundle(gnomad_af=0.10)
    assert rule.evaluate(_vcf(), bundle) is None


# ---------------------------------------------------------------------------
# PM4
# ---------------------------------------------------------------------------


def test_pm4_fires_inframe_indel() -> None:
    rule = PM4Rule()
    bundle = EvidenceBundle(
        protein_length_change=True,
        consequence=ConsequenceType.MISSENSE,
    )
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.PM4


def test_pm4_no_fire_nonsense() -> None:
    rule = PM4Rule()
    bundle = EvidenceBundle(
        protein_length_change=True,
        consequence=ConsequenceType.NONSENSE,
    )
    assert rule.evaluate(_vcf(), bundle) is None


def test_pm4_no_fire_no_length_change() -> None:
    rule = PM4Rule()
    bundle = EvidenceBundle(protein_length_change=False)
    assert rule.evaluate(_vcf(), bundle) is None


# ---------------------------------------------------------------------------
# PP2
# ---------------------------------------------------------------------------


def test_pp2_fires_high_mis_z() -> None:
    rule = PP2Rule()
    bundle = EvidenceBundle(gnomad_mis_z=3.5)
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.PP2


def test_pp2_no_fire_low_mis_z() -> None:
    rule = PP2Rule()
    bundle = EvidenceBundle(gnomad_mis_z=2.0)
    assert rule.evaluate(_vcf(), bundle) is None


def test_pp2_no_fire_none_mis_z() -> None:
    rule = PP2Rule()
    bundle = EvidenceBundle(gnomad_mis_z=None)
    assert rule.evaluate(_vcf(), bundle) is None


# ---------------------------------------------------------------------------
# PP3
# ---------------------------------------------------------------------------


def test_pp3_fires_high_cadd() -> None:
    rule = PP3Rule()
    bundle = EvidenceBundle(cadd_phred=25.0, revel_score=0.4)
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.PP3


def test_pp3_fires_high_revel_alone() -> None:
    rule = PP3Rule()
    bundle = EvidenceBundle(cadd_phred=15.0, revel_score=0.8)
    assert rule.evaluate(_vcf(), bundle) is not None


def test_pp3_no_fire_low_scores() -> None:
    rule = PP3Rule()
    bundle = EvidenceBundle(cadd_phred=10.0, revel_score=0.4)
    assert rule.evaluate(_vcf(), bundle) is None


def test_pp3_handles_none_scores() -> None:
    rule = PP3Rule()
    bundle = EvidenceBundle(cadd_phred=None, revel_score=None)
    assert rule.evaluate(_vcf(), bundle) is None


# ---------------------------------------------------------------------------
# BP4
# ---------------------------------------------------------------------------


def test_bp4_fires_low_cadd_and_revel() -> None:
    rule = BP4Rule()
    bundle = EvidenceBundle(cadd_phred=5.0, revel_score=0.1)
    item = rule.evaluate(_vcf(), bundle)
    assert item is not None
    assert item.code == EvidenceCode.BP4


def test_bp4_no_fire_moderate_cadd() -> None:
    rule = BP4Rule()
    bundle = EvidenceBundle(cadd_phred=12.0, revel_score=0.2)
    assert rule.evaluate(_vcf(), bundle) is None


def test_bp4_no_fire_none_revel() -> None:
    rule = BP4Rule()
    # BP4 requires REVEL to be present
    bundle = EvidenceBundle(cadd_phred=5.0, revel_score=None)
    assert rule.evaluate(_vcf(), bundle) is None
