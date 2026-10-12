# Translator repair plan

Created 2026-10-09 after the independent review of `build/rebuild-manifest.json`.
This is the active repair queue for the six reported findings, starting with #1.
The target contract and implementation handoff in `IMPLEMENTATION_PLAN.md` remain
normative; this plan adds the user's clarified parallel step-group semantics and
supersedes historical claims of translator completeness. Old artifact line numbers
below identify the reviewed snapshot; relocate actions after regeneration.

## Scope and gates

The 2026-10-09 implementation request authorizes repairs #1, #2 and #4 and manual
translation/artifact regeneration. It supersedes the original planning-only gate.
Implementation stays within translator and metadata production, preserving the
existing recursive region/dependency model, deployment lookup and approved worker
reservation policy.

Do not run/add automated tests, execute workflows, change parser/compiler/runtime,
restore deleted fixtures, inspect binaries, commit, push or interact with remotes
under this plan. Manual translation is authorized; source and generated workflows
are not executed. Artifacts, logs and source inspection are structural evidence,
never execution proof.

Implement #1 first, then #2 and #4. Repairs #3, #5 and #6 are deferred together
as a later metadata update, including stdout destinations, output processing and
argument transformations. Resume them after the `.swirl` syntax is frozen and
the user resumes testing on complex workflows such as 1000Genomes. Their design
requires no additional trace operations; later execution support also requires
metadata schema, loader and evaluator changes. This does not authorize tests now.
Keep changes targeted; do not introduce
a new scheduler, IR, parser or general framework. Use existing `EmittedFragment`,
`_sequence`, `_parallel`, producer references, pending gathers and owner obligations.
Keep the reviewed source CWL unchanged: the reported faults belong to translation.

## Immediate repairs

Implementation order: #1, #2, then #4. Finding numbers are retained from the
independent review for traceability.

### 1. Preserve parallel step groups and remove publication-induced cycles

#### Required semantics

The original SWIRL unit is:

```text
step = (recv | ... | recv) . exec . (send | ... | send)
workflow invocation = step_A | step_B | ...
```

Each input group joins before its execution; each publication group joins before
that producer completes. Different step groups run in parallel. A source dependency
is enforced by the required receive, not by sequencing entire groups in traversal
order. Topological order can determine construction and naming without becoming
runtime `.` sequencing. Co-location does not create a dependency.

Scatter extends this structure rather than replacing its dependency semantics:
input reception can include scoped receive/gather stages, execution can be a
worker loop containing recursive parallel groups, and publication can include
producer-local dispatch/distribution. This is an edge-specific correspondence,
not three universal global barriers. Ordinary edges stay ordinary; only explicit
scatter adds a coordinate, and only crossed scatter outputs require gathering.
Completed upstream lists must be gathered before a downstream scatter dispatches
them using its own declaration. Dispatch stays at the actual list producer.

#### Evidence and concrete failure

In the reviewed `build/1000genome/streamflow/workflow.swirl:575`, the local `l1`
chromosome branch synchronously sends the chromosome invariant before executing
`get_intervals` at line 593. Its receiver at line 1928 is behind interval begins
at lines 1910–1912. Those begins need the interval outputs, creating:

```text
chromosome publication -> invariant receive -> interval begins
  -> interval production -> chromosome publication
```

The source `examples/1000genome/main.cwl` has no dependency between
`get_chromosome` and `get_intervals`. `individuals` depends on both. Fix the
general composition rule, not just this trace or this placement.

#### Implementation instructions

1. Follow `lower_region`, `_lower_invocation_body`, `lower_scatter`, final location
   composition and every append to a producer publication tail. Identify where
   separately lowered invocations become a single sequence.
2. Assemble one input/execution/publication group per logical invocation, then
   compose independent groups in parallel in their lexical owner. Apply this
   inside ordinary subworkflows and every recursive scatter task, including
   remote service bodies. Preserve admission/setup and closure outside the groups
   wherever those are actual owner prerequisites or completion obligations.
3. Compose independent destination publications in parallel. A blocked fan-out
   send must not gate another destination or unrelated producer. Retain one
   occurrence per consumer through copies/separate ports; do not duplicate moves
   that compete for the same occurrence.
4. Make all dependent input bindings explicit. Parallelizing existing sequences
   can invalidate direct reuse of local output variables. Use existing owner-local
   staging/send/receive patterns where needed, including self communication, so
   consumers acquire their own payload/ID bindings. Do not assume sibling branches
   share bindings or introduce implicit aliases. Root/ancestor invariants retain
   their real identities and remain reusable.
5. Enable receiving services and collectors before synchronous sends can block
   them. Keep independent input begin/dispatch branches able to progress; workers
   still receive all required begins before admitting data and all required EOFs
   before `end()`. Do not solve startup by weakening that protocol or making sends
   asynchronous.
6. Retain sender-owned EOF after the producer's admitted work and acknowledged
   publication join. Do not wait for downstream final gather/execution before
   producer EOF. Each materialization sender closes its own stream; enclosing
   owners drain committed descendants before their completion.

#### Structural acceptance

- In the genome trace, interval production and dispatch can progress while a
  chromosome invariant publication is blocked. `individuals` still waits for
  both streams and its invariants; `individuals_merge` still waits for gathering.
- Ordinary A -> B remains ordered by data readiness, while independent A and C
  can run concurrently. Several inputs and several output destinations have
  parallel reception/publication with explicit local bindings.
- Walk startup, one admitted task, two concurrent parent tasks and zero-child
  closure through both chromosome placements. Include a deliberately delayed
  consumer in the reasoning. No begin, self-send, publication or EOF wait cycle
  may remain.
- Inner/outer gather stages, list shape, scopes and service closures remain intact
  when the step bodies become parallel. No bare global replacement of `.` by `|`.

### 2. Give every emitted exec its own matching metadata tool

Reviewed evidence: genome `metadata.yml:208` uses `_l5` ports for individuals,
while `workflow.swirl:1943` supplies `_l3`; expression inputs at metadata line 120
use `_l2`, while execution at trace line 593 supplies `_l1`.

The original SWIRL contract requires every distinct emitted `exec` action to
reference a distinct tool entry in metadata, even when commands or port sets are
identical. This applies to ordinary tools, expressions and dispatch/gather helpers.
A single emitted exec inside replication keeps one descriptor: its repeated runtime
instances do not require separate metadata entries.

Inspect registration of `context.steps` and repeated lowering of the same invocation
across workers/controllers. Allocate a unique, deterministic tool name for each
emitted exec and register its descriptor with exactly that action's input/output
ports. Stop one placement from overwriting another's descriptor. Keep full
invocation identity and update helper references, routing and shape descriptors
to the corresponding unique names. Shared descriptors are not an alternative.

Acceptance: each emitted exec references an existing metadata tool entry, and no
two distinct emitted exec actions reference the same entry. Compare every command
argument, expression input and output descriptor against its corresponding exec,
including all workers and parent placements. Every
referenced port must belong to that exec's bound input/output flow. Verify helper
routes and shape references too; do not repair only the last emitted placement.

### 4. Preserve distinct deployment services and options

Implement after #1 and #2; do not defer this repair with the later metadata update.
It affects both location allocation in the trace and deployment metadata. Distinct
services within one deployment must retain their intended distinct locations;
correcting those locations may require an ordinary send/receive between steps.
This preserves the configured placement and introduces no scatter boundary.

Reviewed evidence: basic SLURM `workflow.swirl:7` runs step2 at step1's location;
`metadata.yml:29` omits the distinct services and scheduling options. Expressions
SLURM metadata loses its selected service options as well.

Inspect location allocation, lookup and deployment serialization. Retain service
identity wherever deployment targets are compared or deduplicated; serialize the
selected service options alongside the existing wrapped SSH configuration. Avoid
changing approved scatter worker reservations as a side effect.

Acceptance: `broadwell-step1` and `broadwell-step2` resolve to distinct intended
locations, with partition/nodes/ntasks/time retained. Expressions SLURM retains
its own selected service settings. Local, SSH and split configurations retain
their previous intended routes.

## Deferred metadata update

Resume after `.swirl` syntax freeze and authorized complex-workflow testing.
Implement #3, #5 and #6 together using one tool-level input map and shared
evaluation support; the subsections retain their original finding numbers.
These repairs require no additional SWIRL trace operations.

### 3. Preserve CWL command argument expressions

Reviewed evidence: both ordinary nested `metadata.yml:6` files retain `/bin/sh -c`
but omit the scripts in `trim.cwl`, `upper.cwl` and `tag.cwl` `arguments.valueFrom`.

The selected metadata design uses one tool-level input map for all argument
expressions, rather than separate input maps or `self` port mappings per argument:

```yaml
inputs:
  text: p_text
arguments:
  - expression: "printf '%s' '$(inputs.text)' | tr -s ' '"
```

This excerpt supplements the tool's command and other descriptors. Retain literal
`value` and direct-port `valueFrom` arguments; represent CWL expressions explicitly
as `expression`. Map all named CWL inputs once in `inputs`. For an inputBinding
expression such as `$(self.nameroot)`, normalize the reference to the corresponding
named input, e.g. `$(inputs.population.nameroot)`, using the source binding's known
context. Do not implement that normalization with blind string replacement.

Evaluate expressions during command construction within the existing exec, from
its bound input payloads. Preserve argument ordering and CWL interpolation/quoting
semantics; do not rewrite arbitrary scripts into shell positional arguments.
No additional expression exec, port or communication action is required for inputs
already present in the exec flow. This design changes the emitted metadata format,
not the SWIRL syntax or trace. Implementing it later also requires metadata schema,
loader and command-evaluation support; it is not just a YAML-writing change.

Defer implementation until `.swirl` syntax freeze and authorized complex-workflow
testing. The basic examples do not require this feature, but the ordinary nested
trim/upper/annotate examples already use these expressions: their reported omission
remains unresolved and must not be counted as corrected during the interim review.
Preserve validation/error reporting for unsupported forms rather than silently
omitting them when expression support is implemented.

Acceptance: each nested tool descriptor includes its command script and correct
input context; `text -> trim -> upper -> annotate` preserves ordinary IDs,
declared aliases and split placement. Argument order must agree with the source.

### 5. Preserve stdout and output processing explicitly

Reviewed evidence: scatter and scatter-nested `metadata.yml:71` omit `stdout:
result.txt`; basic and ordinary nested outputs retain a glob but lose stdout,
`loadContents` and `outputEval`.

Defer all of this repair, including explicit stdout preservation, to the later
metadata update with #3 and #6. Encode stdout destinations, loadContents, dynamic
glob expressions and outputEval within the existing tool descriptor. These do not
require additional execs, receives, sends or changes to SWIRL trace syntax.

Use the tool-level `inputs` map from #3 when output expressions reference inputs.
Output processors also have their own CWL `self` context: for example,
`$(self[0].contents.trim())` operates on the matched output File objects after
contents loading, not on a tool input. Supply that output context to the shared
evaluator; do not apply inputBinding normalization to output expressions blindly.
Keep this defect explicitly unresolved during interim translator review.

Retain explicit stdout destinations and output read/evaluation descriptors in
tool metadata. Preserve declared payload types, dynamic glob context and operation
ordering: execute, locate/read outputs, evaluate the processor, then publish the
result envelope. Do not rely on legacy compiler heuristics inferring stdout from
a glob or trimming all string outputs automatically. Compiler implementation is
deferred; document the descriptor contract without claiming it already executes.

Acceptance: echo's File output has an explicit file-creation route; ordinary string
outputs encode the declared loading/trimming expression. Output processing must
operate on payloads and preserve the current invocation ID. List-valued outputs
remain one occurrence at enclosing gathers.

### 6. Preserve inputBinding.valueFrom transformations

Reviewed evidence: genome `metadata.yml:363` and `:421` pass population ports
directly, dropping `$(self.nameroot)` from both source tools.

Use the selected tool-level `inputs` map and expression arguments from #3. For
population, map `population: p_scatter_0_2` (or the corresponding operation's port)
and encode `expression: $(inputs.population.nameroot)`, retaining prefix and
argument order. Do not add a separate per-argument input map or expression exec.
Implement this with #3 after syntax freeze and authorized complex-workflow testing;
do not confuse a port reference with an expression string.

For example, the later tool metadata will use:

```yaml
inputs:
  population: p_scatter_0_2
arguments:
  - value: -pop
  - expression: $(inputs.population.nameroot)
```

The existing exec supplies the population payload; the command evaluator extracts
its nameroot. This updates metadata without adding SWIRL trace actions or changing
the task identity. Implement #3, #5 and #6 as one consistent metadata/evaluation
update, retaining their separate acceptance conditions.

Acceptance: a population File whose nameroot is `AFR` structurally supplies
`-pop AFR`, not its File/path representation. Mutation and frequency output globs
retain the same source name context. Review retained tools for other silently
discarded argument/output descriptors; report unsupported cases explicitly.

## Final translator review and remaining coverage

For future authorized implementation validation, start with all 12 configurations
in `build/rebuild-manifest.json`. Derive source dataflow first, then inspect each
trace, metadata and complete translation log. Check file completeness and logged
exceptions independently of CLI exit status: `tmp_main.py` can exit zero on failure.
Repeat manual translations to compare deterministic artifacts only when that work
is authorized. Record evidence per repair; old success flags are not acceptance.

Review envelopes, binding order, operation isolation, actual producer placement,
declared output aliases, fan-out, gather stages/types and matching begin/EOF routes
with hints ignored. Retain ordinary whole-list inputs and source defaults.

The reviewed build lacks the claimed `build/recursive-validation/final/` probes.
Do not restore deleted fixtures or treat the plan's historical records as coverage.
Future manual probes under build should cover three/five levels, differing concurrent
cardinalities, Cartesian empty dimensions, distinct dimension producers, fan-out,
sibling scatters and delayed consumers, through the same recursive lowering path.

Interim completion covers #1, #2 and #4; explicitly list all of #3, #5 and #6
as outstanding deferred metadata work. Full completion of this repair
queue means the six defects have structural evidence of correction and no introduced
dependency/binding/shape regressions are identified.
Obtain translator acceptance before parser/compiler/runtime work. Exact outputs,
out-of-order completion, hint-free execution and freedom from runtime blocked joins
remain later execution proof; translation alone cannot establish them.


## Implementation evidence — 2026-10-09

Repairs #1, #2 and #4 implemented; user acceptance remains pending. No claim of
runtime correctness or acceptance is made. Repository-root AGENTS.md was absent;
the supplied AGENTS.md instructions and /home/tommo/.codex/RTK.md were applied.

### Changes and structural findings

- Invocation groups run in parallel at root and recursively inside ordinary
  workflows and worker task bodies. Publication tails join parallel destination
  copies. Sibling outputs use explicit consumer ports and receives, including
  self communication; gathered values retain their separate readiness route.
- A first input begin explicitly binds a fresh owner scope before other begin,
  invariant and descendant-opening branches use it. Remaining setup joins before
  task admission. Remote services and collectors participate alongside producers.
- Direct scattered tools and reusable-output occurrence helpers retain execution
  before their publication tail. EOF stays after admitted work and acknowledged
  publications; consumer gather/execution is not added to the producer tail.
- Each concrete exec gets a deterministic allocated metadata name. Replicated
  runtime instances retain their template descriptor. All descriptors record exact
  `inputPorts` and outputs. Dispatch keySpace and gather shapeFrom/helper references
  use allocated names; dispatch routes describe their own producer placement.
- Location keys include deployment and service. Selected SLURM service name and
  partition/nodes/ntasks/time coexist with wrapped SSH settings. Existing lookup
  and descendant worker reservations are retained; placement adds no coordinate.

Source-derived checks: basic step1 -> step2 and greeting fan-out; ordinary nested
trim -> upper -> annotate without scatter coordinates; whole-list ordinary edges;
expression output types; dotproduct coordinate pairing; nested inner File[] then
outer File[][] materialization. Genome chromosome and interval producers are
independent; individuals waits for both dimensions and invariants, merge waits for
its gathered File[], and sifting can progress independently. Mutation/frequency
use separate population scatters and explicit invariant copies.

Walked synchronous startup, admitted tasks, concurrent parent IDs, empty closure
and delayed publication consumers through both genome parent placements and the
nested traces. Parallel chromosome destinations can block independently without
blocking interval production/dispatch. Inner source EOF follows its publication
join before downstream merge/final gather. Remote materialization senders close
their own routes, while enclosing services drain admitted descendants. Nested
stages retain full scope matches, ordering/validation metadata and list nesting.
Compiler hints were ignored in this reasoning. These are structural walks, not
observed runtime scheduling or error behavior.

### Regenerated and inspected configurations

Complete translation.log, workflow.swirl and metadata.yml inspected for each:

- examples/cwl/basic/streamflow-slurm.yml -> build/cwl/basic/streamflow-slurm
- examples/cwl/basic/streamflow-split.yml -> build/cwl/basic/streamflow-split
- examples/cwl/basic/streamflow.yml -> build/cwl/basic/streamflow
- examples/cwl/expressions/streamflow-slurm.yml -> build/cwl/expressions/streamflow-slurm
- examples/cwl/expressions/streamflow.yml -> build/cwl/expressions/streamflow
- examples/cwl/lists/streamflow.yml -> build/cwl/lists/streamflow
- examples/cwl/lists-input/streamflow.yml -> build/cwl/lists-input/streamflow
- examples/cwl/nested/streamflow-split.yml -> build/cwl/nested/streamflow-split
- examples/cwl/nested/streamflow.yml -> build/cwl/nested/streamflow
- examples/cwl/scatter/streamflow.yml -> build/cwl/scatter/streamflow
- examples/cwl/scatter-nested/streamflow.yml -> build/cwl/scatter-nested/streamflow
- examples/1000genome/streamflow.yml -> build/1000genome/streamflow

Used `rtk .venv/bin/swirlc translate -l cwl CONFIG -o OUTPUT`, capturing stdout and
stderr in translation.log. File completeness and full logged failures were checked
independently of exit status. Final repeated translations produced identical SWIRL
and metadata bytes for every configuration. Raw logs differ where CWL diagnostic
printing includes object addresses and inline-workflow UUIDs; logs are not claimed
byte-identical. No logged translation failure found. Metadata inspection found
71 exec actions and 71 unique matching descriptors (44 in genome), with no
missing/unused descriptors, input/output port mismatch or dangling helper reference.

New manual probes under build/repair-probes (not restored historical fixtures):
depth3/streamflow.yml -> depth3/translated, depth5/streamflow.yml -> depth5/translated
and cartesian/streamflow.yml -> cartesian/translated. Complete logs and both output
artifacts inspected; final repetitions were byte-identical for SWIRL/metadata,
with 28 unique matching exec descriptors across the probes. Their source expectations and generated scope/gather
structure cover unequal concurrent parent cardinalities, empty descendants,
three/five explicit scatter levels, independent expression dimension producers,
fan-out to sibling scatters and nested Cartesian 2-by-0 shape [[], []]. Shape is
specified by metadata; actual resulting payload is not runtime-proven.

### Unresolved work and coverage limits

Deferred metadata #3 (command argument expressions), #5 (stdout and output
processing) and #6 (inputBinding.valueFrom transformations) remain unresolved.
`inputPorts` records exec ownership only and does not implement their evaluator or
expression input map. No source CWL was changed to conceal these omissions.
Deep probes are co-located; deeper distributed coverage relies on the available
scatter-nested and genome configurations. The Cartesian empty probe has no admitted
child task; nonempty dotproduct task reasoning uses the manifest examples.
Historical build/recursive-validation/final artifacts remain unavailable and were
not restored or counted. Delayed consumers were reasoned about structurally, not
executed. No automated tests, source/generated workflow execution, parser/compiler/
runtime stages, binary inspection, commits, pushes or remote interaction occurred.
Runtime matching, out-of-order completion, cardinality errors, concrete list payloads
and hint-free execution remain later execution proof, after user authorization.
