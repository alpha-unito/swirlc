#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

baseCommand: ["/bin/sh", "-c"]

requirements:
  - class: InlineJavascriptRequirement

arguments:
  - valueFrom: "printf '%s' '$(inputs.text)' | tr -s ' '"

inputs:
  text:
    type: string

outputs:
  result:
    type: string
    outputBinding:
      glob: stdout.txt
      loadContents: true
      outputEval: $(self[0].contents.trim())

stdout: stdout.txt
