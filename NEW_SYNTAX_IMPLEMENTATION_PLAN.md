# New SWIRL syntax and semantics implementation plan

## Objective and authority

Implement the agreed keyed, parallel scatter model in two strictly separated
phases:

1. Update the CWL translator and review its emitted traces and metadata.
2. After the user accepts the translator, implement the Python compiler/runtime.

Implementation was authorized on 2026-10-02. The user clarified that satisfaction
gates apply to working implementation and emitted artifacts, not acceptance of
the plan alone. Start with a usable translator slice and present its output for
review. Do not commit, push, or interact with Git remotes. Preserve unrelated
worktree changes.

2026-10-05 correction: each scattered input has an independent producer-local
dispatch, and each output has an independent gather. Pair/open payload bundling
is not the intended lowering. The user confirmed that move operations are
deterministic/synchronized so matching keys reach the same worker. See
[corrected implementation review](NEW_SYNTAX_INDEPENDENT_STREAMS_REVIEW.md).

This document is self-contained: syntax, semantics, fixture coverage, review
gates, and implementation boundaries are specified below.

## Review and consent rules

For every part:

1. Implement the authorized scope and generate concrete review artifacts.
2. Manually inspect and explain representative traces, metadata, and limitations.
3. Ask whether the user is satisfied with that part; address requested changes.
4. Only after explicit satisfaction, add/update and run automated unit tests for
   that accepted part. Do not introduce tests, run pytest, or run the existing
   unit suite before this gate. Test failures reopen the affected part for review
   if correction changes its behavior.
5. Record acceptance, approved test results, and any unresolved decisions here
   before continuing to dependent work.

Manual trace inspection, translation commands, and focused artifact checks are
allowed before acceptance. They must not be disguised unit-test suites.

Large internal refactors do not automatically require consent. Proceed without
another approval when extraction, consolidation, or replacement preserves how
the translator interprets CWL and chooses its logical SWIRL execution plan.
Before a rework changes that interpretation or logical lowering, present the
current behavior, proposed behavior, representative before/after trace, and
impact; obtain explicit consent before implementing it. Existing authorization
for the new notation/completion semantics need not be requested again.

Examples requiring a decision include changing input pairing, producer/worker
placement, centralized bundling into distributed dispatch, worker-pool policy,
or supported CWL source/default semantics. Do not silently drop additional
sources, change array shape, or simplify fixtures to avoid a difficult case.

## Current implementation: starting point

Snapshot: 2026-10-01. Reinspect the worktree before implementation; these are
observations, not guarantees about later code.

`swirlc/translator/cwl/cwl_translator.py` already contains `WorkflowRegion`,
`Invocation`, `ScatterSpec`, `LoweringContext`, `build_region_tree()`, and
recursive `lower_region()`, `lower_invocation()`, and `lower_scatter()`.
Full-path analysis and longest-path deployment binding also exist. Extend that
architecture rather than rebuilding the region model from scratch.

Current scatter lowering still emits `name[task_id]`, key-first task tuples,
worker-set moves, and EOF branches without the agreed `end()`/join behavior.
Its dispatch/gather arrangement is already broadly option 1. Pair/open helpers
currently bundle scattered and invariant inputs together. Several source
resolution paths select `sources[0]`; investigate rather than assume all
multi-source CWL bindings are supported. Tool placement and parent/descendant
worker-pool selection also need a preservation audit.

Main Phase 1 files are `swirlc/translator/cwl/cwl_translator.py` and, only where
shared rendering actually requires it, `swirlc/core/translator.py`. Translator
owned context/model helpers, example inputs, documentation, and emitted metadata
contracts are in scope. Prefer existing helpers and the smallest cohesive
change; introduce structured rendering only if current string emission cannot
reliably preserve scopes and operator grouping.

## Agreed language contract

### Variables, values, and collections

- `(?payload, ?key)` is a task data tuple, with payload first.
- Variables are local to an activated replica. Unbound pattern occurrences
  bind; already-bound occurrences match and cannot silently overwrite bindings.
- `exec` inputs and `send` reference bound values. `exec` outputs bind new
  payload variables while preserving already-bound keys.
- Nested instances inherit visible bindings; fresh inner keys use distinct
  variable names. Keep the outer key available for returning gathered results.
- `eof` is a control marker and does not match a data tuple pattern.
- Concrete non-scattered values retain ordinary names and original send/recv
  notation. Receive them once per applicable invocation/location and reuse them
  across task instances. A list passed whole is not automatically scattered.
- `U(port, data)` describes a collection. Dispatch outputs a finite collection;
  gather reads the complete collection in its invocation scope, including an
  empty collection. Agree read/consumption details in Part 1A; ordinary `exec`
  inputs should not accidentally acquire `move` consumption semantics.
- Preserve duplicate occurrences using distinct task keys. Keys contain the
  operation ID and full parent/iteration coordinate path. Metadata retains
  original ordering and output shape; values are not identified by filenames.

### Actions and control

- `move` atomically selects, binds, and consumes one matching item. No trailing
  `(port, variable)` removal annotation is emitted. The claim/removal is atomic,
  but move remains unfinished until its delivery's matching recv commits, just
  as send does; a claimed item can therefore still be in flight at exhaustion.
- `send` copies/transmits a selected value and finishes only after its matching
  `recv` commits. Send completion is not completion of subsequent worker work.
- Receive matching/consumption and variable binding are atomic. References use
  the instance's selected values, not arbitrary values reread from a shared port.
- `+` selects an enabled pattern/action alternative. `+[port has data]` selects
  the data branch when the scoped collection has data and the ending branch
  otherwise. Selection and item claim form one atomic transition.
- `!` offers potentially unbounded parallel activations. It is not a sequential
  loop and does not eagerly allocate infinitely many waiting instances.
- `end()` atomically closes its enclosing replication instance. Stop further
  admissions; drain already-committed instances. Unactivated waiting offers do
  not become completion obligations.
- `A . B` starts B only after A and all its activated parallel descendants
  finish. EOF sends follow replication completion, not an ordinary data branch.
- Dispatch finishes constructing its finite collection before distribution
  begins. Empty means exhausted here. Streaming and stream closure are deferred.
- For aligned distributed inputs, the first/master receive binds the key;
  subsequent receives match it. Dispatch assignments/keys are deterministic or
  coordinated externally; the coordination mechanism is outside this scope.

### Operational semantics: state and scope

The following describes required observable behavior, not a mandated Python
class hierarchy. These rules apply to the emitted trace even without hints.

Each active trace has a location, an invocation scope, a variable environment,
and an enclosing replication owner where applicable. Each replication owner
has an open/closing state and tracks its committed, unfinished instances.
Local memory holds atomic collections and reusable concrete values. Transport
holds pending deliveries identified by source, destination, port, and scope.

Distinguish a scatter invocation from one task within it:

```text
InvocationScope = (operation_id, parent_coordinate_path)
TaskKey         = (operation_id, parent_coordinate_path, task_coordinates)
```

A root scatter has an empty parent path. An inner scatter extends the path
with its outer task's coordinates. Two executions of the same inner operation
under different parents therefore have different invocation scopes, even if
both contain local task coordinate zero. These are conceptual identities; their
serialization is not prescribed here.

Memory selection, transport matching, EOF, availability checks, and U reads all
use invocation scope. A bare `eof` in the trace carries that scope implicitly;
it is not a global shutdown message. Part 1A must settle how generated traces
and metadata establish/propagate this context, or represent it through fresh
logical channels. Leaving data keys scoped while control remains global is not
an acceptable implementation of these semantics.

### Operational semantics: binding and action commitment

Pattern matching is atomic with selecting the occurrence being received or
claimed. Matching an unbound `?name` adds a binding; matching an already-bound
`?name` requires equality. If a tuple member fails to match, no member binding
or collection removal commits. Two occurrences of the same variable within one
pattern must also agree. Matching does not change the original payload/key.

Each replica starts with its enclosing visible bindings and adds its own local
bindings. Parallel branches inside that replica share its invocation environment;
different replicas do not share mutable bindings. Independent sibling branches
must not nondeterministically bind the same unbound variable. Emit a master
binding before parallel keyed receives when they need to share a key.

```swirl
recv((?item_a, ?key) -> p_a, source_a, worker)
.
(
  recv((?item_b, ?key) -> p_b, source_b, worker)
  |
  recv((?item_c, ?key) -> p_c, source_c, worker)
)
```

Here the first receive binds the key. The other receives use that existing key
and bind distinct payload variables. A mismatched message remains available
for another matching invocation; it is not consumed and subsequently rejected.
Once the relevant source closes, an impossible required match must report a
missing input rather than leave a join waiting forever.

For move, source selection/removal and local binding commit together. The
activated instance then owns the selected value, even while delivery is pending.
Its continuation cannot start until the destination recv commits. This separates
an atomic local claim from completion of a potentially remote transfer; it does
not require one global memory/network transaction.

For send, the referenced value is copied into a delivery without consuming its
source occurrence. Both send and move complete only after the matching recv
commits binding and local storage. The receiver's subsequent exec need not have
finished. EOF commits control state and never enters a data collection.

Exec inputs resolve concrete names or existing local bindings. They must not
select unrelated data merely because it occupies the same port. Exec outputs
publish produced values and bind fresh output payload variables. A bound key
in an output remains the same task identity; it cannot be rebound by that exec.
Ordinary reusable inputs remain available to other instances. An operation
failure is not a successful result or EOF; failure must propagate to affected
waits/joins. Automatic retry or restoring consumed work is not specified here.

### Operational semantics: choice, replication, and completion

An unlabelled choice commits one enabled branch-entry action and discards the
other branch for that instance. If neither action can commit, the choice waits.
If both can commit, selection may be nondeterministic; emitted data/EOF patterns
are disjoint so that ambiguity does not arise in the canonical receive choice.

For `data_branch +[port has data] end()`, selecting the data occurrence and
binding/removing it is one atomic action. The closing branch can commit only
when the scoped finite source is empty. Two distributors cannot both claim one
occurrence, or close based on a stale pre-claim check. Empty-source closure
does not imply that previously claimed transfers have finished.

Replication offers fresh instances while its owner is open. An instance becomes
active when its entry action commits; its remaining trace runs in parallel with
other active instances. No fixed iteration count is needed. If an entry action
does not consume a finite resource, finite input elsewhere does not by itself
bound that action's activations. The canonical dispatch and worker entry actions
claim/receive task occurrences, so their useful activations are bounded by tasks.

End changes its nearest enclosing replication owner from open to closing,
preventing further admissions. Other owners remain active. Closing is idempotent
and scoped to the particular invocation, not all uses of the same trace template.
The owner completes only after all already-committed instances finish. Waiting,
unactivated offers are discarded and are not joined as tasks. For a more general
body, already-committed instances blocked later in the trace remain obligations;
end does not silently cancel their unfinished work.

Parallel composition starts both traces and completes only when both complete.
Sequential composition starts its right operand only when the entire left
operand, including nested parallel/replicated descendants, completes. Parentheses
set that boundary; they do not create a second termination mechanism. A valid
trace must arrange every required communication and replication closure so its
obligations can finish. Use a scheduler that permits enabled work to progress;
unlimited theoretical parallelism does not mean infinitely many allocated tasks.

### Dispatch/gather and invariant-input semantics

Dispatch interprets only explicitly scattered inputs as iteration dimensions.
It completes construction of a finite collection before distribution starts:
dotproduct creates aligned tasks; Cartesian products duplicate input payloads
under distinct combination keys. Dispatch/routing must agree across producers,
deterministically or by external coordination. No centralized whole-list
collection is implied by these rules.

Each non-scattered input, including a whole array, is a reusable concrete value
received/established once in the applicable scope. It does not participate in
task exhaustion and is not removed once per task. Exec's use of such a value is
read-only with respect to the binding; application-level file mutation remains
the tool's responsibility. Scalar reuse does not merge separate parent scopes.

U in an output denotes publication of a collection of distinct data occurrences,
not automatic recursive flattening of list-valued payloads. U in a gather input
denotes access to the full scoped collection after its receiver joins, including
zero elements. It is not a pattern that arbitrarily consumes one element.
Part 1A must explicitly accept whether that collection read is non-consuming;
until then, consuming U reads are not an assumed feature.

Gather orders/groups by key coordinates and metadata rather than arrival. It
preserves duplicate-valued tasks, reconstructs flat or nested shape as required,
and returns a list even when the collection is empty. An inner gather returns
its list as one parent-level result associated with the outer key. Empty inner
lists must not disappear or cause sibling parents to merge. Expected task/shape
metadata must permit detecting missing results, including empty dimensions.

### Worked execution of the three-location example

Suppose dispatch publishes `(A, k0)` and `(B, k1)`:

1. l1's distributor claims A and l2's distributor claims B. Which worker claims
   which item is not fixed by these per-worker move traces. Each claim removes
   exactly one occurrence and binds a separate local environment.
2. The source is now empty, so each distributor may select end and close its own
   replication. Its claimed move may still be unfinished at that point.
3. Each worker's matching recv commits and activates a worker instance. Only
   then does the corresponding move finish. Joining that distributor permits
   sending EOF to that worker, regardless of the other distributor's progress.
4. A worker may receive EOF while its previously activated exec is still
   running. End stops new worker admissions but its join waits for the exec and
   its result send. It cannot drop that task just because EOF was received.
5. Each result send finishes only after the matching controller recv stores
   the keyed result. The worker join then permits its result EOF send.
6. The controller closes its receive replication for each source independently.
   Gather starts only after both joins, so both results are present even if B
   finished before A. It reconstructs order from k0/k1 metadata.

For empty input, no data instance activates. Both distributors close and send
EOF, both workers close and forward EOF after their empty joins, and gather
reads an empty collection and returns []. No synthetic data item is required.

For two nested parents, apply the same sequence separately to each invocation
scope. One parent's EOF or empty collection cannot close the other parent's
replication or enter its U gather input.

### Canonical trace shape

Retain option 1:

```text
(dispatch . (distribute_to_worker_1 | distribute_to_worker_2))
|
((collect_worker_1 | collect_worker_2) . gather)
```

Each distributor uses explicitly parenthesized choice branches:

```swirl
(
  !(
    (
      move((?item, ?key) -> p_stream, controller, worker)
    )
    +[p_stream has data]
    (
      end()
    )
  )
)
.
send(eof -> p_stream, controller, worker)
```

Worker replication receives a keyed item, executes the body, and returns its
keyed results. Its EOF alternative receives EOF then calls `end()`; result EOF
is sent after the whole worker replication joins. Each gather receiver similarly
uses `recv((?result, ?key)...) + (recv(eof...) . end())`. Gather receives use one
shared atomic result collection per output/invocation and source-specific EOF.
Gather inputs use `{U(p_res, res)}`. Multiple outputs have explicit corresponding
collections or a documented result record; none may be silently omitted.

### Worker and gather syntax examples

The worker binds its payload/key on receive, uses those bindings as exec inputs,
binds the result payload while retaining the key, and sends result EOF only after
replication completes. This is the l1 worker from the full example below:

```swirl
<l1, {},
  !(
    (
      recv((?item, ?key) -> p_stream, l0, l1)
      .
      exec(s_work_1, {(p_stream, (?item, ?key))} -> {(p_res, (?result, ?key))}, {l1})
      .
      send((?result, ?key) -> p_res, l1, l0)
    )
    +
    (
      recv(eof -> p_stream, l0, l1)
      .
      end()
    )
  )
  .
  send(eof -> p_res, l1, l0)
>
```

Each result receive binds a tuple and appends it to the shared collection;
EOF selects the closing branch instead. Once both source-specific receive
replications finish, gather reads that collection:

```swirl
!(
  (
    recv((?result, ?key) -> p_res, l1, l0)
  )
  +
  (
    recv(eof -> p_res, l1, l0)
    .
    end()
  )
)
```

```swirl
exec(_scatter_gather, {U(p_res, res)} -> {(p_out, d_out)}, {l0})
```

These are proposed-language examples, not inputs accepted by the current
parser/runtime. The complete three-location trace is included in the appendix
so this plan can be reviewed independently of other files.

## Phase 1: translator only

Do not modify `grammar/SWIRL.g4`, generated ANTLR files, compiler visitors,
compiler targets, compiler runtime, parser entry points, or shared metadata
validator/schema code in this phase. Do not compile generated traces, including
with `--target trace`, or execute generated Python workers.

The old parser cannot certify the new syntax. Manually review against the
contract above. Stripping `?`, `U`, guards, and `end()` to parse an old-syntax
skeleton is at most a delimiter/grouping aid, not proof of new syntax or
semantics. A real new-language parser belongs to Phase 2.

### Part 1A: baseline and output contract

Tasks:

- Inspect current diffs and generate baseline traces for basic, simple scatter,
  and minimal nested scatter without changing compiler code or running tests.
- Trace current source resolution, deployment selection, helper metadata, and
  recursive lowering end to end. Record existing logical behavior to preserve.
- Specify the exact emitted forms of variables, tuples, U collections, guarded
  choices, end, and precedence. Use explicit grouping instead of depending on
  ambiguous operator precedence.
- Specify invocation isolation for data, availability predicates, EOF, `end`,
  and U reads. Data keys alone do not isolate unkeyed control markers in repeated
  invocations sharing ports. Decide whether inherited invocation context or
  fresh logical channels supply this isolation; show the representation to the
  user before claiming nested traces are complete.
- Specify metadata descriptors for dynamic variables separately from concrete
  dependency names. Do not enter runtime `?` bindings as ordinary static data.
- Document dispatch pairing/routing and gather ordering/shape contracts. Reuse
  helper types and metadata where sufficient; record required schema evolution
  for Phase 2 rather than silently claiming new metadata validates under old
  schemas. Do not add a metadata version without a concrete need.

Review artifact: baseline output plus a concise syntax/scope contract and a
before/after lowering example. Per the 2026-10-02 clarification, combine this
review with the first working emission slice rather than stop at a plan-only
approval. Only after acceptance of that implementation add/run tests for
translator analysis behavior covered by this accepted part.
New-language parser tests remain deferred to Phase 2.

### Part 1B: simple scatter emission

Tasks:

- Replace old `data[key]` placeholders with payload-first `(?payload, ?key)`
  patterns/references. Separate rendered variable names from static metadata.
- Emit U dispatch/gather flows and explicit guarded dispatch termination.
- Emit end in EOF receive alternatives and move EOF forwarding after joins.
- Keep option 1, two-or-more worker distribution, shared atomic result
  collections, and one receive loop per source/output.
- Preserve ordinary workflows, commands, arguments, expressions, data types,
  output processors, deployment settings, and whole-value list handling.
- Generate simple scatter, empty-input, duplicate-value, scalar-invariant,
  whole-list-invariant, and multiple-output review cases. Add small example
  fixtures only where existing fixtures cannot express the case.

Review artifact: emitted SWIRL/metadata and a hand walk-through for zero, one,
and more tasks than workers. Exit gate: user accepts these outputs; only then
add/update/run focused translator tests for this part. Test metadata and emitted
structure without invoking the old compiler or pretending its parser supports
the new syntax.

### Part 1C: complex and decentralized lowering

Tasks:

- Support dotproduct pairing and equal-length validation; Cartesian expansion
  duplicates task data with distinct coordinate-derived keys. Preserve flat
  versus nested output shape and declaration-order coordinates.
- Preserve scalar/whole-list inputs outside consuming task distribution and
  make them reusable in the applicable scope.
- Lower inputs from different producer locations using the agreed master-key
  binding and keyed matching. Never silently collect whole input lists at one
  controller as a substitute for decentralized lowering.
- Obtain consent before replacing existing centralized pair/open input bundling
  with a logically different distributed dispatch plan, changing placement or
  worker-pool policy, or adding new interpretation of multiple CWL sources.
  Prepare the proposed lowering concretely before requesting that consent.
- Carry complete parent coordinate paths through arbitrarily nested scatters,
  sibling scatters, and scattered subworkflows using existing recursive lowering.
- Scope channels/collections/EOF by invocation according to Part 1A. Inner end
  cannot close an outer replication or another parent's inner invocation.
- Inner gather always emits a list, including [], associated with its parent
  key. Rekey that list as the parent result before returning it outward.
- Handle several outputs and several consumers without an accidental consuming
  read. Preserve metadata ordering and shape rather than infer them from arrival.
- Diagnose missing keyed inputs on closure, mismatched lengths, unresolved
  sources, and unsupported cases explicitly; do not emit a trace known to hang.
- Preserve advisory hints where useful, but correctness cannot depend on them.

Review artifact: traces for all scatter methods; distributed aligned inputs;
two sibling scatters; at least three levels of nesting; different and shared
worker pools; varying inner cardinalities including zero; scalar invariants;
and several outputs. Include a semantic walk-through of matching, EOF, and U
scope for two concurrent parent invocations on the same inner worker.

Exit gate: user accepts this part and any changed logical lowering. Only then
add/update/run its focused translator unit tests. Split this part into smaller
review batches if outputs become difficult to assess.

### Part 1D: final translator acceptance

Generate and inspect the available fixtures:

- `examples/cwl/basic`, `nested`, `expressions`, `lists`, and `lists-input`;
- `examples/cwl/scatter` and `scatter-nested-minimal`;
- `examples/cwl/scatter-nested` and `scatter-nested-zip`;
- `examples/cwl/1000genome` and/or `examples/1000genome`, after checking which
  fixture is the intended acceptance target;
- any narrowly added cases required by Parts 1B/1C.

Commands use separate generated-output directories so one fixture does not
overwrite another before review. The CLI requires the output directory to exist:

```sh
rtk mkdir -p build/scatter-nested-minimal
rtk uv run python ./tmp_main.py translate \
  --language cwl \
  examples/cwl/scatter-nested-minimal/streamflow.yml \
  --outdir build/scatter-nested-minimal

rtk mkdir -p build/scatter-nested-zip
rtk uv run python ./tmp_main.py translate \
  --language cwl \
  examples/cwl/scatter-nested-zip/streamflow.yml \
  --outdir build/scatter-nested-zip
```

Use the configured Python environment directly instead of `uv run` if desired.
Inspect both `workflow.swirl` and `metadata.yml`, including logs: `tmp_main.py`
currently ignores the return value of `main.main`, so shell exit status alone
does not prove translation succeeded. Do not fix that wrapper incidentally.

For each artifact, check grouping, bindings, producers/consumers, concrete names
versus variables, helper contracts, invocation/control scope, deployments,
scatter cardinality, output types/shape, and deterministic naming. Manually
reason through synchronous sends to rule out circular waits. A trace review
establishes the intended plan, not successful distributed execution.

Exit gate: the user explicitly accepts the complete translator implementation
and emitted syntax/semantics. Then run the accepted translator tests and final
translator regression checks. Compiler-dependent tests remain deferred. Do not
change old compiler expectations merely to conceal their incompatibility.

**Phase 2 cannot start before this explicit translator acceptance.**

## Phase 2: new Python compiler and runtime

Start only after the Phase 1 acceptance record exists. Build ordinary execution
first; hint-driven optimization, streaming, retries, and broad scheduler work
are outside this plan. Reuse existing deployment, command/expression execution,
serialization, and generated launcher support where their behavior remains
correct. Do not preserve old scatter runtime heuristics as semantic fallbacks.

### Part 2A: parser and compilation contract

- Extend the grammar for `?variables`, tuple patterns, U collection entries,
  guarded choice, and `end()`. Preserve concrete legacy non-scatter syntax.
- Define operator grouping, binding scope, variable declarations/references,
  supported guard forms, and diagnostics for invalid/unbound uses.
- Regenerate ANTLR reproducibly with the pinned tool/runtime version. Update
  compiler-side utilities and visitors without reducing tuples to static names.
- Implement the smallest structured trace representation needed for binding,
  nested replication ownership, source diagnostics, and completion joins.
- Apply the accepted metadata contract and only necessary validator/schema
  changes. Define the deliberate compatibility boundary for old scatter syntax;
  do not silently compile it with different semantics.
- Manually parse and inspect accepted translator artifacts before user review.

Gate: user accepts parsing and compilation structure; then add/run parser,
binding-diagnostic, metadata, and structural compiler unit tests.

### Part 2B: bindings, collections, and communication

- Implement local/inherited binding environments; unbound pattern members bind,
  bound members match. Exec output payloads bind while task identity is retained.
- Implement invocation-scoped atomic collections and selected-value references.
  move consumes; send copies; invariant values remain reusable.
- Implement synchronous send acknowledgements after recv commits the payload,
  key, and binding/storage effects; move delivery follows the same acknowledgement
  contract. Network arrival alone is not acknowledgement.
- Support keyed receive selection, missing-match diagnostics on stream closure,
  source-specific EOF, shared result appends, and scoped U snapshots.
- Keep operation ID, parent coordinates, shape/order metadata, and control scope
  in message/runtime state. Never derive identity from filenames or payload text.
- Manually inspect/run small local examples of matching and communication.

Gate: user accepts the observed behavior; then add/run focused runtime unit tests
for these operations. No per-helper suite that merely mirrors implementation.

### Part 2C: parallel replication, choice, and joins

- Admit replicas on committed entry actions; run their continuations in parallel.
  Do not implement ! as a serial item-processing loop or eagerly create
  unbounded blocked threads.
- Atomically select guarded/pattern alternatives and close replication on end.
  Closure stops admissions once, remains scoped, and joins committed instances.
- Track sequence/parallel completion so next actions wait for every descendant.
  Worker EOF occurs after work/result sends; dispatch EOF follows item deliveries.
- If bounded scheduling is necessary, suspended parent tasks must not retain all
  execution capacity while waiting for nested children. Preserve theoretical
  parallel semantics independently of a finite hardware limit.
- Propagate execution failures to joins/communication waits rather than treating
  failure as successful completion or leaving waits silently blocked. No retry
  framework is required.
- Manually demonstrate delayed work, out-of-order finishes, zero tasks, and
  concurrent nested parents before review.

Gate: user accepts replication/completion behavior; then add/run its focused
unit tests, using bounded test timeouts only after acceptance.

### Part 2D: dispatch/gather execution and final acceptance

- Implement accepted helper behavior for pairing, Cartesian duplication,
  invariants, full task keys, and gathers with correct order/nested shape.
- Ensure an empty inner gather returns [] with its parent's identity.
- Run the accepted translator outputs locally, then on the relevant existing
  deployment fixtures where available. Confirm decentralized input routes and
  all intended outer/inner worker pools, not just successful helper calls.
- Manually compare outputs against expected values and shape for the Phase 1
  matrix. Removing advisory hints must preserve behavior.
- Present generated Python, execution evidence, remaining limitations, and
  representative outputs for final user review.

Gate: user accepts compiler behavior; then add/run end-to-end regression tests
and the relevant complete suite. Only now can end-to-end execution be claimed.

## Acceptance record

2026-10-02: Part 1A baseline translations and manual inspection completed.
See [Part 1A review](NEW_SYNTAX_PART_1A_REVIEW.md) for artifacts, preservation
findings, proposed U snapshot semantics, qualified-channel isolation, and dynamic
metadata descriptors. Contract acceptance remains pending; no tests have run.

2026-10-02 clarification: Part 1B simple emission is now implemented for review;
see [working translator review](NEW_SYNTAX_PART_1B_REVIEW.md). Root invocation
channels are operation-specific. The earlier qualified-channel extension is
unapproved and unimplemented; nested scatter is diagnosed explicitly until its
scope lowering is implemented. No parser/compiler/runtime/schema changes or unit
tests have been made. Parts 1A/1B await implementation satisfaction together.

2026-10-02: The user accepted the working simple slice ("looks correct to me")
and authorized continuation. Focused simple-scatter/ordinary checks now pass
9/9, including fresh output bindings when CWL input/output names overlap. The
first Part 1C batch emits parent-qualified channels, invocation activation/routes,
nested rekeyed gathers, and method/shape metadata. See
[Part 1C working review](NEW_SYNTAX_PART_1C_REVIEW.md). Existing minimal/shared/ZIP
and new three-level/method fixtures translate for manual review. This batch's
acceptance and automated nested tests remain pending; distributed inputs and
multi-source semantics remain the next consent/review batch. Compiler/runtime
and schemas remain unchanged.

Fill these during implementation; none is accepted merely because it is planned.

| Part | User acceptance | Approved test result | Open decisions |
| --- | --- | --- | --- |
| 1A: baseline/contract | Simple-slice contract accepted 2026-10-02 | 9 focused checks passed with 1B | Nested batch awaits review; dynamic schema for Phase 2 |
| 1B: simple emission | Accepted 2026-10-02: "looks correct to me" | 9 passed | None for accepted simple slice |
| 1C: complex lowering | First nested/method batch implemented; pending satisfaction | New-batch tests deferred; 1B checks pass | Review qualified channels/activation; later consent for distributed lowering |
| 1D: translator complete | Pending; 26-fixture review run on 2026-10-02 superseded by 27 corrected-stream artifacts on 2026-10-05 | 9 accepted checks pass | Corrected streams require review; required Phase 2 gate |
| 2A: parser/compiler contract | Not started | Not run | After translator acceptance |
| 2B: bindings/communication | Not started | Not run | None recorded |
| 2C: replication/joins | Not started | Not run | None recorded |
| 2D: execution complete | Not started | Not run | None recorded |

Stop at each approval boundary. Do not bypass it by writing future-part tests,
changing compiler code in Phase 1, or treating elapsed time as user acceptance.

## Appendix: complete scatter4 trace

Snapshot of [examples/swirl/scatter4.swirl](examples/swirl/scatter4.swirl).
l0 dispatches a finite collection, concurrently collects results from l1 and
l2, and gathers after both receiver replications finish. Both workers preserve
the task key. U collections and tuple variables follow the contract above.
When the accepted example changes, update this embedded trace and the
representative snippets together.

```swirl
<l0, {(p_in1, d_in1)},
  (
    exec(_scatter_dispatch, {(p_in1, d_in1)} -> {U(p_stream, d_stream)}, {l0})
    .
    (
      (
        !(
          move((?item, ?key) -> p_stream, l0, l1)
          +[p_stream has data]
          end()
        )
        .
        send(eof -> p_stream, l0, l1)
      )
      |
      (
        !(
          move((?item, ?key) -> p_stream, l0, l2)
          +[p_stream has data]
          end()
        )
        .
        send(eof -> p_stream, l0, l2)
      )
    )
  )
  |
  (
    (
      !(
        (
          recv((?result, ?key) -> p_res, l1, l0)
        )
        +
        (
          recv(eof -> p_res, l1, l0)
          .
          end()
        )
      )
      |
      !(
        (
          recv((?result, ?key) -> p_res, l2, l0)
        )
        +
        (
          recv(eof -> p_res, l2, l0)
          .
          end()
        )
      )
    )
    .
    exec(_scatter_gather, {U(p_res, res)} -> {(p_out, d_out)}, {l0})
  )
> |

<l1, {},
  !(
    (
      recv((?item, ?key) -> p_stream, l0, l1)
      .
      exec(s_work_1, {(p_stream, (?item, ?key))} -> {(p_res, (?result, ?key))}, {l1})
      .
      send((?result, ?key) -> p_res, l1, l0)
    )
    +
    (
      recv(eof -> p_stream, l0, l1)
      .
      end()
    )
  )
  .
  send(eof -> p_res, l1, l0)
>

|

<l2, {},
  !(
    (
      recv((?item, ?key) -> p_stream, l0, l2)
      .
      exec(s_work_2, {(p_stream, (?item, ?key))} -> {(p_res, (?result, ?key))}, {l2})
      .
      send((?result, ?key) -> p_res, l2, l0)
    )
    +
    (
      recv(eof -> p_stream, l0, l2)
      .
      end()
    )
  )
  .
  send(eof -> p_res, l2, l0)
>
```
