from app.classification.base import EvidenceBundle
from app.domain.enums import ConsequenceType


def pathogenic_bundle() -> EvidenceBundle:
    """High-confidence pathogenic: LoF in pLI gene, rare, ClinVar Pathogenic, high CADD."""
    return EvidenceBundle(
        gnomad_af=0.0001,
        gnomad_pli=0.99,
        gnomad_mis_z=3.5,
        clinvar_significances=["Pathogenic"],
        clinvar_same_residue=[],
        cadd_phred=32.0,
        revel_score=0.85,
        consequence=ConsequenceType.FRAMESHIFT,
        is_frameshift=True,
        is_splice=False,
        protein_length_change=True,
    )


def benign_bundle() -> EvidenceBundle:
    """Common variant: BA1 triggers, ClinVar Benign, low computational scores."""
    return EvidenceBundle(
        gnomad_af=0.15,
        gnomad_pli=0.01,
        gnomad_mis_z=0.5,
        clinvar_significances=["Benign"],
        clinvar_same_residue=[],
        cadd_phred=3.0,
        revel_score=0.1,
        consequence=ConsequenceType.SYNONYMOUS,
        is_frameshift=False,
        is_splice=False,
        protein_length_change=False,
    )


def vus_bundle() -> EvidenceBundle:
    """VUS: rare variant, no ClinVar, intermediate computational scores."""
    return EvidenceBundle(
        gnomad_af=0.0005,
        gnomad_pli=0.4,
        gnomad_mis_z=1.8,
        clinvar_significances=[],
        clinvar_same_residue=[],
        cadd_phred=18.0,
        revel_score=0.5,
        consequence=ConsequenceType.MISSENSE,
        is_frameshift=False,
        is_splice=False,
        protein_length_change=False,
    )


def lof_intolerant_bundle() -> EvidenceBundle:
    """LoF in a highly pLI-intolerant gene, ultra-rare."""
    return EvidenceBundle(
        gnomad_af=0.00001,
        gnomad_pli=0.95,
        gnomad_mis_z=4.1,
        clinvar_significances=[],
        clinvar_same_residue=[],
        cadd_phred=35.0,
        revel_score=None,
        consequence=ConsequenceType.FRAMESHIFT,
        is_frameshift=True,
        is_splice=False,
        protein_length_change=True,
    )
