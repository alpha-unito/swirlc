## Next repair stage: CWL when and skipped/null results (planned)

The detailed active plan is **Next stage: nullable payloads, skipped outputs and
CWL when** at the top of `IMPLEMENTATION_PLAN.md`. Execute in this order:

1. Generic `optional[T]` / null types, assignability, schemas and transport.
2. Generic false-branch null publication with original output IDs and owner closure.
3. Preserve/lower CWL `when` into named conditions over bound per-invocation inputs.
4. Preserve skipped entries in scatter gathers; separately implement explicit
   pickValue selection or continue rejecting unsupported selection/merge forms.
5. Prove both targets and both hints modes, bounded distributed-local execution,
   exact nullable outputs, placement, isolation and failure propagation; rerun the
   eight pipelines, toy genome and supplied ordinary nested local examples.

Null payloads must never stand for missing data or EOF. False conditions must not
run commands or activate skipped subworkflow bodies. Runtime stays independent
of CWL/Node, and length exchange remains unchanged. Keep blanket `when` rejection
until supported forms pass the complete gates; reject unsupported forms clearly.
No implementation has been performed by this documentation update.

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

# Translator repair plan

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

Created 2026-10-09 after the independent review of `build/rebuild-manifest.json`.
All six repairs are implemented; #3/#5/#6 have local execution acceptance below.
The target contract and implementation handoff in `IMPLEMENTATION_PLAN.md` remain
normative; this plan adds the user's clarified parallel step-group semantics and
supersedes historical claims of translator completeness. Old artifact line numbers
below identify the reviewed snapshot; relocate actions after regeneration.

## Scope and gates

Updated 2026-10-14: the initial local compiler milestone is complete, including
both-target compilation and exact execution of plain pipeline depths 0–3 with
and without hints. Follow the active handoff and Part 2D.2 in
`IMPLEMENTATION_PLAN.md`; their scope supersedes the 2026-10-09 no-tests,
translator-only and later syntax/complex-workflow gates.

#3/#5/#6 are complete across translator emission, schemas, loaders and
generated Python command/output evaluation. Local translation, both-target
compilation, execution and focused regressions pass for all eight pipeline cases
with/without hints (see the acceptance record below). Preserve the existing recursive
region/dependency model, concrete SWIRL syntax, deployment lookup and worker
reservation policy. No intermediate approval is needed for routine work here.

Do not restore deleted fixtures, inspect binaries, commit, push, download or
interact with remotes, or perform destructive operations without explicit permission.
No 1000Genomes or actual SSH/SLURM execution is required in this stage.
The metadata design requires no new trace operations for already-bound inputs.
Do not add a scheduler, IR, interpreter or general framework. Keep the reviewed
source CWL unchanged: the reported faults belong to metadata preservation and
evaluation. Sections #1/#2/#4 and the 2026-10-09 evidence below are historical
completed-baseline records, not instructions to redo those repairs.

## Completed repairs (#1/#2/#4; historical instructions)

Finding numbers are retained from the independent review for traceability.

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

## Completed metadata update (#3/#5/#6)

The following descriptor contract is implemented; the acceptance record above
supersedes deferred/unresolved wording in the historical evidence below.

Implement now under the 2026-10-14 handoff. The accepted syntax is the baseline;
complex-workflow execution is not a prerequisite.
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

The plain pipeline examples do not require this feature, but the ordinary nested
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

Implement this repair, including explicit stdout preservation, together with
#3 and #6. Encode stdout destinations, loadContents, dynamic
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
a glob or trimming all string outputs automatically. Implement the descriptor
and evaluator together and establish execution evidence for supported forms.

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
Implement this with #3 and #5 under the current handoff;
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
The local compiler milestone already has plain-example execution evidence.
Next establish exact metadata-example outputs and preserve plain results with and
without hints, as specified by Part 2D.2. Translation alone cannot establish them.


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

Future runtime work may add heartbeat signals to check whether a node expected
to send data is still alive. Keep node liveness separate from workflow-data wait
duration: valid steps may run for days. Heartbeat policy and handling of suspected
node loss are deferred; a missed heartbeat alone does not prove node failure.

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
