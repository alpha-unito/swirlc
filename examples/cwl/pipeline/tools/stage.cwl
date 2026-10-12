cwlVersion: v1.2
class: CommandLineTool
baseCommand: [cp, -T]
inputs:
  sample:
    type: File
    inputBinding:
      position: 1
  destination:
    type: string
    default: staged.txt
    inputBinding:
      position: 2
outputs:
  result:
    type: File
    outputBinding:
      glob: staged.txt
