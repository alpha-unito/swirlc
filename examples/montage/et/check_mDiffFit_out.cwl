cwlVersion: v1.2
class: ExpressionTool

$namespaces:
  s: https://schema.org/

$schemas:
 - https://schema.org/version/latest/schemaorg-current-http.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0009-0009-2600-613X
    s:email: mailto:alberto.mulone@unito.it
    s:name: Alberto Mulone
  - class: s:Person
    s:identifier: https://orcid.org/0000-0001-9290-2017
    s:email: mailto:iacopo.colonnelli@unito.it
    s:name: Iacopo Colonnelli

s:codeRepository: https://github.com/alpha-unito/cwl-montage-workflow
s:dateCreated: "2025-12-01"
s:license: https://spdx.org/licenses/Apache-2.0

requirements:
  InlineJavascriptRequirement: {}
inputs:
  return_code:
    type: int
  log_out: 
    type: File
    loadContents: true
outputs: 
  is_valid:
    type: boolean
expression: |
  ${
    var is_valid = true;
    if (inputs.log_out.contents.includes("[Images don't overlap]")) {
      is_valid = false;
    } else {
      throw new Error(inputs.log_out.contents);
    }
    return { "is_valid": is_valid };
  }