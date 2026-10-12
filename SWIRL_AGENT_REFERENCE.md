# SWIRL project reference

## Compiler execution evidence — 2026-10-12

The accepted concrete contract now uses one ANTLR frontend, structured terms and
strict v1.1 metadata for both targets. Trace output includes envelopes, scoped
guards, fresh/exact bindings, owners, closure and completion joins. Generated
Python uses scoped occurrence storage, atomic matching, synchronous TCP commits,
concurrent replication, descendant joins, independent cardinality publication,
full-key routing and validated shape-preserving gathers. Existing deployment,
launcher, framing, command and expression infrastructure is reused.

All four `examples/cwl/pipeline/depth-{0,1,2,3}/plain` configurations translated,
compiled to both targets, and executed across their configured distinct local
locations, with and without advisory hints. Final File contents matched each
`expected.json` exactly, retaining duplicates, ordering, empty branches and nested
arrays. Depth 0 preserved stage-to-finish file transport. Observed command task
counts were 2, 3, 3 and 4 respectively, each with an isolated work directory.
Logs, traces, generated bundles and per-depth `acceptance.json` reports are under
`build/compiler-contract`. Reproduce with
`rtk .venv/bin/python tests/test_pipeline_contract.py`.

Focused regressions cover parsing/binding rejection, metadata ownership, trace
joins, atomic scoped transport, concurrent reverse completion, dynamic unequal
cardinalities, consistent routing, empty Cartesian shape, invalid/duplicate/missing
gather keys and bounded blocked/failure joins. This evidence supersedes older
claims that the concrete compiler contract is entirely unimplemented; older
execution claims remain historical and must not be extrapolated.

Deferred metadata repairs #3, #5 and #6 remain excluded. SSH/SLURM execution,
1000Genomes and broader CWL conformance are untested. Directory transport still
fails explicitly. Legacy indexed/pair-open scatter is rejected rather than
reinterpreted as independent dispatch. Runtime blocked-action deadlines default
to 60 seconds and can be set with `SWIRLC_RUNTIME_TIMEOUT`.

## Instructions for future agents

Treat this as a dated snapshot, not an authority over the code or newer research. **If a change or discovery contradicts this document, ask the user to update it with the corrected information.** Give the user the exact section, the conflicting evidence, and proposed replacement text. Do not silently rely on a known contradiction. Check the current code and tests before making implementation decisions.

Snapshot: 2026-09-24. The worktree had uncommitted CWL translator and test changes when this was written. `uv run pytest -q` passed: **39 passed**. The papers describe the research model; the repository defines current executable behavior. Planning documents describe intended work, not completed features.

## Sources and status

- **Published foundation:** Colonnelli et al., *Introducing SWIRL: An Intermediate Representation Language for Scientific Workflows*, arXiv:2407.01838v1, especially §§2–5. The supplied PDF is `2407.01838v1.pdf`; the repository cites its FM 2024 / 2025 proceedings version in [README.md](README.md).
- **Unfinished extension draft:** Medić, Tommaso, and Aldinucci, *SWIRL extension????*, supplied as `FGCS___SWIRL_extension.pdf` (4 pages). It has placeholder abstract, annotations, open questions, and incomplete rules. Read it as a research proposal, not an implemented or settled specification.
- **Implementation:** [grammar/SWIRL.g4](grammar/SWIRL.g4), [swirlc/main.py](swirlc/main.py), [swirlc/core/translator.py](swirlc/core/translator.py), [swirlc/translator/cwl/cwl_translator.py](swirlc/translator/cwl/cwl_translator.py), [swirlc/core/compiler.py](swirlc/core/compiler.py), and [swirlc/compiler/default/compiler.py](swirlc/compiler/default/compiler.py).
- **Current plan and status:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) consolidates the superseded implementation plans and distinguishes implemented behavior from pending acceptance and runtime work. Inspect the code before treating a planned item as done.

## What SWIRL represents

SWIRL is a low-level intermediate representation for a *distributed execution plan* of a scientific workflow. It is intended as a compiler target rather than a human authoring language. The toolchain is: source workflow and deployment description → translator → `workflow.swirl` plus `metadata.yml` → compiler → per-location execution bundle. The compiler needs metadata for details outside the formal process term: commands, data types and values, outputs, and deployment settings.

The 2024 paper starts with a directed bipartite workflow graph `W = (S, P, D)`: steps `S`, ports `P`, and dependency edges `D` between them. A workflow instance attaches data elements to ports. A distributed workflow adds locations `L` and a step-to-location mapping `M`; its work queue `Q(l)` contains the steps mapped to location `l`. A SWIRL *workflow system* is a parallel composition of location configurations `⟨l, D, e⟩`, each with local data `D` and an execution trace `e`.

This is a **process algebra** with actions and operators, not just a DAG serialization. In the 2024 formal core, actions are `exec` (execute a step with an input/output dataflow and location mapping), `send` (copy data over a port), and `recv` (receive it). Traces use sequential composition `.` and parallel composition `|`; `0` is the empty trace. Parallel location configurations compose into one system. The reduction rules require inputs before `exec`, synchronize an `exec` mapped to multiple locations, copy data on remote `send`/`recv`, and allow local/parallel/sequential progress. Structural congruence gives identities and commutativity for parallel composition. The paper derives a building block for each `(step, location)` pair: receive inputs, execute, send outputs. Its optimization removes redundant local communication and duplicate transfers, with a weak barbed bisimulation argument for preserving observable step executions. That formal result concerns the **2024 calculus**, not every later extension or current runtime path.

The extension draft explores scatter and repeated work. It adds choice `+`, replication `!`, `move`, `eof`, and task IDs to the calculus. Its example considers scatter dispatch, replicated workers, and gather. The draft explicitly leaves EOF, ID routing, and nested scatter details open; do not cite its reduction rules as settled guarantees. The current grammar independently accepts `+`, unparameterized `!trace`, `move`, `eof`, tuple/keyed data, and destination location sets. It does **not** accept the draft's parameterized replication syntax.

## Translator and compiler in this repository

The CLI in [swirlc/parser.py](swirlc/parser.py) exposes `translate --language dax|cwl` and `compile --target default|trace`. Translation writes `workflow.swirl` and `metadata.yml`; compilation reads both. `translate` requires an existing output directory. The `dax` translator reads a Pegasus directory containing `workflow.yml`, `replica.yml`, `sites.yml`, and `transformations.yml`, builds the common workflow entities, and uses `AbstractTranslator.render`. The CWL translator takes a **StreamFlow YAML configuration**, loads its referenced CWL workflow and input job, and produces SWIRL plus v1.1 metadata. There is no registered Galaxy translator or separate SWIRL optimizer in this checkout, despite their place in the 2024 paper's toolchain diagram.

The CWL translator currently builds a recursive `WorkflowRegion` / `Invocation` tree, with scatter as a `ScatterSpec` on an invocation. It resolves CWL sources to full paths, orders invocations by dependencies, and chooses StreamFlow targets by longest matching path prefix. `LoweringContext` tracks controller location, task identity, available data, per-location trace fragments, steps, dependencies, and scatter regions. `lower_region` / `lower_invocation` recurse through ordinary subworkflows; `lower_scatter` emits pair/open/gather helper steps, dispatch `move`, replicated worker traces, EOF branches, and gather receives. Metadata records helper `type` values (`scatter_pairer`, `scatter_open`, `scatter_gather`) and numbered `scatterRegions`; comments of the form `// @compiler begin|end scatter.<phase> <number>` mark dispatch, worker, and gather spans. The comments are optional hints, not syntax needed for correctness.

The grammar is [grammar/SWIRL.g4](grammar/SWIRL.g4); generated ANTLR Python files live in `swirlc/antlr`. [swirlc/core/parsing.py](swirlc/core/parsing.py) rejects lexer/parser errors before compilation. The compiler validates metadata v1.0 or v1.1, scans optional hints, visits the parse tree, constructs workflow entities from metadata, and calls a target compiler. `--target trace` writes readable per-location `.md` traces and is useful for checking structural lowering. The default target generates per-location Python programs and `run.sh`, with threads and TCP communication. It supports local, SSH, Docker, and Slurm deployment settings; generated JavaScript expression support uses a Python JavaScript engine. See [CWL.md](CWL.md) for current CLI examples and launcher behavior. The default target can also bundle pure-Python dependencies.

## Current CWL scatter state and limits

- **Translated and structurally tested:** simple scatter and nested scatter fixtures, including `tests/fixtures/cwl/scatter-nested-zip`; distinct nested worker pools and full CWL paths are asserted in [tests/test_translator.py](tests/test_translator.py). The `scatter-nested-zip` output compiles with `--target trace`; removing hints yields identical trace output in [tests/test_compiler.py](tests/test_compiler.py).
- **Scatter methods:** the translator recognizes `dotproduct`, `flat_crossproduct`, and `nested_crossproduct`. The pair helper makes task combinations and records coordinates; tests cover duplicate items, empty input, and nested coordinates. Unequal `dotproduct` lengths are rejected when statically known or by the generated pair helper. These checks do not prove complete gather shape or distributed execution semantics.
- **Runtime remains incomplete for nested/keyed scatter:** generated runtime state still uses shared `ports` and per-port readiness events. The gather helper sorts results using IDs guessed from values, file names, or content; it does not reconstruct nested CWL output shape from explicit task coordinates. Trace-level `name[task_id]` syntax is currently reduced to static metadata names. The existing default-target scatter test checks that helper calls are generated; it does not run the nested workflow end to end. The planned keyed message envelopes, per-region queues, scoped completion, deterministic gather, and hint-driven optimization are not implemented as specified in the plans.
- **Other concrete limits:** directory send/receive raises `NotImplementedError` in the default runtime. Do not infer full CWL or StreamFlow feature coverage from supported fixtures. The original paper's optimization proof does not validate the new scatter constructs automatically.

For translator work, inspect [swirlc/translator/cwl/cwl_translator.py](swirlc/translator/cwl/cwl_translator.py), then the focused tests. For compiler/runtime work, inspect [swirlc/core/compiler.py](swirlc/core/compiler.py), [swirlc/compiler/standard/compiler.py](swirlc/compiler/standard/compiler.py), [swirlc/compiler/default/compiler.py](swirlc/compiler/default/compiler.py), and [swirlc/compiler/hints.py](swirlc/compiler/hints.py). Run `uv run pytest -q` after changes. Treat the plan files as design context, and update this snapshot when code or research resolves a documented uncertainty.
