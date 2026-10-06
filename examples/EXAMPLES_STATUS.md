# Example status

Checked on 2026-10-05 against the independent-stream CWL translator and current
legacy compiler. Generated files are under `build/`; source workflows were not
executed and input data were not downloaded.

## Regenerated CWL examples

All **27** `streamflow*.yml` configurations under `examples/cwl`, plus the
distributed `examples/1000genome` configuration included in that count,
translate successfully. Current traces, metadata, translation logs and
compilation logs are in `build/new-syntax/independent/<example>-<configuration>/`.
The distributed 1000Genomes directory is `1000genome-distributed`.
`results.json` indexes the exact source configuration and output directory.

| Coverage | Translation | Legacy compilation |
| --- | --- | --- |
| basic, nested, expressions (including deployment variants), lists, lists-input: 9 configurations | Pass | Pass |
| scatter, nested scatter, scatter methods, independent producers, both 1000Genomes configurations: 18 configurations | Pass | Rejected by legacy metadata schema |

The 13 Python files produced by the nine successful compilations pass Python
syntax checks. New scatter metadata uses `binding`, `collection`, `keySpace`,
and invocation scope descriptors that the old schema rejects. The old parser
also lacks `U`, `?` variables, guarded exhaustion, `end()`, and qualified ports.
Compilation failure here does not mean the CWL sources are outdated: completing
the new compiler/runtime is still Phase 2.

## Handwritten SWIRL examples

| Example | Status |
| --- | --- |
| `swirl/basic`, `broadcast`, `gather`, `example1` | Compile with the current legacy compiler; outputs and logs are in `build/example-audit/<name>/`. Execution prerequisites still apply. |
| `swirl/scatter/source.swirl` and its `config.yml` | Outdated bundled pair/open model, indexed task IDs and EOF inside replicated choices. Source also fails the current parser on its multi-member tuple. |
| `swirl/scatter2.swirl`, `scatter3.swirl` | Historical split/take/put model with indexed IDs and old termination; parse with the legacy parser but are not current-model references. No accompanying metadata was available for compilation. |
| `swirl/nested-scatter-example.swirl` | Historical bundled pair/open nesting without the current invocation-scoped stream model. Parses as legacy syntax; no accompanying metadata for compilation. |
| `swirl/scatter4.swirl` | Current conceptual reference for independent dispatch/gather and joined EOF. Requires the new parser/runtime; not outdated. No accompanying metadata for compilation. |
| `swirl/test.txt` | Mixed design scratch notes, not an executable example. |

`build/example-audit/swirl-results.json` records parser and compilation outcomes.
Parsing alone does not establish executable semantics.

## Outdated documentation

- `cwl/scatter/README.md` still describes ScatterPairer/Open. Current translation
  emits separate producer-local dispatch streams and independent output gathers.
- `swirl/scatter/README.md` describes an unzip/wc/cat pipeline, whereas its source
  and metadata describe paired inputs with ComputeItem/AnalyzeReport.
- `swirl/basic/doc.md` uses nonexistent `examples/basic` paths; the files are
  under `examples/swirl/basic`.

The CWL sources themselves remain usable translation fixtures. Historical SWIRL
sources and their metadata have been retained for comparison rather than
silently rewritten into a different execution model.
