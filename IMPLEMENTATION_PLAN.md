# SWIRL implementation plan

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

`U(port, collection, scope)` denotes a scoped collection, not an unwrapped data
message. Its elements are envelopes; gather produces `(list_payload, scope)`,
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
- `[port has data in scope]` and `U(port, collection, scope)` select only that
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

## Remaining work, in order

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

- Extend grammar/generated ANTLR for variables, tuple patterns, U, guards,
  `end()`, root/composed IDs, begin/EOF envelopes and scoped guards/U. Define
  matching/construction context, precedence and fresh-owner bindings. Decide
  legacy syntax compatibility explicitly; ordinary output now also uses envelopes.
- Regenerate with pinned ANTLR 4.13.2. Add the smallest structured representation
  needed for bindings, explicit scope-opening receives, owner tracking and completion.
- Update schemas, validation and entity registration for the accepted dynamic
  descriptors and helpers. Decide metadata/old-scatter compatibility explicitly;
  neither a version bump nor dual formats is automatically required.
- Inspect accepted artifacts through parsing/validation, then present the result.
  After satisfaction, add/run parser, metadata and structural compiler checks.

### 3. Implement bindings, scoped state and communication (Part 2B)

- Add local/inherited environments, atomic matching/collections, keyed message
  selection, reusable values, scoped EOF and U snapshots.
- Make send copy and move consume exactly the selected occurrence; acknowledge
  only after recv commits. Detect missing closed-stream matches and propagate
  failures. Reuse existing serialization/deployment support where correct.
- Demonstrate ordinary and keyed communication manually; after satisfaction,
  add/run focused behavioral checks.

### 4. Implement parallel replication and joins (Part 2C)

- Implement committed admission, atomic choice/exhaustion, scoped idempotent
  closure, draining and sequence/parallel descendant joins.
- Implement explicit begin-driven scope owners, nested receiving loops and value
  readiness without unbound variables or parent/child wait cycles.
- Demonstrate delayed work, reversed completion, zero tasks and concurrent
  nested parents sharing workers; after satisfaction, add/run timed checks.

### 5. Execute dispatch/gather and prove end-to-end behavior (Part 2D)

- Implement independent cardinality exchange, full-key routing, all methods,
  expected-result validation and deterministic shape-preserving gathers.
- Execute the acceptance matrix below with and without hints. Show generated
  Python, outputs and remaining limitations for review; after satisfaction,
  add/run end-to-end regressions and the relevant complete suite.
- Replace/remove superseded runtime heuristics and stale compiler-dependent
  scatter tests as their supported replacement becomes available. Update or
  safely ignore legacy hint scanning; specialized optimization is deferred.
- Refresh example/reference documentation so translation success is clearly
  distinguished from parse, compile and execution success.

## Acceptance matrix and completion

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

Runtime verification of exact values, out-of-order completion, hint-free behavior
and absence of blocked joins remains a later phase.

Done means the accepted translator outputs parse and validate, execute with
correct identity/shape/completion on intended locations, remain equivalent
without hints, and preserve ordinary workflow behavior. Translation alone is
not end-to-end completion.

## Superseded material and deferred scope

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
then proceed to dependent work. Translator acceptance precedes Phase 2. Internal
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
