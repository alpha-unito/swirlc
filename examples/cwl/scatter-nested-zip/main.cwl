#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}

inputs:
  zip_files: File[]

outputs:
  final_report:
    type: File
    outputSource: final_summary/report

steps:
  process_all_zips:
    run: process_zip.cwl
    scatter: zip_file
    in:
      zip_file: zip_files
    out: [zip_summary]

  final_summary:
    run: clt/final_summary.cwl
    in:
      summaries: process_all_zips/zip_summary
    out: [report]
