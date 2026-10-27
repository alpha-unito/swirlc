# Missing CWL features: minimal fixture

One workflow, four steps, one record, and tiny inline files. No scatter, nested
workflows, external tools, downloads, or domain-specific processing.

| Step | Features exercised |
| --- | --- |
| `generate` | Record array with a nested File; generated script; IWD File staging; automatic `cwl.output.json`; secondary output |
| `optional` | `when` produces a nullable string when skipped |
| `inspect` | Correct multi-source `pickValue: all_non_null`; anonymous Directory listing; `.flat()`; IWD Directory and generated text; secondary input/staging; stdout File; `successCodes`; `runtime.exitCode` |
| `check` | Input `loadContents`; `.includes()`; `Number.isInteger()` |

The default job skips `optional`, then accepts exit code 1 from `inspect`.
Its report must contain `one:seed`, the companion content `meta`, and the single
message `generated`. Source companions are explicit File objects; automatic
discovery on record fields is not tested.

Run locally with Python 3 and Node.js:

```bash
mkdir -p build/missing-features
uv tool run --from cwltool cwltool --no-container \
  --outdir build/missing-features \
  examples/cwl/missing-features/main.cwl examples/cwl/missing-features/inputs.yml \
  > build/missing-features/result.json
python3 examples/cwl/missing-features/check.py build/missing-features/result.json
```

Use `cwltool` directly if installed. Toggle `enabled` to true: expect two
`generated` messages. Set `status` to 0: it succeeds; set it to 2: it must fail.
The checker above checks only the default job.

`streamflow.yml` is the SWIRL entry point. The unchanged workflow now translates,
compiles, and executes locally, including its guards, JavaScript expressions,
and automatic `cwl.output.json` outputs. Default, enabled, status-0, and rejected
status-2 jobs match cwltool; the default result passes `check.py`.

Implemented through metadata: typed records and nullable values, nested File and
Directory staging/transport, secondary files, InitialWorkDir entries, output JSON,
accepted exit codes, `runtime.exitCode`, input content loading, conditional null
outputs, and ordered source selection. Conditional steps use a native SWIRL
`+[condition_id]` choice after input preparation; the false branch publishes null
outputs with the same invocation identities. Guard expressions live under
`conditions` in the metadata. The expression runtime supplies the
`includes`, `Number.isInteger`, and `flat` methods used here.

Run the focused integration checks with:

```bash
.venv/bin/python -m pytest tests/test_cwl_expression_runtime.py -k missing_features -q
```

Selected bundled checks (`iwdr-entry`, `iwdr-empty`, `record_outputeval`, and
`conditional_step_no_inputs`) also match cwltool. Their original tool/workflow
documents were used with local wrappers where needed.

This milestone does not establish general CWL conformance. Writable staging,
general unions, multiple-source subworkflow/scatter bindings, and broader modern
JavaScript remain unsupported. No Fedarcs or Montage execution is required.
