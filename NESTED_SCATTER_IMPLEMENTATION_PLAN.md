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
- the draft choice rule does not clearly discard the unselected alternative;
- the original confluence argument does not automatically hold with consuming
  moves and exclusive choices; and
- optimizations that deduplicate communication are unsafe unless iteration
  identity is part of the comparison.

### Operational supplement

Use one opaque hierarchical task key:

```text
TaskKey = (region ID, parent task key, coordinate vector)
```

Examples:

```text
scatter:/process_all_zips (1)
scatter:/process_all_zips/inspect_step parent=(1) coordinate=(2)
```

The serialized representation is an implementation detail. Do not add one
grammar bracket per nesting level. A single opaque key must work at any depth.

Each scatter region produces:

- keyed task payloads;
- a manifest containing expected count and output shape;
- keyed task results; and
- a completion event scoped to the region and parent key.

Use two different completion concepts:

- **region completion**: all children of one parent task are known and may be
  gathered; and
- **worker-stream EOF**: no more tasks will ever be sent to a worker for that
  region, so its replicated handler may stop.

A global EOF cannot safely represent both.

`send` copies a value. `move` consumes one keyed value from its source queue.

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
  inherited/default deployment
  parent region

Invocation
  path
  process: Tool | WorkflowRegion
  input bindings
  output declarations
  effective deployment
  scatter: ScatterSpec | None

ScatterSpec
  ordered input names
  method
  region ID
  parent region ID | None
```

Prefer small dataclasses or existing entity classes. Do not create abstract
base classes, factories, visitors, or plugin points unless two real
implementations need them.

Important properties:

- A normal subworkflow invokes its region once.
- A scattered subworkflow invokes the same region once per task.
- A scattered tool is a scattered invocation whose process is a tool.
- A nested scatter appends coordinates to its parent task key.
- A region supplies an inherited deployment default, but descendants may
  override it with longer StreamFlow bindings.
- Ordinary regions may be flattened during final lowering when their boundary
  has no runtime meaning.

Do not represent scatter as a separate sibling container type. It is an
execution policy on an invocation.

## Compiler-hint design

### Requirements

Hints are comments, not SWIRL syntax. Use `//`, because the existing lexer
already recognizes it as a comment. Do not use `#`.

Use one-line, versioned JSON so a future raw-source pre-pass can parse hints
without changing the grammar:

```swirl
// @compiler_hint_start {"version":1,"kind":"scatter","phase":"dispatch","region":"scatter:/compute"}
...
// @compiler_hint_end {"region":"scatter:/compute","phase":"dispatch"}
```

Use deterministic JSON serialization:

- sorted keys;
- compact separators;
- no multiline payloads; and
- JSON arrays retain semantically significant order.

### Region identity

`region` must be derived from the full CWL path, for example:

```text
scatter:/compute
scatter:/process_all_zips
scatter:/process_all_zips/inspect_step
```

Do not use generated numeric step counters as region identity. Nested regions
also include `parentRegion` in their start configuration.

### Phases

A distributed scatter region can have three phases:

1. `dispatch`: pair inputs, create IDs/manifests, and distribute work;
2. `worker`: receive/open one task, execute its body, and return results; and
3. `gather`: receive keyed results and reconstruct output arrays.

The first translator milestone may emit `dispatch` and `gather` only, matching
the currently generated controller trace. Add `worker` when the recursive
lowering can identify the complete replaceable worker fragment reliably.

### Suggested dispatch hint

```swirl
// @compiler_hint_start {"controller":"l0","idPort":"p_id","kind":"scatter","method":"flat_crossproduct","payloadPort":"p_group","phase":"dispatch","region":"scatter:/compute","scatterPorts":["p_in1","p_in2"],"step":"s_sc","version":1,"workers":["l1","l2","l3"]}
(
  exec(s_sc, {(p_in1, d_in1), (p_in2, d_in2)} -> {(p_id, id_ID), (p_group, group_ID)}, {l0})
  .
  (
    !(
      (
        move(id_ID -> p_id, l0, {l1, l2, l3}) .
        move(group_ID -> p_group, l0, {l1, l2, l3})
      )
      +
      (
        send(eof -> p_id, l0, l1) |
        send(eof -> p_id, l0, l2) |
        send(eof -> p_id, l0, l3)
      )
    )
  )
)
// @compiler_hint_end {"phase":"dispatch","region":"scatter:/compute"}
```

### Suggested gather hint

Include the gather step as well as its receives. Together they form the
semantic operation that a future optimizer may replace.

```swirl
// @compiler_hint_start {"controller":"l0","inputPorts":["p_res"],"kind":"scatter","outputPorts":["p_out"],"phase":"gather","region":"scatter:/compute","step":"s_G","version":1,"workers":["l1","l2","l3"]}
(
  (
    !(recv(res_ID -> p_res, l1, l0) + recv(eof -> p_res, l1, l0)) |
    !(recv(res_ID -> p_res, l2, l0) + recv(eof -> p_res, l2, l0)) |
    !(recv(res_ID -> p_res, l3, l0) + recv(eof -> p_res, l3, l0))
  )
  .
  exec(s_G, {(p_res, res_ID)} -> {(p_out, d_out)}, {l0})
)
// @compiler_hint_end {"phase":"gather","region":"scatter:/compute"}
```

Keep the sequential `.` connecting dispatch, gather, and subsequent workflow
steps outside the hinted fragments.

### Future compiler behavior

The lexer currently discards comments with `-> skip`; the parser visitor will
not see hints. When compiler support begins, first implement a small raw-source
pre-pass that:

1. scans only directive lines;
2. parses the JSON payload;
3. pairs start/end directives by `region` and `phase`;
4. records source spans;
5. rejects overlapping malformed spans conservatively; and
6. passes validated hint information to the optimizer.

Do not change the grammar merely to expose comments. Moving comments to an
ANTLR hidden channel is an alternative only if source offsets from the
pre-pass prove insufficient.

Unknown versions, kinds, phases, or malformed payloads must be ignored with a
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
- Assert that outer and inner regions have different full-path IDs.
- Add hint assertions for start/end balance and JSON contents.
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

- Centralize StreamFlow binding normalization.
- Centralize deployment-to-location expansion, including `locations`, SSH,
  Slurm wrapping, services, ports, and work directories.
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
- Resolve each invocation's effective deployment using longest-path matching.
- Detect cyclic or unresolved source references and report the full CWL path.
- Generate stable region IDs from full paths.

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

### Tasks

- Retain existing pair/open/gather special step types initially.
- Replace hard-coded names with names derived from full paths.
- Carry parent task-key information through nested lowering.
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
- Hints are balanced and contain stable region IDs.

## Phase 4: Metadata evolution

Do not overload ambiguous fields indefinitely. Add a new metadata version if
the compiler requires new region information.

Suggested region metadata:

```yaml
version: v1.1
scatterRegions:
  scatter:/process_all_zips/inspect_step:
    parentRegion: scatter:/process_all_zips
    method: dotproduct
    scatterPorts: [p_extracted_files]
    idPort: p_inspect_id
    payloadPort: p_inspect_group
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

This phase begins only after translator output is stable.

### Tasks

- Reconcile `grammar/SWIRL.g4` with the checked-in generated ANTLR parser.
- Decide and document parameterized replication syntax.
- Regenerate lexer, parser, listener, and visitor from the grammar.
- Add parser tests for replication, choice, EOF, `move`, indexed/keyed data,
  and compiler comments.
- Remove compiler inference based on display-name substrings such as `pair`,
  `open`, and `gather`; use explicit metadata.
- Add a raw-source compiler-hint scanner without changing trace semantics.
- Validate hint spans against parsed trace operations before optimizing.

### Exit criteria

- The grammar is the source of truth.
- Regeneration produces no unexplained diff.
- Existing SWIRL examples still parse and compile.
- The compiler can read and validate hints but still ignores them for code
  generation.

## Phase 6: Keyed compiler runtime

The current global `ports` dictionary and `Event` per port are insufficient for
concurrent nested instances. Replace them with the smallest keyed queue model
that supports the operational supplement.

### Message envelope

Every runtime communication involved in scatter should carry:

```text
kind
region ID
parent task key
task key
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
- `move`: remove and transmit exactly one selected keyed value.
- `recv`: enqueue the received envelope under its key.
- `exec`: consume inputs for one key and publish outputs under that key.
- pair: create child task keys and a manifest.
- open: unpack one keyed payload.
- gather: wait for the manifest count, group by parent, and reconstruct CWL
  shape from coordinates.

### Replication and choice

- Compile replicated worker handlers as loops over region messages.
- Select DATA versus completion based on the received message kind.
- Do not derive choice guards from the first textual predicate.
- Stop a worker handler only on its scoped `WORKER_EOF`.
- Complete one nested gather on `REGION_COMPLETE` or its manifest count without
  stopping the worker pool.

### Exit criteria

- Two parent tasks may run inner scatters concurrently without overwriting
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
2. Outer and inner scatter use distinct full-path region IDs.
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
