# Nested Scatter Implementation Plan

## Purpose

This document is an implementation handoff for adding general nested scatter
support to the SWIRL toolchain. Work starts in the CWL-to-SWIRL translator and
continues later in the SWIRL compiler/runtime.

The implementation must support scattered tools and scattered subworkflows at
arbitrary nesting depth without adding a separate code path for each depth.
Ordinary nested workflows should use the same internal region model even when
they are not scattered.

The plan deliberately separates:

1. preserving nested workflow structure in the translator;
2. emitting valid, semantically complete SWIRL traces;
3. adding advisory compiler hints as comments; and
4. teaching the compiler/runtime to optimize and execute nested scatter later.

Compiler hints must never be required for correctness. Removing every hint
from a trace must leave an equivalent valid SWIRL program.

## Repository state and precautions

Before starting, inspect the worktree and preserve unrelated changes:

```sh
git status --short
```

At the time this plan was written,
`examples/cwl/scatter-nested-zip/clt/unzip.cwl` contained a user-owned
modification. Do not overwrite or revert it.

The baseline test suite passed before this work began:

```text
13 passed
```

Relevant files:

- `swirlc/translator/cwl/cwl_translator.py`
- `swirlc/core/entity.py`
- `swirlc/core/translator.py`
- `grammar/SWIRL.g4`
- `swirlc/core/compiler.py`
- `swirlc/compiler/standard/compiler.py`
- `swirlc/compiler/default/compiler.py`
- `swirlc/config/schemas/v1.0/config_schema.json`
- `tests/test_translator.py`
- `tests/test_compiler.py`
- `examples/cwl/scatter-nested/`
- `examples/cwl/scatter-nested-zip/`

## Current behavior

The current translator has three materially different paths:

- normal workflows use `_translate()` and `AbstractTranslator.translate()`;
- one ordinary scatter uses `_translate_scatter()`; and
- one root-level scattered subworkflow uses
  `_translate_subworkflow_scatter()`.

The scatter paths write SWIRL and metadata directly instead of using the normal
workflow model. `_translate_subworkflow_scatter()` handles only one subworkflow
level. Scatter operations inside that subworkflow are recorded on ordinary
steps and executed as local loops by the generated Python runtime.

Consequently, the `scatter-nested` test passes because its inner scatters stay
inside each outer worker. It does not prove distributed nested scatter.

`scatter-nested-zip` is the correct primary acceptance case:

- `/process_all_zips` is scattered over two `zip_workers`;
- `/process_all_zips/inspect_step` is scattered over three `file_workers`;
- the current translator emits only the coordinator and zip workers; and
- the `file_workers` binding is ignored.

Other known scatter limitations:

- only the first relevant scatter is selected;
- sibling scatter regions are not handled generally;
- subworkflow boundaries are erased by `_flatten_leaf_steps()`;
- `dotproduct` silently truncates to the shortest input instead of rejecting
  unequal lengths;
- `nested_crossproduct` is accepted by the schema but behaves like dot product;
- gather ordering is inferred from filenames or file contents;
- iteration identity is not transmitted with normal data messages;
- EOF state is global to `(source, port)`;
- one global worker index is shared by all scatter activity; and
- runtime ports contain one mutable value rather than keyed queues.

## Scope

### Required

- Preserve arbitrary nested workflow structure in translator analysis.
- Support any number of sibling and nested scatter operations.
- Support scatter applied to a command-line tool, expression tool, or
  subworkflow.
- Respect the longest matching StreamFlow binding at every nested path.
- Support distinct worker pools for outer and inner scatter regions.
- Implement CWL `dotproduct`, `flat_crossproduct`, and
  `nested_crossproduct` semantics.
- Preserve deterministic CWL output ordering and shape.
- Handle empty scatter inputs without deadlock.
- Distinguish duplicate equal-valued inputs by iteration identity.
- Emit advisory, machine-readable compiler hints as SWIRL comments.
- Preserve all existing non-scatter behavior.

### Initially out of scope

Do not broaden this project into general CWL conformance unless a feature is
needed by an acceptance fixture. In particular, keep these separate:

- arbitrary `linkMerge` and `pickValue` behavior;
- CWL conditionals and `when`;
- retries, failure recovery, or speculative execution;
- a general distributed scheduler;
- changes to the published SWIRL optimization proofs; and
- exposing workflow regions as a new public SWIRL syntax construct.

The zip fixture currently uses workflow-step `valueFrom`. Either implement the
minimal required `valueFrom` behavior as an explicit prerequisite or simplify
the fixture. Do not silently treat a file path as its `nameroot`.

## Theoretical basis and required supplement

The original SWIRL paper models a fixed workflow instance with finite traces.
Its grammar has `exec`, `send`, and `recv`, but no runtime replication or
dynamic scatter. It mentions loops as future work.

The supplied SWIRL extension draft adds replication, choice, IDs, EOF, and a
consuming `move`. It provides the intended outline for scatter:

```text
pair -> repeatedly distribute keyed work or EOF -> execute workers -> gather
```

However, the draft does not completely define nested scatter. The implementation
must document that it is following a small operational supplement rather than
claiming that nested behavior is already proved by the paper.

The unresolved theoretical issues are:

- nested iteration IDs are explicitly left open;
- `move` has a reduction rule but is missing from the draft action grammar;
- EOF is not scoped to a region or parent iteration;
- a set of data values cannot represent order or multiplicity by itself;
- statically known `Out^D(s)` does not describe data-dependent fan-out;
- choice selects an executable alternative, but its interaction with consuming
  moves still needs a confluence argument;
- the original confluence argument does not automatically hold with consuming
  moves and exclusive choices; and
- optimizations that deduplicate communication are unsafe unless iteration
  identity is part of the comparison.

### Operational supplement

Use one runtime identity containing only the numeric region ID and an opaque,
hierarchical iteration ID:

```text
TaskKey = (region ID, iteration ID)
```

Examples:

```text
TaskKey(0, [1])
TaskKey(1, [1, 2])
```

The serialized representation is an implementation detail. Do not add one
grammar bracket per nesting level. A single opaque key must work at any depth.

Each scatter region uses a stable numeric suffix assigned during lowering. Its
task identity and payload are named `task_id_N` and `task_payload_N`, where `N`
is the scatter region ID. `task_id_N` contains the opaque serialized `TaskKey`;
scatter dispatch creates it and nested dispatch extends it.

Transport identity and payload atomically as one tuple:

```swirl
(task_id_N, task_payload_N)
```

Write dynamically scoped data as `name[task_id_N]`, for example
`result_0[task_id_0]`. Do not use a `_ID` suffix, the old `taskID` placeholder,
or separate messages for task identity and payload.

Tuple data is recursive SWIRL data syntax:

```antlr
data : ID ('[' ID ']')? | ZERO | EOF_VAL | '(' data ',' data ')' ;
```

Tuple transport is atomic. `move` consumes one tuple instance, and `recv`
destructures that instance into its component names. Equal payloads remain
distinct because each tuple contains its own task identity.

Each scatter region produces:

- atomic task tuples containing identity and payload;
- a manifest containing expected count and output shape;
- keyed task results; and
- a completion event scoped to the region and enclosing iteration prefix.

Use two different completion concepts:

- **region completion**: all children of one enclosing iteration are known and may be
  gathered; and
- **worker-stream EOF**: no more tasks will ever be sent to a worker for that
  region, so its replicated handler may stop.

A global EOF cannot safely represent both.

`send` copies a value. `move` consumes one value, including one complete tuple,
from its source queue.

## General workflow-region model

Regions are a translator intermediate representation, not initially a SWIRL
language primitive.

Use the following conceptual model:

```text
WorkflowRegion
  path
  inputs
  outputs
  child invocations
  inherited requirements
  inherited/default deployments
  parent region

Invocation
  path
  process: Tool | WorkflowRegion
  input bindings
  output declarations
  effective deployments
  scatter: ScatterSpec | None

ScatterSpec
  ordered input names
  method
  region path
```

Prefer small dataclasses or existing entity classes. Do not create abstract
base classes, factories, visitors, or plugin points unless two real
implementations need them.

Important properties:

- A normal subworkflow invokes its region once.
- A scattered subworkflow invokes the same region once per task.
- A scattered tool is a scattered invocation whose process is a tool.
- A nested scatter appends coordinates to its enclosing iteration ID.
- A region supplies inherited deployment defaults, but descendants may
  override it with longer StreamFlow bindings.
- Ordinary regions may be flattened during final lowering when their boundary
  has no runtime meaning.

Do not represent scatter as a separate sibling container type. It is an
execution policy on an invocation.

## Compiler-hint design

### Requirements

Hints are comments, not SWIRL syntax. Use `//`, because the existing lexer
already recognizes it as a comment. Do not use `#`.

Use named, single-line directives so a future raw-source pre-pass can parse
hints without changing the grammar:

```swirl
// @compiler begin scatter.dispatch 0
...
// @compiler end scatter.dispatch 0
```

### Region identity

Assign each scatter region a zero-based integer ID in stable traversal order.
The ID only needs to remain consistent within one generated SWIRL and metadata
pair. It is not a persistent ID across translations.

Keep the full CWL path in metadata for diagnostics:

```yaml
scatterRegions:
  "0":
    name: /process_all_zips
  "1":
    name: /process_all_zips/inspect_step
```

At runtime, identify work with only the region ID and hierarchical iteration
ID. Do not repeat paths, methods, controllers, or worker lists in every hint.

### Phases

A distributed scatter region can have three phases:

1. `dispatch`: pair inputs, create IDs/manifests, and distribute work;
2. `worker`: receive/open one task, execute its body, and return results; and
3. `gather`: receive keyed results and reconstruct output arrays.

Emit all three phases. A worker hint encloses the complete replicated work/EOF
choice at each worker location. Nested dispatch and gather spans may therefore
appear inside an outer worker span.

### Suggested dispatch hint

```swirl
// @compiler begin scatter.dispatch 0
(
  exec(_s_scatter_0, {(p_in1, d_in1), (p_in2, d_in2)} -> {(p_task_0, (task_id_0, task_payload_0))}, {l0})
  .
  (
    !(
      (
        move((task_id_0, task_payload_0) -> p_task_0, l0, {l1, l2, l3})
      )
      +
      (
        send(eof -> p_task_0, l0, l1) |
        send(eof -> p_task_0, l0, l2) |
        send(eof -> p_task_0, l0, l3)
      )
    )
  )
)
// @compiler end scatter.dispatch 0
```

### Suggested worker hint

```swirl
// @compiler begin scatter.worker 0
!(
  (
    recv((task_id_0, task_payload_0) -> p_task_0, l0, l1) .
    exec(_s_open_0, {(p_task_0, task_payload_0)} -> {(p_a, a[task_id_0]), (p_b, b[task_id_0])}, {l1}) .
    exec(s_work, {(p_a, a[task_id_0]), (p_b, b[task_id_0])} -> {(p_result_0, result_0[task_id_0])}, {l1}) .
    send(result_0[task_id_0] -> p_result_0, l1, l0)
  )
  +
  (
    recv(eof -> p_task_0, l0, l1) .
    send(eof -> p_result_0, l1, l0)
  )
)
// @compiler end scatter.worker 0
```

### Suggested gather hint

Include the gather step as well as its receives. Together they form the
semantic operation that a future optimizer may replace.

```swirl
// @compiler begin scatter.gather 0
(
  (
    !(recv(result_0[task_id_0] -> p_result_0, l1, l0) + recv(eof -> p_result_0, l1, l0)) |
    !(recv(result_0[task_id_0] -> p_result_0, l2, l0) + recv(eof -> p_result_0, l2, l0)) |
    !(recv(result_0[task_id_0] -> p_result_0, l3, l0) + recv(eof -> p_result_0, l3, l0))
  )
  .
  exec(_s_gather_0, {(p_result_0, result_0[task_id_0])} -> {(p_out, d_out)}, {l0})
)
// @compiler end scatter.gather 0
```

Keep the sequential `.` connecting dispatch, gather, and subsequent workflow
steps outside the hinted fragments.

### Future compiler behavior

The lexer currently discards comments with `-> skip`; the parser visitor will
not see hints. When compiler support begins, first implement a small raw-source
pre-pass that:

1. scans only directive lines;
2. parses the phase and numeric region ID;
3. pairs begin/end directives by `region` and phase using a stack;
4. records source spans;
5. permits properly nested spans and rejects crossing or unmatched spans; and
6. passes validated hint information to the optimizer.

Do not change the grammar merely to expose comments. Moving comments to an
ANTLR hidden channel is an alternative only if source offsets from the
pre-pass prove insufficient.

Unknown kinds, phases, or malformed directives must be ignored with a
warning. The compiler must fall back to compiling the ordinary trace.

## Implementation phases

## Phase 0: Lock behavior with tests

Do this before restructuring production code.

### Tasks

- Add a translator-only test for `scatter-nested-zip`.
- Assert that the translation includes:
  - one coordinator;
  - two distinct zip-worker locations; and
  - three distinct file-worker locations.
- Assert that the inner scatter references the file-worker pool.
- Assert that outer and inner regions have different numeric IDs and retain
  their full paths in metadata.
- Add hint assertions for begin/end balance, region IDs, and worker spans.
- Parse the emitted trace with the existing ANTLR parser to prove comments do
  not change syntax.
- Add fixtures or focused unit tests for all three scatter methods.
- Add an unequal-length dot-product case that must fail clearly.
- Add empty-input and duplicate-value cases.

### Exit criteria

- New tests fail for the known missing behavior rather than unrelated CWL
  features.
- Existing tests continue to pass before production changes.
- The expected output order and nested array shape are explicit in tests.

## Phase 1: Extract shared translator utilities

The existing scatter translators duplicate deployment parsing, value coercion,
command construction, glob resolution, and location creation. Extract only the
pieces needed by both normal and scatter translation.

### Tasks

- Centralize StreamFlow binding normalization as ordered deployment targets.
- Map each deployment to exactly one SWIRL location. Scatter bindings may list
  multiple deployments; ordinary bindings retain one target.
- Reject `locations`; represent each worker location as its own deployment.
- Reuse the coordinator location when a scatter selects its deployment, and
  combine its controller and worker trace fragments in one location trace.
- Preserve SSH, Slurm wrapping, services, ports, and work directories.
- Centralize workflow input loading and CWL-to-SWIRL type coercion.
- Centralize command arguments and output processor construction.
- Preserve full CWL paths throughout; do not match nested steps by basename.

### Exit criteria

- No behavior changes yet.
- Existing tests pass.
- `_translate_scatter()` and `_translate_subworkflow_scatter()` use the shared
  utilities or are ready to be replaced by the next phase.

## Phase 2: Build the recursive region IR

### Tasks

- Parse the root CWL workflow into a `WorkflowRegion`.
- Represent each workflow step as an `Invocation`.
- Recursively construct child regions for subworkflow invocations.
- Preserve input and output boundary mappings.
- Preserve ordered scatter input declarations exactly as CWL declares them.
- Store the scatter method and validate it early.
- Resolve each invocation's effective deployments using longest-path matching.
- Detect cyclic or unresolved source references and report the full CWL path.
- Preserve full region paths for metadata and diagnostics. Numeric compile-time
  IDs are assigned later during stable lowering traversal.

Do not lower to SWIRL strings during this phase.

### Exit criteria

- Unit tests can inspect the region tree for basic, nested, scattered, and
  nested-scattered workflows.
- `/process_all_zips/inspect_step` resolves to `file_workers`.
- A non-scattered nested workflow remains represented as a child region.
- Sibling scatters appear as independent `Invocation` objects.

## Phase 3: Add one recursive lowering algorithm

Replace depth-specific translation with a single recursive lowering pass.

Conceptually:

```text
lower_region(region, context):
    bind region inputs
    lower each invocation according to dependencies
    if invocation.scatter:
        lower_scattered_invocation(invocation, context)
    else if invocation.process is a workflow region:
        lower_region(invocation.process, context)
    else:
        lower_tool(invocation, context)
    bind region outputs back to parent
```

For a scattered invocation:

```text
lower_scattered_invocation(invocation, context):
    create pair/manifest operation
    create dispatch trace for selected worker pool
    recursively lower the invocation body with child task context
    create keyed return trace
    create gather operation at the enclosing controller
```

Use one generated naming scheme throughout:

```text
steps:   _s_scatter_N, _s_open_N, _s_gather_N
data:    task_id_N, task_payload_N, result_N
ports:   p_task_N, p_result_N
```

The leading underscore distinguishes translator-generated steps from CWL
steps. After `_s_open_N`, keep domain names such as `batch`, `file`, and
`report` instead of repeating workflow provenance in generated names.

### Tasks

- Retain existing pair/open/gather special step types initially.
- Replace hard-coded names with the generated region naming scheme above.
- Carry the hierarchical iteration ID through nested lowering.
- Emit each dispatch output, `move`, and `recv` as one atomic
  `(task_id_N, task_payload_N)` tuple.
- Destructure the tuple at `recv`; `_s_open_N` consumes `task_payload_N` while
  `task_id_N` keys opened data and results.
- When an inner gather completes, rekey its gathered result with the enclosing
  task ID before returning it to the outer gather.
- Emit one scatter region per scattered invocation.
- Permit the inner region's worker pool to differ from its parent pool.
- Ensure ordinary descendant invocations inherit their region's effective
  location unless a longer binding overrides it.
- Generate output types according to the scatter method and nesting depth.
- Emit compiler hints from the region object, not from hand-written literals.
- Keep hints advisory and parseable as comments.

### CWL method behavior

`dotproduct`:

- require every scattered input to have identical length;
- one coordinate per aligned element;
- one output array dimension.

`flat_crossproduct`:

- generate every Cartesian-product combination;
- use a coordinate vector internally;
- flatten gathered outputs into one array in CWL order.

`nested_crossproduct`:

- generate every Cartesian-product combination;
- retain the coordinate vector;
- rebuild one nested output dimension per scattered input, in declaration
  order.

Single-input scatter defaults to dot-product behavior and adds one output
array dimension.

If a scattered input is empty, produce the appropriate empty output structure
without dispatching tasks.

### Exit criteria

- `_translate_scatter()` and `_translate_subworkflow_scatter()` are deleted or
  reduced to a temporary compatibility wrapper around the recursive lowering.
- No code branches on scatter nesting depth.
- Translator tests cover multiple sibling and nested scatter regions.
- The emitted trace parses successfully.
- Hints are balanced and contain deterministic compile-time region IDs.

## Phase 4: Metadata evolution

Do not overload ambiguous fields indefinitely. Add a new metadata version if
the compiler requires new region information.

Suggested region metadata:

```yaml
version: v1.1
scatterRegions:
  "1":
    name: /process_all_zips/inspect_step
    method: dotproduct
    scatterPorts: [p_extracted_files]
    taskPort: p_task_1
    controllerLocations: [l1, l2]
    workerLocations: [l3, l4, l5]
    inputPorts: [p_extracted_files]
    outputPorts: [p_info]
```

Exact field names may change, but keep one source of truth. Hint payloads should
identify the region and trace phase; detailed static information may live in
metadata rather than being duplicated in every comment.

### Compatibility

- Keep reading `v1.0` metadata for existing examples.
- Emit `v1.1` only when the new lowering requires it, or migrate all generated
  metadata in one deliberate change.
- Reject unsupported versions explicitly.
- Update the JSON schema and schema tests together.

## Phase 5: Compiler/parser preparation

This phase makes the current translator output a reliable input to the trace
compiler. It does not implement keyed execution or hint-driven optimization.

### Readiness snapshot after Phases 1-4

The translator already emits the Phase 5 language features:

- unparameterized replication (`!trace`);
- unlabelled choice (`left + right`);
- `move`;
- `eof`;
- recursive tuple data such as `(task_id_0, task_payload_0)`;
- keyed data such as `result_0[task_id_0]`; and
- balanced `// @compiler begin|end scatter.<phase> <region>` directives.

Metadata v1.1 and explicit `steps[*].type` values for `_s_scatter_N`,
`_s_open_N`, and `_s_gather_N` also exist. Do not redesign these contracts in
this phase.

The parser/compiler boundary is not ready yet. Regenerating the parser exposed
stale visitor assumptions: mapping now goes through `locationSet`, while
`CompileVisitor` still calls `mapping().name()`; `visitTraceRepl()` still asks
for removed replication parameters. The current test baseline is 24 passed,
5 failed, and 1 xfailed, with all five failures entering the compiler through
the stale mapping access. Treat restoring this baseline as the first Phase 5
gate, not as a Phase 6 runtime problem.

### Fixed syntax decisions

- Keep replication unparameterized: `!trace`. Remove the unused
  `param`/`domain` plumbing from compiler callbacks and trace output; do not add
  syntax that the translator does not emit.
- Keep choice unlabelled. Phase 5 preserves both alternatives structurally; it
  must not derive a semantic guard from the first predicate.
- Keep comments skipped by the lexer. The hint scanner operates on raw source;
  do not move comments onto an ANTLR channel unless source offsets prove
  insufficient.
- Keep tuple and keyed data in the existing `data` rule. Use a small recursive
  parser helper where structure is required; do not introduce a second SWIRL
  AST in this phase.
- Keep destination sets in `locationSet`. Add one compiler helper for reading
  either a singleton or braced set and use it for mappings and `move`
  destinations.

### 5.1 Restore the generated-parser contract

Files:

- `grammar/SWIRL.g4`
- `scripts/generate-antlr4-parsers.sh`
- `swirlc/antlr/SWIRL*.py`
- `swirlc/core/compiler.py`
- `swirlc/core/utils.py`

Tasks:

1. Pin parser generation to the same ANTLR release as
   `antlr4-python3-runtime` and make regeneration write to a temporary
   directory before replacing the four generated files.
2. Regenerate lexer, parser, listener, and visitor only from `SWIRL.g4`.
3. Update `CompileVisitor` for the generated API:
   - read mappings through `mapping().locationSet()`;
   - read singleton and set destinations through the same helper;
   - visit replication without `ID` parameters; and
   - preserve tuple/keyed data text losslessly for existing compiler targets.
4. Install an ANTLR error listener used by the CLI and tests. Any lexer or
   parser error must make `compile` fail before metadata registration or target
   output begins.
5. Run generation a second time and require an empty diff in generated files.

### 5.2 Lock the language surface with parser tests

Add one focused parser test module rather than spreading syntax assertions
through translator tests. Cover:

- plain and parenthesized replication;
- nested replication;
- unlabelled choice and operator nesting;
- `send`, `recv`, and `move` with singleton and set destinations;
- `eof` and `0`;
- nested tuples;
- keyed tuple members and keyed results;
- line and block comments, including compiler directives; and
- malformed tuples, unmatched delimiters, old labelled choice, and old
  parameterized replication as explicit failures.

Also parse every checked-in `examples/swirl/**/*.swirl` file and the translated
output of each scatter fixture. Parser tests assert zero syntax errors through
the shared strict parser entry point, not by inspecting ANTLR stderr.

### 5.3 Make compilation metadata-driven

Files:

- `swirlc/core/compiler.py`
- `swirlc/config/schemas/v1.0/config_schema.json`
- `swirlc/config/schemas/v1.1/config_schema.json`
- affected example metadata

Tasks:

1. Delete display-name and command substring inference for `scatter_pairer`,
   `scatter_open`, and `scatter_gather`.
2. Read helper behavior only from explicit `steps[*].type`. Ordinary steps may
   continue to omit `type`.
3. Require the three generated scatter helper types in v1.1 metadata and keep
   v1.0 readable for non-scatter examples. If a legacy scatter example needs
   compatibility, add its explicit types to metadata rather than restoring
   inference.
4. Add a regression case whose ordinary step name contains `pair`, `open`, or
   `gather` and prove it remains an ordinary step.

### 5.4 Scan and validate compiler hints

Add one small raw-source scanner, for example
`swirlc/compiler/hints.py`. It returns validated spans with only:

```text
phase
region ID
start/end source offsets
```

The scanner must:

1. recognize only complete directive lines;
2. pair begin/end markers with one stack;
3. allow proper nesting and repeated worker spans for one region;
4. reject crossing or unmatched spans;
5. warn and ignore unknown phases, malformed directives, and invalid region
   IDs; and
6. validate each accepted span against the parsed trace: it must contain the
   expected generated helper operation for `dispatch`, `worker`, or `gather`,
   and its region must exist in `metadata.scatterRegions`.

Pass the validated spans into `CompileVisitor`, but do not expose them through
every compiler callback. Phase 5 records them on the compilation context and
all targets ignore them. A trace with no hints, malformed hints, or stripped
hints must compile identically apart from warnings.

### 5.5 Use the trace target as the Phase 5 oracle

The existing `--target trace` compiler is the narrowest way to test the
translator/compiler boundary without invoking the distributed runtime. Adapt
it to the fixed syntax instead of creating another test compiler.

Add an integration test that translates `scatter-nested-zip`, compiles the
result with `--target trace`, and asserts that the per-location trace contains:

- outer and inner replication;
- both alternatives of each choice;
- tuple-valued `move`/`recv` operations without lost key text;
- explicit EOF operations;
- `_s_scatter_N`, `_s_open_N`, and `_s_gather_N` from metadata; and
- file-worker operations only at the three file-worker locations.

Compile a copy with all compiler directives removed and compare normalized
trace-target output. They must match exactly. Do not execute generated default
runtime code here; keyed execution remains Phase 6.

### Verification order

1. Parser unit tests.
2. Hint-scanner unit tests.
3. Existing compiler tests.
4. Translator-to-trace-target integration test.
5. Full `uv run pytest -q`.
6. Parser regeneration followed by a clean generated-file diff.

### Exit criteria

- `SWIRL.g4` is the only handwritten syntax source and regeneration is
  reproducible with the pinned tool/runtime version.
- Invalid SWIRL fails compilation deterministically; no partial target output
  is treated as success.
- Every checked-in example and every Phase 1-4 translator output parses and
  compiles with `--target trace`.
- Compiler behavior for scatter helpers comes only from explicit metadata.
- Valid hint spans are available to future optimization, but hinted,
  hint-free, and malformed-hint traces retain identical compilation semantics.
- The full pre-Phase-6 suite passes. No keyed queues, message envelopes,
  scheduling, or runtime scatter execution are added in this phase.

## Phase 6: Keyed compiler runtime

The current global `ports` dictionary and `Event` per port are insufficient for
concurrent nested instances. Replace them with the smallest keyed queue model
that supports the operational supplement.

### Message envelope

Every runtime communication involved in scatter should carry:

```text
kind
region ID
iteration ID
port
data type
payload
```

Suggested kinds:

- `DATA`
- `REGION_COMPLETE`
- `WORKER_EOF`

Do not infer completion from an empty Python list or a filename.

### Runtime state

- Queue values by `(region, task key, port)`.
- Keep ordinary non-scatter data under a root task key.
- Scope worker scheduling state per region.
- Preserve FIFO only where the SWIRL trace requires it; gather ordering comes
  from task coordinates, not network arrival.
- Clear or consume readiness state per keyed value.

### Operations

- `send`: copy the selected keyed value.
- `move`: remove and transmit exactly one selected value; task tuples remain
  atomic.
- `recv`: enqueue the received envelope under its key and destructure tuple
  names for the following trace.
- `exec`: consume inputs for one key and publish outputs under that key.
- pair: create child task keys and a manifest.
- open: unpack one keyed payload.
- gather: wait for the manifest count, group by parent, and reconstruct CWL
  shape from coordinates.

### Replication and choice

- Compile replicated worker handlers as loops over region messages.
- Select DATA versus completion based on the received message kind.
- An unlabelled `+` selects whichever branch can execute; it carries no ID or
  textual guard.
- Stop a worker handler only on its scoped `WORKER_EOF`.
- Complete one nested gather on `REGION_COMPLETE` or its manifest count without
  stopping the worker pool.

### Exit criteria

- Two outer iterations may run inner scatters concurrently without overwriting
  ports or mixing outputs.
- Duplicate values remain separate tasks.
- Out-of-order completion yields deterministic CWL order.
- Empty nested scatter terminates.
- More tasks than workers is supported.

## Phase 7: Hint-driven optimization

Only after the non-optimized keyed trace works correctly:

- recognize validated scatter phases through hint spans;
- replace a whole hinted fragment with specialized generated runtime code;
- preserve the ordinary trace as the fallback;
- compare optimized and unoptimized outputs in tests; and
- ignore hints if any referenced step, port, location, or region differs from
  the parsed trace.

Never make the compiler depend on hints to understand correctness-critical
task identity or completion.

## Testing strategy

## Translator tests

Test structure, not only substrings:

- inspect region IR directly;
- parse emitted SWIRL through ANTLR;
- parse hint JSON and verify balanced start/end pairs;
- inspect metadata types, paths, regions, and locations; and
- assert exact scatter output shapes.

Required cases:

- no scatter;
- one scattered tool;
- one scattered subworkflow;
- outer subworkflow scatter plus inner tool scatter;
- inner scatter on a distinct worker pool;
- two sibling scatter regions;
- three nesting levels;
- multiple outputs;
- duplicate values;
- empty input;
- unequal dot-product lengths;
- flat cross-product; and
- nested cross-product.

## Compiler tests

- Compile both hinted and hint-free versions of the same trace.
- Assert hints have no effect before optimization is enabled.
- Execute outer task count greater than worker count.
- Use differing inner cardinalities per outer task.
- Add deliberate sleeps to reverse completion order.
- Verify no outputs cross parent boundaries.
- Verify exact nested array shape.
- Verify EOF does not terminate another parent's inner scatter.
- Verify two independent scatter regions do not share round-robin state.
- Use timeouts so deadlocks fail deterministically.

## Primary end-to-end acceptance scenario

Use `examples/cwl/scatter-nested-zip` with:

- two zip archives;
- different file counts per archive;
- two zip workers;
- three file workers; and
- deliberately reordered file-inspection completion.

Acceptance requirements:

1. Translation emits all six physical locations: coordinator, two zip workers,
   and three file workers.
2. Outer and inner scatter use distinct numeric region IDs, with their full
   paths retained in metadata.
3. Inspection commands execute in file-worker traces, not zip-worker traces.
4. Each zip summary contains only reports belonging to that zip.
5. Reports appear in deterministic CWL order.
6. The final summary contains both zip summaries.
7. Removing compiler hints does not change the result.
8. The workflow exits without blocked worker or gather threads.

## Recommended implementation sequence for an agent

Use small, reviewable commits. Do not attempt the translator and runtime rewrite
in one patch.

1. **Tests and contract**
   - Add failing nested-placement and scatter-method tests.
   - Add a short comment/hint format specification.

2. **Shared translator utilities**
   - Remove deployment and CWL binding duplication without changing output.

3. **Region IR**
   - Build and test the recursive workflow/invocation structure.

4. **Recursive lowering**
   - Replace the special subworkflow scatter path.
   - Initially reproduce existing single-scatter output.

5. **Nested translator output**
   - Emit distinct inner worker locations and traces.
   - Emit stable compiler hints.

6. **Scatter semantics**
   - Correct dot product and implement flat/nested cross products.

7. **Grammar/compiler preparation**
   - Synchronize grammar and generated parser.
   - Add hint scanning with no optimization.

8. **Keyed runtime**
   - Add envelopes, queues, scoped completion, and deterministic gather.

9. **Optimization**
   - Use validated hints to select specialized code generation.

10. **Cleanup**
    - Delete old depth-specific translation and runtime heuristics.
    - Update documentation and examples.

After every step:

```sh
pytest -q
```

Also run formatting, lint, and schema validation commands already used by the
repository before handing off a commit.

## Invariants the implementation must preserve

- Hints are optional comments.
- Full CWL paths, not basenames, identify nested invocations.
- Every scattered result has exactly one task key.
- Child task keys include their parent identity.
- Gather never uses arrival order or filename contents for ordering.
- Region completion never shuts down a reusable worker stream.
- Dot product never silently truncates.
- A nested worker binding overrides its enclosing region's default binding.
- Non-scattered workflows do not pay for scatter runtime machinery.
- There is one recursive lowering algorithm, not one function per supported
  nesting depth.

## Completion checklist

- [ ] Current worktree changes preserved.
- [ ] Baseline tests recorded.
- [ ] Region and invocation IR implemented.
- [ ] Longest-path deployment resolution tested.
- [ ] One recursive lowering path replaces scatter special cases.
- [ ] Compiler hints emitted as balanced `//` comments.
- [ ] Hint JSON is versioned, deterministic, and full-path keyed.
- [ ] Generated SWIRL parses with and without hints.
- [ ] Dot product validates equal lengths.
- [ ] Flat cross-product output ordering is correct.
- [ ] Nested cross-product output shape is correct.
- [ ] Empty scatter produces empty outputs without work.
- [ ] Inner scatter uses its configured worker pool.
- [ ] Runtime messages carry hierarchical task keys.
- [ ] Gather is keyed and deterministic.
- [ ] Region completion and worker EOF are distinct.
- [ ] Hinted and hint-free execution are equivalent.
- [ ] Existing non-scatter and simple-scatter tests pass.
- [ ] `scatter-nested-zip` passes end to end with differing inner sizes.
- [ ] Old heuristic/depth-specific code is removed.

## Stop conditions

Pause and request a design decision rather than guessing if any of these arise:

- the desired formal syntax for parameterized replication conflicts with the
  extension paper;
- a public SWIRL representation for scoped completion is required;
- compatibility requires old and new metadata to be emitted simultaneously;
- StreamFlow binding inheritance differs from longest-prefix behavior; or
- the project requires a formal proof before adopting hierarchical task keys.

Otherwise, proceed translator-first and keep compiler optimization disabled
until ordinary hinted and hint-free traces are semantically equivalent.
