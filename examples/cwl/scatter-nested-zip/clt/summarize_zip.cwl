cwlVersion: v1.2
class: CommandLineTool

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/summarize_zip.py
        entry:
          $include: ../scripts/summarize_zip.py

baseCommand: [python3, scripts/summarize_zip.py]

inputs:
  zip_name:
    type: string
    inputBinding:
      prefix: -z
      position: 1
  infos:
    type: File[]
    inputBinding:
      prefix: -i
      position: 2

outputs:
  zip_summary:
    type: File
    outputBinding:
      glob: zip_summary.txt
