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

inputs:
  band_id: int
  in_1_fits: File
  in_2_fits: File
  diff_tbl: File
  region_oversized: File
  mProject_prefix: string

outputs: 
  status_fits: 
    type: File?
    outputSource: mDiffFit/status_fits
  is_valid:
    type: boolean
    outputSource: check_mDiffFit_out/is_valid

steps:
  get_diff:
    run: clt/get_diff.cwl 
    in:
      in_1_fits: in_1_fits
      in_2_fits: in_2_fits
      in_1_name: 
        valueFrom: "$(inputs.in_1_fits.basename)"
      in_2_name: 
        valueFrom: "$(inputs.in_2_fits.basename)"
      diff_tbl: diff_tbl
      prefix_project: mProject_prefix
    out: [diff_name]

  mDiffFit:
    run: clt/mDiffFit.cwl
    in:
      band_id: band_id
      in_1_fits: in_1_fits
      in_2_fits: in_2_fits
      diff_name: get_diff/diff_name
      out_name:
        valueFrom: "$(inputs.band_id)-$(inputs.diff_name)"
      template_hdr: region_oversized
      statusfile:
        valueFrom: "$(inputs.band_id)-fit.$(inputs.diff_name.replace(/(diff.|.fits)/g, '')).txt"
    when: "$(inputs.diff_name !== '')"
    out: [status_fits, log_out, return_code]

  check_mDiffFit_out:
    run: et/check_mDiffFit_out.cwl 
    in: 
      return_code: mDiffFit/return_code
      log_out: mDiffFit/log_out
    out: [is_valid]
    when: "$(Number.isInteger(inputs.return_code) && inputs.return_code !== 0)"