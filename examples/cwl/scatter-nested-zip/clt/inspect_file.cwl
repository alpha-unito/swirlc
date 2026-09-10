cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/inspect_file.py
        entry:
          $include: ../scripts/inspect_file.py

baseCommand: [python3, scripts/inspect_file.py]

inputs:
  target_file:
    type: File
    inputBinding:
      prefix: -f
      position: 1

outputs:
  info:
    type: File
    outputBinding:
      glob: file_info.txt
