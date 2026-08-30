#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: ExpressionTool

requirements:
  InlineJavascriptRequirement: {}

inputs:
  sample: string
  multiplier: int
  threshold: int

outputs:
  prefix: string
  score: int
  accepted: boolean
  words:
    type: string[]

expression: |-
  ${
    function weightedScore(items, multiplier) {
      return Math.max(items.length * multiplier, 0);
    }

    var words = inputs.sample.split("-");
    var score = weightedScore(words, inputs.multiplier);
    return {
      prefix: inputs.sample.substring(0, 5),
      score: score,
      accepted: score >= inputs.threshold && inputs.sample.length > 0,
      words: words
    };
  }
