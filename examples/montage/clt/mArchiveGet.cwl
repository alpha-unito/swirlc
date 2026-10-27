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
  NetworkAccess:
    networkAccess: true
baseCommand: [ mArchiveGet ]
arguments:
- position: 2
  valueFrom: "$(inputs.data.file.replace(/.gz$/, ''))"

inputs:
  data:
    type: 
      type: record
      fields:
        file: 
          type: string
        url: 
          type: string
          inputBinding:
            position: 1
outputs:
  image_fits:
    type: File 
    outputBinding:
      glob: "$(inputs.data.file.replace(/.gz$/, ''))"

