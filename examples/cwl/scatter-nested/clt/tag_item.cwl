cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/tag_item.py
        entry:
          $include: ../scripts/tag_item.py

baseCommand: [python3, scripts/tag_item.py]

inputs:
  summary:
    type: File
    inputBinding:
      prefix: -s
      position: 1
  tag:
    type: File
    inputBinding:
      prefix: -t
      position: 2

outputs:
  output_file:
    type: File
    outputBinding:
      glob: tagged_result.txt
