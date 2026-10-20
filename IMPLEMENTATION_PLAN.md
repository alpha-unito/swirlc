## Next stage: nullable payloads, skipped outputs and CWL when (planned)

Status: not implemented. Named guards are complete; CWL `when` remains explicitly
rejected until the stages below pass. This is the next conditional-execution
handoff, not a reopening of frontend, scoped-runtime, dispatch/gather or metadata
milestones. Keep length exchange and the existing placement/reservation model.
This plan update does not authorize dependency downloads or remote execution.

### 1. Define the generic null contract

- Add a canonical `optional[T]` payload type and a `null` value/type through the
  shared type model, strict schemas, loader, serializer, transport and generated
  Python. Lower CWL `T?` and two-member null/T unions into `optional[T]`; reject
  broader unions clearly until separately supported. Check nested types rather
  than accepting arbitrary type strings. Define assignability explicitly: T may
  flow to optional[T]; optional[T] may not flow to T without explicit selection
  or validation.
- Keep Python None / JSON null as an actual payload. Preserve it through scalar,
  File/Directory and nested-array conversion, including optional[list[T]] versus
  list[optional[T]]. Do not stringify None or attempt to stage/read it as a file.
- A skipped invocation publishes null for every declared output, at that output's
  original invocation ID. Null is distinct from no occurrence, an empty array,
  an empty File, pending input, EOF/begin control messages and the SWIRL zero
  process. Retain internal skipped provenance only if execution needs it; do not
  add diagnostic-only metadata or expose a source-language-specific sentinel.

### 2. Publish skipped results through generic control flow

- Reuse `left +[condition_id] right` and typed input declarations. Evaluate a
  condition using the current invocation's already-bound inputs; add no extra
  communication or evaluator exec solely to reconstruct those inputs.
- Define the smallest generic output-publication operation needed by the false
  branch. It must publish typed null payloads without launching the command,
  creating a command workdir, resolving stdout/globs, loading files or running
  output processors. Reuse existing publication mechanisms where possible;
  document the chosen descriptor contract before broad integration.
- Both branches expose the same output ports, IDs and compatible nullable types.
  Keep explicit concrete SWIRL scope, worker placement, owner admission and
  closure. False branches must publish/acknowledge results before closing their
  owner, and must not wait for receives or workers belonging only to the true
  branch. Skipped subworkflows do not activate their internal steps.
- Preserve direct generated Python and the generic pure-Python evaluator.
  Non-Boolean conditions, unbound inputs and evaluator failures fail promptly;
  they never become skipped/null results. Check cancellation and peer failure
  propagation while another branch is waiting.

### 3. Lower CWL when with correct invocation context

- Preserve `when` on the translator invocation model. Lower its source using the
  existing CWL expression frontend into a generic named expression condition;
  runtime metadata/code must not parse CWL or depend on CWL libraries/Node.
- Construct the step's named inputs after source/default and supported step-input
  transformations. For scatter, evaluate separately for each scattered invocation
  using its element values, full enclosing ID and bound invariant inputs. Do not
  evaluate once for the whole input array. If required step-input valueFrom or
  another source feature is unsupported, reject it instead of changing context.
- Keep original declared payload information while making conditional output
  interfaces nullable. Validate downstream consumers: optional inputs can receive
  null; required inputs must not silently coerce it or hang awaiting replacement.
- Replace the blanket `when` rejection only for the fully supported forms. Retain
  clear errors for unsupported expressions, type unions and conditional wiring.

### 4. Preserve scatter shape and downstream selection

- Gather one result per admitted task key, including null for skipped tasks;
  never drop/reindex skipped entries. Preserve declaration order, duplicates,
  full nested IDs, flat/nested crossproduct shapes and empty branches. A zero-item
  scatter yields an empty collection, while a skipped scalar invocation yields
  null. An entirely skipped subworkflow output array is null, not an invented [].
- Validate mixed true/false, all-false and empty scatters at multiple nesting
  depths, with unequal parent cardinalities and shared reserved worker pools.
  Existing length exchange/validation stays unchanged.
- Plan explicit generic selection/merge support for CWL pickValue forms
  first_non_null, the_only_non_null and all_non_null, preserving source order and
  rejecting invalid cardinalities. Implement this as a separate bounded slice;
  until then, reject unsupported pickValue/linkMerge combinations explicitly.
  Null support alone must not be described as complete CWL conditional coverage.

### 5. Acceptance and handover gates

- Add focused tests for nullable type parsing/assignability, JSON/transport round
  trips, nested null arrays, optional Files without staging, strict Boolean checks,
  false branches with no command side effects, skipped subworkflows, optional and
  required downstream inputs, error propagation and successful owner termination.
- Add small conditional CWL fixtures with independent expected outputs: ordinary
  true/false, per-item dotproduct and both crossproducts, nested scatters, repeated
  values, mixed/all-skipped inputs and zero-item branches. Do not alter existing
  example sources, expected results or comparison rules to conceal defects.
- Inspect full translation logs, metadata, concrete SWIRL and direct generated
  Python. Compile trace/default targets and execute at configured distinct local
  locations under bounded deadlines, with/without hints. Check exact null values,
  nested shape, task isolation, placement, closure and no command workdirs for
  skipped commands.
- Rerun all eight existing plain/metadata pipelines, toy genome and supplied
  ordinary nested local examples; preserve current results. Translate/inspect
  real 1000Genomes only; no downloads or real workflow execution.
- Regenerate the parser with authorized local ANTLR tooling when available and
  verify named/legacy guards; current manual guard-rule/serialized-ATN limitation
  remains documented independently of nullable payload implementation.
- Record exact commands, counts, evidence paths and remaining unsupported CWL
  forms in implementation/repair plans, example status and handover notes.
  Completion means null/skipped semantics pass end to end, not translation alone.

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

## Scatter metadata policy cleanup (2026-10-15)

Removed fixed `keySpace.cardinalities`, `keySpace.validation` and
`keySpace.routing` descriptors, plus the duplicate scatter scope `routing` field.
`keySpace` now contains only participating `dispatches`. Strict v1.1 schemas reject
the removed fields; retranslate existing generated metadata before compiling it.
The runtime is unchanged: length publication/exchange and its existing barrier
remain in place, dotproduct length validation derives from `scatterMethod`, and
routing by operation/full task ID remains unconditional. Evaluate the length
barrier separately later.

Validation: 68 focused tests and 3 subtests passed (metadata, CWL descriptors,
scoped runtime, Python codegen and trace contracts). Toy genome acceptance in
`build/scatter-policy-cleanup/acceptance.json`: both targets, both hints modes,
six local locations, exact outputs and 29 isolated command tasks per execution.

# SWIRL implementation plan

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

## Active handoff — 2026-10-14

The initial local compiler milestone is complete. This section and Part 2D.2 are
the stage contract. Local metadata acceptance is recorded below; the remaining queue is 2D.3. They supersede the older translator-only,
no-tests, syntax-freeze and per-slice approval gates retained in historical
sections below. Do not repeat completed compiler stages or wait for a separate
translator acceptance gate before the next metadata stage.

### Completed baseline and evidence

- Translator repairs #1/#2/#4 are implemented: parallel invocation/publication
  groups, unique exec descriptors and distinct deployment/service placement.
- Shared ANTLR parsing, structured operands/bindings and strict v1.1 metadata
  support both targets. Current collection syntax is
  `U(port, (collection, scope))`; metadata work must preserve it and the accepted
  envelope, owner, routing and closure contract.
- Trace compilation exposes flows, scopes, matching, owners and joins. Default
  compilation produces direct Python functions/control flow calling scoped
  runtime primitives, not a serialized workflow interpreted at runtime.
- Scoped communication, concurrent replication, descendant joins, independent
  dispatch/cardinality exchange and validated gathers have local execution
  evidence. All four plain pipeline examples (depths 0–3) compiled to both
  targets and executed with and without hints, matching expected markers, order,
  duplicate occurrences, empty nested branches and isolated task directories.
- Current retained reports, execution logs, traces and generated bundles are in
  `build/compiler-paired-collections/depth-{0,1,2,3}`. Earlier
  `build/compiler-contract`/`build/compiler-direct` records are historical paths;
  do not require unavailable artifacts. See `examples/EXAMPLES_STATUS.md` and
  `tests/test_pipeline_contract.py` for the acceptance harness.

This establishes the initial local milestone, not complete CWL conformance or
proof of the entire acceptance matrix. SSH/SLURM execution, 1000Genomes and
Directory transport remain outside the verified scope. Directory transport and
legacy indexed/pair-open scatter currently fail explicitly.

### Completed stage: tool metadata and evaluation (#3/#5/#6)

The three repairs are implemented together across CWL emission, metadata validation/
loading and generated Python execution. Preserve named inputs, argument
expressions and inputBinding transformations, stdout destinations, dynamic globs,
loadContents and outputEval. Part 2D.2 gives the implementation and acceptance
details; `TRANSLATOR_REPAIR_PLAN.md` retains the precise descriptor design.

The next-stage handoff includes implementation, local translation, both-target
compilation, generated Python execution and focused automated regressions. Use
all four metadata pipeline examples as new acceptance cases and all four plain
examples as preservation checks, with and without hints. No intermediate plan
or implementation-satisfaction approval is required for routine work in this
scope. This documentation update itself does not execute workflows or tests.

Do not change the concrete SWIRL syntax, introduce extra exec/communication
actions for already-bound tool inputs, change placements or worker reservations,
restore deleted fixtures, add a scheduler/IR/interpreter, or expand into broad
CWL conformance. No commits, pushes, remote interaction, downloads, destructive
operations or binary inspection without explicit permission. Actual cluster or
1000Genomes execution is a later stage, not a prerequisite for this handoff.

### Subsequent work

After metadata acceptance, extend local coverage to the remaining retained
ordinary/nested examples and the wider scatter matrix where not already proven.
Then validate available deployment variants and complex workflows under separately
agreed execution resources. Do not claim remote or genome execution from local
examples, metadata inspection or generated bundles.

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

## Historical planning baseline (2026-10-08–12)

The records below explain the original implementation sequence. Their missing-work
statements and authorization gates are historical; the active handoff above and
the current Part 2D.2 take precedence. Language/execution contracts remain normative.

Updated 2026-10-08 for arbitrary recursive scatter nesting, dependency-routed
outputs with consumer-side gathers, depth-indexed bindings, explicit begin/EOF lifecycles and uniform
`(data, id)` envelopes. The translator implementation now follows the recursive output-boundary
contract below. Manual emission evidence is recorded separately from deferred
parser/compiler/runtime correctness.
The target contract and implementation handoff here remain normative. The active
repair queue is now [TRANSLATOR_REPAIR_PLAN.md](TRANSLATOR_REPAIR_PLAN.md), created
2026-10-09 after independent artifact review and clarification of parallel step groups.
The three superseded implementation plans were removed on 2026-10-06.
Earlier review records are historical evidence, not additional work queues.
Do not recreate deleted plans or reviews.

## Compiler planning update — 2026-10-12

This is a source/artifact review and implementation roadmap, not authorization to
resume compiler changes, automated tests or workflow execution. The existing
translator acceptance and implementation-satisfaction gates still apply.
The latest translator evidence is the 2026-10-09 section of
`TRANSLATOR_REPAIR_PLAN.md`, not the historical status table below.

- Translator repairs #1 (parallel invocation/publication groups), #2 (one tool
  descriptor per emitted exec) and #4 (deployment/service identity and options)
  are recorded as implemented. The current manifest lists 12 configurations;
  current examples are under `build/cwl` and `build/1000genome`, with additional
  three-/five-level and Cartesian probes under `build/repair-probes`. Recorded
  repeatability and structural checks are translation evidence only. Acceptance
  remains pending; historical `build/recursive-validation/final` coverage is
  unavailable and must not be counted.
- Metadata repairs #3 (argument expressions), #5 (stdout/output processing) and
  #6 (inputBinding transformations) remain deferred until syntax freeze and
  authorized complex-workflow testing. They are necessary before claiming
  correct nested command outputs or 1000Genomes execution.
- The CLI exposes `--target trace` and `--target default`; default generates
  Python. Both use `CompileVisitor` and `StandardCompiler`. Trace is a static
  per-location Markdown explanation, not a runtime simulator.
- The grammar lacks variables, composed IDs, scoped U, guarded choice and
  `end()`. Although ordinary `(payload, root)` tuples can parse, the visitor
  treats their text as dependency names. Metadata v1.1 only inherits the old
  schema; it does not implement the translator's new descriptor contract.
  Neither target currently supports the complete newly emitted workflows.
- The default backend already supplies deployment, transport, command/expression
  execution and bundle generation. Its legacy scatter helpers, serial replication,
  port-global state and heuristic gathers cannot establish the scoped contract.
  Reuse the ordinary execution infrastructure and replace those semantics at
  their shared responsibility points.

Implementation proceeds through the expanded Part 2 roadmap below. Complete the
trace backend after the shared frontend, before debugging Python execution. This
provides a reviewable representation of scopes, matching, admission and joins
without pretending that readable traces prove scheduling or output correctness.

## Goal and boundaries

Complete the uniformly identified, independently dispatched CWL workflow model:
first accept the translator's emitted SWIRL and metadata, then implement the
parser/compiler/runtime that executes them. Preserve ordinary workflows,
deployment support, commands, expressions, output processing and whole-list
inputs. Reuse the existing recursive translator rather than rebuilding it.
Every scatter depth must use the same lowering operation and recursive call;
there must be no separate one-level, two-level or N-level implementations.
The immediate implementation scope remains translator and trace production.
Automated tests and compiler/runtime implementation remain excluded until the
user asks to resume them.

This update changes documentation only. Code inspection establishes
implementation presence, not successful execution or user acceptance. No tests,
workflow execution, downloads, commits or remote operations were performed for
this audit. Test counts below are dated records from the reviews, not fresh runs.

## Recursive translator implementation (2026-10-08)

The translator now uses one `lower_scatter` path at every depth. Existing region,
invocation, scatter, dependency ordering, deployment lookup and worker reservation
structures remain authoritative. `LoweringContext.bound_path` carries structural
scope/coordinate bindings; `EmittedFragment` composes owner-local trace actions;
`PendingGather` records an unmaterialized boundary; `OutputOccurrence` records
actual publishers; `ScatterWorker` carries begin/EOF and descendant-service
completion obligations. These extend lowering state, not the workflow IR.

- Explicit scatter appends exactly one coordinate. Remote enclosing owners open
  before task admission, then match the bound prefix plus that coordinate.
  Ordinary subworkflow nesting adds no coordinate. The two-level restriction
  is removed; no depth selects a different lowering algorithm.
- Dependency consumers resolve pending gathers at their deployment locations.
  Declared output aliases materialize inside-out, once per operation/output/scope
  and destination. Fan-out copies completed values to separate receiver ports.
  Multiple worker sources have distinct stream ports and explicit source closure.
- Ordinary internal steps honor their full-path placements and retain the task ID.
  Tool/port/payload names use full invocation paths so ordinary sibling regions
  cannot overwrite identically named internal operations. Independent admission and explicit same-location receives establish payload
  bindings without sharing variables across parallel fragments. External access
  to undeclared internal ports fails during source resolution.
- Dispatch remains producer-local and independent per dimension. Producer-bound
  input lists are explicitly staged before dispatch; scattered consumers first
  materialize the preceding boundary rather than forwarding occurrences directly.
- Root and ancestor invariants retain their identities and remain reusable.
  A directly exposed invariant gets a visible expression copy constructing the
  output occurrence at the current task ID. Array item type normalization handles
  parser-qualified names without adding scatter boundaries to payload list shape.
- Each actual occurrence/materialization sender owns result begin/EOF. EOF follows
  its admitted work and acknowledged publications, without waiting for the final
  consumer gather or execution. Guarded distribution and stream hints remain.
- Concrete and virtual references and retained scatter documentation are reconciled
  with the corrected consumer routing, bindings, stage shape and closure contract.

Manual CLI regeneration and inspection artifacts are in
`build/recursive-validation/final/`: 11 retained CWL configurations, distributed
1000Genomes, and 17 temporary three-/five-level and other probes under build.
All 28 valid configurations translated twice without logged exceptions and with
identical trace/metadata hashes. The remaining probe rejects an unexposed
internal port as expected. The manifest records all 29 configurations and hashes.
Logs, envelopes, owner bindings, helper metadata, source routes, output types,
empty shape requirements and repeat hashes were inspected. Expected invalid
internal-port access fails clearly even though the CLI exits zero.
Automated tests, parser/compiler/runtime changes and workflow execution remain
excluded. This is translation evidence, not execution proof or user acceptance.

## Current status

This section and its progress/acceptance subsections record the pre-recursive
baseline/history, not instructions to repeat old work. For implementation use the target contract,
implementation handoff and remaining-work sections. Historical line numbers,
removed fixtures and earlier gather/return models do not override those sections.

| Area | Status and evidence |
| --- | --- |
| Recursive translator | Implemented: `WorkflowRegion`, `Invocation`, `ScatterSpec`, full source paths, dependency ordering, longest-prefix deployment lookup and recursive lowering. The region traversal is recursive; the current scatter depth limit and placement-dependent branches still require the uniform lowering work below. See `swirlc/translator/cwl/cwl_translator.py:65`, `:101`, `:655`, `:1112`. |
| Independent input streams | Current emission: producer-local dispatch per dimension, scoped begin/EOF, composed IDs and synchronized operation/full-ID routing. No bundled payload lowering. See scoped scatter progress below. |
| Output gathers | Scoped gathers and explicit parent result joins are emitted. Gathers must follow output dependencies at their consumer locations and retain the sending operation's scope; an unconditional return-to-parent policy is incorrect. Runtime behavior remains missing. |
| Nested scatter | Explicit enclosing receiving owners and keyed gathered lists emitted for two levels. Three-level owner admission remains unfinished and fails clearly. Older fixtures were removed by the user; use `examples/cwl/scatter-nested`. Not execution proof. |
| Methods and invariants | Dotproduct, flat/nested Cartesian contracts and scalar/whole-list reuse emitted. Known direct-root dotproduct lengths are checked during translation (`:1489`); dynamic validation belongs to the future runtime. |
| Worker closure | All scoped input EOFs are received in declaration order before `end()`; result EOF follows worker/descendant joins. Manually inspected; automated tests remain excluded. |
| Review coverage | Latest independent-stream review records 27 regenerated CLI configurations and 16/16 focused checks on 2026-10-06. The earlier 9/9 and 26-configuration records are historical subsets. Broader acceptance is still pending. |
| Ordinary compiler | Existing support retained. `examples/EXAMPLES_STATUS.md` records nine ordinary configurations compiling and 13 generated Python files passing syntax checks on 2026-10-05. No new execution claim. |
| New scatter parser/schema | Missing: grammar lacks `?`, U, guarded choices, `end()` and qualified ports; schemas reject new descriptors/helper types. See `grammar/SWIRL.g4:17`, `swirlc/config/schemas/v1.0/config_schema.json:185`, `:238`. |
| New scatter compiler/runtime | Missing: compiler still requires static `dataName`; runtime uses legacy port state, serial replication and heuristic gather ordering. See `swirlc/core/compiler.py:244`, `swirlc/compiler/default/compiler.py:977`, `:1013`, `:1836`. |
| Advisory hints | Legacy scanner exists but expects old pair/open helper names and does not understand current stream hints (`swirlc/compiler/hints.py:18`). Correctness must work with all hints removed. |

### Active recursive target (2026-10-08)

The user's latest dataflow clarification supersedes the unconditional
return-to-caller design. Each produced value follows the ordinary workflow dependency graph and
deployment routes. Ordinary edges inside one invocation keep their ID and do
not gather. Only an edge crossing a scattered step's output boundary requires
consumer-side reception of worker occurrences and gathering before the dependent
step runs. Workflow boundaries determine identity and output shape; they do not
imply a call/return transport destination. Nested scatter still uses one recursive
lowering rule. Earlier progress records and handwritten/virtual references are
historical designs until reconciled with this consumer-side gather contract.

### Scoped scatter implementation progress (2026-10-08)

- Slice 1B emission now uses composed IDs, plain ports, scoped U/guards, input and
  result begins, all-input scoped EOF closure and result EOF after the worker
  join. Dispatches remain independent and producer-local; metadata carries
  cardinality publication, operation/full-ID routing and gather validation/shape
  contracts. Root collectors bind scope before their parallel receive loops.
- Slice 1C is implemented for the retained two-level example: nested dispatch and
  gather stay in the parent task; remote descendants have enclosing begin/EOF
  receiving owners. The parent opens them before admitting tasks and closes them
  after its replication join. Local nested workers match the already-bound parent
  scope. Gathered lists return through explicit self-send/receive joins, binding
  the result in the parent continuation before it forwards the list.
- Remote nested root-list producers have explicit invocation-begin receivers;
  lists remain at their producer. Arbitrary remote parent-payload routes and
  ancestor-keyed invariants beyond the immediate parent still fail clearly.
- Independent review found that three-level concurrent owners need constrained
  child admission. More than two scatter levels are explicitly rejected until
  that part of slice 1C is implemented; full translator acceptance is pending.
- All 11 remaining CWL example configurations regenerated and produced identical
  traces/metadata on repetition. Manual CLI artifact inspections also covered
  empty/one/many/duplicate inputs, declaration-order dotproduct, two workers,
  multiple outputs, input/output name reuse, scalar/whole-list invariants, flat
  and nested Cartesian products (including an empty dimension), independent
  producer locations, empty outer lists and local nested workers. Known unequal
  dotproduct lengths and unsupported third-level nesting produced clear errors.
  Artifacts/logs are under `build/new-syntax-validation/`.
- No unit tests, compiler/runtime execution, downloads, commits or remotes.
  The user removed relocated fixtures; do not recreate them. Validation now uses
  retained examples and temporary manual artifacts under build, not those tests.

### CWL example cleanup (2026-10-08)

- Keep five ordinary workflow examples, one paired dotproduct scatter and one
  two-level nested scatter under `examples/cwl`. The nested input includes an
  empty middle list. Both scatter READMEs link the intended handwritten begin
  references and distinguish them from current legacy scatter emission.
- Historical cleanup: larger scatter and CWL 1000Genomes cases were moved to
  `tests/fixtures/cwl`, then deleted by the user. Do not move or recreate them.
  Distributed `examples/1000genome` stays.
- All 11 remaining example configurations translate successfully. Basic outputs
  are under `build/cwl-examples`; simple scatter traces are under `build/scatter`
  and `build/scatter-nested`. No automated tests or compiler/runtime checks run.

### Translator implementation progress (2026-10-08)

- Started slice 1A: CWL payload references now keep payload names, identities and
  binding status separately. Ordinary datasets, exec flows, sends/receives,
  defaults and final gathers emit root envelopes; task-local outputs retain the
  existing task identity until slices 1B/1C replace the legacy key syntax.
- Defaults are staged as typed root values, including expression inputs and
  subworkflow defaults; step defaults override process defaults. Workflow aliases
  preserve the source identity. Unsupported multi-source ordinary inputs fail
  clearly instead of silently selecting the first source.
- The shared ordinary renderer used by DAX emits root envelopes and data-to-port
  receives. Fixed its dangling parallel separator for dataset-only locations.
- Manual CLI validation regenerated all 26 available CWL StreamFlow configurations
  and the distributed 1000Genomes configuration under
  `build/envelope-validation/`. Logs and trace/metadata files were inspected;
  repeated translation produced identical artifacts for all 27 configurations.
  Additional manual probes checked step/subworkflow defaults and distributed
  shared rendering. System Python lacks dependencies; use `.venv/bin/python`.
- No automated unit tests, compiler changes, runtime execution, downloads, commits
  or remote operations. No DAX fixtures were available; its shared renderer was
  checked directly. Complete syntax acceptance is still pending: begin/scoped EOF,
  composed IDs, scoped U/guards, plain ports and explicit nested receiving owners
  remain for slices 1B/1C. Legacy nested traces still contain unbound detached
  parent-key references and must not be interpreted as complete target traces.

### Acceptance record

- 2026-10-02: working simple slice accepted ("looks correct to me"); nine focused
  checks recorded. This is historical acceptance of that slice.
- 2026-10-05: independent-stream correction implemented after the user's model
  clarification and routing confirmation; corrected artifacts presented for review.
- 2026-10-06: all-input EOF closure update and 16 passing focused checks recorded
  in `NEW_SYNTAX_INDEPENDENT_STREAMS_REVIEW.md`.
- Complete corrected translator acceptance is not recorded. Phase 2 remains
  gated on that acceptance; passing emission checks do not establish it.

## Target language and execution contract

This target supersedes bracket-qualified ports, `?key_N` tuple bindings and
implicit parent-task template activation. Current implementation presence above
is a baseline, not evidence that this target already works. Design references:
`examples/swirl/1-nested-scatter.swirl`,
`examples/swirl/2-nested-scatter.swirl` and
`examples/swirl/3-nested-scatter.swirl`. The conceptual counterparts are
`examples/swirl/1-nested-scatter-virtual.swirl` and
`examples/swirl/2-nested-scatter-virtual.swirl`. Reference numbering describes
example depth, not separate translator algorithms. Apply the depth-indexed
variable convention below when updating these references; the current handwritten
files still use earlier names.

### Uniform data envelopes

Every actual data value has the form `(payload, id)`, including workflow input
memory, exec inputs/outputs, sends, receives, invariant copies, defaults and
whole lists. A list remains one payload until explicitly scattered. A tool's
payload can itself be a tuple; the outer pair is always the identity envelope.

Ordinary top-level data uses `root`, the empty key path:

```swirl
<l0, {(p_input, (d_input, root))},
  exec(s_work, {(p_input, (d_input, root))}
    -> {(p_output, (d_output, root))}, {l0})
  .
  send((d_output, root) -> p_output, l0, l1)
>
```

Receives always use data-to-port notation, for example
`recv((d_output, root) -> p_output, l0, l1)`. An ordinary step executing inside a
scatter task preserves that task's ID instead of resetting it to `root`.
`begin` and `eof` are reserved control payloads and also carry IDs:
`(begin, scope)` and `(eof, scope)`. No bare data or bare EOF remains in newly
emitted traces. Ordinary one-shot communication does not require stream
begin/EOF merely because its value now has an ID.

`U(port, (collection, scope))` denotes a scoped collection with one paired
data/identity operand. Its elements are envelopes; gather produces `(list_payload, scope)`,
including `([], scope)`. The collection name is an identifier, not an additional
payload requiring another envelope. Use this explicit scoped form in dispatch
collection outputs as well as gather inputs.

### Keys, matching and scope

- `root` is the literal empty path. `?scope_0` binds the outermost invocation ID;
  `?iteration_1`, `?iteration_2`, ... bind one coordinate at their scatter level.
  Full paths can be written as `?scope_0 / ?iteration_1 / ?iteration_2` when the
  receiver inherits the earlier bindings. Cartesian coordinates are tuples
  treated as one component; coordinate order follows the scatter declaration.
- `?scope_d` may name a complete invocation path at depth d only when a receive
  actually binds it. It is never an implicit alias for the composed parent path.
  A fresh owner may use `?scope_d / ?iteration_(d+1)` for its immediate children.
  The subscripts are generation conventions, not new language syntax.
- In a receive, every already-bound prefix component matches exactly. A fresh
  iteration binds exactly one additional coordinate; a bound iteration requires
  equality. No unrestricted prefix matching, string concatenation or silent
  variable overwrite is permitted.
- Admission into an enclosing owner must match one immediate child of that
  owner's bound scope. For example, with `?scope_0` and `?iteration_1` already
  bound, `(begin, ?scope_0 / ?iteration_1 / ?iteration_2)` admits that matrix's
  list invocation, not another matrix's list. A freely bound `(begin, ?scope_2)`
  alone does not establish that ownership relation.
- Match begin/EOF against the complete control pattern exactly. Destructuring a
  composed begin ID binds its explicitly fresh component; it does not introduce
  an implicit data-prefix rule or leave a second scope variable silently aliased.
- Each replication instance owns its fresh bindings. Sibling operations at the
  same depth retain distinct lexical owner environments. Where emitted code
  inherits bindings, allocate distinct internal names rather than shadowing them.
  Operation/owner paths disambiguate ports and metadata; depth alone is not an
  operation identity.
- `[port has data in scope]` and `U(port, (collection, scope))` select only that
  operation's immediate-child data in that invocation. Controls are excluded.
  Independent operations may both have `root / 0` without sharing state.
- Ports remain plain identifiers. Preserve `d_name`, `stream_d_name` and
  `element_d_name`; add only operation/input disambiguation that is needed.

### Stream lifecycle and communication

Each producer sends `(begin, scope)` for each stream to each selected worker,
including zero-task streams. Its synchronous send completes when that worker
receives it; the worker receives all required begins before admitting data.
There is no extra global barrier requiring every producer to acknowledge every
other producer. Begin messages from the required producers identify the same
invocation. Each producer can then dispatch and distribute independently.

At depth d, the first data receive binds `?iteration_(d+1)`; subsequent
input receives match the same complete ID under that invocation's scope. Deterministic/synchronized moves route matching full keys
to the same worker within the same scatter operation. Each input has its own
producer-local dispatch and stream; no pair/open payload bundling is reintroduced.

The worker's termination branch receives `(eof, invocation_scope)` from every required
input in declaration order, then calls `end()`. Internal result EOF follows the
replication join, after committed work and acknowledged internal result sends
finish. The consuming gather receiver receives begin before its result loop and closes
each source independently. After all contributing sources join, gather produces
one list envelope at the producing invocation's scope for the consuming step.
Further ordinary communication of that completed list needs no extra stream
lifecycle. Transport of individual worker results does require scoped begin/EOF.
Missing required keys on a closed stream and mismatched cardinalities are
errors, not blocked forever or silently incomplete gathers.

Move atomically claims one matching occurrence; send copies a selected value.
Both complete only after the corresponding recv commits. Tuple matching and
binding are atomic; mismatch consumes nothing. Control messages are never
accepted by a generic data branch or included in U snapshots. Empty means
exhausted only after dispatch has finished constructing its finite collection.

`end()` closes the nearest replication owner, stops admissions and drains
committed instances. Sequence waits for all activated descendants; parallel
composition joins both branches. Waiting, uncommitted offers are not completion
obligations. Nested children must progress while their parents wait.

### Recursive workflow dataflow and virtual view

Workflow boundaries determine which output edges exist. If subworkflow A is
scattered and contains ordinary steps A1, A2 and A3, each iteration runs those
steps inside one invocation of A. They communicate through ordinary send/recv
and exec operations at the same task ID; membership in a scattered subworkflow
does not independently scatter each internal step or gather its internal edges.
Only an internal step with its own scatter declaration adds another coordinate
and another receive/gather boundary.

A step B outside A can reference only A's declared workflow outputs, never the
internal output ports of A1/A2/A3 directly. A exposes an internal value through
its output mapping; the corresponding occurrence retains A's iteration ID until
consumer-side gathering presents the scattered A output to B. A scalar output
becomes a list across A's iterations; a list output preserves an additional list
level. B may consume that gathered value normally or explicitly scatter it again.
Physical transfer optimizations must preserve this logical output boundary.

For any workflow invocation at ID S:

1. Bind its declared inputs with their actual identities. A whole list stays one
   payload at S until an explicitly scattered step dispatches it.
2. Lower ordinary tools/subworkflows through the existing recursive traversal at S.
3. For a scattered step, independently dispatch each dimension at its actual
   producer, append one coordinate to S and recursively lower its process for
   each admitted child. The body may contain ordinary steps or more scatters;
   use the same recursive call at every depth.
4. Route each declared output to its actual downstream consumers within the
   containing workflow, just as normal sends follow workflow dependencies.
   Cross a subworkflow boundary only through its declared output mapping; do not
   connect an external consumer directly to an arbitrary internal step port.
   Send the worker occurrence at its full child ID. Destination is determined by the output edge and deployment, not
   by caller, parent worker or a fixed common collector. Workflow output aliases
   expose values to the containing workflow without inventing a return route.
5. For an output edge crossing a scattered step's boundary, open a receive
   owner at the consuming location for S and this producer
   operation/output. Its loop receives immediate-child results from the relevant
   workers. Close each source on its exact scoped EOF, join all contributing
   sources, then gather `(list_payload, S)` before executing the consuming step.
   Preserve coordinate order, expected cardinalities, duplicates validation and
   empty/nested shape. Fan-out must stage/copy values for each consumer; receiving
   for one edge must not steal another edge's occurrences.

Nested dispatch belongs inside the current worker's task body. A receive/gather
for an inner output may likewise run inside a downstream task body at the same
invocation depth, alongside its producers. The outer iteration is already bound;
the receiving replica binds only the next coordinate. Its scoped U and EOFs must
exclude every other outer iteration's data. If nested outputs become parent-level
outputs, gather one level at the relevant consumer before that list is used as a
single payload by the enclosing operation. Never flatten across those boundaries.

“Same depth” describes the receive owner's invocation scope and stream keys. It
does not imply that the consuming CWL step must itself declare scatter. A scattered
step can feed a non-scattered step that consumes its gathered array; a subsequently
scattered consumer explicitly dispatches that array again according to its own
scatter declaration. Do not fuse adjacent scatter steps or forward occurrences
one-for-one merely because both are scattered; preserve their declared CWL
input/output types, methods, ordering and list boundaries.

`scatter_send`, `scatter_exec` and `scatter_recv` are conceptual shorthand for
producer dispatch/result transport, mapped workflow execution, and consumer-side
scoped reception/gathering. Their routes follow ordinary output dependencies.
The current virtual files' eager worker-local gather/return interpretation must
be updated before treating them as accepted expansions. Virtual operations may
pipeline internally; they are not implemented grammar, a new public IR or a
required runtime API. First emit the concrete trace primitives; public virtual
syntax remains separately deferred.

### Recursive receiving owners and reusable inputs

Each receiving owner carries the enclosing invocation path and logical operation
identity. It opens with explicit begin, repeatedly admits only immediate-child
invocations belonging to that path, and closes on the matching enclosing EOF.
A child's owner repeats exactly the same rule. Concrete traces therefore contain
as many replication/owner layers as the workflow needs, possibly distributed
across locations; the translator implements one recursive rule, not a depth-sized
set of special cases.

Establish admission by matching the bound enclosing path plus a fresh coordinate,
then use those bindings consistently for input begins, data, output routes and closure.
If a complete fresh `?scope_d` is needed in a remote owner, the opening protocol
must explicitly establish its relation to the enclosing owner. Do not receive
an unconstrained scope and merely assert ownership in comments or metadata.
The three-level reference demonstrates constrained component matching; lowering
may keep that composed form rather than invent a scope-alias primitive.

Open descendant services before admitting parent work, even for empty streams.
Close each service only after its admitted parent tasks and acknowledged dependent output
transfers join. Every accepting loop has a matching enclosing EOF. Begin sends
across workers/independent streams must allow parallel progress; invariant
setup and output receivers must not create synchronous startup cycles.

Preserve actual producer locations, existing deployment lookup and worker-pool
policy. Local and remote owners follow the same logical contract; route-specific
send/recv scaffolding is permitted, separate depth implementations are not.
Do not move whole input lists to a controller merely to simplify bindings.

Scalar and whole-list invariants remain reusable. Root envelopes stay root;
ancestor-specific values retain their actual ancestor ID. Pass the needed
payload/identity bindings through explicit routes without treating invariants as
scatter dimensions. Any identity change requires a visible operation. Consumed
output bindings must be established in the downstream owner by a receive or another
explicit owner-visible operation, never by assuming that parallel branch
variables are shared. A local self-send/receive is permitted when that boundary
requires it, but is not mandatory for every local invocation.

### Implementation handoff: edge classification and recursive contract

This section is normative for the next implementation agent. The latest target
contracts and this handoff override historical progress records and inconsistent
handwritten/virtual examples. Read the existing translator before editing; reuse
its region tree, dependency ordering, deployment lookup and payload metadata.
Reconcile the reference traces with this contract during implementation rather
than copying their older gather placement literally.

#### Classify the logical edge before emitting communication

| Edge | Envelope at producer | Required consumer action |
| --- | --- | --- |
| Ordinary A1 -> A2 inside one A invocation | `(value, S / i)` | Ordinary receive if remote, then ordinary exec; retain ID, no gather |
| Ordinary nested workflow alias without scatter | `(value, S / i)` | Resolve declared output alias; retain ID and payload shape |
| Scattered A -> external B through A output port | One `(value_i, S / i)` per task | Receive/gather all A occurrences at S, then give B `(list, S)` |
| Scattered C inside A -> ordinary A3 | One `(value_j, S / i / j)` per C task | Receive/gather C at `S / i`, then give A3 `(list, S / i)` |
| C output exposed directly as A output | C occurrences at `S / i / j` | Materialize C's list at A's declared output interface at `S / i`; publish that list as one A occurrence; B gathers A at S |
| Gathered A -> another explicitly scattered step B | `(list, S)` | Gather A first; B then dispatches using its own declared method and coordinate owner |

`S / i / j` in this table is explanatory notation, not a literal generated
variable name. A declared workflow output interface is a logical consumer when
it exposes an internal scattered output. It must account for that internal
gather even when no ordinary internal step consumes the value first. It does
not create an unconditional send back to a caller. Its physical receive/gather
owner follows the resolved output route and existing placement contract; if a
consumer location performs several stages, those stages still retain separate
logical ports, scopes and completion obligations.

Resolve aliases through declared region outputs, recording the scatter
boundaries crossed in order. Materialize them from the innermost boundary outward,
exactly once per edge stage. Do not count ordinary subworkflow nesting as scatter
depth. Do not treat a list's payload nesting as additional scatter boundaries.
A list-valued output remains one payload during its parent's gather. Neither
alias resolution nor a co-located route may flatten or silently drop a boundary.
Reject undeclared external references to internal ports before trace emission.

#### State carried by one recursive lowering invocation

Extend the existing context/value representation only where needed; these are
logical fields, not a requirement for new classes or a second IR:

- Current region and full invocation/operation path, the actual bound invocation
  ID expression, and scatter depth used only to allocate variable names.
- An explicit binding environment: which scope/coordinate/payload symbols are
  bound, which may be bound freshly, and their lexical owner. Represent paths
  structurally before rendering; do not recover them by splitting SWIRL strings.
- Available payload references with their payload types, actual IDs, producer
  locations/ports and readiness/completion obligations. Reusable ancestor
  references retain their original IDs and need explicit routes if remote.
- Resolved logical consumer edges, declared output alias mappings, and any
  pending boundary stages (operation, enclosing scope, child coordinate shape,
  declared method and expected cardinalities). Distinguish a child-occurrence
  stream from a completed list value; both cannot be represented as an ordinary
  already-available scalar/list with no completion condition.
- Existing deployment targets/worker reservations, and owner-local fragments at
  participating locations with explicit opening/closing obligations per source.

The recursive result supplies owner-local producer/consumer fragments, exposed
output references including pending gather stages, and obligations needed to
publish those outputs and close admitted descendants. Returning a result from
this Python lowering function is not a SWIRL data send or a return-to-caller
policy. A descriptor becomes usable by exec only once its required receive,
gather and binding actions have been emitted in the consuming owner.

For each region, resolve output consumers and aliases before finalizing terminal
sends; output placement cannot be discovered by scanning already-rendered text.
Use the region dependency graph to connect outputs to each consumer. Every
result source is the actual sender location for that edge stage, not necessarily
the worker that executed the original tool. Route metadata and EOF accounting
must agree with the generated sends/receives, including co-located staging.

The algorithm is one recursive traversal:

```text
lower_region(region, context):
    resolve declared local edges and output mappings
    for invocation in dependency order:
        bind inputs through their edge-specific ordinary/scatter boundary stages
        if invocation is explicitly scattered:
            outputs = lower_scatter(invocation, context)
        else:
            outputs = lower_process(invocation.process, context at the same ID)
        register outputs against their declared consumers/output aliases
    expose only the region's declared outputs and their completion obligations

lower_scatter(invocation, context):
    define one operation with enclosing scope S and its declared worker pool
    open required producer, worker and consumer owners for S
    independently dispatch each dimension at its actual producer
    for each admitted child coordinate c in the emitted worker replication:
        child = context at S / c, with inherited bindings and fresh child owner
        lower_process(invocation.process, child)
        publish only declared step outputs through their resolved edges
    close input/result sources and descendant services after their proper joins
    expose child-output streams plus consumer materialization obligations

lower_process(process, context):
    tool: emit existing command/expression exec at context ID
    workflow: lower_region(process, context)
```

The `for each admitted child` is emitted runtime replication, not a Python loop
over job values or static unrolling. Recursive lowering visits the CWL process
structure; generated owners handle dynamic invocation IDs and cardinalities.
There is no branch selecting algorithms for depths 1, 2, 3 or N. Placement may
select local reuse versus explicit communication but not different semantics.
Apply full-path deployment bindings to ordinary internal steps as well: being
inside a scatter does not justify forcing every A1/A2/A3 onto the parent worker.
Keep the existing approved worker-pool reservation policy separate from recursion.

#### Receiving-owner protocol to emit at every level

A scope owner is identified by operation/route and enclosing invocation ID, not
by location alone. Generate its enclosing begin/EOF protocol recursively so that
all parent prefix components are already bound before child admission. At the
root, a one-shot begin binds `?scope_0` to `root`; this is bootstrap, not a separate
root-scatter lowering algorithm. At a deeper receiver, a composed begin pattern
matches those bound components and binds exactly the next fresh coordinate.

A schematic service body for bound parent pattern P is:

```text
recv((begin, P) -> enclosing_control, enclosing_owner, receiver)
.
!(
    (
      recv((begin, P / ?iteration_d) -> invocation_control,
           invocation_source, receiver)
      .
      // P / ?iteration_d is now this admitted invocation's exact ID.
      // Receive its required input begins and invariants in their owner.
      // Run its data replication/recursive process, scoped to that ID.
      // Publish declared outputs; join work and acknowledge routed sends.
      // Close its internal result streams and descendant services.
    )
    +
    (recv((eof, P) -> enclosing_control, enclosing_owner, receiver) . end())
)
```

This skeleton denotes generated fragments, not a new public syntax. P is a
structural path supplied by the enclosing binding environment, never an unbound
variable or an implicit alias. A first input begin can serve as invocation
admission instead of a separate control message if it uses that same constrained
pattern; emit exactly one matching send/receive protocol, not both accidentally.
For example, an inner service inside matrix `?scope_0 / ?iteration_1` admits
`(begin, ?scope_0 / ?iteration_1 / ?iteration_2)`. Bound iteration 1 excludes
another matrix. Its data loop adds fresh iteration 3. Replicas bind iterations
2 and 3 locally; an EOF at the matrix scope closes the invocation-accepting loop,
while EOF at the list scope closes only that list's data loop.

The enclosing execution owner sends service begin before admitting its parent
tasks, even with zero tasks, and service EOF after those parent tasks and their
routed output sends join. Each invocation's dimension producers send input begin
before data and input EOF after finite publication/distribution. Each actual
result producer sends result begin before results and result EOF after its work
and sends join. The consuming receiver closes each source separately, joins all
receive loops and gathers once. A completed gathered value sent on an ordinary
edge is one-shot and does not acquire another begin/EOF lifecycle automatically.

A producer's completion obligation is its own admitted work and acknowledgement
of its output occurrences committed into the consumer collection, not the
downstream consumer's EOF join, full-scope gather, exec or owner closure. Emit producer result EOF after those occurrence sends join; then the
consumer can finish gathering and execute. If output-interface materialization
introduces another sending stage, that stage owns its result EOF and emits it
only after its own publications join. The original tool/parent worker must not
emit EOF on behalf of an unfinished materialization sender.
Waiting for B's completed gather
before emitting A's EOF would create a cycle (B needs that EOF). A parent task
waits for an internal gather only when it needs that completed value to execute
or publish a declared output occurrence at its own task ID.

Schedule independent begin sends and receive services in parallel where synchronous
acknowledgements would otherwise form a cycle. Receive all required dimension
begins before data admission; match subsequent input coordinates against the
first input's bound coordinate. Invariant sends must be able to progress while
workers complete startup. Consumer loops must be active while producers send;
never put the receive after a sequence that waits for those sends to finish.
Give every owner/source its exact closure route, including empty worker streams,
multiple outputs and sibling scatter services. Joining an enclosing owner waits
for committed descendants, not forever-blocked uncommitted offers.

#### Concrete walkthrough and review checklist

For scattered A at S with ordinary `A1 -> A2 -> A3` and external B:

- A's dispatch/worker loop admits task `S / i`. A1/A2/A3 run ordinary execs at
  `S / i`. Remote internal edges send/receive exactly that ID; local edges reuse
  ready values. There are no A1/A2/A3 gathers merely because A is scattered.
- Resolve A's exposed output to A3's payload, preserving A3's type and the task
  ID. Publish only the declared A output edge to B's receive owner. B's loop
  receives all A workers' `S / i` outputs, joins scoped EOF and gathers at S.
- B's exec receives the completed gathered list at S. A list payload from A3
  makes this a list of lists; A3's scalar payload makes it a list of scalars.
- If A2 explicitly scatters C, C's task IDs become `S / i / j`. A3 gathers C at
  `S / i` before running normally. If C is exposed directly as A's output, the
  output-interface materialization replaces A3's consumer role: first gather C
  at `S / i`, then publish that list as A's occurrence for B's gather at S.

For each manual artifact, trace an empty case and two concurrent parent IDs
with different child cardinalities from begin to final EOF. Check every fresh
binding at its first receive, every bound prefix match, every output mapping,
every gather boundary/type, and every closure obligation against actual routes.
Also inspect fan-out, two independent dimensions, sibling scatters, multiple
outputs, local/remote steps and invariants. A lexical/binding/route inspection
using existing translator structures is allowed; do not build a new SWIRL parser
or invoke automated unit tests while the user has excluded that work. Runtime
ordering/progress remains unverified until the later compiler/runtime phases.

### Dispatch, gather, metadata and hints

Dispatches share scoped cardinalities, not other producers' payloads. Validate
dotproduct alignment; Cartesian dispatches duplicate their own values across
consistent full coordinates. Each helper publishes its own length before
waiting for peer lengths. Gather retains complete shape state for empty
Cartesian dimensions, checks expected/duplicate keys, and reconstructs declared
order independently of completion order, filenames or payload contents.

Metadata distinguishes payload dependencies and their types/values from identity
expressions, stream scopes, lifecycle routes and helper contracts. Concrete
root envelopes must not be misclassified as dynamic variable bindings. Do not
register IDs, composed ID expressions, begin or EOF as file dependencies. Tool
commands, expression evaluation and processors operate on payloads, never on
envelopes as accidental tool arguments. The new compiler will implement that
unwrapping/wrapping contract.

Keep CLI command/version headers. Keep advisory `scatter_stream` and
`gather_stream` hints outside the marked parentheses, naming collection,
location and plain port. Keep worker hints. Required begin/scope/matching rules
must remain visible in traces and metadata when all comments are removed.

## Original implementation sequence and current metadata stage

Sections 1, 2, 3, 4 and 2D.1 below are completed-baseline design/checklists, not
the active work queue. They retain wider verification obligations that should not
be inferred from the four plain examples alone. Start new implementation at 2D.2;
historical requests for per-slice test approval do not apply to this handoff.

### 1. Update the translator, then complete translator acceptance

Implementation and manual emission validation are now recorded above. Complete
translator acceptance by the user remains pending; the slices below retain the
acceptance contract and must not trigger repeated work or compiler changes.

Implement the following bounded slices using manual translation and artifact
inspection. The user has asked to ignore automated tests and compiler work for
now; do not add/run tests or enter Phase 2 until they ask to resume that work.
Keep making routine implementation progress within the authorized translator
scope. Complete translator acceptance still precedes compiler/runtime work.

#### 1A. Uniform ordinary envelopes

- Extend the existing value representation to track payload and ID separately
  from producer location and payload type. Reuse the recursive region model.
  Use a small cohesive record only if the existing tuples become ambiguous;
  do not introduce a second IR or a text parser for generated key expressions.
- Update root datasets, `_tool_trace`, `_bind_region_inputs`, workflow aliases,
  ordinary send/recv setup, defaults and `_output_descriptor`. Replace string
  heuristics such as `data.startswith("(?")` with the actual binding/ID fields.
- Audit every emission path, including `AbstractTranslator.render` and DAX:
  the user requires every data piece to carry an ID, not only CWL scatter data.
  Apply root envelopes in the shared ordinary renderer while preserving its
  existing deployment/dataflow choices. No unrelated DAX feature work.
- Review basic/nested/expressions/lists/lists-input and available DAX fixtures:
  all selected values are envelopes, types remain payload types, whole arrays
  are not scattered, producer locations and command metadata are preserved.

#### 1B. Root scatter scopes

- Replace `?key_N` uses with `root / ?iteration_1` on root producers and
  `?scope_0 / ?iteration_1` after receiver begin bindings. Use the same
  depth-indexed binding allocator at deeper levels; no depth-specific emitter.
- Emit begin for every input/worker and result source/collector, including empty
  streams. Emit scoped EOFs inside the all-input termination branch and after
  worker joins. Root remains explicit for invariant references as appropriate.
- Emit scope-qualified guards/U and plain ports. Preserve independent dispatch
  and gather continuations and deterministic/synchronized routing.
- Review zero/one/many/duplicate cases, multiple producers, multiple outputs,
  same-name inputs/outputs and all methods. Walk through synchronous startup,
  data and closure to rule out dependency cycles.

#### 1C. One recursive scatter lowering path at every depth

- Reuse `WorkflowRegion`, `Invocation`, `ScatterSpec`, `lower_region`,
  `lower_invocation` and `lower_scatter`. Ordinary tool/region lowering is the
  recursion's base case. At a scattered invocation, construct one scope owner,
  dispatch its dimensions and recursively lower its process inside each task.
  A nested scatter is encountered by that normal recursive descent, never by a
  special one-level/two-level/N-level emitter or repeated whole-trace rewriting.
- Extend the existing lowering context only as needed to carry the logical
  owner/operation, bound invocation path, fresh coordinate, producer routes,
  input/output values, dependency routes, consumer gather ownership and child-service
  open/close obligations.
  Keep these fields structured; do not parse rendered identity strings, add a
  parallel IR or introduce a generic framework. Depth is useful for variable
  naming, not for selecting different lowering behavior.
- Generate `?scope_0`, `?iteration_1`, `?iteration_2`, ... deterministically.
  Allocate fresh owner-local bindings for sibling operations. Introduce a full
  `?scope_d` only with a visible receive that establishes its identity and owner
  relation; otherwise retain the bound composed prefix.
- Replace unconstrained remote child admission with structural matching of the
  bound enclosing scope and exactly one fresh coordinate. Carry these bindings
  through all begin/data/EOF actions and output dependency routes. Apply the same rule
  recursively for local workers, remote workers and nested remote producers.
- Put nested dispatch in the current task's workflow body. Send worker outputs
  to their actual consuming steps. Construct consumer-side receive loops at the
  producing invocation depth; drain all relevant worker sources, join closure and
  gather each declared input list before consumer execution. Do not replace the
  current gather with an unconditional worker-local gather/return-to-caller path.
  Multiple outputs and fan-out need separate scoped collection ownership/routes.
- Preserve subworkflow encapsulation: ordinary A1/A2/A3 edges inside scattered
  A stay ordinary at A's task ID. External B receives only A's exposed workflow
  outputs after the applicable gather, not direct internal ports. Audit region
  output aliases and dependency routing to enforce this at every recursive level.
- Construct per-owner fragments with explicit inputs, outputs and completion
  obligations. Recurse with a child context; join child work before gathering,
  publishing gathered inputs and closing enclosing services. No detached fragment may
  reference an unbound parent variable or depend on silent branch binding exports.
- Preserve source placement, existing worker reservations, independent dimension
  dispatch, scalar/whole-list invariants and ancestor IDs. Resolve currently
  rejected ancestor/remote payload routes through explicit bindings and transfers;
  do not remove validation by silently relabeling values.
- Prove constrained admission and closure on a three-level concurrent example,
  then remove the hard-coded two-level rejection. Verify one, two, three and a
  generated deeper case (for example five levels) through the same lowering
  path. Do not recreate user-deleted fixtures or add production depth limits.
- Stop this slice when arbitrary finite nesting emits bound, isolated owners and
  correct dependency-routed, consumer-side list boundaries. Compiler/runtime execution and public
  virtual-operation syntax remain separate later work.

#### 1D. Metadata, hints and example consistency

- Update helpers/routes/scope descriptors for explicit begin/EOF and composed
  IDs. Remove superseded activation and bracket-channel descriptors, while
  retaining cardinalities, gather shape and routing requirements.
- Update current reference traces and manual generated artifact inspections for
  depth-indexed names, recursive owners and dependency-routed consumer gathers.
  Keep virtual references consistent with their concrete expansions. Automated
  emission and DAX/shared renderer test updates remain deferred by user request.
- Keep trace naming, outside-parentheses hints and CLI provenance consistent.
  Historical examples may be labeled as such; do not hide incompatible outputs
  by weakening old compiler tests or pretending the old schema accepts them.

#### 1E. Final translator review

- Regenerate every retained CWL configuration in separate output directories,
  the retained distributed 1000Genomes workflow and applicable available DAX
  examples. Generate small manual deeper-nesting inputs under build; do not
  restore removed CWL/fixture directories. Inspect actual return
  status, logs, trace and metadata; `tmp_main.py` does not propagate exit status.
- Check every dataset/action envelope, binding order, ID composition, begin/EOF
  counterpart, scope filter, empty shape, invariant reference, source/worker
  location and hint boundary. Repeat translations to establish determinism.
- Audit known source/default/name collisions before broad preservation claims.
  General CWL `linkMerge`/`pickValue` remains unsupported unless separately
  agreed; unsupported cases must fail clearly rather than choose one source.
- Record explicit acceptance of the complete corrected translator. Automated
  regressions remain deferred until the user resumes tests. Old compiler rejection
  is expected until Phase 2; translation is not runtime execution proof.

### 2. Implement parser, metadata and compiler structure (Part 2A)

#### 2A.1 Shared syntax, descriptors and binding contract

Reach: `grammar/SWIRL.g4`, generated `swirlc/antlr/*`,
`swirlc/core/parsing.py`, `core/utils.py`, `core/entity.py`, `core/compiler.py`,
both config schemas and their validator. Both targets consume this same contract.

- Freeze concrete syntax and operator precedence against accepted translator
  artifacts and handwritten references. Cover payload/ID envelopes, literal root,
  variable and tuple patterns, composed paths, U(port, (collection, scope)),
  scoped guarded choices, begin/EOF and `end()` distinct from zero.
- Regenerate with the already pinned ANTLR 4.13.2. Keep strict parse-error
  rejection. The existing regeneration script downloads/builds Docker and removes
  temporary files; invoking it must respect remote/destructive-operation rules.
- Replace string interpretation at `get_pair`/`get_flow` and visitor boundaries
  with the smallest structured terms for payloads, identities, patterns and
  collections. Preserve declaration order where semantically required. Resolve
  an ordinary envelope's underlying payload in `dependencies`; do not register
  IDs, controls or identity expressions as file dependencies.
- Register static dataName, dynamic binding and collection descriptors explicitly.
  Validate exact exec port ownership and helper/shape/route references. Preserve
  payload types instead of defaulting unknown dynamic/control terms to file.
  Support the emitted scatter_dispatch and scatter_gather descriptor contracts.
  Metadata v1.1 currently only inherits v1.0; decide schema ownership explicitly,
  without adding a version solely to avoid fixing its loader.
- Track lexical owners, definitely available payload/ID bindings, fresh pattern
  bindings and inherited prefix matches. Receive matching, exec output production
  and moves establish bindings according to their action semantics. Sequence can
  use established bindings; independent parallel branches cannot silently export
  variables to siblings. Give each replica a fresh child environment. Resolve
  `end()` to its nearest replication owner and reject unbound construction terms.
- Compatibility recommendation: retain ordinary legacy fixtures by normalizing
  bare values to root at the shared boundary. Inventory supported legacy scatter
  before changing it; retain or explicitly reject its distinct syntax/contracts.
  Never silently reinterpret pair/open workflows as independent streams. Decide
  this policy before editing grammar, descriptors or public compiler hooks.

Exit artifact: accepted ordinary/scatter/deep examples parse, validate and register
without missing metadata or unbound owner references. Invalid bindings/descriptors
produce useful diagnostics. This proves frontend structure, not execution.
After implementation satisfaction and test authorization, update focused parser
and metadata checks; do not weaken validation to admit unsupported descriptors.

#### 2A.2 Complete the trace target

Reach: `BaseCompiler`/`CompileVisitor` hooks, `StandardCompiler`/`TraceNode`,
`compiler/trace/compiler.py`, and trace assertions in `tests/test_compiler.py`.
Change corresponding DefaultTarget signatures with the shared interface; no
target-specific parser or second workflow IR.

- Keep existing per-location Markdown files, thread blocks and waits. Print exec
  input/output envelopes, U terms and mappings, not only the tool name.
- Show begin/EOF patterns, bound versus fresh components, scoped guards, operation
  and owner identity, replication admission and its completion join. Render
  `end()` as closing/draining its owner; retain zero as the null process.
- Make sequence/parallel joins readable inside replicated and nested bodies.
  A closure branch must remain visibly separate from admitted work. Print dynamic
  patterns symbolically; this backend does not execute helpers or enumerate tasks.
- Hints must not supply required structure. Ignore unsupported legacy hints
  safely or update their scanner; removing comments must preserve the same
  semantic trace. Keep naming deterministic across repeated compilation.

Exit artifact: trace output for ordinary, root scatter, nested and three-/five-level
examples exposes every binding, boundary and join needed to review the contract.
After satisfaction, authorize focused trace assertions and hint-free equivalence
checks. Trace readability does not prove progress, atomicity or gather values.

### 3. Implement bindings, scoped state and communication (Part 2B)

Reach: Python generation/runtime in `compiler/default/compiler.py`, shared action
terms and entity data access. Reuse framing, location launch, SSH/SLURM integration,
payload serialization, command execution and existing expression evaluation where
their behavior matches the contract. Keep new matching/state logic in one cohesive
runtime unit rather than scattering special cases through emitted strings.

- First restore ordinary root-envelope execution: initialize envelope datasets,
  resolve action inputs, unwrap payloads for commands/expressions/processors and
  wrap outputs with the action's actual ID. Whole lists stay one payload.
- Introduce occurrence storage and lookup isolated by logical operation/route,
  port and full identity, plus per-owner binding environments. Separate controls
  from data and retain per-source, per-scope lifecycle state. Location or depth
  alone is not a state key. Reusable root/ancestor values retain their identity.
- Match payload and ID patterns atomically; mismatch binds/consumes nothing.
  Bound prefixes compare exactly and a fresh child coordinate adds one component.
  A receive for one operation/parent cannot steal another's occurrence.
- Send copies; move atomically claims/removes only its selected occurrence.
  Replace destructive list-pop and per-port overwrite behavior. Acknowledge a
  transfer after receive/collection commit, rather than on socket queue arrival.
  Preserve local self-communication and the same protocol across remote routes.
- Extend existing framing with identity/control information while keeping payload
  serialization separate. Preserve declared scalar types across transport; the
  current scalar decoder returns text. Directory transport is currently explicitly
  unsupported: retain a clear rejection until separately implemented, rather than
  claiming general File/Directory support from ordinary file transfer.
- U snapshots contain only that operation's immediate-child data in the selected
  scope; exclude begin/EOF. Closed-stream missing keys raise an error. Propagate
  transport, exec and matching failures to waiting actions and the launcher so
  they do not hang or report successful partial output.

Exit artifacts: ordinary local and split-location examples execute unchanged in
payload meaning; a small keyed exchange demonstrates exact selection, copy versus
move, reusable invariants, scoped closure and missing-key failure. After satisfaction
and test authorization, add focused behavioral checks. Do not start recursive
scatter execution until these communication semantics hold.

### 4. Implement parallel replication and joins (Part 2C)

Reach: shared grouping/owner hooks and Python choice/repl/thread generation.
Reuse the existing concurrency facilities; remove serial-loop/global-worker-state
assumptions rather than layering another scheduler over them.

- Commit an enabled admission/choice atomically, create an isolated replica
  environment, then allow its continuation to run while subsequent admissions
  proceed. A waiting offer is not admitted work. Multi-input receives match the
  same full task ID; closure cannot consume data or strand required inputs.
- Evaluate exhaustion against a completed finite dispatch collection. An empty
  queue while production is still possible is not termination. Receive all input
  EOFs in declaration order before `end()`; preserve all-input begin setup.
- `end()` stops nearest-owner admissions, drains committed replicas and is scoped
  and idempotent. Sequence waits for all activated descendants; parallel joins
  both branches. Result EOF follows acknowledged publications, before downstream
  final gather/exec whenever waiting for it would form a cycle.
- Apply the same owner rule recursively. Bound-parent-plus-fresh-child admission
  excludes other concurrent parents; zero-task owners still open/close services.
  Parent waits must allow child services and sibling producers to progress.
- Keep output/error propagation and work directories isolated by invocation ID;
  cancellation on failure must wake blocked receives and completion joins.

Exit artifacts: delayed tasks complete in reverse order, empty owners terminate,
two parents with different cardinalities share workers safely, and a blocked
publication does not stop an independent producer. After satisfaction and test
authorization, add bounded-time progress/failure checks; syntax tests cannot prove
these properties.

### 5. Execute dispatch/gather and prove end-to-end behavior (Part 2D)

#### 2D.1 Execute the emitted helper contracts

Reach: step/helper registration and DefaultTarget helper execution. Replace the
pair/open path for modern workflows; keep any explicitly supported legacy path
bounded by the compatibility decision from 2A.

- Implement scatter_dispatch independently at each actual dimension producer.
  Publish each cardinality before waiting for peer lengths. Exchange shape/key
  state by operation and invocation across locations without moving/bundling all
  producers' payload lists onto a controller.
- Support declaration-order dotproduct with dynamic equal-length validation,
  flat Cartesian coordinates and tuple-valued nested Cartesian coordinates.
  Route the same full task key to the same worker for all dimensions using the
  accepted worker pool; worker hints cannot determine correctness.
- Gather only after all relevant result sources close and committed receives
  join. Validate expected keys and reject duplicates, missing or invalid keys.
  Sort/reconstruct by coordinates and shape state, never filenames, payloads,
  arrival order or list/string heuristics.
- Retain cardinalities even with no child results: zero dotproduct gives [],
  nested Cartesian [2, 0] gives [[], []]. List-valued worker output remains one
  element. Materialize crossed boundaries inside-out at actual consumer routes;
  fan-out collections stay independent. No special implementation for depth N.

Exit artifacts: root dotproduct, both Cartesian methods and nested scatter produce
exact expected values/shapes, including duplicates in payloads and empty branches.
Three-/five-level examples traverse the same owner/helper implementation. After
satisfaction and test authorization, add focused helper/end-to-end regressions.

#### 2D.2 Complete locally: tool metadata and evaluation (#3/#5/#6)

The 2026-10-14 tool metadata acceptance record above supplies completion evidence.
The following requirements remain the preservation contract, not an unfinished queue.

The initial local compiler milestone supplies the frontend/runtime baseline.
Implement these repairs together now under the next-stage handoff. Syntax freeze
and a 1000Genomes run are not new gates; use the retained small local examples.

Reach: CWL tool metadata emission, schemas, Step/Processor loading, Python command
construction/output processing, relevant translator/runtime checks and examples.
No additional SWIRL actions are needed for inputs already in an exec.

- Preserve the selected tool-level named input map and explicit expression
  arguments. Normalize inputBinding self references using their known input
  context; retain ordering/prefix/quoting and explicit unsupported-form errors.
  Retain literal value and direct-port valueFrom arguments. Order argument and
  inputBinding entries by their CWL positions; do not prepend expression arguments
  independently of their declared order. Supply CWL File fields such as nameroot
  from bound payloads without passing envelope IDs or File dictionaries directly
  to command arguments. Use contextual normalization, not blind string replacement.
- Preserve stdout destinations, dynamic glob, loadContents and outputEval.
  Execute, locate outputs, load requested contents, evaluate output self context,
  then wrap/publish. Reuse expression evaluation without confusing tool inputs
  with output File objects. Remove heuristic stdout inference/automatic trimming
  only where their explicit supported replacement is complete.
  Input expressions see the named tool inputs; output self sees the matched File
  objects after requested content loading. Preserve declared scalar/list types and
  invocation IDs through processing. Errors must propagate and wake blocked work,
  rather than silently dropping descriptors, returning empty output or hanging.
- Extend the existing strict schema and loader for the selected descriptor fields.
  Reuse the existing evaluator with the two correct contexts; do not add a new
  expression language/framework. Generated Python must remain directly compiled.
  Explicitly reject unsupported expressions/descriptors at the appropriate boundary.
- Adapt `tests/test_pipeline_contract.py` to cover plain and metadata variants,
  resolving final declared outputs for both File and string payloads. Keep raw
  string outputs unchanged; recursively read plain File contents and remove only
  the final newline, as specified by the example README.

Required acceptance, for each depth 0–3 and both variants:

1. Translate to separate variant/depth directories. Inspect logs, complete trace
   and metadata, including preservation of expression, transformation, stdout,
   loading/evaluation descriptors and exact exec port ownership.
2. Compile with trace and default targets; inspect scope/binding/placement/joins
   and direct generated Python. Metadata-only semantics must not require extra
   trace actions for inputs already in the exec.
3. Execute across configured distinct local locations, with bounded deadlines.
   Compare final declared outputs against per-depth expected.json, preserving
   exact order, duplicate occurrences, nested shape and empty branches. Verify
   task isolation and successful termination.
4. Repeat without advisory hints. Require equivalent values/shapes and preserve
   all four plain example results. Retain artifacts/logs and per-case reports.
5. Add focused checks for ordered literal/expression arguments, nameroot input
   transformations, explicit stdout, dynamic glob context, output self after
   loadContents, failure propagation and unchanged envelopes/IDs. Include command
   failures and malformed/unsupported expressions. Run the relevant existing
   parser/schema/trace/code-generation/runtime regressions; report genuine failures
   without weakening checks or changing source examples to conceal them.

Also execute the retained ordinary nested trim/upper/annotate examples locally
where their supplied inputs permit it. Structurally verify population nameroot
arguments and output glob contexts in the retained 1000Genomes translation; no
genome data download or workflow execution is required in this stage.

Exit: all eight pipeline configurations translate, compile to both targets and
execute with exact expected output semantics with/without hints; focused checks
pass; supported literal/direct-port commands remain compatible. Update evidence
in this plan, `TRANSLATOR_REPAIR_PLAN.md`, the pipeline README, example status and
handover docs. List unsupported forms and untested deployment/complex workflows.

#### 2D.3 Final acceptance and migration cleanup

- Execute the acceptance matrix below with and without hints. Stage local/split
  runs before available deployment runs; do not claim SSH/SLURM/genome execution
  from generated bundles or local helper checks. Use small local inputs first;
  downloads and actual cluster execution need their own authorization/resources.
- Show trace output, generated Python, exact payload/shape results and failure
  behavior for review. After satisfaction and test authorization, update stale
  parser/compiler/translator assertions and run relevant complete checks. Existing
  tests expecting pair/open, bare EOF or two-argument U are historical, not proof
  of the new contract. Do not restore deleted fixtures.
- Remove superseded port/EOF/gather heuristics only after the supported replacement
  passes its acceptance checks. Preserve ordinary command/expression/list/default
  behavior, deployment/service options and dependency bundling.
- Refresh `examples/EXAMPLES_STATUS.md`, `SWIRL_AGENT_REFERENCE.md` and
  `scratch/CURRENT_CONTEXT.md` to distinguish translate, parse, trace compile,
  Python compile and execution. Keep hints advisory; optimization is deferred.

Current completion order: completed local compiler baseline -> metadata #3/#5/#6
and all-eight-example acceptance -> remaining wider local coverage -> separately
authorized deployment/complex-workflow execution.
Stop when the existing contract and acceptance matrix hold; public virtual syntax,
new scheduling frameworks, broad CWL conformance and optimization remain deferred.

## Acceptance matrix and completion

Start the small full-pipeline checks with `examples/cwl/pipeline`: eight local,
distributed configurations covering depths 0/1/2/3 in plain and metadata-dependent
versions. Its README and per-depth expected.json specify exact markers, order and
empty nested shapes. Plain depths 0–3 now have both-target compilation and local
execution evidence with/without hints; metadata depths 0–3 are the active
#3/#5/#6 acceptance cases. These examples complement, rather than replace, the
wider matrix.

Cover ordinary basic/nested/expression/list workflows and deployment variants;
simple scatter with zero/one/many/duplicate inputs; scalar and whole-list
invariants; identical input/output names; declaration-order dotproduct (including
unequal dynamic lengths), flat and nested Cartesian products; `[2, 0]` empty
dimensions; two independent producers; multiple outputs/consumers; sibling
scatters; one, two, three and generated deeper nesting levels through the same
recursive lowering path; shared and separate worker pools; different
inner cardinalities and out-of-order completion. Verify parsing, schema validity,
deterministic names, producer/consumer bindings, locations, exact output values
and shapes, isolated closure, failure propagation and hint-free equivalence.

Current translator acceptance starts with `examples/cwl/scatter` and
`examples/cwl/scatter-nested`, and the one-/two-/three-level handwritten
references. Generate a three-level and a deeper manual CWL configuration under
build, including concurrent parents with different cardinalities, empty branches,
sibling scatters and multiple workflow outputs. Inspect that child admission
cannot match another enclosing scope; each consumer gather exposes exactly one list per
input edge under the producing invocation ID; consumer placement follows the
dependency graph rather than an assumed parent return; outermost shape is
preserved; all control EOFs follow the appropriate joins. Repeat translations
for deterministic output. Do not special-case the chosen validation depths.

Use retained `examples/1000genome/streamflow.yml` for distributed translator
acceptance without downloading data. The removed CWL 1000Genomes and nested-zip
fixtures are historical references, not available acceptance dependencies.
Include scattered A with ordinary internal A1/A2/A3 and an external unscattered
B: inspect same-ID internal communication without intermediate gathers, declared
A output mapping, consumer-side gather before B, and preservation of scalar versus
list output shapes. External references to A's unexposed internal ports must fail
clearly. An explicitly scattered internal step must add exactly one level.

Local plain-example execution and focused runtime checks establish a bounded
subset of this matrix. Metadata-dependent behavior and remaining distributed,
complex-workflow and broader matrix cases still require their own evidence.

Done means the accepted translator outputs parse and validate, execute with
correct identity/shape/completion on intended locations, remain equivalent
without hints, and preserve ordinary workflow behavior. Translation alone is
not end-to-end completion.

## Superseded material and deferred scope

- **Future node liveness:** consider heartbeat signals from nodes that a receiver
  expects data from, so it can distinguish a live node doing long-running work
  from a suspected lost node. Workflow-data waits must not use elapsed task time
  as evidence of failure; heartbeat policy and failure handling remain future work.
- **Do not redo:** region IR construction, recursive lowering, longest-prefix
  deployment lookup, translator flat-path removal and initial hint scaffolding.
  Unchecked boxes in the older nested plan do not establish missing work.
- **Replaced:** centralized pair/open payload bundles, indexed payload IDs,
  filename-based keys/gather order, finite-publication template activation,
  serial worker loops, global EOF and EOF inside work branches. The current
  target model uses independent streams and explicit begin-driven receiving owners.
  Bracket-qualified channels and parent-task template admission are also replaced.
- **Stale records:** Part 1A/1B nested-rejection statements, Part 1C/1D publication
  activation, nine-check-only status, 26-fixture-only status, legacy-parser
  acceptance and the old "run pytest after every step" instruction. Follow the
  later implementation-satisfaction gates; run tests only for approved parts.
- **Documentation cleanup:** `SWIRL_AGENT_REFERENCE.md` and
  `scratch/CURRENT_CONTEXT.md` describe legacy scatter capabilities; several
  handwritten scatter examples are historical. User-deleted test fixtures are
  not documentation or validation dependencies. `examples/swirl/scatter/README.md` describes a
  different pipeline; `examples/swirl/basic/doc.md` has obsolete paths. See
  `examples/EXAMPLES_STATUS.md` for the detailed inventory.
- **Deferred:** hint-driven optimization, streaming, retry/recovery frameworks,
  broad CWL conformance, `when`, new public region syntax, service-placement
  expansion, cluster execution beyond available fixtures and formal proofs.
  These are not prerequisites for arbitrary recursive scatter lowering.
  Public `scatter_send`/`scatter_exec`/`scatter_recv` grammar is also deferred;
  their virtual reference notation does not require a new translator IR.

## Review rules and source history

Implement each authorized slice and produce concrete artifacts before requesting
review. Record satisfaction, approved check results and remaining decisions;
then proceed to dependent work. The active handoff supersedes historical
translator/Phase-2 and per-slice approval gates for the next metadata stage. Internal
behavior-preserving refactors need no new consent; materially changed lowering,
placement/worker policy or CWL interpretation needs a concrete reviewed proposal.
No commits, pushes, remotes or destructive operations without explicit permission.

This plan consolidates the removed nested-scatter, recursive-region and
new-syntax implementation plans. Historical sources included the removed
`NEW_SYNTAX_*_REVIEW.md` files.
Current references include `examples/EXAMPLES_STATUS.md`,
`SWIRL_AGENT_REFERENCE.md`, `scratch/CURRENT_CONTEXT.md`, and Markdown example
documentation. The 2026-10-05 independent-stream correction and 2026-10-06 EOF
update take precedence over older design snapshots. Do not restore user-deleted
review documents. Maintain the current repair queue in `TRANSLATOR_REPAIR_PLAN.md`;
retain the language contract and later execution phases here. The 2026-10-08 uniform-envelope and explicit-scope target above
and arbitrary recursive dataflow/consumer-gather target takes precedence over earlier
emitted contracts. Current two-level emission is partial implementation evidence,
not acceptance of that target.
