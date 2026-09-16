cwlVersion: v1.2
class: CommandLineTool

baseCommand: echo
stdout: output.txt

inputs:
  item:
    type: string
    inputBinding:
      position: 1

outputs:
  output:
    type: File
    outputBinding:
      glob: output.txt
