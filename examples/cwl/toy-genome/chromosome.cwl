cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
inputs:
  script: File
  snp_file: File
  sift_file: File
  populations: File[]
  step: int
outputs:
  overlap_files:
    type: File[]
    outputSource: mutation_overlap/output_file
  freq_files:
    type: File[]
    outputSource: frequency/output_file
  freq_summaries:
    type: string[]
    outputSource: frequency/summary
steps:
  get_chromosome:
    run: tools/get_chromosome.cwl
    in:
      snp_file: snp_file
    out:
    - chromosome
  get_intervals:
    run: tools/get_intervals.cwl
    in:
      snp_file: snp_file
      step: step
    out:
    - counters
    - stops
  individuals:
    run: tools/individuals.cwl
    in:
      script: script
      input_file: snp_file
      chromosome: get_chromosome/chromosome
      counter: get_intervals/counters
      stop: get_intervals/stops
    out:
    - output_file
    scatter:
    - counter
    - stop
    scatterMethod: dotproduct
  individuals_merge:
    run: tools/individuals_merge.cwl
    in:
      script: script
      individuals: individuals/output_file
      chromosome: get_chromosome/chromosome
    out:
    - output_file
  sifting:
    run: tools/sifting.cwl
    in:
      script: script
      input_file: sift_file
      chromosome: get_chromosome/chromosome
    out:
    - output_file
  mutation_overlap:
    run: tools/mutation_overlap.cwl
    in:
      script: script
      input_file: individuals_merge/output_file
      chromosome: get_chromosome/chromosome
      population: populations
      sift_file: sifting/output_file
    out:
    - output_file
    scatter: population
  frequency:
    run: tools/frequency.cwl
    in:
      script: script
      input_file: individuals_merge/output_file
      chromosome: get_chromosome/chromosome
      population: populations
      sift_file: sifting/output_file
    out:
    - output_file
    - summary
    scatter: population
