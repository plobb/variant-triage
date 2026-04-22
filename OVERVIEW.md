# What is variant-triage?

## The problem

When a patient has their DNA sequenced, the result is a file containing thousands of genetic variants - positions where their DNA differs from a reference genome. Most of these differences are harmless. A small number may be clinically significant: linked to inherited disease, cancer risk, or drug response.

The challenge is working out which is which.

This process - called **variant interpretation** - is currently one of the most labour-intensive bottlenecks in clinical genomics. It requires cross-referencing multiple scientific databases, applying internationally agreed classification rules, and producing a written report that a clinician can act on. In many labs, it still involves a combination of manual lookups, spreadsheets, and institutional knowledge.

---

## What this project does

**variant-triage** is a software service that automates the structured parts of this workflow.

You send it a VCF file - the standard format for storing genetic variants - and it returns a classification for each variant, explaining what evidence was found and why the variant was scored the way it was.

It handles two types of variants:

**Germline variants** - inherited mutations present in every cell of the body. These are relevant for conditions like hereditary breast and ovarian cancer (BRCA1/2), Lynch syndrome, and other heritable diseases. The service applies the **ACMG/AMP 2015 criteria** - the internationally recognised standard used by clinical genetics labs worldwide - scoring variants as Pathogenic, Likely Pathogenic, Uncertain Significance, Likely Benign, or Benign.

**Somatic variants** - mutations that arise in specific tissues, such as tumour cells. These are relevant in oncology, where knowing whether a mutation has a targeted therapy available can directly affect treatment decisions. The service applies the **AMP/ASCO/CAP tiering framework**, classifying variants from Tier I (strong clinical significance, FDA-approved therapies exist) to Tier IV (benign or likely benign).

---

## Where the evidence comes from

The classifications aren't guesswork. For each variant, the service queries:

- **gnomAD** - a database of genetic variation across hundreds of thousands of human genomes, used to assess how common or rare a variant is in the general population
- **ClinVar** - a public archive of clinically observed variants and their reported significance, maintained by NCBI
- **CIViC** - a curated knowledgebase of cancer variants and their clinical evidence, including known therapies
- **OncoKB** - Memorial Sloan Kettering's precision oncology knowledge base, covering actionable cancer mutations

---

## The interpretation assistant

Once a variant is classified, the service can draft a plain-English interpretation using an AI assistant built on Claude. The draft explains the classification in clinical language, cites the relevant evidence, and is designed for review by a qualified geneticist rather than direct clinical use.

The assistant has built-in guardrails: it will never state a diagnosis, never recommend a specific treatment, and always ends its output with a reminder that the interpretation must be reviewed before clinical application.

---

## Why this matters

The bottleneck in clinical genomics isn't sequencing - sequencing has become fast and cheap. The bottleneck is interpretation. A single whole-genome sequence can contain millions of variants, and determining which ones are relevant to a patient's condition requires significant expert time.

Software that can handle the structured, rules-based parts of this workflow - consistently, traceably, and at scale - frees clinical scientists to focus on the genuinely complex cases that require human judgement.

That is what this project is designed to demonstrate.

---

## What this project is not

This is a **portfolio and research project**. It uses only synthetic data and has not been validated for clinical use. It is not a medical device and should not be used to inform real clinical decisions.

For more detail on what would be required to deploy something like this in a clinical setting, see [SECURITY_CONSIDERATIONS.md](SECURITY_CONSIDERATIONS.md).

---

*For a technical walkthrough of the API, see [TUTORIAL.md](TUTORIAL.md).*  
*For the full codebase, see [github.com/plobb/variant-triage](https://github.com/plobb/variant-triage).*
