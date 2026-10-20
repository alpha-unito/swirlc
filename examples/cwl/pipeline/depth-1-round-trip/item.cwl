cwlVersion: v1.2
class: Workflow
inputs:
  sample: File
outputs:
  result:
    type: File
    outputSource: "3/result"
steps:
  "1":
    run: ../tools/stage.cwl
    in:
      sample: sample
    out: [result]
  "2":
    run: ../tools/copy.cwl
    in:
      sample: "1/result"
    out: [result]
  "3":
    run: ../tools/stage.cwl
    in:
      sample: "2/result"
    out: [result]
