cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}
inputs:
  samples: File[]
outputs:
  results:
    type: File[]
    outputSource: process_items/result
steps:
  process_items:
    run: item.cwl
    in:
      sample: samples
    out: [result]
    scatter: sample
