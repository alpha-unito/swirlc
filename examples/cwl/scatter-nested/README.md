# Simple nested scatter

The outer scatter distributes three lists: `[a, b]`, `[]`, and `[c]`.
The inner scatter echoes each item. Gathering should preserve the nested shape
`[[file_a, file_b], [], [file_c]]`, including the empty middle batch.

There is one source, one outer worker and one inner worker. This is the CWL
counterpart of `examples/swirl/2-nested-scatter.swirl`. Inner dispatch stays at
its producer, the outer worker. Inner occurrences travel directly to the source,
where the declared output interface materializes each inner list at the outer
task ID. That interface sends one list occurrence into the outer gather and
owns its stream EOF after its publications join. The worker does not wait for
the final outer gather.

The same recursive lowering supports arbitrary finite scatter depth. Remote
owners admit only a bound enclosing path plus one fresh coordinate. Manual
three- and five-level configurations and inspected artifacts are under
`build/recursive-validation/`; the parser/compiler/runtime for this syntax
remain separate work.

```sh
mkdir -p build/scatter-nested
.venv/bin/python tmp_main.py translate --language cwl examples/cwl/scatter-nested/streamflow.yml --outdir build/scatter-nested
```

Translation generates a trace and metadata; it does not execute the workflow.
