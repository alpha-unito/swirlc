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
        items:
          type: array
          items: File
outputs:
  results:
    type:
      type: array
      items:
        type: array
        items:
          type: array
          items: File
    outputSource: process_groups/results
steps:
  process_groups:
    run: group.cwl
    in:
      samples: samples
    out: [results]
    scatter: samples
