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

baseCommand: [ "python", "generate_region_hdr.py" ]
hints:
  - class: DockerRequirement
    dockerPull: docker.io/python:3-slim
inputs:
  center:
    type: string
    inputBinding:
      position: 1
  degrees:
    type: float 
    inputBinding:
      position: 2
outputs:
  region:
    type: File 
    outputBinding:
      glob: "region.hdr"
  region_oversized:
    type: File 
    outputBinding:
      glob: "region-oversized.hdr"
requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: 'generate_region_hdr.py' 
        entry: |
          import sys
          center = sys.argv[1]
          degrees = sys.argv[2]
          (crval1, crval2) = center.split()
          crval1 = float(crval1)
          crval2 = float(crval2)

          cdelt = 0.000277778
          naxis = int((float(degrees) / cdelt) + 0.5)
          crpix = (naxis + 1) / 2.0

          with open('region.hdr', 'w') as f:
            f.write('SIMPLE  = T\n')
            f.write('BITPIX  = -64\n')
            f.write('NAXIS   = 2\n')
            f.write('NAXIS1  = %d\n' %(naxis))
            f.write('NAXIS2  = %d\n' %(naxis))
            f.write('CTYPE1  = \'RA---TAN\'\n')
            f.write('CTYPE2  = \'DEC--TAN\'\n')
            f.write('CRVAL1  = %.6f\n' %(crval1))
            f.write('CRVAL2  = %.6f\n' %(crval2))
            f.write('CRPIX1  = %.6f\n' %(crpix))
            f.write('CRPIX2  = %.6f\n' %(crpix))
            f.write('CDELT1  = %.9f\n' %(-cdelt))
            f.write('CDELT2  = %.9f\n' %(cdelt))
            f.write('CROTA2  = %.6f\n' %(0.0))
            f.write('EQUINOX = %d\n' %(2000))
            f.write('END\n')

          # we also need an oversized region which will be used in the first part of the 
          # workflow to get the background correction correct
          with open('region-oversized.hdr', 'w') as f:
            f.write('SIMPLE  = T\n')
            f.write('BITPIX  = -64\n')
            f.write('NAXIS   = 2\n')
            f.write('NAXIS1  = %d\n' %(naxis + 3000))
            f.write('NAXIS2  = %d\n' %(naxis + 3000))
            f.write('CTYPE1  = \'RA---TAN\'\n')
            f.write('CTYPE2  = \'DEC--TAN\'\n')
            f.write('CRVAL1  = %.6f\n' %(crval1))
            f.write('CRVAL2  = %.6f\n' %(crval2))
            f.write('CRPIX1  = %.6f\n' %(crpix + 1500))
            f.write('CRPIX2  = %.6f\n' %(crpix + 1500))
            f.write('CDELT1  = %.9f\n' %(-cdelt))
            f.write('CDELT2  = %.9f\n' %(cdelt))
            f.write('CROTA2  = %.6f\n' %(0.0))
            f.write('EQUINOX = %d\n' %(2000))
            f.write('END\n')
            f.close()
