#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

baseCommand: >-
  sh -c 'if [ "$#" -eq 1 ]; then echo "$1 from $(hostname)"; else printf "%s\n%s from %s\n" "$1" "$2" "$(hostname)"; fi' _

inputs:
  previous:
    type: string?
    inputBinding:
      position: 1

  greeting:
    type: string
    inputBinding:
      position: 2

outputs:
  command_line:
    type: string
    outputBinding:
      glob: stdout.txt
      loadContents: true
      outputEval: $(self[0].contents.trim())

stdout: stdout.txt
