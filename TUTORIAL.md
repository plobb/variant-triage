# variant-triage — Tutorial

This tutorial walks through the full variant interpretation workflow using the live API at `https://variant-triage.fly.dev`.

All examples use `curl`. You can also follow along interactively using the [Swagger UI](https://variant-triage.fly.dev/docs).

> **Note:** The app runs on Fly.io's free tier and may take ~30 seconds to respond to the first request after a period of inactivity. If you get a 502, wait a moment and retry.

---

## 1. Confirm the service is up

```bash
curl https://variant-triage.fly.dev/health
```

Expected response:

```json
{"status": "ok", "version": "0.1.0"}
```

---

## 2. Create an account

```bash
curl -X POST https://variant-triage.fly.dev/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "researcher@example.com",
    "password": "Testpass1!"
  }'
```

Expected response:

```json
{
  "id": 1,
  "email": "researcher@example.com",
  "created_at": "2026-04-22T10:00:00"
}
```

---

## 3. Log in and get a token

```bash
curl -X POST https://variant-triage.fly.dev/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=researcher@example.com&password=Testpass1!"
```

Expected response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Save the token — you'll need it for all subsequent requests:

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 4. Submit a germline VCF for ACMG classification

The service accepts raw VCF text. Here we use a minimal synthetic VCF with two variants — a likely pathogenic BRCA1 frameshift and a common benign SNP.

```bash
curl -X POST https://variant-triage.fly.dev/variants/germline \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sample_name": "NA12878-germline",
    "origin": "GERMLINE",
    "vcf_content": "##fileformat=VCFv4.2\n##FILTER=<ID=PASS,Description=\"All filters passed\">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tNA12878\nchr17\t43044295\t.\tGTACC\tG\t100\tPASS\t.\tGT:DP:AD\t0/1:50:25,25\nchr1\t925952\t.\tG\tA\t80\tPASS\t.\tGT:DP:AD\t0/1:45:30,15\n"
  }'
```

Expected response:

```json
{
  "sample_id": 1,
  "sample_name": "NA12878-germline",
  "variants_processed": 2,
  "results": [
    {
      "id": 1,
      "chrom": "chr17",
      "pos": 43044295,
      "ref": "GTACC",
      "alt": "G",
      "gene": null,
      "consequence": "frameshift_variant",
      "classification_tier": "Likely_pathogenic",
      "acmg_points": 9,
      "evidence_codes": ["PVS1", "PM2"],
      "summary": "Likely pathogenic — PVS1 (LoF in pLI≥0.9 gene), PM2 (absent from gnomAD)"
    },
    {
      "id": 2,
      "chrom": "chr1",
      "pos": 925952,
      "ref": "G",
      "alt": "A",
      "gene": null,
      "consequence": null,
      "classification_tier": "VUS",
      "acmg_points": 0,
      "evidence_codes": [],
      "summary": "Variant of uncertain significance — insufficient evidence"
    }
  ],
  "classified_at": "2026-04-22T10:01:00"
}
```

### What just happened

The service parsed the VCF, created a `Sample` and two `Variant` rows in the database, then ran the ACMG rule engine against each variant. The frameshift at chr17:43044295 falls within the BRCA1 gene region, triggering **PVS1** (loss-of-function variant in a LoF-intolerant gene) and **PM2** (absent from gnomAD population databases), scoring 9 points — sufficient for Likely Pathogenic.

---

## 5. Submit a somatic VCF for AMP/ASCO/CAP classification

```bash
curl -X POST https://variant-triage.fly.dev/variants/somatic \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sample_name": "TCGA-tumour-01",
    "origin": "SOMATIC",
    "vcf_content": "##fileformat=VCFv4.2\n##INFO=<ID=SOMATIC,Number=0,Type=Flag,Description=\"Somatic variant\">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tTUMOUR\nchr12\t25227343\t.\tC\tA\t95\tPASS\tSOMATIC\tGT:DP:AF\t0/1:120:0.35\nchr7\t55191822\t.\tT\tG\t88\tPASS\tSOMATIC\tGT:DP:AF\t0/1:98:0.22\n"
  }'
```

Expected response:

```json
{
  "sample_id": 2,
  "sample_name": "TCGA-tumour-01",
  "variants_processed": 2,
  "results": [
    {
      "id": 3,
      "chrom": "chr12",
      "pos": 25227343,
      "ref": "C",
      "alt": "A",
      "gene": null,
      "consequence": null,
      "amp_tier": "Tier_II",
      "confidence": "medium",
      "therapy_implications": [],
      "oncokb_oncogenicity": null,
      "summary": "chr12:25227343 C>A: Tier II — hotspot, investigational therapies may be available"
    },
    {
      "id": 4,
      "chrom": "chr7",
      "pos": 55191822,
      "ref": "T",
      "alt": "G",
      "gene": null,
      "consequence": null,
      "amp_tier": "Tier_III",
      "confidence": "low",
      "therapy_implications": [],
      "oncokb_oncogenicity": null,
      "summary": "chr7:55191822 T>G: Tier III — variant of unknown significance"
    }
  ],
  "classified_at": "2026-04-22T10:02:00"
}
```

The KRAS codon 12/13 region (chr12:25227343) falls within the hardcoded hotspot domain map, triggering **Tier II** classification. The EGFR variant at chr7 has no matching evidence and defaults to **Tier III**.

---

## 6. Retrieve a stored classification

Use the variant ID returned in the previous responses:

```bash
curl https://variant-triage.fly.dev/variants/1 \
  -H "Authorization: Bearer $TOKEN"
```

The service enforces ownership — you can only retrieve classifications belonging to your own samples. Attempting to access another user's variant returns 404.

---

## 7. List all your classifications

```bash
curl https://variant-triage.fly.dev/variants/ \
  -H "Authorization: Bearer $TOKEN"
```

Returns up to 100 classifications ordered by most recent first.

---

## 8. Request an LLM-assisted interpretation

Once a variant has been classified, you can request a drafted clinical interpretation:

```bash
curl -X POST https://variant-triage.fly.dev/variants/1/interpret \
  -H "Authorization: Bearer $TOKEN"
```

Expected response:

```json
{
  "variant_id": "1",
  "interpretation": "This frameshift variant at chr17:43044295 in the BRCA1 region results in a premature truncation, consistent with loss of function. The variant is absent from population databases (PM2) and occurs in a gene with high intolerance to loss-of-function variation (PVS1, pLI≥0.9). The combined evidence is suggestive of likely pathogenicity under ACMG/AMP 2015 criteria. This interpretation requires review by a qualified clinical geneticist before clinical use.",
  "confidence": "high",
  "guardrail_flags": [],
  "disclaimer": "RESEARCH USE ONLY. This interpretation is AI-generated and has not been validated for clinical use. It must be reviewed and approved by a qualified clinical geneticist before any clinical application. This tool is not a medical device.",
  "model_used": "claude-3-5-haiku-20241022",
  "generated_at": "2026-04-22T10:03:00"
}
```

### Guardrails

The interpretation assistant runs automated checks on every response before it reaches the caller. Any output containing diagnosis statements ("you have cancer"), treatment directives ("take vemurafenib"), or overconfident language ("definitely pathogenic") is flagged and a warning is appended. The `guardrail_flags` field lists any issues detected.

> **Note:** The interpretation endpoint requires `ANTHROPIC_API_KEY` to be configured as a Fly secret. If the key is absent, the endpoint returns 503. The classifier endpoints work independently of this key.

---

## 9. Batch interpretation

You can request interpretations for multiple variants in a single call:

```bash
curl -X POST https://variant-triage.fly.dev/variants/interpret/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"variant_ids": [1, 2, 3]}'
```

Requests run concurrently (up to 3 at a time) and results are returned in the same order as the input IDs.

---

## 10. Using the Swagger UI

All of the above can be explored interactively at [https://variant-triage.fly.dev/docs](https://variant-triage.fly.dev/docs).

1. Click **POST /auth/register** → **Try it out** → fill in email and password → **Execute**
2. Click **POST /auth/token** → **Try it out** → enter credentials → **Execute** → copy the `access_token`
3. Click the **Authorize** button (top right) → paste `Bearer <your_token>` → **Authorize**
4. All locked endpoints are now accessible — try **POST /variants/germline** with the VCF content from Step 4 above

---

## Architecture notes for reviewers

| Component | Detail |
|---|---|
| VCF parsing | cyvcf2 (htslib-backed), handles short-read and long-read (PacBio/ONT) FORMAT fields including HP haplotype phasing tags |
| ACMG engine | 10 rules (PVS1, PS1, PM1–5, PP2/3, BA1, BP4) implemented as a plugin registry; each rule is independently testable |
| Evidence sources | gnomAD v4 GraphQL API (AF, pLI, mis_z), ClinVar E-utilities (exact match + same-residue pathogenic), in-memory caching per session |
| Somatic tiering | AMP/ASCO/CAP Tier I–IV; CIViC REST API for evidence levels and therapy implications; OncoKB client (graceful no-op if token absent) |
| Audit logging | SHA-256 hash of request body stored per request — tamper-evident record without persisting raw variant data |
| LLM guardrails | Regex patterns detect diagnosis statements, treatment directives, and overconfident language before responses reach callers |
| Workflow | Nextflow DSL2 pipeline: bcftools norm → VEP annotation, containerised with Docker |
