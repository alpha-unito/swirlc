cwlVersion: v1.2
class: CommandLineTool

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
s:programmingLanguage: Bash

requirements:
  InitialWorkDirRequirement:
    listing: $(inputs.individuals)

inputs:
  script:
    type: File
    inputBinding:
      position: 0
  chromosome:
    type: int
    inputBinding:
      position: 1
  individuals:
    type: File[]
    inputBinding:
      position: 2

outputs:
  output_file:
    type: File
    outputBinding:
      glob: "chr$(inputs.chromosome)n.tar.gz"
