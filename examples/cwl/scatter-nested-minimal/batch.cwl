cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}

inputs:
  batch: string[]

outputs:
  echoed:
    type: File[]
    outputSource: echo_item/output

steps:
  echo_item:
    run: clt/echo.cwl
    scatter: item
    in:
      item: batch
    out: [output]
