cwlVersion: v1.2
class: ExpressionTool

requirements:
  InlineJavascriptRequirement: {}

inputs:
  count: int

outputs:
  items: int[]

expression: |
  ${
    var arr = [];
    for (var i = 1; i <= inputs.count; i++) {
      arr.push(i);
    }
    return {"items": arr};
  }
