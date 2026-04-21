nextflow.enable.dsl=2

include { NORMALIZE } from './modules/normalize'
include { ANNOTATE  } from './modules/annotate'

params.input            = "data/*.vcf.gz"
params.outdir           = "results"
params.skip_annotation  = false

workflow VARIANT_TRIAGE {
    Channel.fromPath(params.input)
        .map { vcf -> [vcf.simpleName, vcf] }
        .set { vcf_ch }

    NORMALIZE(vcf_ch)

    if (!params.skip_annotation) {
        ANNOTATE(NORMALIZE.out)
    }
}

workflow {
    VARIANT_TRIAGE()
}

workflow.onComplete {
    log.info "Pipeline complete. Results in ${params.outdir}"
    log.info "Duration: ${workflow.duration}"
    log.info "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
}
