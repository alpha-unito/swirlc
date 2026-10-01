# Recursive Region Translator Plan

## Goal

Replace the CWL translator's flat and scatter-specific paths with one recursive
pipeline:

```text
CWL
  -> WorkflowRegion tree
  -> recursive lowering
  -> SWIRL trace and metadata
```

Every workflow uses this path. Backwards compatibility with internal translator
helpers is not required. Scope ends at emitted SWIRL syntax and metadata.

The compiler is a downstream consumer and may be named when explaining an
output contract. This plan does not change compiler code, compiler behavior, or
compiler tests. All implementation tasks belong to the CWL translator and, only
where emitted syntax requires it, the SWIRL grammar/parser surface.

## Why

The translator currently uses different representations for ordinary workflows
and scattered workflows. Ordinary translation flattens subworkflows into leaf
steps, while scatter translation preserves some nesting and emits trace strings
directly. This duplicates source resolution, command construction, deployment
selection, port creation, metadata generation, and output wiring.

Flattening also removes boundaries needed by nested scatter. For example:

```text
/chromosome                         outer scatter
  /individuals                     nested scatter
  /mutation_overlap                sibling nested scatter
  /frequency                       sibling nested scatter
```

The region boundary determines the inner controller, inherited deployment,
parent task identity, gather scope, and output shape. Reconstructing this after
flattening is harder than retaining it.

## Desired model

Scatter remains an execution policy on an invocation, not a separate workflow
or container type.

```text
WorkflowRegion
  path
  inputs
  outputs
  invocations
  deployments
  parent

Invocation
  path
  process: Tool | WorkflowRegion
  inputs
  outputs
  deployments
  scatter: ScatterSpec | None
```

Add only the missing information required for lowering:

- input and output types;
- exact region-boundary source mappings;
- stable dependency order;
- optional/default input state; and
- effective deployment targets.

Do not add visitors, factories, abstract region classes, or public region
syntax.

## Lowering API

Use one recursive algorithm:

```python
def lower_region(region, context):
    bind_region_inputs(region, context)
    for invocation in dependency_order(region.invocations):
        lower_invocation(invocation, context)
    return bind_region_outputs(region, context)


def lower_invocation(invocation, context):
    if invocation.scatter:
        return lower_scatter(invocation, context)
    if isinstance(invocation.process, WorkflowRegion):
        return lower_region(invocation.process, context.child(invocation))
    return lower_tool(invocation, context)


def lower_scatter(invocation, context):
    child_context = emit_dispatch(invocation, context)
    results = lower_invocation_body(invocation, child_context)
    return emit_gather(invocation, results, context)
```

`lower_invocation_body()` lowers either a tool or a workflow region. It does
not inspect scatter depth.

## Lowering context

Keep one small mutable context owned by the lowering pass:

```text
LoweringContext
  controller location
  current TaskKey, if any
  available values: source path -> port/data/type
  trace fragments by location
  generated steps
  dependencies
  scatter-region numbering
```

A child context inherits visible values and deployment defaults. A scattered
child extends the opaque hierarchical task identity. Values produced inside a
scatter are keyed by that identity until gathered.

Do not store generated SWIRL names in the region IR. Naming belongs to lowering.

## Implementation phases

### Phase 0: Lock translator behavior

Add or retain translator-only acceptance tests before structural changes.

Required fixtures:

- basic workflow;
- ordinary nested workflow;
- list inputs and outputs;
- one scattered tool;
- minimal nested scatter;
- nested zip scatter with distinct worker pools;
- 1000 Genomes with multi-input and sibling nested scatters; and
- expression tools.

For every fixture:

- translation succeeds;
- emitted SWIRL parses with zero syntax errors;
- each metadata location appears exactly once in the trace;
- commands, arguments, processors, types, and deployment mappings remain
  correct; and
- validation stops after parsing the emitted SWIRL and checking metadata.

Specific 1000 Genomes assertions:

```text
region 0: /chromosome
region 1: /chromosome/individuals
region 2: /chromosome/mutation_overlap
region 3: /chromosome/frequency
```

Also assert:

- `individuals` scatters `counter` and `stop` together;
- both population scatters remain independent;
- `individuals_merge` consumes the gathered inner result keyed by the outer
  chromosome task;
- final output types are `list[list[file]]`; and
- `path`, relative `location`, and `file://` inputs normalize correctly.

### Phase 1: Complete the region IR

Make `build_region_tree()` the only CWL analysis path.

Tasks:

1. Normalize inline and referenced subworkflow sources in one helper.
2. Preserve typed region inputs and outputs.
3. Preserve all input sources rather than selecting the first source.
4. Record optional/default values without lowering them.
5. Resolve full paths at region construction time.
6. Resolve effective deployments by longest matching StreamFlow binding.
7. Validate scatter methods and missing scatter inputs.
8. Detect unresolved sources and cycles with full CWL paths.
9. Topologically order invocations within each region.

Exit criteria:

- tests can inspect complete trees for every fixture;
- no lowering code calls `_flatten_leaf_steps()`; and
- the 1000 Genomes tree contains four independent scatter specifications.

### Phase 2: Lower ordinary workflows recursively

Implement `LoweringContext`, `lower_region()`, and `lower_tool()` without
scatter first.

Move existing behavior into shared helpers:

- workflow input coercion;
- CWL type conversion;
- command and argument construction;
- expression metadata;
- output processors and glob handling;
- port/data allocation;
- deployment-to-location creation; and
- trace and metadata rendering.

Ordinary subworkflows call `lower_region()` recursively. Their boundary inputs
and outputs are aliases in the lowering context; no synthetic SWIRL step is
emitted unless data must cross locations.

Exit criteria:

- basic, nested, list, and expression fixtures use recursive lowering;
- their traces parse;
- `_EffStep` and `_flatten_leaf_steps()` have no callers; and
- no scatter-specific behavior has moved into `lower_tool()`.

### Phase 3: Lower every scatter through one function

Implement `lower_scatter()` around recursive body lowering.

For each scatter invocation:

1. Assign a stable numeric region ID in preorder traversal.
2. Select the invocation's complete ordered worker pool.
3. Emit pair/manifest metadata and dispatch trace.
4. Pack all scattered and invariant inputs atomically into the task payload.
5. Open the payload at the worker.
6. Lower the tool or child region using a child task context.
7. Return keyed outputs to the enclosing controller.
8. Gather results in CWL order and shape.
9. Rekey nested gathered results with the parent task identity.
10. Emit balanced advisory compiler comments for dispatch, worker, and gather.

Scatter methods:

- `dotproduct`: require equal lengths and pair by index;
- `flat_crossproduct`: Cartesian product with flat output; and
- `nested_crossproduct`: Cartesian product with nested output dimensions.

Empty inputs produce correctly shaped empty outputs without worker dispatch.
Duplicate values remain distinct through task identity.

Sibling scatters receive separate region IDs, manifests, EOF scopes, result
queues, and gathers even when they share worker deployments.

Exit criteria:

- scattered tools and scattered subworkflows call the same `lower_scatter()`;
- nested depth does not appear in conditionals;
- no synthetic `SimpleNamespace` workflow adapter remains;
- minimal nested scatter and 1000 Genomes pass translator acceptance; and
- removing advisory compiler comments leaves a valid equivalent SWIRL trace.

### Phase 4: Delete the old system

Delete, rather than retain as compatibility wrappers:

- `_EffStep`;
- `_flatten_leaf_steps()`;
- `_has_scatter()`;
- depth-specific scatter translation helpers;
- synthetic workflow adapters;
- duplicated command/glob/deployment helpers; and
- old normal translation routing through `AbstractTranslator.translate()`.

`CWLTranslator.translate()` should only:

```python
region = self.build_region_tree()
result = lower_region(region, initial_context)
render(result, workflow_output, metadata_output)
```

Exit criteria:

- one CWL representation;
- one lowering path;
- one location registry;
- one metadata builder; and
- repository search finds no flat-step translator implementation.

### Phase 5: Final translator validation

Run:

```sh
python ./tmp_main.py translate \
  --language cwl \
  examples/cwl/scatter-nested-minimal/streamflow.yml \
  --outdir build

python ./tmp_main.py translate \
  --language cwl \
  examples/1000genome/streamflow.yml \
  --outdir build
```

Validate both generated files after each command:

- `workflow.swirl` parses with zero syntax errors;
- `metadata.yml` validates against its schema;
- generated helper names and region IDs are deterministic;
- every trace port/data pair exists in metadata;
- every metadata output used downstream has one producer;
- deployment pools match the longest bound paths; and
- output types and scatter shapes match CWL declarations.

Run translator and parser tests. Generated traces are not executed in this
change.

## Change order

Keep the worktree runnable through the refactor:

1. Add acceptance assertions.
2. Complete region information.
3. Introduce ordinary recursive lowering.
4. Switch non-scatter fixtures.
5. Introduce generic scatter lowering.
6. Switch scatter fixtures.
7. Delete flat and specialized paths.
8. Run final translator validation.

Do not maintain both systems after their fixtures have moved. Each phase should
end by deleting the replaced code.

## Non-goals

- Changes under `swirlc/compiler/` or `swirlc/core/compiler.py`.
- Compiler execution, optimization, or runtime generation.
- Execution semantics beyond what must be represented in emitted SWIRL.
- Compiler interpretation or optimization of advisory region comments.
- General CWL conformance unrelated to current fixtures.
- `when`, retries, failure recovery, or speculative execution.
- New public SWIRL region syntax.
- Compatibility for private translator helpers removed by this refactor.

## Completion definition

The change is complete when every CWL fixture translates through the recursive
region path, both requested workflows produce parseable and internally
consistent SWIRL/metadata, and all flat or depth-specific translator code has
been deleted.
