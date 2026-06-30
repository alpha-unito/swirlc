cwlVersion: v1.2
class: Workflow

inputs:
  text:
    type: string

outputs:
  processed:
    type: string
    outputSource: step_upper/result

steps:
  step_trim:
    run: trim.cwl
    in:
      text: text
    out: [result]

  step_upper:
    run: upper.cwl
    in:
      text: step_trim/result
    out: [result]
