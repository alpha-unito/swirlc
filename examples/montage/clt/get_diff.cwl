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

baseCommand: [ "python", "generate.py" ]
hints:
  - class: DockerRequirement
    dockerPull: opencadc/astropy:3.9-slim
inputs:
  in_1_name: 
    type: string
    inputBinding:
      position: 1
  in_2_name: 
    type: string
    inputBinding:
      position: 2
  diff_tbl: 
    type: File
    inputBinding:
      position: 3
  prefix_project:
    type: string 
    inputBinding: 
      position: 4
outputs:
  diff_name: string
requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: 'generate.py' 
        entry: |
          import sys
          import json
          from astropy.io import ascii
          data = ascii.read(sys.argv[3])
          out = {}
          for row in data:
            if sys.argv[1] == f"{sys.argv[4]}{row['plus']}" and sys.argv[2] == f"{sys.argv[4]}{row['minus']}":
              out["diff_name"] = row["diff"]
              break
          if not out:
            out["diff_name"] = ""
          with open('cwl.output.json', 'w') as f:
            json.dump(out, f)




