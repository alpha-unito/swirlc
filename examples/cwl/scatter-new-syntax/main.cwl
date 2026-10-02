#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}

inputs:
  items: string[]
  prefix: string
  labels: string[]

outputs:
  rendered:
    type: string[]
    outputSource: process/rendered
  invariant_counts:
    type: int[]
    outputSource: process/invariant_count

steps:
  process:
    scatter: item
    in:
      item: items
      prefix: prefix
      labels: labels
    out: [rendered, invariant_count]
    run:
      class: ExpressionTool
      requirements:
        InlineJavascriptRequirement: {}
      inputs:
        item: string
        prefix: string
        labels: string[]
      outputs:
        rendered: string
        invariant_count: int
      expression: |-
        ${
          return {
            rendered: inputs.prefix + inputs.item + ":" + inputs.labels.join(","),
            invariant_count: inputs.labels.length
          };
        }
