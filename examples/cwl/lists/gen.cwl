#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

# The whole shell pipeline is kept as a single scalar baseCommand because the
# swirlc CWL translator only carries baseCommand[0] as the step command and does
# not (yet) wire inputBinding arguments. This tool takes no inputs and emits
# three files, so its output is a File[] (-> SWIRL list[file]).
baseCommand: "sh -c 'for i in 1 2 3; do echo part-$i-data > part_$i.txt; done'"

inputs: {}

outputs:
  parts:
    type: File[]
    outputBinding:
      glob: part_*.txt
