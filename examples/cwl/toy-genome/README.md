# Toy genome workflow

A local, dependency-free analogue of `examples/1000genome`. The fake processing
uses Python's standard library and tiny committed text files. It neither downloads
nor processes genomic data. The generated SWIRL bundle uses the repository's normal
Python runtime requirements, including its JavaScript evaluator.

## Structure and concepts

`main.cwl` performs paired dotproduct scatter over three SNP/sift File pairs into
an ordinary `chromosome.cwl` subworkflow. Each invocation contains:

1. Independent `get_chromosome` and `get_intervals` ExpressionTools. Both derive
   values from the SNP File's `nameroot`; interval calculation additionally uses
   the `step` input.
2. Paired counter/stop dotproduct scatter into `individuals`, followed by an
   explicit File-array gather into `individuals_merge`.
3. Independent `sifting`, and then sibling population scatters for
   `mutation_overlap` and `frequency`. Both consume merged and sifted Files.

This reproduces the original's nested scatter/gather shape, ordinary subworkflow,
shared worker pools, File transport, expressions and sibling data dependencies.
Tools use explicit stdout destinations, dynamic output globs, positional and
prefixed arguments, and `inputBinding.valueFrom: $(self.nameroot)` for population
Files. An expression argument carries a label containing a space, exercising
quoting. Frequency exposes the same stdout as a File and as a string through
`loadContents`/`outputEval`.

All outputs retain outer chromosome order and inner population order. Populations
are `[AFR, EUR, AFR]`, deliberately preserving duplicates. Chromosome row counts
are `[5, 3, 0]`, so interval scatter cardinalities are `[3, 2, 0]`. The empty
chromosome has an empty interval gather, but still produces three population
outputs; its final branch is not empty.

## Fake processing and expectations

Individuals extracts the selected 1-based inclusive row interval; merging
concatenates chunks in their original order. Sifting copies the paired candidate
numbers. Overlap retains candidates present in the merged values. AFR keeps all
such candidates; EUR additionally requires divisibility by four. Frequency prints
retained count, total count and retained sum. There is no division by zero.

`expected.json` contains exact final declared outputs. Compare File leaves by
reading their contents and removing only their final newline. Compare string
leaves directly. Preserve trailing spaces in the empty overlap markers, nested
arrays, ordering and duplicate AFR outputs.

## Local execution

From the repository root, run the complete bounded validation:

```sh
rtk .venv/bin/python -m tests.test_toy_genome --output build/toy-genome
```

This translates once, compiles trace and direct Python targets, executes all six
local locations, and repeats without advisory hints. Installed Python expression
dependencies are bundled and pip indexes are disabled. Logs, generated code,
output manifests and `acceptance.json` remain under `build/toy-genome`.

To run it as an automated regression:

```sh
rtk .venv/bin/python -m pytest tests/test_toy_genome.py -q
```


Use `streamflow.yml` as the translator input and compile the resulting SWIRL with
both trace and default targets. Run the generated Python bundle at every configured
location with bounded deadlines. Six distinct local locations are configured:
coordinator (35800), two chromosome workers (35810, 35811), and three inner workers
(35820, 35821, 35822). The same inner workers are reused by all three inner scatter
steps. No containers, SSH or external services are involved.

The repository validation test provides the exact translate/compile/run sequence
and checks outputs with advisory hints both enabled and disabled.

## Validation — 2026-10-15

The original configuration passes both targets and both hint modes: four
compilations, two executions, exact declared output values/types and 29 isolated
command invocations in each execution. The command counts are five interval
chunks, three merges, three sift copies, nine overlaps and nine frequencies.
Duplicate populations, unequal interval counts and the zero-interval chromosome
are retained. Declared File outputs are compared by contents minus only their
last newline; strings are compared unchanged.

This example exposed gaps that the smaller pipelines did not exercise: paired
single-destination stream routing, nested dispatch of root invariants, separate
bindings for transported File copies, and concurrent Js2Py code generation.
Those paths have focused regressions. The eight earlier pipeline configurations
also pass again; their artifacts are in `build/toy-genome-regressions`.
This is local execution evidence, not execution of the real genome workflow.

Focused compiler/runtime/translator regressions: 137 tests and three subtests
passed; four ordinary local list/nested checks also passed.
