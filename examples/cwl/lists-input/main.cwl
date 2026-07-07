cwlVersion: v1.2
class: Workflow

# A File[] workflow input (like the 1000-genome snp_files / populations inputs).
# The input data lives on deployment `alpha`; `merge` runs on `beta`, so the
# whole list[file] is sent alpha -> beta. `report` runs back on `alpha`, so the
# merged File is sent beta -> alpha.

inputs:
  snp_files: File[]

outputs:
  final:
    type: File
    outputSource: report/report

steps:
  merge:
    run: merge.cwl
    in:
      parts: snp_files
    out: [merged]

  report:
    run: report.cwl
    in:
      merged: merge/merged
    out: [report]
