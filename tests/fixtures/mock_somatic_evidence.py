from app.classification.somatic.base import SomaticEvidenceBundle, TherapyImplication


def tier1_bundle() -> SomaticEvidenceBundle:
    """Tier I: approved therapy (CIViC A) + OncoKB LEVEL_1."""
    return SomaticEvidenceBundle(
        civic_evidence_levels=["A"],
        civic_has_approved_therapy=True,
        civic_has_investigational_therapy=True,
        civic_therapy_implications=[
            TherapyImplication(
                drug="vemurafenib",
                disease="melanoma",
                evidence_level="A",
                source="CIViC",
            )
        ],
        oncokb_oncogenicity="Oncogenic",
        oncokb_highest_sensitive_level="LEVEL_1",
        oncokb_highest_resistance_level=None,
        oncokb_therapy_implications=[],
        gnomad_af=0.0001,
        is_synonymous=False,
        is_hotspot=True,
    )


def tier2_civic_bundle() -> SomaticEvidenceBundle:
    """Tier II: CIViC level C evidence, no approved therapy."""
    return SomaticEvidenceBundle(
        civic_evidence_levels=["C"],
        civic_has_approved_therapy=False,
        civic_has_investigational_therapy=True,
        civic_therapy_implications=[
            TherapyImplication(
                drug="pembrolizumab",
                disease="colorectal cancer",
                evidence_level="C",
                source="CIViC",
            )
        ],
        oncokb_oncogenicity=None,
        oncokb_highest_sensitive_level=None,
        oncokb_highest_resistance_level=None,
        oncokb_therapy_implications=[],
        gnomad_af=0.0005,
        is_synonymous=False,
        is_hotspot=True,
    )


def tier2_hotspot_bundle() -> SomaticEvidenceBundle:
    """Tier II: hotspot only, no CIViC or OncoKB evidence."""
    return SomaticEvidenceBundle(
        civic_evidence_levels=[],
        civic_has_approved_therapy=False,
        civic_has_investigational_therapy=False,
        civic_therapy_implications=[],
        oncokb_oncogenicity=None,
        oncokb_highest_sensitive_level=None,
        oncokb_highest_resistance_level=None,
        oncokb_therapy_implications=[],
        gnomad_af=0.0001,
        is_synonymous=False,
        is_hotspot=True,
    )


def tier3_bundle() -> SomaticEvidenceBundle:
    """Tier III: no evidence, rare, not a hotspot."""
    return SomaticEvidenceBundle(
        civic_evidence_levels=[],
        civic_has_approved_therapy=False,
        civic_has_investigational_therapy=False,
        civic_therapy_implications=[],
        oncokb_oncogenicity=None,
        oncokb_highest_sensitive_level=None,
        oncokb_highest_resistance_level=None,
        oncokb_therapy_implications=[],
        gnomad_af=0.0002,
        is_synonymous=False,
        is_hotspot=False,
    )


def tier4_af_bundle() -> SomaticEvidenceBundle:
    """Tier IV: common variant in gnomAD (AF > 0.01)."""
    return SomaticEvidenceBundle(
        civic_evidence_levels=[],
        civic_has_approved_therapy=False,
        civic_has_investigational_therapy=False,
        civic_therapy_implications=[],
        oncokb_oncogenicity=None,
        oncokb_highest_sensitive_level=None,
        oncokb_highest_resistance_level=None,
        oncokb_therapy_implications=[],
        gnomad_af=0.05,
        is_synonymous=False,
        is_hotspot=False,
    )


def tier4_synonymous_bundle() -> SomaticEvidenceBundle:
    """Tier IV: synonymous variant."""
    return SomaticEvidenceBundle(
        civic_evidence_levels=[],
        civic_has_approved_therapy=False,
        civic_has_investigational_therapy=False,
        civic_therapy_implications=[],
        oncokb_oncogenicity=None,
        oncokb_highest_sensitive_level=None,
        oncokb_highest_resistance_level=None,
        oncokb_therapy_implications=[],
        gnomad_af=0.001,
        is_synonymous=True,
        is_hotspot=False,
    )
