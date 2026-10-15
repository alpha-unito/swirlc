cwlVersion: v1.2
class: CommandLineTool
requirements:
  InlineJavascriptRequirement: {}
baseCommand: python3
arguments:
- position: 1
  valueFrom: frequency
- position: 6
  prefix: --label
  valueFrom: $(inputs.chromosome + " " + inputs.population.nameroot)
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
  population:
    type: File
    inputBinding:
      position: 4
      prefix: --population
      valueFrom: $(self.nameroot)
  sift_file:
    type: File
    inputBinding:
      position: 5
      prefix: --sift
stdout: $(inputs.chromosome + "-" + inputs.population.nameroot + "-frequency.txt")
outputs:
  output_file:
    type: File
    outputBinding:
      glob: $(inputs.chromosome + "-" + inputs.population.nameroot + "-frequency.txt")
  summary:
    type: string
    outputBinding:
      glob: $(inputs.chromosome + "-" + inputs.population.nameroot + "-frequency.txt")
      loadContents: true
      outputEval: $(self[0].contents.trim())
