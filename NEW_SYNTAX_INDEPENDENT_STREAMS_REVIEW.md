# Independent dispatch and gather streams

Implemented for review on 2026-10-05 after the user corrected the bundled
pair/open model and confirmed that move operations are deterministic/synchronized
across input streams. This supersedes the pair/open and finite-publication
activation contracts in the earlier Part 1B/1C/1D review artifacts.

## Emission

Each scattered dimension has one `scatter_dispatch` helper taking only its own
list and producing its own finite keyed collection. There is no task-record
bundle and no `scatter_open` helper. Dispatch fragments run independently at
their input producers. Each output has a separate receiver join, snapshot read,
and `scatter_gather` helper. Dispatch and gather are not paired in a common
sequence/parallel group. Subsequent consumers wait for their input values.

For two inputs produced on l1 and l2:

```swirl
exec(_s_dispatch_0_0, {(p_left_source_items, d_left_source_items)}
  -> {U(p_scatter_0_0, stream_d_left_source_items)}, {l1})

exec(_s_dispatch_1_0, {(p_right_source_items, d_right_source_items)}
  -> {U(p_scatter_1_0, stream_d_right_source_items)}, {l2})
```

Each collection has its own replicated move loops and EOF sends. Per-worker
loops are wrapped in advisory `@compiler begin/end scatter_stream` comments
carrying the stream collection name, destination location and qualified channel.
Hints sit outside the branch parentheses and include the loop and its following
EOF send. Names follow the source value:
`d_files_a` becomes `stream_d_files_a` and `?element_d_files_a`; the key is a
separate binding. Reusing one source for multiple dimensions adds the dimension
name to distinguish streams and payload variables. Worker outputs use
`?element_d_compute_result`, result collections use `stream_d_compute_result`,
and gathered lists use `d_compute_result` (a variable inside a parent task).
Keys remain separate tuple members: payload, port and step names no longer
contain `_key_N` suffixes. Workers bind
the master key, then match it in the remaining receives before executing:

```swirl
recv((?element_d_left_source_items, ?key_0) -> p_scatter_0_0, l1, l3)
.
recv((?element_d_right_source_items, ?key_0) -> p_scatter_1_0, l2, l3)
.
exec(s_process, ...)
```

For more than two inputs, secondary receives run in parallel after the master
receive. Synchronized moves must assign the same full key to the same worker
across dimensions. This is mandatory semantics, not an optimization hint.

The worker termination branch receives every input EOF in declaration order,
then calls `end()`. Replication completion joins all committed tasks before the
worker sends result EOFs. No input EOF receive occurs after that join. Missing keyed data after its stream closes must
raise an error rather than leave a receive waiting forever.

## Shape, scope and producers

Dispatch helpers share only invocation-scoped dimension cardinalities. They
publish their own length before waiting for the other lengths, validate
dotproduct alignment, and construct declaration-order keys. Cartesian helpers
repeat their own values across the other coordinates without collecting other
payloads. Gather's `shapeFrom` lists these dispatches, preserving empty shapes
such as `[[], []]`. The future runtime must implement this cardinality exchange.

Nested independent continuations activate on admission of the enclosing parent
task, rather than publication by a particular input dispatch. Metadata identifies
the parent operation and complete parent keys. Dispatch, invariant-copy, worker
and gather templates share that parent's binding environment; each action waits
for the values it needs. In particular, a detached inner gather binds the same
parent environment used by the parent's result send; template activation must
not copy that environment. Gathered values become available before the parent
join completes, so the send can finish without a join dependency cycle.
Admission starts templates without waiting for input
construction or child completion. Active continuations participate in the
enclosing task's join; unpublished/unadmitted templates do not. Empty child
streams still have worker/result EOF owners and yield empty gathered lists.

Value ownership is tracked through workflow aliases and tool/gather outputs.
Ordinary producer tools now honor their configured deployment and copy their
required inputs there. Each scattered list is dispatched where produced;
invariants are copied from their actual producer, including to a worker at the
coordinator. Repeated ordinary consumers retain paired sends and receives.
The existing scatter worker-pool reservation policy remains in use.

## Review artifacts and checks

`build/new-syntax/independent/results.json` indexes all **27 configurations**.
Each directory contains `workflow.swirl` and `metadata.yml`. All translations
were repeated with identical traces and equivalent metadata; all lack pair/open
helpers, have one collection/output per gather, and balanced parentheses.

The new `examples/cwl/scatter-distributed-new-syntax` fixture has two separate
list producers, a producer-side scalar invariant, three workers including the
coordinator, and two output gathers. Its trace was checked for producer-local
dispatch, absence of whole-list transfers to the coordinator, master-key matching,
invariant copies and secondary EOF joins. A manual repeated-consumer case checks
that two remote input receives have two matching sends.

An independent read-only review found and verified fixes for producer-side
invariant routing and unmatched sends after transfer deduplication. Its final
review found no additional blocker under the declared shared-environment,
value-readiness and join semantics.

The nine previously accepted simple/ordinary checks were updated for the
corrected stream representation and pass. Lint passes. New nested/distributed
unit tests remain subject to the implementation review gate. No compiler,
runtime or schema changes were made; these traces have not been executed.

General CWL multi-source interpretation remains unsupported and diagnosed.
Complete Phase 1 acceptance and Phase 2 remain pending review of this corrected
implementation and its mandatory routing/cardinality/activation semantics.

2026-10-06: Updated worker closure to the requested all-input EOF branch. Seven
example-based regression cases cover dotproduct, Cartesian/empty streams,
distributed producers and shared/separate nested pools; the focused suite passes
16/16. All 27 CLI translations were regenerated and their worker EOF placement
checked. This verifies emission, not runtime execution.
