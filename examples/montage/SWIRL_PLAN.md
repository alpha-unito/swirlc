# Plan: run Montage with SWIRL

## Target and current state

Translate, compile, and execute `main_montage.cwl` using the prepared
`data-small/config_montage.json`: 0.05 degrees, three 2MASS bands, five images
per band, and 100 background iterations. Keep dataset generation under cwltool
for now; translating `main_get_dataset.cwl` is outside this first milestone.

Work directly in `/mnt/shared/tfogliobonda/swirlc` on Fedarcs. Use
`/mnt/shared/tfogliobonda/swirlc/tmp` for scratch. Do not commit or push without
approval. Preserve downloaded data and successful results; stop failed-run
processes before cleaning their scratch files.

Current translation fails on `when` at `/band/wdiff/diff/mDiffFit`. Removing
that check alone will not make Montage runnable. Nested workflows, scatter,
flat crossproduct, basic expressions, command bindings, and output
`loadContents`/`outputEval` already exist and should be reused.

## 1. Establish a reference run and correct the CWL wiring

Before changing SWIRL, run the small mosaic with cwltool and the project-local
Montage tools/shared venv. Validate outputs and retain logs as the reference.
Fix example defects exposed by that run, including:

- In `band.cwl`, the embedded `wdiff` passes `in_1_fits` into both scatter inputs.
  Connect its second input to `in_2_fits`.
- Review nullable wiring in `diff.cwl`, including conditional `is_valid`, and
  the declared output types in `et/get_rgb.cwl` if missing colors are allowed.
  Do not change types merely to silence warnings; match actual skipped values.
- Resolve the warning about `pickValue: all_non_null` on a single array source.
  Follow CWL source-selection semantics. If the intent is to filter null items
  within a scattered result array, express that filtering explicitly; do not
  implement `pickValue` as arbitrary flattening or list filtering.
- Check the real mDiffFit exit status and non-overlap message. Its wrapper must
  distinguish an expected empty overlap from missing inputs or other failures.

Done when cwltool completes this example and produces three grayscale mosaics
and the RGB mosaic. Record any remaining warnings and their explanation.

## 2. Preserve record values and nested file references

Main entry points: `swirlc/translator/cwl/cwl_translator.py`, core data/transport
handling, metadata schemas, and generated runtime helpers in
`swirlc/compiler/default/compiler.py` / `runtime.py`.

- Add a structured record descriptor instead of falling back to `file`.
- Preserve record objects, arrays of records, nested arrays, and field types
  through input loading, expression bindings, execution, and transport.
- Recursively stage/transfer File and Directory fields inside records. Montage's
  band records contain tables and image arrays; serializing them as JSON alone
  does not make those files available on another worker.
- Keep record fields accessible as `inputs.band.bid`, `inputs.band.images_fits`,
  etc. Preserve existing scalar/list/file behavior.

Proof: a band record survives translation and local/remote execution, including
its nested files; invalid field values are rejected at the appropriate boundary.

## 3. Add nullable values and conditional execution

- Retain nullability in type descriptors instead of discarding the null member.
- Evaluate each step's `when` after its scattered inputs and `valueFrom` values
  are bound, using those named inputs.
- A false condition runs no command and produces null for every declared output.
- Preserve iteration identity, output positions, and completion/EOF signals for
  skipped executions. A skipped branch must not strand a gather or peer transfer.
- Implement any `pickValue` behavior still required after step 1 using CWL link
  semantics. Keep it separate from scatter gathering and array flattening.

Proof: true/false conditions inside nested crossproducts, mixed and all-skipped
results, null-aware selection, and clean completion without deadlocks.

## 4. Materialize InitialWorkDir entries and Directory listings

Lower CWL staging requirements to generic invocation staging descriptors; keep
CWL-specific parsing in the translator and filesystem execution in the runtime.
Support the forms used here:

- Inline text entries with `entryname`, such as get_diff's generated `generate.py`.
- File entries and arrays of files placed into the command's working directory.
- Expressions producing anonymous Directory objects with `basename` and
  `listing`, used by `mConcatFit` and `mImgtbl`.

Evaluate entries with the invocation's bound inputs. Preserve names, validate
entry paths against traversal/escape, and detect conflicting entries. Recursively
materialize Directory listings and their file companions. Do not mutate source
inputs while staging them.

Proof: a generated script executes, an anonymous Directory contains the expected
files, and the same invocation works with inputs received from another location.

## 5. Make get_diff outputs explicit; avoid a general JSON-output protocol

`get_diff.cwl` writes `cwl.output.json`, whose `diff_name` controls `mDiffFit`.
Use the already supported output processor instead of adding special handling
of that filename to the runtime:

```yaml
diff_name:
  type: string
  outputBinding:
    glob: cwl.output.json
    loadContents: true
    outputEval: $(JSON.parse(self[0].contents).diff_name)
```

This extraction was tested successfully in the existing runtime. Exercise both
an actual difference filename and an empty string with the real generated tool.

`retrieve_urls.cwl` uses the same JSON convention, but is only in the dataset
workflow. It does not block running the prepared mosaic. Defer its adaptation
and general automatic `cwl.output.json` handling.

## 6. Preserve secondary area images

`mProject`, `mBackground`, and `mAdd` declare accompanying `_area.fits` files.
These coverage images must travel and stage beside their primary FITS files.

- Lower the secondary-file expressions actually used by these tools.
- Retain companions in typed File values and output collection.
- Recursively transfer and stage primary/secondary groups with compatible names,
  including inside arrays, records, and Directory listings.
- Check required companions exist; do not silently ignore a missing area file.

Proof: move a projected FITS file between isolated locations and run the next
Montage tool with its area image present. Cover the final corrected-image array
staged for `mAdd`. Do not substitute no-area/equal-weight processing.

## 7. Support the mDiffFit status-checking contract

- Lower `successCodes: [0, 1]` to generic accepted exit statuses. Keep `[0]` as
  the default for existing tools; other nonzero statuses must still fail.
- Expose the completed process's exit status to output expressions so
  `$(runtime.exitCode)` produces an integer.
- Support input `loadContents: true` for `check_mDiffFit_out`'s log File, using
  the same bounded text-loading policy as existing output content loading.
- Preserve stdout as a File output (`log_out`) as well as redirecting it. Verify
  the CWL `type: stdout` shorthand is normalized correctly.
- Ensure code 1 with the recognised non-overlap message is handled as intended,
  while code 1 for a different error is propagated as a failure.

Proof: status 0, recognised status-1 non-overlap, unexpected status-1 failure,
other nonzero status, and a skipped mDiffFit invocation.

## 8. Use JavaScript supported by the existing engine

Js2Py currently fails on String.includes and Number.isInteger. For this milestone,
rewrite the two Montage expressions using tested ES5-compatible equivalents:

```javascript
text.indexOf(message) !== -1
```

```javascript
typeof x === "number" && isFinite(x) && Math.floor(x) === x
```

Test null, zero, a nonzero integer, and a non-integer for the conditional guard.
No engine replacement is needed. Array.flat occurs in dataset generation, which
continues to use cwltool for this milestone.

## 9. Configure the actual execution environment

- Use the shared venv's absolute Python path for Python CLTs such as get_diff.
  The venv contains Astropy; activating it on the coordinator does not configure
  worker SSH sessions automatically.
- Make `.tools/montage/usr/bin` and its required library directory available to
  every executing location. Include grid tools such as mDiffFit/mConcatFit.
- Treat Docker hints separately from actual provisioning: do not assume SWIRL
  launches the hinted Python/Astropy containers.
- First use the existing local `streamflow.yml` to isolate language/runtime
  issues. Then add explicit SSH bindings and verify the same small workflow
  across workers, using user-owned work directories and conflict-free ports.

## 10. Acceptance gates

1. Focused regression tests pass for each new contract above. Extend existing
   tests in `tests/test_cwl_tool_metadata.py`, `test_tool_metadata_runtime.py`,
   `test_metadata_contract.py`, and scoped/trace tests where relevant.
2. Existing toy-genome and 1000genome paths retain their behavior. Do not broaden
   implementation scope to unrelated CWL features or dependency upgrades.
3. Montage translates into schema-valid metadata and compiles into executable
   traces without removing its guards or weakening error handling.
4. The small workflow completes locally, then across SSH locations, with no
   missing area images, unmatched transfers, stalled gathers, or orphan workers.
5. Compare three grayscale outputs and the RGB output to the cwltool reference:
   expected dimensions/WCS, finite pixel coverage, and numerical values within
   a documented tolerance. Archive/image byte identity is not required.
6. Verify outputs are copied out of scratch before successful-run cleanup. On
   failure, preserve logs, stop the failed run's processes, and clear only its
   generated scratch data.

Stop when the prepared small Montage run meets these gates. Full-dataset tuning,
a general cwl.output.json implementation, a new JavaScript engine, and compiling
the dataset downloader are deferred.
