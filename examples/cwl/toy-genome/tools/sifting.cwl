cwlVersion: v1.2
class: CommandLineTool
requirements:
  InlineJavascriptRequirement: {}
baseCommand: python3
arguments:
- position: 1
  valueFrom: sifting
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
  input_file:
    type: File
    inputBinding:
      position: 3
      prefix: --input
stdout: $(inputs.chromosome + "-sifting.txt")
outputs:
  output_file:
    type: File
    outputBinding:
      glob: $(inputs.chromosome + "-sifting.txt")
