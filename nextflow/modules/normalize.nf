process NORMALIZE {
    tag "${sample_id}"
    container 'quay.io/biocontainers/bcftools:1.19--h8b25389_1'

    input:
    tuple val(sample_id), path(vcf)

    output:
    tuple val(sample_id), path("${sample_id}.norm.vcf.gz"), path("${sample_id}.norm.vcf.gz.tbi")

    script:
    """
    bcftools norm \\
        --multiallelics -both \\
        --output-type z \\
        --output ${sample_id}.norm.vcf.gz \\
        ${vcf}
    bcftools index --tbi ${sample_id}.norm.vcf.gz
    """
}
