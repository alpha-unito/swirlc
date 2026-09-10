cwlVersion: v1.2
class: ExpressionTool

$namespaces:
  s: https://schema.org/

$schemas:
 - https://schema.org/version/latest/schemaorg-current-http.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0001-9290-2017
    s:email: mailto:iacopo.colonnelli@unito.it
    s:name: Iacopo Colonnelli

s:codeRepository: https://github.com/alpha-unito/cwl-1000genome-workflow
s:dateCreated: "2022-09-28"
s:license: https://spdx.org/licenses/Apache-2.0
s:programmingLanguage: JavaScript

requirements:
  InlineJavascriptRequirement: {}

inputs:
  step: int
  total: int

outputs:
  counters: int[]
  stops: int[]

expression: |
  ${
    var length = Math.ceil(inputs.total / inputs.step);
    var current = 0;
    var counters = new Array(length);
    var stops = new Array(length);

    for (var i = 0; i < length; i++) {
      counters[i] = current + 1;
      current += inputs.step;
      stops[i] = Math.min(current, inputs.total);
    }

    return {"counters": counters, "stops": stops};
  }
