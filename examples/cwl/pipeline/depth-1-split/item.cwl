cwlVersion: v1.2
class: Workflow
inputs:
  sample: File
outputs:
  result:
    type: File
    outputSource: finish/result
steps:
  stage:
    run: ../tools/stage.cwl
    in:
      sample: sample
    out: [result]
  finish:
    run: ../tools/copy.cwl
    in:
      sample: stage/result
    out: [result]
