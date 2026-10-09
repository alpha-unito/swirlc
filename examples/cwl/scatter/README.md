# Simple scatter

Two lists are paired by position: `(a, 1)` and `(b, 2)`. One worker echoes
both inputs into `result.txt`; gathering preserves the input order. Each input
has its own dispatch stream. The source also collects the results.

This is the CWL counterpart of `examples/swirl/1-nested-scatter.swirl`, with both
input producers and the collector sharing the source location. The handwritten
reference describes the begin/scope/EOF syntax now emitted by the translator.
The generated trace uses two independent input streams, composed task IDs,
scoped collections and result EOF after the worker join.

```sh
mkdir -p build/scatter
.venv/bin/python tmp_main.py translate --language cwl examples/cwl/scatter/streamflow.yml --outdir build/scatter
```

Translation generates a trace and metadata; it does not execute the workflow.
