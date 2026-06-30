cwlVersion: v1.2
class: Workflow

inputs:
  word:
    type: string
  count:
    type: int
  tag:
    type: string?

outputs:
  step1_result:
    type: string
    outputSource: step1/command_line

  step2_result:
    type: string
    outputSource: step2/command_line

steps:
  step1:
    run: tool.cwl
    in:
      first: word
      second: word
      times: count
      label: tag
    out: [command_line]

  step2:
    run: tool.cwl
    in:
      first: step1/command_line
      second: word
      times: count
    out: [command_line]
