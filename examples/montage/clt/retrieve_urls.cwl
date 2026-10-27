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

baseCommand: [ "python", "extract.py" ]
hints:
  - class: DockerRequirement
    dockerPull: opencadc/astropy:3.9-slim
inputs:
  images_tbl:
    type: File
    inputBinding:
      position: 1
outputs:
  urls:
    type: 
      type: array 
      items:
        type: record
        fields:
          file: string
          url: string
requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: 'extract.py' 
        entry: |
          import sys
          import json
          from astropy.io import ascii
          data = []
          for row in ascii.read(sys.argv[1]):
            data.append({'file': row['file'], 'url': row['URL']})
          with open('cwl.output.json', 'w') as f:
              json.dump({"urls": data}, f)
    
    

