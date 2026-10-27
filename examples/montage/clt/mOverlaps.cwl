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

baseCommand: [ mOverlaps ]
arguments:
- position: 2
  valueFrom: "$(inputs.band_id)-diff.tbl"
inputs:
  raw_tbl: 
    type: File 
    inputBinding: 
        position: 1
  band_id: int 
outputs:
  diff_tbl:
    type: File
    outputBinding:
      glob: "$(inputs.band_id)-diff.tbl"
