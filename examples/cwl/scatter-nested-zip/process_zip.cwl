#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}
  InlineJavascriptRequirement: {}
  StepInputExpressionRequirement: {}

inputs:
  zip_file: File

outputs:
  zip_summary:
    type: File
    outputSource: summarize/zip_summary

steps:
  unzip_step:
    run: clt/unzip.cwl
    in:
      archive: zip_file
    out: [extracted_files]

  inspect_step:
    run: clt/inspect_file.cwl
    scatter: target_file
    in:
      target_file: unzip_step/extracted_files
    out: [info]

  summarize:
    run: clt/summarize_zip.cwl
    in:
      zip_name:
        source: zip_file
        valueFrom: $(self.nameroot)
      infos: inspect_step/info
    out: [zip_summary]
