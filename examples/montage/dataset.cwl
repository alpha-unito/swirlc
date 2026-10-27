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

inputs:
  center: string
  degrees: float
  n_iter: int
  band:
    type:
      type: record
      fields:
        bid: int
        survey: string
        band: string
        color: string
  region: File
  region_oversized: File

outputs: 
  diff_tbl:
    type: File 
    outputSource: mOverlaps/diff_tbl
  corrected_tbl:
    type: File 
    outputSource: mDAGTbls/corrected_tbl
  image_fits:
    type: File[]
    outputSource: mArchiveGet/image_fits
  images_tbl:
    type: File 
    outputSource: mArchiveList/images_tbl
  projected_tbl: 
    type: File 
    outputSource: mDAGTbls/projected_tbl
  statfile:
    type: File 
    outputSource: generate_statfile/statfile
steps:
  mArchiveList:
    run: clt/mArchiveList.cwl
    in:
      band: band
      object_location: center
      degrees: degrees
      width: 
        valueFrom: "$(inputs.degrees * 1.42)" 
      height: 
        valueFrom: "$(inputs.degrees * 1.42)" 
      outfile:
        valueFrom: "$(inputs.band.bid)-images.tbl"
    out: [ images_tbl ]

  mDAGTbls:
    run: clt/mDAGTbls.cwl
    in:
      images_tbl: mArchiveList/images_tbl
      region: region_oversized
      band: band
      band_id:
        valueFrom: "$(inputs.band.bid)"
    out: [ raw_tbl, projected_tbl, corrected_tbl ]
  
  mOverlaps:
    run: clt/mOverlaps.cwl
    in:
      raw_tbl: mDAGTbls/raw_tbl
      band: band
      band_id:
        valueFrom: "$(inputs.band.bid)"
    out: [ diff_tbl ]

  generate_statfile:
    run: clt/generate_statfile.cwl 
    in:
      diff_tbl: mOverlaps/diff_tbl
      band: band
      band_id:
        valueFrom: "$(inputs.band.bid)"
    out: [ statfile ]

  retrieve_urls:
    run: clt/retrieve_urls.cwl
    in: 
      images_tbl: mArchiveList/images_tbl
    out: [ urls ]

  mArchiveGet:
    run: clt/mArchiveGet.cwl 
    in:
      data: retrieve_urls/urls 
    out: [ image_fits ]
    scatter: data 
