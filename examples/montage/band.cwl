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
  band_id: int
  corrected_tbl: File
  diff_tbl: File 
  images_fits: File[]
  images_tbl: File
  n_iter: int
  projected_tbl: File
  region: File 
  region_oversized: File
  statfile: File
  mProject_prefix:
    type: string 
    default: "p"
  mBackground_prefix:
    type: string 
    default: "c"
outputs: 
  out_fits: 
    type: File 
    outputSource: mAdd/out_fits
  out_png: 
    type: File
    outputSource: mViewer/out_png
steps:
  mProject:
    run: clt/mProject.cwl
    in:
      template: region_oversized
      in_fits: images_fits
      mProject_prefix: mProject_prefix
      out_name:
        valueFrom: "$(inputs.mProject_prefix)$(inputs.in_fits.nameroot)"
    out: [out_fits]
    scatter: in_fits

  wdiff:
    in:
      band_id: band_id
      mProject_prefix: mProject_prefix
      in_1_fits: mProject/out_fits
      in_2_fits: mProject/out_fits
      diff_tbl: diff_tbl
      region_oversized: region_oversized
    out: [status_fits]
    run: 
      class: Workflow
      inputs:
        band_id: int
        in_1_fits: File[]
        in_2_fits: File[]
        diff_tbl: File
        mProject_prefix: string
        region_oversized: File
      outputs:
        status_fits:
          type: File[]
          outputSource: diff/status_fits
          pickValue: all_non_null
      steps:
        diff:
          run: diff.cwl
          in:
            band_id: band_id
            mProject_prefix: mProject_prefix
            in_1_fits: in_1_fits
            in_2_fits: in_1_fits
            diff_tbl: diff_tbl
            region_oversized: region_oversized
          out: [status_fits]
          scatter: [in_1_fits,in_2_fits]
          scatterMethod: flat_crossproduct

  mConcatFit:
    run: clt/mConcatFit.cwl
    in:
      statfiles_tbl: statfile
      band_id: band_id 
      fits_tbl: 
        valueFrom: "$(inputs.band_id)-fits.tbl"
      statutes: wdiff/status_fits
      statdir: 
        valueFrom: "${return {'class': 'Directory', 'basename': 'data', 'listing': inputs.statutes}}"
    out: [ out_fits ]

  mBgModel:
    run: clt/mBgModel.cwl 
    in:
      images_tbl: images_tbl
      fits_tbl: mConcatFit/out_fits
      n_iter: n_iter
      band_id: band_id
      out_name:
        valueFrom: "$(inputs.band_id)-corrections.tbl"
    out: [corrections_tbl]

  mBackground:
    run: clt/mBackground.cwl
    in:
      in_fits: mProject/out_fits
      mBackground_prefix: mBackground_prefix
      out_name: 
        valueFrom: "$(inputs.mBackground_prefix)$(inputs.in_fits.nameroot.substring(1))"
      projected_tbl: projected_tbl
      corrections_tbl: mBgModel/corrections_tbl
    out: [out_fits]
    scatter: in_fits
  
  mImgtbl:
    run: clt/mImgtbl.cwl
    in: 
      cfits: mBackground/out_fits
      in_dir: 
        valueFrom: "${return {'class': 'Directory', 'basename': 'data', 'listing': inputs.cfits}}"
      out_name: 
        valueFrom: "$(inputs.band_id)-updated.corrected.tbl"
      band_id: band_id
      imglist: corrected_tbl
    out: [out_table]

  mAdd:
    run: clt/mAdd.cwl
    in:
      image: mImgtbl/out_table
      template: region
      band_id: band_id
      out_name: 
        valueFrom: "$(inputs.band_id)-mosaic"
      in_fits: mBackground/out_fits
    out: [out_fits]

  mViewer:
    run: clt/mViewer.cwl 
    in:
      color_table:
        default: 1
      gray_file: mAdd/out_fits
      gray_min_range:
        default: "-1s"
      gray_max_range:
        default: "max"
      gray_distribution:
        default: "gaussian"
      png_out_name:
        valueFrom: "$(inputs.gray_file.nameroot).png"
    out: [out_png]
