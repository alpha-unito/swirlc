## Named condition validation (2026-10-15)

Named-condition validation evidence:
- Focused regressions: 180 tests plus 3 subtests; includes 23 condition checks
  covering both targets, both Boolean branches, native stream pending/exhausted
  states, strict Boolean results, evaluator errors, short-circuiting, concurrent
  task isolation and parallel input merges. Generated tests bundle installed
  dependencies offline and use bounded deadlines.
- Toy: `build/named-conditions-toy/acceptance.json`, six locations, both compiler
  targets and hints modes, exact expected results, 29 isolated commands each.
- Eight pipelines: `build/named-conditions-pipelines/`, 32 trace/default compiles
  and 16 local runs, with/without hints, exact ordered outputs and termination.
- Ordinary examples: 4 passed (`tests/test_pipeline_contract.py -k ordinary`),
  including the supplied nested split configuration executed as a local mirror.
Expected results, source examples and comparison rules were unchanged.

## Single typed input declaration (2026-10-15)

The active v1.1 step contract is `inputs: {port: {type: TYPE}}`. It replaces
`inputPorts` and `fileInputs`; both old fields are rejected by the strict schema.
Expression port bindings contain only `port`, and obtain their types from the
step's input declarations. File/Directory staging, including nested arrays,
also derives from those declarations independently of expression variable names.
Object and execution-context bindings are unchanged. Tool, expression, dispatch,
gather and occurrence-publisher descriptors use this contract. Ordinary legacy
literal/direct-port descriptors without bindings remain supported.

The compiler verifies exact exec input-port ownership and rejects known payload
types that conflict with declared input types. The shared serializer preserves
typed declarations. Generated Python remains direct and source-language-neutral;
no CWL/Node runtime dependency, additional communication or exec action is added.
Regenerate older v1.1 metadata rather than mixing the two contracts.

Validation evidence for typed inputs:
- Eight depth/variant pipelines: `build/typed-inputs/pipelines-final/`, 32 trace/default
  compilations and 16 local executions, with/without hints, exact expected values,
  configured placement, isolated task directories and successful termination.
- Toy genome: `build/typed-inputs-toy/acceptance.json`, both targets/modes, six
  locations and 29 isolated command tasks per execution.
- Focused descriptor/schema/expression/codegen/trace tests: 87 passed; scoped
  runtime/compiler/parser/collections/cancellation/hints: 60 passed plus 3 subtests;
  ordinary lists/lists-input/nested/nested-split local mirror: 4 passed.
- Real 1000Genomes translated and strict metadata validated only:
  `build/typed-inputs-genome/translation.log`, 44 descriptors and 12 population
  File port contexts. No data downloads or real genome execution.
- A simultaneous duplicate toy validation attempt hit occupied local ports; the
  final toy and pipeline evidence above comes from separate, successful runs.

## Production metadata excludes scatterRegions (2026-10-15)

Removed `scatterRegions` from CWL translator output and the strict v1.1 schema,
and deleted internal bookkeeping used solely to construct that diagnostic block.
Execution retains scatter methods, routes, types and dispatch/gather descriptors;
SWIRL retains scope, ownership, placements and closure actions. No runtime change.
Legacy v1.0 schema/hint handling is unchanged. Retranslate previous v1.1 artifacts.

Acceptance checks now inspect participating dispatch operation IDs and routes,
and resolve declared final outputs through root gather output descriptors instead
of diagnostic region records. Expected outputs and comparison rules are unchanged.
Evidence: `build/scatter-regions-cleanup/acceptance.json` passes toy genome with
six locations, both targets/hints modes and 29 isolated commands per execution.
All eight pipelines pass in `build/scatter-regions-pipelines/`: 32 compilations,
16 executions, exact outputs including nested empty branches and duplicates.
Focused checks: 70 tests plus 3 subtests (metadata, CWL descriptors, scoped runtime,
Python codegen, trace and hints). Historical deleted-fixture/checksum failures
remain outside this cleanup; fixtures were not restored.

# Example status

## Toy genome — 2026-10-15

`examples/cwl/toy-genome` is a retained local analogue of the 1000Genomes graph:
paired outer File scatter, ordinary chromosome subworkflow, two independent
ExpressionTools, paired interval scatter/gather, parallel sifting, sibling
population scatters over a reusable root File array, repeated populations and
File[][]/string[][] final aliases. Three tiny chromosomes have 3/2/0 intervals;
all fake commands use Python's standard library. Six configured local locations
reuse the same inner worker pool, with no data downloads or genomic dependencies.

Both trace/default compilation and hints/no-hints execution pass exact expected
values, types, task IDs, configured placement and 29 isolated command directories
per run. Four compilations and two executions are retained in `build/toy-genome`,
with full logs, manifests and `acceptance.json`. Run:
`rtk .venv/bin/python -m tests.test_toy_genome --output build/toy-genome`.
See [toy-genome/README.md](cwl/toy-genome/README.md) for fake processing and outputs.
All eight earlier pipelines pass again (32 compilations, 16 executions), with
four ordinary local list/nested checks, under `build/toy-genome-regressions`.

## Generic expression execution — 2026-10-14

CWL syntax and context interpretation now belong to the CWL translator. It emits
source-language-independent JavaScript function-body descriptors (`language`,
`source`, optional `bindings`). Sole expressions retain their value type;
interpolation is lowered into JavaScript string-building code. InputBinding
`self` is an explicit local port binding, not rewritten source text. Output
processors explicitly bind `self` to the generic `matchedFiles` execution context.
The runtime never parses CWL `$()`/`${}` syntax or imports `cwl_utils`.

Generic bindings may reference typed ports, nested objects or named execution
contexts; variable names are chosen by the translator. `fileInputs` requests file
staging independently of expression variable names. Output descriptors use
`readContents` and `evaluate`; dynamic stdout/globs carry generic expression
objects. `_evaluate_expression` executes bodies through the existing pure-Python
Js2Py engine, and `_execute_command` performs generic command/output operations.
The compiler/schema/shared serializer preserve these descriptors. Node is neither
required nor invoked; installed Python dependencies can still be bundled offline.
Literal/direct-port legacy commands retain their existing execution path.

The previous CWL-specific expression metadata must be regenerated by translating
its source; raw expression wrappers and the former inputs/inputTypes/outputEval/
loadContents fields are not the new v1.1 descriptor contract. This ownership
refactor adds no SWIRL actions and does not expand CWL feature coverage. Earlier
runtime-context/expressionLib, JS scanner/conformance, Directory transport and
remote/genome execution limits remain. The earlier tool-metadata implementation
and its incident report are historical records below.

Final verification: all eight pipelines pass **8 translations, 32 compilations
and 16 executions**, with both targets and hints modes. **67 focused tests,
66 core regressions, four ordinary local examples and three subtests pass**.
Every pipeline SWIRL action body is unchanged from the completed metadata stage;
only its generated command header differs. Generated Python AST inspection finds
no CWL parser/helper/import and retains direct workflow control flow. See
`build/compiler-generic-expressions/summary.json`. Depth-3 validation required a
retry while an unrelated desktop outbound socket occupied configured port 35662;
the original ports/examples passed after it cleared. No process was killed,
source example modified, expected value changed or dependency downloaded.

This generic contract supersedes the earlier CWL-specific metadata descriptor
fields while retaining their validated semantics. Reproduce the matrix with
`rtk .venv/bin/python tests/test_pipeline_contract.py --output build/compiler-generic-expressions`.

Current validation artifacts are under `build/compiler-generic-expressions`,
with per-depth/variant reports and generic generated Python. The same eight-case
acceptance harness checks both targets and hints modes, exact values/types/IDs,
placements, isolated task directories, scopes and successful termination.
1000Genomes was translated and inspected only: 44 matching exec descriptors and
12 population nameroot/glob binding contexts, in `genome/inspection.json`.

## Historical tool metadata acceptance — 2026-10-14

Repairs #3/#5/#6 are implemented across CWL emission, strict v1.1 metadata,
loading and directly compiled Python execution. Each command descriptor has one
`inputs` name-to-port map and matching `inputTypes`. Arguments retain literal
`value`, direct-port `valueFrom` or `expression` (exactly one), their source
position and prefix/separate/shellQuote/itemSeparator options. InputBinding
`self` is normalized within expression tokens to its named input; quoted/escaped
literal text and output `self` are preserved. Base-command tokens precede the
CWL-position-ordered bindings. No extra exec or communication actions are added.

The existing JavaScript evaluator handles typed File fields, interpolation and
output `self`. Explicit stdout is written in each isolated invocation directory;
dynamic globs use named inputs. Matched File objects gain contents only when
requested (UTF-8, at most 64 KiB), then outputEval runs before publication.
Declared output types are checked; raw strings are never implicitly trimmed.
Legacy descriptors without the new input map retain their prior command path.
JavaScript array conversion now retains lists rather than numbered dictionaries.
Concurrent dependency bootstrap uses process-specific temporary archive paths.

All eight `examples/cwl/pipeline/depth-{0,1,2,3}/{plain,metadata}` configurations
passed translation, trace/default compilation and bounded execution at their
configured distinct local locations, both with and without advisory hints:
**8 translations, 32 compilations, 16 executions**. Complete logs, SWIRL,
metadata, traces, direct Python and final output manifests are retained under
`build/compiler-tool-metadata/depth-N/VARIANT/{hints,no-hints}/{trace,default}`;
per-case `acceptance.json` records exact expected outputs, placement and isolated
command-task counts **2/3/3/4** at depths 0/1/2/3 in both variants and modes.
Plain File contents lose only their final newline for comparison; metadata
strings are compared unchanged. Ordering, duplicates, nested arrays, empty
branches, exec port ownership, scope bindings and joined termination pass.
The plain SWIRL action bodies match the completed paired-collections baseline;
only the generated command comment differs with the new output directory.

Reproduce the retained matrix with:
`rtk .venv/bin/python tests/test_pipeline_contract.py --output build/compiler-tool-metadata`.
Default acceptance bundles installed dependencies; tests disable pip indexes.
The focused/parser/schema/trace/codegen/scoped-runtime/expression/cancellation/
hints suite passed **119 tests and 3 subtests**; `test_compiler.py` passed **4**;
the complete pipeline/list/nested suite passed **12**. Focused tests include
argument ordering/options, nameroot, dynamic scalar/list globs, loaded File self,
exact string/list/type/ID preservation, malformed/unsupported expressions,
command/output failure wakeup and a deterministic concurrent bootstrap race.

Ordinary `nested/streamflow.yml` returns `[processed] HELLO WORLD`. The split
configuration retains its original SSH metadata and was executed only via a
separate explicitly local metadata mirror with two locations; it returns the
same string. Retained evidence is in `build/compiler-tool-metadata/nested`.
1000Genomes was translated and inspected, never executed: all **44** exec
metadata entries are unique/matching and **12** population-tool descriptors
retain `-pop $(inputs.population.nameroot)` and the same named input in output
globs. See `build/compiler-tool-metadata/genome/inspection.json`.

Limits: expression positions are rejected; supported expressions use the existing
Js2Py JavaScript engine (not full modern JavaScript/CWL conformance). Runtime and
expressionLib contexts, secondary-file/staging requirements and broader optional/
union/output schemas remain unverified; Directory transport and legacy pair/open
scatter remain explicitly unsupported. SSH/SLURM/Docker and genome execution are
not established by this local evidence. The historical `test_cwl_new_syntax.py`
run still has 15 failures due to deleted fixtures and one obsolete SWIRL assertion;
fixtures were not restored and validation/source expectations were not weakened.
The full failure log is `build/compiler-tool-metadata/legacy-cwl-syntax.log`.

Validation incident: an initial nested split launcher unintentionally attempted
SSH/SCP to `hpc.example.org` and failed DNS/key lookup (exit 255). Earlier list
launchers installed cached wheels; no download was observed, but index access
cannot be excluded. These attempts violated the requested no-remote boundary.
They were stopped; subsequent tests inspect deployments, mirror split metadata
locally and bundle dependencies. Exact evidence and limitations are recorded in
`build/compiler-tool-metadata/nested/streamflow-split/remote-attempt.md`.
No commits, pushes, binary inspection, destructive operations or fixture restoration.

## Historical direct Python compilation — 2026-10-13

The default target lowers the shared structured frontend into ordinary Python
`workflow` functions. Generated programs call scoped receive, step execution and
send primitives directly; replication admission uses explicit `while`/`if`
control flow, and parallel branches are generated functions with completion
joins. Operand constructors describe payload/identity patterns only. The bundle
contains no serialized `TRACE` program or generic workflow interpreter.
Transport, occurrence storage, matching, cardinalities, gathers, deployment and
command/expression execution remain shared runtime primitives.

All four plain pipeline examples were translated, compiled with both targets
and executed again with and without advisory hints. Exact final outputs,
configured location ports, duplicate occurrences, nested empty branches and
isolated task directories passed unchanged. Direct-compilation logs, traces,
bundles and per-depth `acceptance.json` reports are under `build/compiler-direct`.
Reproduce with `rtk .venv/bin/python tests/test_pipeline_contract.py --output build/compiler-direct`. The acceptance harness inspects native Python calls and
literal input/output ports and placement; it no longer reads a runtime trace.

Deferred metadata repairs #3/#5/#6 and SSH/SLURM execution remain outside this
local evidence. The earlier compiler record below describes the original scoped
implementation and is retained as historical evidence.

## Historical compiler execution evidence — 2026-10-12

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
