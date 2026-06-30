cwlVersion: v1.2
class: Workflow

requirements:
  - class: SubworkflowFeatureRequirement

inputs:
  text:
    type: string
  tag:
    type: string

outputs:
  final_result:
    type: string
    outputSource: step_annotate/result

steps:
  step_preprocess:
    run: sub.cwl
    in:
      text: text
    out: [processed]

  step_annotate:
    run: tag.cwl
    in:
      text: step_preprocess/processed
      tag: tag
    out: [result]
