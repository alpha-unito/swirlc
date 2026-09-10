cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}

inputs:
  group_file: File
  tags: File[]
  num_items: int

outputs:
  group_summary:
    type: File
    outputSource: merge_items/output_file
  tagged_results:
    type: File[]
    outputSource: tag_item/output_file

steps:
  generate_items:
    run: clt/generate_items.cwl
    in:
      count: num_items
    out: [items]

  compute_item:
    run: clt/compute_item.cwl
    scatter: item
    in:
      group: group_file
      item: generate_items/items
    out: [output_file]

  merge_items:
    run: clt/merge_items.cwl
    in:
      inputs: compute_item/output_file
    out: [output_file]

  tag_item:
    run: clt/tag_item.cwl
    scatter: tag
    in:
      summary: merge_items/output_file
      tag: tags
    out: [output_file]
