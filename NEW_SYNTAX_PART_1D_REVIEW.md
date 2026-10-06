# Part 1D: translator acceptance run

Historical run. The 2026-10-05 correction replaces bundled pair/open dispatch
and fixes ordinary producer placement. See
[independent streams review](NEW_SYNTAX_INDEPENDENT_STREAMS_REVIEW.md) for the
current implementation and regenerated artifacts.

Run on 2026-10-02. Fixture generation and inspection are complete for the current
implementation; the complete-translator acceptance gate remains open.

## Results

All **26 configurations** produced nonempty `workflow.swirl` and `metadata.yml`
with clean translation logs. Artifacts are under `build/new-syntax/part-1d/`,
each in its own directory; `results.json` records the configuration and result.
Shell exit status was checked alongside artifacts and logs because `tmp_main.py`
does not propagate the translator return value.

Coverage includes basic/nested/expressions deployment variants, lists and
lists-input, scatter and scatter-split, all three existing nested-scatter
fixtures, both 1000Genomes variants, and the ten added simple/nesting/method
configurations. Repeating every translation produced identical traces and
equivalent YAML metadata. Parentheses balance, concrete dependency names, and
one location declaration per scatter deployment were checked. These structural
checks do not establish parseability or runtime execution.

The nine ordinary configurations have byte-identical traces and equivalent
metadata compared with the current HEAD translator. The nine previously
accepted simple-scatter tests pass; lint passes. Compiler-dependent checks and
new batch unit tests remain deferred under the plan's acceptance gates.

## Trace review

Pair/open descriptors retain scatter declaration order and payload-first keyed
bindings. Gather descriptors retain coordinate ordering, snapshot reads and
dispatch shape state, including empty Cartesian dimensions. Nested task and
result channels carry ancestor qualifiers; inner gather produces a list with
the parent key before returning it outward. Invariants remain reusable outside
consuming task moves. Scalar/list/file types, expression sources, command
arguments and output processors remain present in metadata.

Distribution owners join before sending task EOF; worker owners join before
result EOF; collection receivers join before gather snapshots. Dispatch and
collection run in parallel, allowing result sends to receive acknowledgments
while distribution continues. Nested publication precedes invariant sends and
opens workers even for empty input. Root receivers open at workflow start.
An independent read-only review found no circular wait in the distributed
1000Genomes trace under these declared activation semantics. The future runtime
must implement those semantics; no distributed execution was performed.

Use `1000genome-original` as the distributed acceptance artifact: its config
selects two chromosome workers and three inner workers, plus the coordinator.
The `examples/cwl/1000genome` variant is a useful single-location smoke case.
Both were generated without downloading or executing workflow data/scripts.

## Outstanding acceptance limits

- Part 1C distributed producer/input matching and general multiple-source
  handling remain unfinished. Existing centralized pair/open lowering is
  preserved; this run does not establish decentralized-input coverage.
- Ordinary deployment bindings remain an existing limitation: `lists` and
  `nested-split` emit their tools on l0, despite bindings to other deployments.
  In particular, `lists` does not exercise its intended inter-location list
  transfer. This matches HEAD, but prevents claiming complete placement
  acceptance. Changing placement needs the concrete proposal/consent required
  by Part 1C.
- Qualified channels and finite-publication activation are translator contracts
  awaiting a new compiler/runtime. Successful generation is not execution proof.

Phase 1D's review run is done. Complete translator acceptance and Phase 2 remain
pending resolution of these limits and explicit user acceptance.
