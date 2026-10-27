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

baseCommand: [ mDiffFit ]
inputs:
  in_1_fits:
    type: File
    inputBinding:
      position: 4
  in_2_fits:
    type: File
    inputBinding:
      position: 5
  out_name:
    type: string 
    inputBinding:
      position: 6
  template_hdr:
    type: File
    inputBinding:
      position: 7
  statusfile:
    type: string 
    inputBinding:
      position: 3
      prefix: -s
  debug:
    type: boolean 
    default: true
    inputBinding:
      position: 2
      prefix: -d
stdout: mDiffFit.out
outputs:
  status_fits:
    type: File
    outputBinding:
      glob: "$(inputs.statusfile)"
  log_out: 
    type: stdout
  return_code:
    type: int
    outputBinding:
      outputEval: $(runtime.exitCode)
successCodes: [0, 1]
