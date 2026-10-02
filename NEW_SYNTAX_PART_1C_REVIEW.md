# Part 1C, first batch: scoped nesting and scatter methods

Implemented for review on 2026-10-02. This is a working translator batch, not
complete Part 1C acceptance or runtime execution. The accepted simple-scatter
checks pass **9/9**; new nesting/method tests wait for satisfaction with this
batch, as required by the plan. Parser/compiler/runtime/schema files are unchanged.

## Try the implementation

```sh
rtk mkdir -p build/new-syntax/try-nested
rtk .venv/bin/python tmp_main.py translate --language cwl \
  examples/cwl/scatter-nested-minimal/streamflow.yml \
  --outdir build/new-syntax/try-nested
```

For three levels, use
`examples/cwl/scatter-nested-new-syntax/streamflow-shared.yml` or
`streamflow-separate.yml`. For methods, use the configurations under
`examples/cwl/scatter-methods-new-syntax/`.

Generated review directories under `build/new-syntax/part-1c/`:

| Directory | Coverage |
| --- | --- |
| `minimal` | Existing two-level fixture; outer coordinator/worker2 and inner worker1 |
| `shared` | Existing shared-pool fixture; sibling inner scatters, keyed invariants, two outer outputs |
| `zip` | Existing ZIP fixture; separate outer/inner pools and post-gather commands |
| `three-shared` | Three levels on one shared pool; empty middle/leaf invocations; duplicates; two outputs; scalar/list invariants |
| `three-separate` | Same input with distinct two-worker pools at each level |
| `dotproduct` | Aligned two-dimensional input; declaration-order dimensions |
| `flat_crossproduct` | Four coordinate-distinct tasks from duplicate values |
| `nested_crossproduct` | Same tasks with nested output shape |
| `empty-inner` | Nested Cartesian product with lengths `[2, 0]`; expected shape `[[], []]` |
| `aliases` | Manual IR variant: two workflow outputs expose the same inner source |
| `ancestor-passthrough` | Manual IR variant: explicit diagnostic for a result carrying an ancestor key |

The CWL fixtures translated with status 0; traces, logs and metadata were
inspected. The last two are narrowly modified in-memory region trees used for
manual artifact/diagnostic review. No automated nested suite was run.

## Visible invocation isolation

The translator emits the previously proposed **qualified port syntax**:

```swirl
p_task_1[?key_0]
p_task_2[?key_0, ?key_1]
```

These qualify logical channels, not data names. A port identity combines its
operation-specific base with the evaluated full parent task keys. Task keys
retain the operation ID, complete parent coordinate path and local coordinates.
All nested move/recv actions, guards, invariant copies, result collections and
EOF messages use the qualified channels. `end()` closes the nearest receive/
distribution owner in that invocation, not every occurrence of its template.

The controller's nested trace retains option 1: `(dispatch . distribution)` runs
in parallel with `(collection . gather)`. Dispatch publishes the finite U
collection before invariant sends and task moves. Root invariants keep their
accepted setup-before-dispatch ordering.

Representative minimal nested forms:

```swirl
exec(_s_scatter_1, {(p_open_data_0_0, (?input_process_batch_batch_key_0, ?key_0))}
  -> {U(p_task_1[?key_0], tasks_1)}, {l0})

move((?payload_1, ?key_1) -> p_task_1[?key_0], l0, l1)
send(eof -> p_task_1[?key_0], l0, l1)

exec(_s_gather_1,
  {U(p_process_batch_echo_item_output_key_1[?key_0], results_0_1)}
  -> {(p_gather_data_0_1[?key_0], (?gather_d_process_batch_echo_item_output_1_key_0, ?key_0))},
  {l0})

send((?gather_d_process_batch_echo_item_output_1_key_0, ?key_0)
  -> p_gather_data_0_1, l0, l0)
```

The action snippets omit the surrounding groups; inspect the complete generated
trace for replication/EOF joins. Inner gather returns a list under the bound
outer key. Its invocation-local output channel has the parent qualifier; the
outer return channel drops that qualifier so all outer keyed results append to
the enclosing invocation's collection. The two memory roles are distinct.

At three levels, channel qualifiers contain both ancestor bindings. The deepest
key derives the full parent coordinate path once from its ancestry, rather than
concatenating already-full paths repeatedly. Arrival order and payload/file
names never define identity.

## Activation contract, including empty input

Qualified receive fragments at remote locations are **channel-family templates**.
Their owner is identified by operation, parent keys, controller/source route,
worker, and receive role. A single global owner cannot serve multiple parents.

Mandatory `scatterRegions.scope` metadata declares `parentKeys`, `taskChannel`,
`resultChannels`, `routes`, and `activation`:

- Root templates open at `workflow_start`, allowing initial invariant receives
  before the controller publishes tasks.
- Nested templates open once per `finite_collection_publication`, including a
  zero-element collection. Publication establishes the invocation, its empty
  result collections, inherited parent context/key bindings, and the selected
  controller/worker route. Workers receive reusable input payloads before their
  task replication. No data task is synthesized to open an empty invocation.
- Registration does not make worker continuations children that dispatch exec
  must join before returning. Dispatch completes after finite construction;
  the trace's later EOF/result joins synchronize work. Otherwise dispatch would
  deadlock waiting for tasks that distribution has not sent yet.
- Unpublished template offers are not active task/join obligations. Exact
  duplicate route templates are emitted only once; each published invocation
  opens its own owner. This matters when shared pools appear at several levels.

Channel qualifiers and the metadata descriptors are semantic input to the new
compiler, not advisory `@compiler` hints. Removing those comments leaves the
same channels, routes and activation rules. The new parser must accept qualified
port references wherever a port occurs, including inside U and guarded choices.
The new runtime must implement this publication/instantiation contract; it has
not been implemented or proved by running these traces in Phase 1.

## Two parents on the same worker

Suppose outer A has an empty batch and outer B has two items; both use inner l1.
They may also run on the same outer controller.

1. A publishes `p_task_1[A]` with no occurrences; B publishes `p_task_1[B]` with
   two coordinate-keyed occurrences. Both establish distinct l1 receiver owners
   and empty result collections, including A's zero-task invocation.
2. A's distributor closes immediately and sends EOF on `p_task_1[A]`. B's
   distributor can still claim/deliver B tasks. Neither guard reads the other
   parent's collection, and A's EOF cannot match B's owner.
3. A's worker closes an empty replication and forwards result EOF on the A
   result channel. B can receive its task EOF while exec is unfinished, but its
   join still waits for all committed work and acknowledged result sends.
4. A gathers an empty U snapshot and returns `[]` with A's outer key. B gathers
   its complete result collection and reconstructs coordinate order regardless
   of finish order. B's messages cannot enter A's U snapshot.
5. Outer gather receives two list-valued results with distinct outer keys. Its
   EOF still follows the outer worker join; the empty A result is not lost.

The three-level fixture extends the same reasoning to an empty middle invocation
and an empty leaf invocation under a nonempty middle parent. Both outputs retain
the input's nesting shape; their expected values are in the fixture README.

Nested invariant setup uses the same qualified receive storage for local and
remote workers. Even self-copies use matched send/recv in parallel location
fragments, so one shared tool descriptor describes both cases. Publication
precedes those synchronous sends; workers' initial receives do not depend on
task distribution. Gather receivers run alongside distribution, so result sends
have enabled counterparts. This is a manual circular-wait analysis, not a
scheduler/runtime execution proof.

## Preservation and edge cases

- Restored the baseline descendant-worker reservation rule: exclude descendant
  scatter targets only if some unreserved outer targets remain. The minimal
  fixture retains outer l0/l2 and inner l1; fully shared pools remain shared.
- Pair/open keeps centralized lowering. Only the explicit scatter dimensions
  participate in task records. Dimension order follows the scatter declaration,
  even when CWL's input binding map has a different order.
- Dotproduct preflight rejects unequal known direct-root input lengths. Dynamic
  lengths remain a dispatch-helper validation obligation in Phase 2. Gather
  retains `shapeFrom` dispatch state, needed for zero-result Cartesian shapes.
- Input, exec-output and gather-output payload namespaces are disjoint. A CWL
  tool can have identically named inputs/outputs without trying to overwrite
  an already-bound payload. Existing command/expression/glob metadata remains.
- Aliased workflow outputs get distinct result channels/collections when their
  source is shared, preventing duplicate owners competing for a single EOF.
- A scatter result must carry its current task key. Concrete or ancestor-keyed
  passthrough outputs that require an additional rekey operation report an
  explicit diagnostic instead of generating incorrectly keyed gather input.

## Remaining Part 1C work and gate

Distributed producer/input matching, general CWL multi-source interpretation,
and any changed centralized-to-decentralized dispatch plan remain a separate
batch with the plan's concrete before/after consent requirement. No deployment
placement policy has been changed to imply that those cases already work.
Broad ordinary-fixture acceptance is Part 1D. The old parser/compiler tests remain
deferred and unchanged; new dynamic metadata does not claim old-schema validity.

Review these emitted nested traces, qualified-channel/activation semantics and
shape contracts. After satisfaction with this implementation batch, add/run its
focused translator checks before continuing to the distributed-input batch.
