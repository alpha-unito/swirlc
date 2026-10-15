cwlVersion: v1.2
class: CommandLineTool
requirements:
  InlineJavascriptRequirement: {}
baseCommand: python3
arguments:
- position: 1
  valueFrom: individuals
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
  counter:
    type: int
    inputBinding:
      position: 4
      prefix: --counter
  stop:
    type: int
    inputBinding:
      position: 5
      prefix: --stop
stdout: $(inputs.chromosome + "-individuals.txt")
outputs:
  output_file:
    type: File
    outputBinding:
      glob: $(inputs.chromosome + "-individuals.txt")
