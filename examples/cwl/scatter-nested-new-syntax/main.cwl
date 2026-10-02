cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}
inputs:
  groups:
    type:
      type: array
      items:
        type: array
        items:
          type: array
          items: string
  prefix: string
  labels:
    type:
      type: array
      items: string
outputs:
  rendered:
    type:
      type: array
      items:
        type: array
        items:
          type: array
          items: string
    outputSource: outer/rendered
  counts:
    type:
      type: array
      items:
        type: array
        items:
          type: array
          items: int
    outputSource: outer/counts
steps:
  outer:
    run:
      class: Workflow
      requirements:
        ScatterFeatureRequirement: {}
        SubworkflowFeatureRequirement: {}
      inputs:
        group:
          type:
            type: array
            items:
              type: array
              items: string
        prefix: string
        labels:
          type:
            type: array
            items: string
      outputs:
        rendered:
          type:
            type: array
            items:
              type: array
              items: string
          outputSource: middle/rendered
        counts:
          type:
            type: array
            items:
              type: array
              items: int
          outputSource: middle/counts
      steps:
        middle:
          run:
            class: Workflow
            requirements:
              ScatterFeatureRequirement: {}
              SubworkflowFeatureRequirement: {}
            inputs:
              batch:
                type:
                  type: array
                  items: string
              prefix: string
              labels:
                type:
                  type: array
                  items: string
            outputs:
              rendered:
                type:
                  type: array
                  items: string
                outputSource: leaf/rendered
              counts:
                type:
                  type: array
                  items: int
                outputSource: leaf/count
            steps:
              leaf:
                run:
                  class: ExpressionTool
                  requirements:
                    InlineJavascriptRequirement: {}
                  inputs:
                    item: string
                    prefix: string
                    labels:
                      type:
                        type: array
                        items: string
                  outputs:
                    rendered: string
                    count: int
                  expression: '${ return {rendered: inputs.prefix + inputs.item +
                    ":" + inputs.labels.join(","), count: inputs.labels.length}; }'
                scatter: item
                in:
                  item: batch
                  prefix: prefix
                  labels: labels
                out:
                - rendered
                - count
          scatter: batch
          in:
            batch: group
            prefix: prefix
            labels: labels
          out:
          - rendered
          - counts
    scatter: group
    in:
      group: groups
      prefix: prefix
      labels: labels
    out:
    - rendered
    - counts
