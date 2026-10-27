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
  outs_fits: File[]
  bands: 
    type:
      type: array
      items:
        type: record
        fields:
          bid: int
          corrected_tbl: File
          diff_tbl: File
          projected_tbl: File
          statfile: File
          images_tbl: File
          images_fits: File[]
          color: string
outputs: 
  red: File 
  green: File
  blue: File
expression: |
  ${
    var red = null;
    var green = null;
    var blue = null;

    if (inputs.outs_fits.length !== inputs.bands.length) {
      throw new Error("Input lists must have the same length");
    }

    for (var i = 0; i < inputs.outs_fits.length; i++) {
      if (red === null && inputs.bands[i].color === "red") {
        red = inputs.outs_fits[i];
      } else if (green === null && inputs.bands[i].color === "green") {
        green = inputs.outs_fits[i];
      } else if (blue === null && inputs.bands[i].color === "blue") {
        blue = inputs.outs_fits[i];
      } else {
        throw new Error("Unexpected color " + inputs.bands[i].color + " at position " + i);
      }
    }

    return { "red": red, "green": green, "blue": blue };
  }