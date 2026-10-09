# CWL examples

| Workflow | Demonstrates |
| --- | --- |
| `basic` | Two ordinary command steps |
| `nested` | An ordinary subworkflow |
| `expressions` | An expression with scalar and list outputs |
| `lists` | Producing and passing a whole list |
| `lists-input` | A whole-list workflow input |
| `scatter` | One dotproduct scatter over two short lists |
| `scatter-nested` | Two scatter levels, including an empty inner list |

Each directory has a `streamflow.yml` entry point. Basic workflows also retain
existing deployment variants. The larger scatter and CWL 1000Genomes examples
were removed; the distributed `examples/1000genome` workflow remains separate.

To generate traces, create an output directory and run:

```sh
mkdir -p build/scatter
.venv/bin/python tmp_main.py translate --language cwl examples/cwl/scatter/streamflow.yml --outdir build/scatter
```

The two scatter examples correspond to the handwritten begin/scope references
in `examples/swirl`. Their traces now use explicit begin/scoped-EOF lifecycles
and receiving owners for two scatter levels. Deeper nested admission remains
unfinished; translation success is not compiler or runtime validation.
