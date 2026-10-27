cwlVersion: v1.2  
class: Workflow

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
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}

inputs:
  center: string
  degrees: float
  bands: 
    type:
      type: array
      items:
        type: record
        fields:
          bid: int
          survey: string
          band: string
          color: string
  n_iter: int

outputs:
  config_file:
    type: File 
    outputSource: generate_config/config_file

steps:
  regions:
    run: clt/generate_region.cwl
    in: 
      center: center
      degrees: degrees
    out: [region, region_oversized]

  dataset:
    run: dataset.cwl
    in:
      center: center
      degrees: degrees
      band: bands
      n_iter: n_iter
      region: regions/region
      region_oversized: regions/region_oversized
    out: [diff_tbl, corrected_tbl, image_fits, images_tbl, projected_tbl, statfile]
    scatter: band

  generate_config:
    run: clt/generate_config.cwl
    in:
      bands: bands
      diff_tbl: dataset/diff_tbl
      corrected_tbl: dataset/corrected_tbl
      images_tbl: dataset/images_tbl
      image_fits: dataset/image_fits
      n_iter: n_iter
      projected_tbl: dataset/projected_tbl
      statfile: dataset/statfile
      region: regions/region
      region_oversized: regions/region_oversized
    out: [config_file]