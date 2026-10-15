cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}
inputs:
  script: File
  snp_files: File[]
  sift_files: File[]
  populations: File[]
  step: int
outputs:
  overlap_files:
    type: &id001
      type: array
      items:
        type: array
        items: File
    outputSource: chromosome/overlap_files
  freq_files:
    type: *id001
    outputSource: chromosome/freq_files
  freq_summaries:
    type:
      type: array
      items:
        type: array
        items: string
    outputSource: chromosome/freq_summaries
steps:
  chromosome:
    run: chromosome.cwl
    in:
      script: script
      snp_file: snp_files
      sift_file: sift_files
      populations: populations
      step: step
    out:
    - overlap_files
    - freq_files
    - freq_summaries
    scatter:
    - snp_file
    - sift_file
    scatterMethod: dotproduct
