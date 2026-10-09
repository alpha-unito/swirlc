cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
inputs:
  letters: string[]
  numbers: string[]
outputs:
  results:
    type: File[]
    outputSource: echo_pair/result
steps:
  echo_pair:
    run: echo.cwl
    in:
      letter: letters
      number: numbers
    out: [result]
    scatter: [letter, number]
    scatterMethod: dotproduct
