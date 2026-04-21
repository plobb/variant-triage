# variant-triage Nextflow pipeline

Two-step DSL2 pipeline: VCF normalisation (bcftools) → annotation (VEP).

> **CLINICAL DISCLAIMER** — this pipeline processes synthetic data only.
> It is a portfolio demonstration and must not be used for clinical decisions.

## Prerequisites

- [Nextflow](https://www.nextflow.io/) ≥ 23.10
- Docker (for containerised processes)

```bash
# Install Nextflow
curl -s https://get.nextflow.io | bash
sudo mv nextflow /usr/local/bin/
```

## Quick start (demo mode — no VEP cache required)

```bash
nextflow run nextflow/main.nf \
  --input "tests/fixtures/*.vcf" \
  --outdir results \
  -profile demo
```

The `demo` profile sets `--skip_annotation true`, so only the bcftools
normalisation step runs.

## Full pipeline (requires VEP cache)

```bash
nextflow run nextflow/main.nf \
  --input "tests/fixtures/*.vcf" \
  --outdir results
```

### Download the VEP cache

```bash
docker run -it ensemblorg/ensembl-vep:release_111.0 \
  perl INSTALL.pl --AUTO cf \
  --SPECIES homo_sapiens \
  --ASSEMBLY GRCh38 \
  --CACHEDIR /opt/vep/.vep
```

## Pipeline overview

```
[input VCFs]
     │
     ▼
 NORMALIZE          bcftools norm: left-align + split multiallelics
     │              output: <sample>.norm.vcf.gz + .tbi
     ▼
 ANNOTATE           VEP release 111, GRCh38, --everything
                    output: <sample>.vep.vcf.gz
```

## Parameters

| Parameter          | Default          | Description                     |
|--------------------|------------------|---------------------------------|
| `--input`          | `data/*.vcf.gz`  | Glob pattern for input VCFs     |
| `--outdir`         | `results`        | Output directory                |
| `--skip_annotation`| `false`          | Skip VEP step (demo/CI mode)    |

## Profiles

| Profile    | Description                                       |
|------------|---------------------------------------------------|
| `standard` | Docker enabled (default)                          |
| `demo`     | Skips annotation — no VEP cache required          |
| `ci`       | Docker disabled — used for syntax validation only |
