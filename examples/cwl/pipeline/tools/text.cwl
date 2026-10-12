cwlVersion: v1.2
class: CommandLineTool
requirements:
  InlineJavascriptRequirement: {}
baseCommand: [printf, '%s\n']
inputs:
  text:
    type: string
    inputBinding:
      position: 1
stdout: result.txt
outputs:
  result:
    type: string
    outputBinding:
      glob: result.txt
      loadContents: true
      outputEval: $(self[0].contents.trim())
