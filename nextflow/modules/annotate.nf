// VEP cache required at /opt/vep/.vep for production use
// For demo: run with --profile demo to skip annotation

process ANNOTATE {
    tag "${sample_id}"
    container 'ensemblorg/ensembl-vep:release_111.0'

    input:
    tuple val(sample_id), path(vcf), path(tbi)

    output:
    tuple val(sample_id), path("${sample_id}.vep.vcf.gz")

    script:
    """
    vep \\
        --input_file ${vcf} \\
        --output_file ${sample_id}.vep.vcf.gz \\
        --format vcf \\
        --vcf \\
        --compress_output bgzip \\
        --offline \\
        --cache \\
        --dir_cache /opt/vep/.vep \\
        --assembly GRCh38 \\
        --fork 4 \\
        --everything \\
        --no_progress
    """
}
