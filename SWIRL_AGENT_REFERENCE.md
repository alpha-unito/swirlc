## Operation-driven replication termination (2026-10-21)

`end()` is removed from the grammar. An unguarded `+` selects a branch whose
first operation can activate. Data moves/sends require matching port data;
EOF sends require an exhausted port in the selected scope. Receives activate
on a matching incoming offer. Executions require their input port data. Existing
explicit condition choices remain available. The Python backend requires an
unguarded branch to start with an action (or `0`); a parallel group or nested
replication in that position is rejected because it has no single admission action.

A replication stops admission when its selected branch starts with `send(eof)`
or `recv(eof)`. The selected branch still executes its remaining operations,
including additional EOF receives. The replication joins admitted work and its
descendants before continuing; EOF publication must follow prior data transfers.
An EOF later in a normal iteration does not terminate its enclosing replication.
A publisher therefore uses `!(move(data) + send(eof))`, with scoped envelopes,
rather than a guarded `end()` followed by an EOF send.

## Named condition guards (2026-10-15)

Modern CWL translation emits `left +[condition_id] right`, resolved against a
strict top-level `conditions` map. Built-in `{type: has_data, port: PORT,
scope: SCOPE}` checks execute directly in Python: available=true,
closed/exhausted=false, temporarily unavailable=pending. The pending state never
selects the false branch. Existing inline guards remain accepted for compatibility.
Expression conditions use `{type: expression, inputs: {PORT: {type: TYPE}},
bindings: ..., expression: {language: javascript, source: BODY}}`. Port bindings
reference already-bound values in the current invocation; no extra receive/exec
is introduced. Expression results must be booleans; missing inputs, unsupported
forms and evaluator failures propagate. Conditions are evaluated lazily once per
selection attempt. Both compiler targets resolve named references; default output
remains direct Python. Scope/undefined-reference checks run before code generation.

CWL `when` now fails explicitly rather than silently running unconditionally.
This change implements generic conditional checks, not nullable skipped-output
semantics needed for complete CWL `when` support.

Parser maintenance: no local ANTLR generator was available, and downloads were
not authorized. Grammar and generated guard method were updated together without
new tokens; serialized ATN remains from the earlier grammar. Named/legacy guard
and mixed nested operator tests pass; full parser regeneration remains deferred.

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

## Remaining fixed policy fields removed (2026-10-15)

Removed dispatch `key.coordinates`; gather `order`, `validation`, `emptyShape`,
`completion`; result-route `eofOwner`; and scope `admission`, `activation`,
`missingKey`, `lifecycle`. These describe unconditional execution behavior rather
than choices. Translator output and strict schema now omit/reject them. Structural
`key`, `scatterRegions`, routes, collection descriptors and owner records remain.
No runtime changes: length exchange/barrier, validation, routing, ordering, empty
shape preservation, admission and closure behavior are retained. Retranslate old
metadata before compiling it.

Verification: 68 focused tests plus 3 subtests passed. Toy genome evidence:
`build/scatter-fixed-policy-cleanup/acceptance.json` (trace/default compilation,
execution with/without hints, six local locations, exact results, 29 isolated
command tasks each). The broader `tests/test_translator.py` run yielded 5 passed,
18 failed: missing historical fixtures and an old metadata checksum assertion.
Deleted fixtures were not restored and checksum expectations were not weakened.

## Scatter policy metadata (2026-10-15)

Scatter `keySpace` contains only `dispatches`. Length publication before peer
wait, method-derived shape validation, and operation/full-ID routing are runtime
invariants, not configurable policy strings. The current length exchange barrier
is retained for later evaluation. The duplicate scope `routing` field is also
removed. Retranslate older metadata carrying these fields for the strict schema.

# SWIRL project reference

## Toy genome execution fixes — 2026-10-15

The retained `examples/cwl/toy-genome` exercises the genome-shaped local path:
paired outer/inner dotproduct scatters, six locations and reused worker pools,
ordinary subworkflow steps, independent expression producers, empty interval
gather, sibling population scatters over root invariants, duplicate populations,
File transport, nameroot arguments, dynamic stdout/globs and loaded string outputs.
All final File[][]/string[][] values match `expected.json` with/without hints.
Both targets compile; 29 isolated commands execute per mode. Evidence is in
`build/toy-genome/acceptance.json`; the source README contains the reproduction command.

The example exposed four concrete gaps now fixed at their existing boundaries:

- Single-destination dispatcher branches claim only keys assigned to that worker
  by the operation/full-ID route. The dispatcher retains the actual occurrence's
  worker reservation, including when scoped invocations share a producer/port.
- Dispatch task identity/cardinality scope comes from its explicit output
  collection, while reusable input envelopes retain their real ancestor IDs.
- Existing ordinary, gather-readiness and invariant transfers receive into fresh
  consumer payload bindings. Distinct local File copies cannot collide at
  parallel joins or incorrectly compare paths against an inherited binding.
  Receives remain explicit; the binding repair adds no exec/communication action.
- Pure-Python Js2Py evaluation is serialized per process because its code
  generation shares mutable state. Command tasks and locations stay concurrent.

No SWIRL syntax, placements, worker pool configuration, expected data or hint
requirements were changed. Receiver symbol/port names change where isolation is
needed; re-translate older artifacts to obtain those corrected bindings.
The eight previous pipelines pass again across both targets and both hint modes
(32 compilations/16 executions); four ordinary local list/nested checks also pass.
Their artifacts are in `build/toy-genome-regressions`. Real genome execution and
remote deployment coverage remain outside this local proof. Earlier expression
coverage limits are unchanged. No remotes, dependency downloads, binary inspection,
commits, destructive operations or deleted-fixture restoration occurred in this stage.

Focused checks passed **137 tests and three subtests**; the four ordinary local
list/nested checks passed separately. Full focused output is retained at
`build/toy-genome/focused-regressions.log`.

## Generic expression execution — 2026-10-14

CWL syntax and context interpretation now belong to the CWL translator. It emits
source-language-independent JavaScript function-body descriptors (`language`,
`source`, optional `bindings`). Sole expressions retain their value type;
interpolation is lowered into JavaScript string-building code. InputBinding
`self` is an explicit local port binding, not rewritten source text. Output
processors explicitly bind `self` to the generic `matchedFiles` execution context.
The runtime never parses CWL `$()`/`${}` syntax or imports `cwl_utils`.

Generic bindings may reference typed ports, nested objects or named execution
contexts; variable names are chosen by the translator. Typed step `inputs`
declarations drive file staging independently of expression variable names. Output descriptors use
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

## Instructions for future agents

Treat this as a dated snapshot, not an authority over the code or newer research. **If a change or discovery contradicts this document, ask the user to update it with the corrected information.** Give the user the exact section, the conflicting evidence, and proposed replacement text. Do not silently rely on a known contradiction. Check the current code and tests before making implementation decisions.

Snapshot: 2026-09-24. The worktree had uncommitted CWL translator and test changes when this was written. `uv run pytest -q` passed: **39 passed**. The papers describe the research model; the repository defines current executable behavior. Planning documents describe intended work, not completed features.

## Sources and status

- **Published foundation:** Colonnelli et al., *Introducing SWIRL: An Intermediate Representation Language for Scientific Workflows*, arXiv:2407.01838v1, especially §§2–5. The supplied PDF is `2407.01838v1.pdf`; the repository cites its FM 2024 / 2025 proceedings version in [README.md](README.md).
- **Unfinished extension draft:** Medić, Tommaso, and Aldinucci, *SWIRL extension????*, supplied as `FGCS___SWIRL_extension.pdf` (4 pages). It has placeholder abstract, annotations, open questions, and incomplete rules. Read it as a research proposal, not an implemented or settled specification.
- **Implementation:** [grammar/SWIRL.g4](grammar/SWIRL.g4), [swirlc/main.py](swirlc/main.py), [swirlc/core/translator.py](swirlc/core/translator.py), [swirlc/translator/cwl/cwl_translator.py](swirlc/translator/cwl/cwl_translator.py), [swirlc/core/compiler.py](swirlc/core/compiler.py), and [swirlc/compiler/default/compiler.py](swirlc/compiler/default/compiler.py).
- **Current plan and status:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) consolidates the superseded implementation plans and distinguishes implemented behavior from pending acceptance and runtime work. Inspect the code before treating a planned item as done.

## What SWIRL represents

SWIRL is a low-level intermediate representation for a *distributed execution plan* of a scientific workflow. It is intended as a compiler target rather than a human authoring language. The toolchain is: source workflow and deployment description → translator → `workflow.swirl` plus `metadata.yml` → compiler → per-location execution bundle. The compiler needs metadata for details outside the formal process term: commands, data types and values, outputs, and deployment settings.

The 2024 paper starts with a directed bipartite workflow graph `W = (S, P, D)`: steps `S`, ports `P`, and dependency edges `D` between them. A workflow instance attaches data elements to ports. A distributed workflow adds locations `L` and a step-to-location mapping `M`; its work queue `Q(l)` contains the steps mapped to location `l`. A SWIRL *workflow system* is a parallel composition of location configurations `⟨l, D, e⟩`, each with local data `D` and an execution trace `e`.

This is a **process algebra** with actions and operators, not just a DAG serialization. In the 2024 formal core, actions are `exec` (execute a step with an input/output dataflow and location mapping), `send` (copy data over a port), and `recv` (receive it). Traces use sequential composition `.` and parallel composition `|`; `0` is the empty trace. Parallel location configurations compose into one system. The reduction rules require inputs before `exec`, synchronize an `exec` mapped to multiple locations, copy data on remote `send`/`recv`, and allow local/parallel/sequential progress. Structural congruence gives identities and commutativity for parallel composition. The paper derives a building block for each `(step, location)` pair: receive inputs, execute, send outputs. Its optimization removes redundant local communication and duplicate transfers, with a weak barbed bisimulation argument for preserving observable step executions. That formal result concerns the **2024 calculus**, not every later extension or current runtime path.

The extension draft explores scatter and repeated work. It adds choice `+`, replication `!`, `move`, `eof`, and task IDs to the calculus. Its example considers scatter dispatch, replicated workers, and gather. The draft explicitly leaves EOF, ID routing, and nested scatter details open; do not cite its reduction rules as settled guarantees. The current grammar independently accepts `+`, unparameterized `!trace`, `move`, `eof`, tuple/keyed data, and destination location sets. It does **not** accept the draft's parameterized replication syntax.

## Translator and compiler in this repository

The CLI in [swirlc/parser.py](swirlc/parser.py) exposes `translate --language dax|cwl` and `compile --target default|trace`. Translation writes `workflow.swirl` and `metadata.yml`; compilation reads both. `translate` requires an existing output directory. The `dax` translator reads a Pegasus directory containing `workflow.yml`, `replica.yml`, `sites.yml`, and `transformations.yml`, builds the common workflow entities, and uses `AbstractTranslator.render`. The CWL translator takes a **StreamFlow YAML configuration**, loads its referenced CWL workflow and input job, and produces SWIRL plus v1.1 metadata. There is no registered Galaxy translator or separate SWIRL optimizer in this checkout, despite their place in the 2024 paper's toolchain diagram.

The CWL translator currently builds a recursive `WorkflowRegion` / `Invocation` tree, with scatter as a `ScatterSpec` on an invocation. It resolves CWL sources to full paths, orders invocations by dependencies, and chooses StreamFlow targets by longest matching path prefix. `LoweringContext` tracks controller location, task identity, available data, per-location trace fragments, steps, dependencies, and scatter regions. `lower_region` / `lower_invocation` recurse through ordinary subworkflows; `lower_scatter` emits pair/open/gather helper steps, dispatch `move`, replicated worker traces, EOF branches, and gather receives. Metadata records helper `type` values (`scatter_pairer`, `scatter_open`, `scatter_gather`) and numbered `scatterRegions`; comments of the form `// @compiler begin|end scatter.<phase> <number>` mark dispatch, worker, and gather spans. The comments are optional hints, not syntax needed for correctness.

The grammar is [grammar/SWIRL.g4](grammar/SWIRL.g4); generated ANTLR Python files live in `swirlc/antlr`. [swirlc/core/parsing.py](swirlc/core/parsing.py) rejects lexer/parser errors before compilation. The compiler validates metadata v1.0 or v1.1, scans optional hints, visits the parse tree, constructs workflow entities from metadata, and calls a target compiler. `--target trace` writes readable per-location `.md` traces and is useful for checking structural lowering. The default target generates per-location Python programs and `run.sh`, with threads and TCP communication. It supports local, SSH, Docker, and Slurm deployment settings; generated JavaScript expression support uses a Python JavaScript engine. See [CWL.md](CWL.md) for current CLI examples and launcher behavior. The default target can also bundle pure-Python dependencies.

## Current CWL scatter state and limits

- **Translated and structurally tested:** simple scatter and nested scatter fixtures, including `tests/fixtures/cwl/scatter-nested-zip`; distinct nested worker pools and full CWL paths are asserted in [tests/test_translator.py](tests/test_translator.py). The `scatter-nested-zip` output compiles with `--target trace`; removing hints yields identical trace output in [tests/test_compiler.py](tests/test_compiler.py).
- **Scatter methods:** the translator recognizes `dotproduct`, `flat_crossproduct`, and `nested_crossproduct`. The pair helper makes task combinations and records coordinates; tests cover duplicate items, empty input, and nested coordinates. Unequal `dotproduct` lengths are rejected when statically known or by the generated pair helper. These checks do not prove complete gather shape or distributed execution semantics.
- **Runtime remains incomplete for nested/keyed scatter:** generated runtime state still uses shared `ports` and per-port readiness events. The gather helper sorts results using IDs guessed from values, file names, or content; it does not reconstruct nested CWL output shape from explicit task coordinates. Trace-level `name[task_id]` syntax is currently reduced to static metadata names. The existing default-target scatter test checks that helper calls are generated; it does not run the nested workflow end to end. The planned keyed message envelopes, per-region queues, scoped completion, deterministic gather, and hint-driven optimization are not implemented as specified in the plans.
- **Other concrete limits:** directory send/receive raises `NotImplementedError` in the default runtime. Do not infer full CWL or StreamFlow feature coverage from supported fixtures. The original paper's optimization proof does not validate the new scatter constructs automatically.

For translator work, inspect [swirlc/translator/cwl/cwl_translator.py](swirlc/translator/cwl/cwl_translator.py), then the focused tests. For compiler/runtime work, inspect [swirlc/core/compiler.py](swirlc/core/compiler.py), [swirlc/compiler/standard/compiler.py](swirlc/compiler/standard/compiler.py), [swirlc/compiler/default/compiler.py](swirlc/compiler/default/compiler.py), and [swirlc/compiler/hints.py](swirlc/compiler/hints.py). Run `uv run pytest -q` after changes. Treat the plan files as design context, and update this snapshot when code or research resolves a documented uncertainty.
