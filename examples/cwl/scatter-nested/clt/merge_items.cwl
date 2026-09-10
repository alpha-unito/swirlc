cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/merge_items.py
        entry:
          $include: ../scripts/merge_items.py

baseCommand: [python3, scripts/merge_items.py]

inputs:
  inputs:
    type: File[]
    inputBinding:
      prefix: -i
      position: 1

outputs:
  output_file:
    type: File
    outputBinding:
      glob: group_summary.txt
