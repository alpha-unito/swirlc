cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
inputs:
  samples:
    type:
      type: array
      items: File
outputs:
  results:
    type:
      type: array
      items: string
    outputSource: process_items/result
steps:
  process_items:
    run: ../../tools/render.cwl
    in:
      sample: samples
    out: [result]
    scatter: sample
