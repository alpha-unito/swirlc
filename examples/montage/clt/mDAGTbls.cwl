cwlVersion: v1.2
class: CommandLineTool

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

baseCommand: [ mDAGTbls ]
arguments:
  - position: 3
    valueFrom: "$(inputs.band_id)-raw.tbl"
  - position: 3
    valueFrom: "$(inputs.band_id)-projected.tbl"
  - position: 3
    valueFrom: "$(inputs.band_id)-corrected.tbl"
inputs:
  images_tbl:
    type: File
    inputBinding:
      position: 1
  region:
    type: File 
    inputBinding:
      position: 2
  band_id:
    type: int
outputs:
  raw_tbl:
    type: File
    outputBinding:
      glob: "$(inputs.band_id)-raw.tbl"
  projected_tbl:
    type: File
    outputBinding:
      glob: "$(inputs.band_id)-projected.tbl"
  corrected_tbl:
    type: File
    outputBinding:
      glob: "$(inputs.band_id)-corrected.tbl"
