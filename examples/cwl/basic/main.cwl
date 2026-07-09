cwlVersion: v1.2
class: Workflow

inputs:
  greeting:
    type: string

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
      greeting: greeting
    out: [command_line]

  step2:
    run: tool.cwl
    in:
      previous: step1/command_line
      greeting: greeting
    out: [command_line]
