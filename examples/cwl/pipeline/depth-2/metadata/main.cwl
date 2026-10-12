cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}
inputs:
  samples:
    type:
      type: array
      items:
        type: array
        items: File
outputs:
  results:
    type:
      type: array
      items:
        type: array
        items: string
    outputSource: process_batches/results
steps:
  process_batches:
    run: batch.cwl
    in:
      samples: samples
    out: [results]
    scatter: samples
