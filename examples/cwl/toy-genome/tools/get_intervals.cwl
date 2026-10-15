cwlVersion: v1.2
class: ExpressionTool
requirements:
  InlineJavascriptRequirement: {}
inputs:
  snp_file: File
  step: int
outputs:
  counters: int[]
  stops: int[]
expression: '${ var total = parseInt(inputs.snp_file.nameroot.split("_")[1]); var
  counters = []; var stops = []; for (var i = 1; i <= total; i += inputs.step) { counters.push(i);
  stops.push(Math.min(i + inputs.step - 1, total)); } return {counters: counters,
  stops: stops}; }'
