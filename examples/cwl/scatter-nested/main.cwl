cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}
inputs:
  batches:
    type:
      type: array
      items: string[]
outputs:
  results:
    type:
      type: array
      items: File[]
    outputSource: echo_batch/results
steps:
  echo_batch:
    run: batch.cwl
    in:
      items: batches
    out: [results]
    scatter: items
