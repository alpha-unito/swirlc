cwlVersion: v1.2
class: CommandLineTool
requirements:
  InlineJavascriptRequirement: {}
baseCommand: python3
arguments:
- position: 1
  valueFrom: individuals_merge
inputs:
  script:
    type: File
    inputBinding:
      position: 0
  chromosome:
    type: string
    inputBinding:
      position: 2
      prefix: --chromosome
  individuals:
    type: File[]
    inputBinding:
      position: 3
      prefix: --parts
stdout: $(inputs.chromosome + "-individuals_merge.txt")
outputs:
  output_file:
    type: File
    outputBinding:
      glob: $(inputs.chromosome + "-individuals_merge.txt")
