cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/final_summary.py
        entry:
          $include: ../scripts/final_summary.py

baseCommand: [python3, scripts/final_summary.py]

inputs:
  summaries:
    type: File[]
    inputBinding:
      prefix: -s
      position: 1

outputs:
  report:
    type: File
    outputBinding:
      glob: final_report.txt
