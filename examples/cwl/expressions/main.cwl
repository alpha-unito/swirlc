cwlVersion: v1.2
class: Workflow

inputs:
  sample:
    type: string
  multiplier:
    type: int
  threshold:
    type: int

outputs:
  prefix:
    type: string
    outputSource: evaluate/prefix
  score:
    type: int
    outputSource: evaluate/score
  accepted:
    type: boolean
    outputSource: evaluate/accepted
  words:
    type: string[]
    outputSource: evaluate/words

steps:
  evaluate:
    run: evaluate.cwl
    in:
      sample: sample
      multiplier: multiplier
      threshold: threshold
    out: [prefix, score, accepted, words]
