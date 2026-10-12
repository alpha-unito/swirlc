cwlVersion: v1.2
class: CommandLineTool
requirements:
  InlineJavascriptRequirement: {}
baseCommand: printf
arguments:
  - position: 1
    valueFrom: $("item=%s\n")
inputs:
  sample:
    type: File
    inputBinding:
      position: 2
      valueFrom: $(self.nameroot)
stdout: result.txt
outputs:
  result:
    type: string
    outputBinding:
      glob: result.txt
      loadContents: true
      outputEval: $(self[0].contents.trim())
