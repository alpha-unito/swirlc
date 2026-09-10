cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/compute_item.py
        entry:
          $include: ../scripts/compute_item.py

baseCommand: [python3, scripts/compute_item.py]

inputs:
  group:
    type: File
    inputBinding:
      prefix: -g
      position: 1
  item:
    type: int
    inputBinding:
      prefix: -i
      position: 2

outputs:
  output_file:
    type: File
    outputBinding:
      glob: item_result.txt
