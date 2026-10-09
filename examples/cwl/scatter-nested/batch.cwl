cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
inputs:
  items: string[]
outputs:
  results:
    type: File[]
    outputSource: echo_item/result
steps:
  echo_item:
    run: echo.cwl
    in:
      item: items
    out: [result]
    scatter: item
