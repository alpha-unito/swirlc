# Example status

## Compiler execution evidence — 2026-10-12

The accepted concrete contract now uses one ANTLR frontend, structured terms and
strict v1.1 metadata for both targets. Trace output includes envelopes, scoped
guards, fresh/exact bindings, owners, closure and completion joins. Generated
Python uses scoped occurrence storage, atomic matching, synchronous TCP commits,
concurrent replication, descendant joins, independent cardinality publication,
full-key routing and validated shape-preserving gathers. Existing deployment,
launcher, framing, command and expression infrastructure is reused.

All four `examples/cwl/pipeline/depth-{0,1,2,3}/plain` configurations translated,
compiled to both targets, and executed across their configured distinct local
locations, with and without advisory hints. Final File contents matched each
`expected.json` exactly, retaining duplicates, ordering, empty branches and nested
arrays. Depth 0 preserved stage-to-finish file transport. Observed command task
counts were 2, 3, 3 and 4 respectively, each with an isolated work directory.
Logs, traces, generated bundles and per-depth `acceptance.json` reports are under
`build/compiler-contract`. Reproduce with
`rtk .venv/bin/python tests/test_pipeline_contract.py`.

Focused regressions cover parsing/binding rejection, metadata ownership, trace
joins, atomic scoped transport, concurrent reverse completion, dynamic unequal
cardinalities, consistent routing, empty Cartesian shape, invalid/duplicate/missing
gather keys and bounded blocked/failure joins. This evidence supersedes older
claims that the concrete compiler contract is entirely unimplemented; older
execution claims remain historical and must not be extrapolated.

Deferred metadata repairs #3, #5 and #6 remain excluded. SSH/SLURM execution,
1000Genomes and broader CWL conformance are untested. Directory transport still
fails explicitly. Legacy indexed/pair-open scatter is rejected rather than
reinterpreted as independent dispatch. Runtime blocked-action deadlines default
to 60 seconds and can be set with `SWIRLC_RUNTIME_TIMEOUT`.

## Full-pipeline acceptance examples (2026-10-12)

`examples/cwl/pipeline` adds eight workflows: scatter depths 0, 1, 2 and 3, each
with a plain version avoiding deferred metadata features and a metadata version
requiring argument expressions, input transformations and stdout/output processing.
All are split across distinct local deployments. Shared dummy input files and
per-depth expected marker JSON make values, order and empty nested shapes explicit.
See [pipeline/README.md](pipeline/README.md) for placement, commands and checks.

All eight configurations translated twice with identical SWIRL/metadata bytes;
artifacts are under `build/pipeline-examples`. All CWL documents loaded, input
files/expectations and emitted depths/location counts were checked. This is source
and translation validation only. Current compiler support and metadata repairs
remain incomplete; no workflow execution or automated tests were performed.
These are new retained examples, not restored deleted fixtures. The older
11-configuration inventory below predates their addition.

## Current CWL examples (2026-10-08)

`examples/cwl` contains five basic workflows (`basic`, `nested`, `expressions`,
`lists`, `lists-input`), one simple paired scatter (`scatter`) and one simple
nested scatter (`scatter-nested`). The basic workflows retain their deployment
variants: **11 configurations** in total.

All 11 configurations translated successfully after cleanup. Basic outputs are
under `build/cwl-examples/<workflow>/<configuration>/`; scatter outputs are under
`build/scatter/` and `build/scatter-nested/`. Each directory contains the generated
trace, metadata and translation log.

The simple scatter pairs `[a, b]` with `[1, 2]`. The nested scatter uses
`[[a, b], [], [c]]` and preserves a `list[list[file]]` output type. Trace and
metadata inspection establishes emission only; no workflow was executed.
The translator now emits begin/scoped-EOF, composed IDs and explicit receiving
owners using one recursive lowering path at arbitrary finite scatter depth.
The one-/two-/three-level concrete references and one-/two-level virtual
references now describe dependency-routed gathers and sender-owned EOF.
Manual three-/five-level, empty, sibling, ordinary internal, invariant and
multiple-consumer artifacts are under `build/recursive-validation/final/`.
Receiving owners constrain admission to one child of their bound enclosing path;
exposed output lists materialize from the innermost scatter boundary outward.
The existing compiler does not support the complete new syntax.

The larger scatter and CWL 1000Genomes cases were initially moved to
`tests/fixtures/cwl`, then removed by the user. Automated tests were not run.
Additional manual artifact checks are under `build/new-syntax-validation/`.
The distributed `examples/1000genome` workflow remains in its original location.
Earlier 27-configuration translation records refer to the pre-cleanup layout;
their generated files remain under `build/envelope-validation/`.

## Handwritten SWIRL examples

| Example | Status |
| --- | --- |
| `swirl/basic`, `broadcast`, `gather`, `example1` | Compile with the current legacy compiler; outputs and logs are in `build/example-audit/<name>/`. Execution prerequisites still apply. |
| `swirl/scatter/source.swirl` and its `config.yml` | Outdated bundled pair/open model, indexed task IDs and EOF inside replicated choices. Source also fails the current parser on its multi-member tuple. |
| `swirl/scatter2.swirl`, `scatter3.swirl` | Historical split/take/put model with indexed IDs and old termination; parse with the legacy parser but are not current-model references. No accompanying metadata was available for compilation. |
| `swirl/nested-scatter-example.swirl` | Historical bundled pair/open nesting without the current invocation-scoped stream model. Parses as legacy syntax; no accompanying metadata for compilation. |
| `swirl/scatter4.swirl` | Current conceptual reference for independent dispatch/gather and joined EOF. Requires the new parser/runtime; not outdated. No accompanying metadata for compilation. |
| `swirl/test.txt` | Mixed design scratch notes, not an executable example. |

`build/example-audit/swirl-results.json` records parser and compilation outcomes.
Parsing alone does not establish executable semantics.

## Historical documentation

The handwritten SWIRL status above records the 2026-10-05 legacy compiler audit,
not a new compilation check. `swirl/scatter/README.md` and `swirl/basic/doc.md`
still contain historical pipeline/path descriptions.
