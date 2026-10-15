cwlVersion: v1.2
class: ExpressionTool
requirements:
  InlineJavascriptRequirement: {}
inputs:
  snp_file: File
outputs:
  chromosome: string
expression: '${ return {chromosome: inputs.snp_file.nameroot.split("_")[0]}; }'
