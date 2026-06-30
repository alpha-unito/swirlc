#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

baseCommand: echo

requirements:
  - class: InlineJavascriptRequirement

inputs:
  first:
    type: string
    inputBinding:
      position: 1

  second:
    type: string
    inputBinding:
      position: 2

  times:
    type: int
    inputBinding:
      prefix: --times
      position: 0

  label:
    type: string?
    inputBinding:
      prefix: --label
      position: 3

  verbose:
    type: boolean?
    inputBinding:
      prefix: --verbose
      position: 4

outputs:
  command_line:
    type: string
    outputBinding:
      glob: stdout.txt
      loadContents: true
      outputEval: $(self[0].contents.trim())

stdout: stdout.txt
