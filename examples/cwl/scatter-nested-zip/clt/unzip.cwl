cwlVersion: v1.2
class: CommandLineTool

requirements:
  InlineJavascriptRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - entryname: scripts/unzip_archive.py
        entry:
          $include: ../scripts/unzip_archive.py

baseCommand: [python3, scripts/unzip_archive.py]

inputs:
  archive:
    type: File
    inputBinding:
      prefix: -z
      position: 1

outputs:
  extracted_files:
    type: File[]
    outputBinding:
      glob: "*"
      outputEval: |
        ${
          return self.filter(function(f) {
            return f.basename !== "scripts";
          });
        }
