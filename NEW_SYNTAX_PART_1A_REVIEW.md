# Part 1A review: baseline and proposed output contract

Prepared 2026-10-02. Awaiting user acceptance; no translator/compiler behavior
has changed, and no tests or generated workers have been run.

Historical baseline review: the user subsequently clarified that the gate is
implementation satisfaction. See [Part 1B](NEW_SYNTAX_PART_1B_REVIEW.md) for the
working simple-scatter slice. The qualified-channel syntax proposed below remains
unapproved and unimplemented, and is not required to try that slice.

## Baseline artifacts and manual inspection

Each directory contains `workflow.swirl` and `metadata.yml`:

- [Basic](build/new-syntax/part-1a/basic/workflow.swirl): two sequential local
  commands reuse `d_greeting`; their outputs remain concrete string dependencies.
- [Scatter](build/new-syntax/part-1a/scatter/workflow.swirl): `/compute` uses
  flat Cartesian pairing of two five-element file arrays, hence 25 intended
  tasks. Its selected pool includes the coordinator (`l0`) and both workers
  (`l1`, `l2`). Gather feeds the ordinary list-valued `/analyze` input.
- [Minimal nested](build/new-syntax/part-1a/scatter-nested-minimal/workflow.swirl):
  two outer batches each contain two strings. Outer workers are `l0` and `l2`;
  inner workers are `l1`. Inner gather returns a list to its outer task; outer
  gather's declared result is `list[list[file]]`.

Generated using the configured `.venv/bin/python tmp_main.py translate` entry
point, separately for each fixture. All logs completed without translation
errors, and all six output files were opened and inspected. Shell status alone
was not used as evidence. These are old-language baselines, not executable
evidence of the proposed semantics. `build/` is ignored by Git; regenerate using
the commands in the implementation plan with these output directories.

The old scatter trace has key-first task tuples, bracketed data placeholders,
one worker-set move, and EOF sends inside replicated alternatives. Neither
workers nor gather receivers emit `end()`. The nested trace shares bare inner
channels across repeated parents, so unkeyed EOF has no parent isolation.
`echo_item_output` is also used for a scalar worker output and the inner gathered
list; the latter overwrites its dependency type. These are gaps to fix, not
behavior to preserve.

## Existing logical behavior to preserve

- Analysis resolves sources to full workflow paths, orders steps by dependencies,
  and recursively retains subworkflow regions. Scatter dimensions retain CWL
  declaration order; the default method is dotproduct.
- Deployment lookup uses the longest matching path, falling back to `/`.
  One location is created per deployment. A configured coordinator may also
  participate as a worker; do not silently exclude it.
- Outer scatter pools exclude descendant scatter locations when at least one
  unreserved target remains; otherwise the original pool is retained. The
  minimal nested baseline specifically reserves `l1` for the inner scatter.
- Pair/open currently bundles all bound inputs, including invariants. Separating
  reusable invariant storage is required by the agreed contract, but replacing
  centralized pairing with distributed dispatch remains a separate Part 1C
  decision. The current available-value tuple does not track producer location.
- Ordinary tool lowering executes at the current controller, even when the
  invocation has a different deployment binding. This limitation is not a
  reason to silently change placement during notation work.
- Full source paths do not yet extend to emitted tool/port names: repeated local
  step names can collide. StreamFlow service fields are retained in analysis
  but unused in placement. New dynamic names must include operation/path identity.
- Source analysis retains multiple sources, but region input binding, scatter
  pairing, and subworkflow output projection select the first. Tool flow lists
  available sources while command/expression binding uses the first port.
  This does not implement general CWL linkMerge/pickValue semantics. Resolve
  support explicitly in Part 1C rather than claiming preservation of a feature
  the baseline does not provide.
- Command/default argument handling, expressions, output glob processors,
  deployment configuration, and ordinary whole-value lists remain in scope for
  preservation. Defaults are not uniformly materialized as workflow values;
  optional/unbound values need an explicit audit before expanding support.

Audit locations: `cwl_translator.py:654` (region analysis), `:929` (input aliases),
`:939` (tool naming/placement), `:1075` (scatter lowering), `:1104` (worker pool),
`:1277` (limited root dotproduct preflight), and `:1314` (metadata normalization).
The shared `core/translator.py:97` renderer emits v1.0 and lacks CWL's scatter
region/pairer-port metadata; the current CWL path writes its own v1.1 metadata.
There is no reason to route CWL through that renderer for this part.

## Proposed syntax and collection contract

Use the plan's payload-first tuple `(?payload_0, ?key_0)`. Names are deterministic
and include the operation index and input/output identity. Every activated
replica owns its local bindings and inherits visible parent bindings. A bound
key matches; exec cannot overwrite it. Parallel receivers must bind distinct
payloads; aligned inputs receive the master key before sibling keyed receives.

Dispatch publishes `U(p_task_0, tasks_0)`, a finite collection of keyed payload
records. Each output has its own result collection, such as
`U(p_result_0_0, results_0_0)`. U input is a non-consuming snapshot of all
occurrences in that invocation after receive joins, including zero occurrences.
Move is the only consuming dispatch read; ordinary exec and U reads do not
remove input values. Result receives append atomically, retaining duplicates.

Every choice operand, distributor, and sequence/parallel boundary is explicitly
parenthesized. A distributor closes via guarded `end()`, joins pending moves,
then sends EOF. A worker closes on EOF, joins exec/result sends, then forwards
result EOF. A gather receiver closes independently for each source/output;
gather starts after all receiver joins. Compiler execution remains deferred.

Before (one worker's distributor):

```swirl
!((move((task_id_0, task_payload_0) -> p_task_0, l0, {l1}))
  + (send(eof -> p_task_0, l0, l1)))
```

Proposed after (repeat in parallel for every selected worker):

```swirl
(
  !(
    (move((?payload_0, ?key_0) -> p_task_0, l0, l1))
    +[p_task_0 has data]
    (end())
  )
)
.
send(eof -> p_task_0, l0, l1)
```

For zero tasks, each distributor closes without a data activation, then the
worker and result receiver close on EOF; gather reads an empty U snapshot. For
one task, exactly one atomic move wins. For more tasks than workers, replication
admits parallel task instances; EOF may arrive during work, but joins retain
every committed exec and acknowledged result send.

## Invocation isolation proposal requiring acceptance

Recommend fresh logical channels parameterized by the complete parent task
key. This makes isolation visible in the trace rather than dependent on compiler
hints. The following is a proposed extension to port syntax, not syntax already
accepted by the old parser or implemented by the translator:

```swirl
exec(_s_scatter_1, {(p_batch_0, (?batch_0, ?key_0))}
  -> {U(p_task_1[?key_0], tasks_1)}, {l0})

move((?payload_1, ?key_1) -> p_task_1[?key_0], l0, l1)
+[p_task_1[?key_0] has data]
end()

send(eof -> p_task_1[?key_0], l0, l1)
recv(eof -> p_task_1[?key_0], l0, l1)
exec(_s_gather_1, {U(p_result_1_0[?key_0], results_1_0)}
  -> {(p_parent_result_0, (?batch_result_0, ?key_0))}, {l0})
```

The middle snippets are individual actions/choice operands; the full lowering
uses the explicit replication and grouping shown above. Brackets here qualify a
**port**, never a payload. Root channels need only their operation-specific name.
Inner channels are identified by `(operation, port role, complete parent key)`.
Task keys contain `(operation ID, full parent coordinate path, local coordinates)`.
The parent key qualifier preserves all ancestor identity without filenames.

Finite dispatch publication establishes the invocation even when its collection
is empty. Remote receive bodies are channel-family templates instantiated once
per published invocation, with the parent qualifier bound before their receive
replication opens. This channel-family activation rule is necessary: a single
global receive owner closed by the first parent's EOF would still be wrong.
The registration includes the controller and selected workers so concurrent
parents at different controllers route independently. This is a semantic
requirement of the proposed qualified channel/U syntax, not an advisory hint.

For outer parents A and B sharing `l1`, inner channels `p_task_1[A]` and
`p_task_1[B]` have distinct receive owners, result collections and EOF state.
A may be empty and close immediately while B continues processing. A's U read
returns `[]`; it cannot include B's results. Inner gather publishes A's list
under A's bound outer key, separately from B's list.

All move/recv matching, guarded availability, U reads, EOF and replication-owner
identity use this logical channel scope. Outer result ports and inner result
ports have distinct generated names, even if their CWL source output is the
same. Removing compiler hints leaves the same channel identities and semantics.

This adds a Phase 2 grammar/runtime obligation and is presented for a decision
before implementation. An inherited-context design is possible instead, but
would need an equally explicit invocation creation/remote activation contract;
bare task keys and bare EOF alone do not supply one.

## Proposed metadata and helper contracts

Keep concrete dependency names and output `dataName` fields for reusable/static
values only. Runtime variables, keys, payload records and EOF are not static
dependencies. Dynamic outputs use a distinct `binding` descriptor, for example:

```yaml
outputs:
  p_compute_result:
    binding: {payload: result_0_0, key: key_0, type: file}
    glob: result.txt
```

Binding names omit the rendered `?`. Collection output descriptors use a
distinct `collection` descriptor with payload-field types and key identity;
they are not a fake `file` dependency. Scalar task results and gathered lists
have different descriptors and names. Helpers retain existing type names
(`scatter_pairer`, `scatter_open`, `scatter_gather`) where their role suffices.

Extend each existing scatter-region descriptor with its operation ID, parent
region/key, task/result channel roles, controller/worker routes, declaration-
ordered dimension names, invariant ports, output collection mappings, and shape
policy. Parent qualifiers refer to enclosing bindings; channel template names
remain static metadata keys. Concrete output types remain `list[T]` for flat
products/dotproduct and dimension-nested lists for nested products.

Pairer validates dotproduct lengths, creates Cartesian coordinate tuples in
declaration order, and retains original cardinalities/shape in invocation state.
Each duplicate occurrence has a different coordinate key. Open binds the
selected record's scattered fields while retaining its key; invariants are
received once per applicable location/invocation and reused outside task claims.
Gather reads every mapped result collection, checks missing/duplicate task keys,
and reconstructs declaration-order coordinates rather than arrival order.
Empty inner gathers return `[]` keyed by their parent. Cartesian empty dimensions
and nested shapes must retain the dimension cardinalities, not infer shape from
the absence of results.

The current v1.1 schema inherits closed v1.0 output descriptors requiring
`dataName`; it does not validate the proposed dynamic descriptors. Phase 2 must
update the relevant schema/validator deliberately. No schema edits or metadata
version bump are made in Part 1A; compatibility/version policy stays explicit
at the Phase 2 contract gate.

## Gate

Accept or revise the U snapshot contract, explicit qualified-channel proposal
(including empty-invocation template activation), and dynamic metadata separation
before Part 1B. Existing deployment/source interpretation changes still require
their own Part 1C review. Automated tests remain deferred until explicit Part 1A
acceptance, as required by the implementation plan.
