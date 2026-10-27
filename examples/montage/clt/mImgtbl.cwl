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

baseCommand: [ mImgtbl ]
inputs:
  in_dir:
    type: Directory
    inputBinding:
      position: 3
  out_name:
    type: string 
    inputBinding:
      position: 4
  imglist:
    type: File 
    inputBinding:
      position: 2
      prefix: -t
outputs:
  out_table:
    type: File 
    outputBinding:
      glob: "$(inputs.out_name)"

