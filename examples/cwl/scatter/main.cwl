#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}

inputs:
  files_a: File[]
  files_b: File[]

outputs:
  report:
    type: File
    outputSource: analyze/report

steps:
  compute:
    run: compute.cwl
    scatter: [file_a, file_b]
    scatterMethod: flat_crossproduct
    in:
      file_a: files_a
      file_b: files_b
    out: [result]

  analyze:
    run: analyze.cwl
    in:
      inputs: compute/result
    out: [report]
