#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

# Consumes the single merged File (transferred back from the other location) and
# writes a line count report.
baseCommand: "sh -c 'wc -l merged.dat > report.out'"

inputs:
  merged:
    type: File

outputs:
  report:
    type: File
    outputBinding:
      glob: report.out
