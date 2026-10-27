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
  diff_tbl:
    type: File
    inputBinding:
      position: 1
  band_id:
    type: int 
    inputBinding: 
      position: 2
outputs:
  statfile:
    type: File 
    outputBinding:
      glob: "$(inputs.band_id)-stat.tbl"
requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: 'generate.py' 
        entry: |
          import re
          import sys
          from astropy.io import ascii
          t = ascii.read(sys.argv[1])
          band_id = sys.argv[2]
          # make sure we have a wide enough column
          t['stat'] = ' '*66
          for row in t:
              base_name = re.sub('(diff\.|\.fits.*)', '', row['diff'])
              row['stat'] = '%s-fit.%s.txt' %(band_id, base_name)
          ascii.write(t, '%s-stat.tbl' %(band_id), format='ipac')