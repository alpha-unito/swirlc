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
  InlineJavascriptRequirement: {}
  ScatterFeatureRequirement: {}
  StepInputExpressionRequirement: {}
  SubworkflowFeatureRequirement: {}

inputs:
  bands: 
    type:
      type: array
      items:
        type: record
        fields:
          bid: int
          corrected_tbl: File
          diff_tbl: File
          projected_tbl: File
          statfile: File
          images_tbl: File
          images_fits: File[]
          color: string
  region: File 
  region_oversized: File
  n_iter: int

outputs: 
  grey_pngs: 
    type: File[]
    outputSource: band/out_png
  color_png:
    type: File?
    outputSource: color_image/out_png

steps:
  band:
    run: band.cwl
    in:
      band: bands
      band_id: 
        valueFrom: $(inputs.band.bid)
      corrected_tbl:
        valueFrom: $(inputs.band.corrected_tbl)
      images_fits: 
        valueFrom: $(inputs.band.images_fits)
      diff_tbl: 
        valueFrom: $(inputs.band.diff_tbl)
      statfile: 
        valueFrom: $(inputs.band.statfile)
      projected_tbl: 
        valueFrom: $(inputs.band.projected_tbl)
      images_tbl: 
        valueFrom: $(inputs.band.images_tbl)
      region: region
      region_oversized: region_oversized
      n_iter: n_iter
    out: [out_fits, out_png]
    scatter: band

  get_rgb:
    run: et/get_rgb.cwl 
    in:
      outs_fits: band/out_fits
      bands: bands
    out: [red, green, blue]

  color_image:
    run: clt/mViewer.cwl 
    in: 
      red_file: get_rgb/red
      red_min_range: 
        default: -0.5s
      red_max_range: 
        default: max
      red_distribution: 
        default: gaussian-log
      green_file: get_rgb/green
      green_min_range: 
        default: -0.5s
      green_max_range: 
        default: max
      green_distribution: 
        default: gaussian-log
      blue_file: get_rgb/blue
      blue_min_range: 
        default: -0.5s
      blue_max_range: 
        default: max
      blue_distribution: 
        default: gaussian-log
      png_out_name:
        default: mosaic-color.png
    when: $(inputs.red_file !== null && inputs.green_file !== null && inputs.blue_file !== null)
    out: [ out_png ]