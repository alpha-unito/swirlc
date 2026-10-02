cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
inputs:
  left: string[]
  right: string[]
outputs:
  joined:
    type: string[]
    outputSource: process/joined
steps:
  process:
    run:
      class: ExpressionTool
      requirements:
        InlineJavascriptRequirement: {}
      inputs:
        a: string
        b: string
      outputs:
        joined: string
      expression: '${ return {joined: inputs.a + ":" + inputs.b}; }'
    scatter:
    - a
    - b
    scatterMethod: dotproduct
    in:
      b: right
      a: left
    out:
    - joined
