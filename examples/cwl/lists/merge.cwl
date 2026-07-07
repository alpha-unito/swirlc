#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

# Consumes the File[] produced by gen.cwl. The received files are symlinked into
# this step's working directory (each element of the list), so a plain glob over
# them works. Emits a single merged File.
baseCommand: "sh -c 'cat part_*.txt > merged.txt'"

inputs:
  parts:
    type: File[]

outputs:
  merged:
    type: File
    outputBinding:
      glob: merged.txt
