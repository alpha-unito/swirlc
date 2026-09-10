cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/final_report.py
        entry:
          $include: ../scripts/final_report.py

baseCommand: [python3, scripts/final_report.py]

inputs:
  summaries:
    type: File[]
    inputBinding:
      prefix: -s
      position: 1
  tagged:
    type:
      type: array
      items:
        type: array
        items: File
    inputBinding:
      prefix: -t
      position: 2

outputs:
  report:
    type: File
    outputBinding:
      glob: final_report.txt
