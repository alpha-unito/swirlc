#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}

inputs:
  batches:
    type:
      type: array
      items:
        type: array
        items: string

outputs:
  echoed:
    type:
      type: array
      items:
        type: array
        items: File
    outputSource: process_batch/echoed

steps:
  process_batch:
    run: batch.cwl
    scatter: batch
    in:
      batch: batches
    out: [echoed]
