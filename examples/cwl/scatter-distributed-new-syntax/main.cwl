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
  tagged:
    type: string[]
    outputSource: process/tagged
steps:
  left_source:
    run:
      class: ExpressionTool
      requirements:
        InlineJavascriptRequirement: {}
      inputs:
        items: string[]
      outputs:
        items: string[]
        tag: string
      expression: '${ return {items: inputs.items, tag: "tag:"}; }'
    in:
      items: left
    out:
    - items
    - tag
  right_source:
    run:
      class: ExpressionTool
      requirements:
        InlineJavascriptRequirement: {}
      inputs:
        items: string[]
      outputs:
        items: string[]
      expression: '${ return {items: inputs.items}; }'
    in:
      items: right
    out:
    - items
  process:
    run:
      class: ExpressionTool
      requirements:
        InlineJavascriptRequirement: {}
      inputs:
        a: string
        b: string
        tag: string
      outputs:
        joined: string
        tagged: string
      expression: '${ return {joined: inputs.a + ":" + inputs.b, tagged: inputs.tag
        + inputs.a}; }'
    scatter:
    - a
    - b
    scatterMethod: dotproduct
    in:
      b: right_source/items
      a: left_source/items
      tag: left_source/tag
    out:
    - joined
    - tagged
