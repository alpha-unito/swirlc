#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

# Receives the File[] workflow input (a list[file] transferred from the location
# that holds the input data). Each received file is symlinked into this step's
# working directory by basename, so a plain glob concatenates them.
baseCommand: "sh -c 'cat snp_*.txt > merged.dat'"

inputs:
  parts:
    type: File[]

outputs:
  merged:
    type: File
    outputBinding:
      glob: merged.dat
