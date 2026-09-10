#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/compute.py
        entry:
          $include: scripts/compute.py

baseCommand: [python3, scripts/compute.py]

inputs:
  id:
    type: File?
    inputBinding:
      prefix: --id
      position: 0
  file_a:
    type: File
    inputBinding:
      prefix: -a
      position: 1
  file_b:
    type: File
    inputBinding:
      prefix: -b
      position: 2
  output_filename:
    type: string
    default: "result.txt"
    inputBinding:
      prefix: -o
      position: 3

outputs:
  result:
    type: File
    outputBinding:
      glob: $(inputs.output_filename)
