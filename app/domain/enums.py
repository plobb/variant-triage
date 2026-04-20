from enum import Enum


class VariantOrigin(str, Enum):
    GERMLINE = "GERMLINE"
    SOMATIC = "SOMATIC"
    UNKNOWN = "UNKNOWN"


class Zygosity(str, Enum):
    HOMOZYGOUS_REF = "HOM_REF"
    HETEROZYGOUS = "HET"
    HOMOZYGOUS_ALT = "HOM_ALT"
    HEMIZYGOUS = "HEMI"
    UNKNOWN = "UNKNOWN"


class ConsequenceType(str, Enum):
    MISSENSE = "missense_variant"
    NONSENSE = "stop_gained"
    FRAMESHIFT = "frameshift_variant"
    SPLICE_DONOR = "splice_donor_variant"
    SPLICE_ACCEPTOR = "splice_acceptor_variant"
    SYNONYMOUS = "synonymous_variant"
    INTRON = "intron_variant"
    UPSTREAM = "upstream_gene_variant"
    DOWNSTREAM = "downstream_gene_variant"
    UTR_5 = "5_prime_UTR_variant"
    UTR_3 = "3_prime_UTR_variant"
    STRUCTURAL = "structural_variant"
    UNKNOWN = "unknown"


class ClassificationTier(str, Enum):
    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely_pathogenic"
    VUS = "Variant_of_uncertain_significance"
    LIKELY_BENIGN = "Likely_benign"
    BENIGN = "Benign"


class EvidenceCode(str, Enum):
    # ACMG/AMP 2015 codes
    PVS1 = "PVS1"
    PS1 = "PS1"
    PS2 = "PS2"
    PS3 = "PS3"
    PS4 = "PS4"
    PM1 = "PM1"
    PM2 = "PM2"
    PM3 = "PM3"
    PM4 = "PM4"
    PM5 = "PM5"
    PM6 = "PM6"
    PP1 = "PP1"
    PP2 = "PP2"
    PP3 = "PP3"
    PP4 = "PP4"
    PP5 = "PP5"
    BA1 = "BA1"
    BS1 = "BS1"
    BS2 = "BS2"
    BS3 = "BS3"
    BS4 = "BS4"
    BP1 = "BP1"
    BP2 = "BP2"
    BP3 = "BP3"
    BP4 = "BP4"
    BP5 = "BP5"
    BP6 = "BP6"
    BP7 = "BP7"


class SVType(str, Enum):
    DEL = "DEL"
    DUP = "DUP"
    INV = "INV"
    INS = "INS"
    BND = "BND"
    CNV = "CNV"


class AuditAction(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CLASSIFY = "CLASSIFY"
    EXPORT = "EXPORT"
