cwlVersion: v1.2
class: CommandLineTool
baseCommand: echo
inputs:
  item:
    type: string
    inputBinding:
      position: 1
stdout: result.txt
outputs:
  result:
    type: File
    outputBinding:
      glob: result.txt
