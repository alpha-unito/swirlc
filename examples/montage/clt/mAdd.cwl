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

requirements: 
  InitialWorkDirRequirement:
    listing: 
      - entry: $(inputs.in_fits)
baseCommand: [ mAdd ]
arguments:
- position: 4
  valueFrom: "$(inputs.out_name).fits"
inputs:
  exact_size:
    type: boolean
    default: true
    inputBinding:
      position: 1
      prefix: -e
  image:
    type: File
    inputBinding:
      position: 2
  template:
    type: File 
    inputBinding:
      position: 3
  out_name:
    type: string
  in_fits:
    type: File[]
outputs:
  out_fits:
    type: File
    outputBinding:
      glob: "$(inputs.out_name).fits"
    secondaryFiles:
      - "$(inputs.out_name)_area.fits"

