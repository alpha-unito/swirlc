cwlVersion: v1.2
class: Workflow

# step1 (gen)   runs on deployment `alpha`  -> produces list[file]
# step2 (merge) runs on deployment `beta`   -> receives the list[file] from alpha
# The cross-location edge forces a send/recv of a list[file] value.

inputs: {}

outputs:
  final:
    type: File
    outputSource: step2/merged

steps:
  step1:
    run: gen.cwl
    in: {}
    out: [parts]

  step2:
    run: merge.cwl
    in:
      parts: step1/parts
    out: [merged]
