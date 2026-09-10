#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}

inputs:
  groups: File[]
  tags: File[]
  num_items: int

outputs:
  final_report:
    type: File
    outputSource: final_report/report
  all_tagged:
    type:
      type: array
      items:
        type: array
        items: File
    outputSource: process_group/tagged_results

steps:
  process_group:
    run: batch_subworkflow.cwl
    scatter: group_file
    in:
      group_file: groups
      tags: tags
      num_items: num_items
    out: [group_summary, tagged_results]

  final_report:
    run: clt/final_report.cwl
    in:
      summaries: process_group/group_summary
      tagged: process_group/tagged_results
    out: [report]
