cwlVersion: v1.2
class: CommandLineTool
baseCommand: echo
inputs:
  letter:
    type: string
    inputBinding:
      position: 1
  number:
    type: string
    inputBinding:
      position: 2
stdout: result.txt
outputs:
  result:
    type: File
    outputBinding:
      glob: result.txt
