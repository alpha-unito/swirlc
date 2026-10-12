# Full-pipeline CWL examples

Eight small workflows for translator, trace compiler and Python execution
acceptance. All deployments are local, with different locations/ports following
the existing scatter examples. They need only GNU `cp` and `printf`, with four
tiny input files already in `data/`. No downloads or external services are needed.

Each `depth-N` directory contains two independently configured workflows:

- `plain`: copies marker files, using static commands, direct input bindings and
  literal output globs. No deferred metadata features are required. Outputs are
  Files whose contents are `item=NAME` followed by one newline.
- `metadata`: prints the same markers and returns strings without the newline.
  These versions require all three deferred repairs: argument expressions (#3),
  stdout plus loadContents/outputEval (#5), and inputBinding.valueFrom (#6).

The output types intentionally differ: copying a File exercises the existing
payload path; returning its marker as a string exercises output processing.
Shared tools live in `tools/`; every workflow has its own `main.cwl`, `inputs.yml`
and `streamflow.yml`. Nested cases also have ordinary CWL subworkflow files.

## Workflows and expected results

| Depth | Work | Local locations | Expected marker value |
| --- | --- | --- | --- |
| 0 | Two dependent steps, no scatter | source -> stage -> finish | `item=alpha` |
| 1 | Scatter over three files, including a repeated input | source -> worker | `["item=alpha", "item=beta", "item=alpha"]` |
| 2 | Scatter over batches, then each batch's files | source -> outer -> inner | `[["item=alpha", "item=beta"], [], ["item=gamma"]]` |
| 3 | Scatter over groups, then batches, then files | source -> outer -> middle -> inner | `[[["item=alpha", "item=beta"], [], ["item=gamma"]], [], [["item=delta"]]]` |

These are genuinely nested scatter invocations, not multi-input Cartesian
scatter or nested arrays handled by one task. Unequal lengths and empty batches/
groups check scope isolation and preservation of empty output dimensions.
Repeated alpha in depth 1 checks that occurrences are identified by coordinate,
not deduplicated by filename or value.

Each depth has an `expected.json` shared by both variants. Depth 0 exports
`result`; the others export `results`. For plain results, recursively replace
each output File with its text minus its final newline before comparing. Metadata
results are already strings. Compare complete arrays in declaration order,
including empty arrays; sorting or flattening them hides gather errors.

Check final workflow outputs, rather than globbing every task work directory:
intermediate copies are not extra final results. Every task must have an isolated
work directory because all leaf tasks deliberately use the same output basename.
The depth-0 plain stage writes `staged.txt`, then finish writes `result.txt`, so
the second copy cannot collide with its staged input filename.

## Placement

Full step-path bindings select a separate local deployment at every scatter
level. For example, depth 3 binds `/process_groups` to outer,
`/process_groups/process_batches` to middle, and
`/process_groups/process_batches/process_items` to inner. All use distinct ports:

| Depth | Plain ports | Metadata ports |
| --- | --- | --- |
| 0 | 35600–35602 | 35610–35612 |
| 1 | 35620–35621 | 35630–35631 |
| 2 | 35640–35642 | 35650–35652 |
| 3 | 35660–35663 | 35670–35673 |

The depth-0 dependency requires transport between stage and finish; nested
variants require transport between scatter owners. Locations all run on the same
machine. These examples do not require multiple workers at the same level.

## Translate now; compile and execute after compiler implementation

From the repository root, select a depth and variant:

```sh
depth=2
variant=plain
example="examples/cwl/pipeline/depth-$depth/$variant"
output="build/pipeline-examples/depth-$depth/$variant"
rtk mkdir -p "$output"
rtk .venv/bin/swirlc translate -l cwl "$example/streamflow.yml" -o "$output"
```

After the shared frontend and the corresponding backend support these artifacts:

```sh
rtk mkdir -p "$output/trace" "$output/python"
rtk .venv/bin/swirlc compile "$output/workflow.swirl" "$output/metadata.yml" \
  --target trace -o "$output/trace"
rtk .venv/bin/swirlc compile "$output/workflow.swirl" "$output/metadata.yml" \
  --target default -o "$output/python"
rtk sh -c 'cd "$1" && ./run.sh' sh "$output/python"
```

The current compilers do not support the full emitted envelope/scoped syntax,
including the plain variants. Metadata variants additionally retain intentionally
unsupported source features: `render.cwl` uses an expression for the printf format,
transforms the File input with `self.nameroot`, redirects stdout, loads the result
and evaluates `self[0].contents.trim()`. Missing descriptors are a failure to
preserve the source contract, even if translation returns zero.

## Validation record — 2026-10-12

All 18 CWL documents loaded through the installed cwl-utils parser. All eight
StreamFlow configurations translated twice with identical SWIRL/metadata bytes,
without logged errors; artifacts and logs are under `build/pipeline-examples`.
Manual structural checks confirmed input paths/marker contents, expected JSON
shapes, unique local ports, location counts and 0/1/2/3 emitted scatter levels.
Plain depth 0 retains its ordered cp arguments/defaults and literal output globs.
Metadata depth 0 still omits its argument expression, transformation, stdout and
output evaluation, as expected from the unresolved metadata repairs.

No compiler runs, workflow execution or automated test suite was performed.
Exact runtime outputs, concurrent progress and hint-free execution remain future
acceptance checks; the expected files describe required results, not observed ones.
