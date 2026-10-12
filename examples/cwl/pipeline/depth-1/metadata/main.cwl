cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
inputs:
  samples: File[]
outputs:
  results:
    type: string[]
    outputSource: process_items/result
steps:
  process_items:
    run: ../../tools/render.cwl
    in:
      sample: samples
    out: [result]
    scatter: sample
