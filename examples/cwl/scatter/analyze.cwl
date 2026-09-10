#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/analyze.py
        entry:
          $include: scripts/analyze.py

baseCommand: [python3, scripts/analyze.py]

inputs:
  inputs:
    type: File[]
    inputBinding:
      prefix: -i
      position: 1
  output_filename:
    type: string
    default: "analysis_report.txt"
    inputBinding:
      prefix: -o
      position: 2

outputs:
  report:
    type: File
    outputBinding:
      glob: $(inputs.output_filename)
