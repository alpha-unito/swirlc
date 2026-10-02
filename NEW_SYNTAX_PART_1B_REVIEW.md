# Working simple-scatter translator review

Implemented 2026-10-02. Satisfaction applies to the implementation and generated
artifacts. No unit tests, parser/compiler execution, or generated workers have
run before this review gate.

Accepted 2026-10-02. The subsequent focused simple-scatter checks pass 9/9.
The nested-isolation boundary described below is historical: the first nested
batch is now available for review in [Part 1C](NEW_SYNTAX_PART_1C_REVIEW.md).

## Try it

```sh
rtk mkdir -p build/new-syntax/try
rtk .venv/bin/python tmp_main.py translate --language cwl \
  examples/cwl/scatter-new-syntax/streamflow-many.yml \
  --outdir build/new-syntax/try
```

Inspect `workflow.swirl` and `metadata.yml`. Replace `many` with `empty`, `one`,
or `duplicate` for the other review cases. The existing
`examples/cwl/scatter/streamflow.yml` also translates using the same CLI.

## Emitted behavior

Dispatch constructs `U(p_task_0, tasks_0)` from only the scattered inputs. Each
selected worker has its own parallel distributor, with a payload-first move,
guarded `end()`, and EOF after its replication joins:

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

Workers bind the task payload/key, open scattered fields, execute using those
bindings and concrete invariants, and send each keyed output. Their EOF receive
alternative calls `end()`; all output EOF sends follow the worker replication
join. Each controller source/output receiver also closes via `recv(eof).end()`.
Gather reads one U snapshot per output after all receivers have joined.

The scalar prefix and complete labels list are sent/received once per worker
before admission. They remain ordinary concrete names and are not moved or
opened per task. An extra manual shared-source artifact confirms that an array
can be both scattered through one input and passed whole through another without
the scalar field replacing that invariant binding.

The helper types remain `scatter_pairer`, `scatter_open`, and `scatter_gather`.
Metadata now separates dynamic `binding`/`collection` descriptors from concrete
`dependencies`, records dimension order, operation/key identity, selected routes,
collection-to-output mappings, and gather shape/order. Pairer invocation state
must retain cardinalities for empty/nested Cartesian shapes in Phase 2.
No variables or EOF are registered as static file/string dependencies.

## Artifacts and manual walkthrough

Generated under `build/new-syntax/part-1b/`; each scatter case has a translation
log, trace, and metadata. All CLI translations returned status 0 and their
outputs were inspected. These traces describe intended behavior, not completed
distributed execution.

| Directory | Review coverage |
| --- | --- |
| `basic` | Trace and metadata byte-identical to the Part 1A ordinary baseline |
| `scatter` | Existing file-command fixture; Cartesian dimensions; coordinator plus two workers; list feeds ordinary analyze command |
| `empty` | No task activations; two empty output collections; scalar/list invariants still established |
| `one` | One atomic move wins; other distributor closes empty; both workers eventually forward EOF |
| `duplicate` | Two equal payload occurrences remain distinct coordinate keys; gather must retain both |
| `many` | Five tasks on two workers; parallel admission; two separately gathered outputs |
| `shared-source` | Manual in-memory variant of `one`: labels uses the same source list as item, but remains whole/reusable |

For empty input, invariant receives complete first. Dispatch publishes an empty
finite collection; both distributors close and send task EOF. Each worker closes
its empty replication and sends EOF for both outputs. Four independent result
receivers close, then gather reads two empty collections and produces two lists.

For one item, exactly one move claims the occurrence. Exhaustion may close the
distributors while that delivery is pending, but their joins delay task EOF
until recv commits. Worker EOF may arrive while the selected task executes; the
worker join waits for both result sends to be acknowledged before result EOF.
Both outputs reach the gather collections before their source-specific EOF.

For five items, task continuations can overlap on either worker. Result arrival
order does not define output order: metadata specifies coordinate ordering.
Duplicate payload values likewise cannot collapse coordinate-distinct results.
The controller runs distribution and collection in parallel, so synchronous
result sends have active receivers. Invariant setup only waits on workers'
initial receives, which do not wait for task dispatch; this introduces no
circular wait in these cases.

## Current boundary

- Nested scatter explicitly fails with an invocation-isolation diagnostic.
  The earlier qualified-port proposal is not implemented or treated as accepted.
  Root channels and result ports are distinct per operation; repeated parent
  invocation scope requires Part 1C work before nested traces can be emitted.
- Multiple-source scatter bindings and outputs requiring ambiguous projection
  fail explicitly. General CWL source merging/default interpretation and
  decentralized producer routes remain for their designated review batch.
- Existing worker target selection is retained for this supported slice, including
  a coordinator listed in its worker pool. Ordinary placement is unchanged.
- The old grammar/runtime/schema cannot consume the new scatter syntax and
  dynamic descriptors. Metadata retains its existing version field; schema and
  compatibility decisions belong to Phase 2. Translation does not claim metadata
  validation or execution under the old compiler.
- All three scatter methods are represented by the emitter and shape metadata,
  but the review coverage here exercises dotproduct and flat Cartesian output.
  Complete method/nesting/decentralized acceptance remains Part 1C.

Review the implementation and artifacts before adding/running the focused unit
tests required by the plan. Existing compiler-dependent scatter tests have not
been altered to hide their incompatibility.
