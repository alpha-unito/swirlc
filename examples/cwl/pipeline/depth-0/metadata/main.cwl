cwlVersion: v1.2
class: Workflow
inputs:
  sample: File
outputs:
  result:
    type: string
    outputSource: finish/result
steps:
  stage:
    run: ../../tools/render.cwl
    in:
      sample: sample
    out: [result]
  finish:
    run: ../../tools/text.cwl
    in:
      text: stage/result
    out: [result]
