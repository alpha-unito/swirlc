# Implement the missing CWL features

## Goal and scope

Translate, compile, and run `main.cwl` locally without rewriting its expressions,
replacing `cwl.output.json` with explicit bindings, or removing its guards.
Match the existing cwltool reference: `ok: true`, code 1, and the report checked
by `check.py`. Also exercise `enabled: true`, status 0, and rejected status 2.

This plan supersedes the workaround choices in `examples/montage/SWIRL_PLAN.md`
for this fixture. Leave Fedarcs, Montage execution, downloads, and unrelated CWL
features out of scope. Completing this fixture does not establish full Montage
or CWL conformance.

## Implementation boundaries

- CWL parsing and lowering: `swirlc/translator/cwl/cwl_translator.py`.
- Metadata propagation and validation: `swirlc/core/translator.py`,
  `swirlc/core/compiler.py`, `swirlc/config/validator.py`, and the applicable
  schema in `swirlc/config/schemas/`.
- Generated execution, expression conversion, and transport helpers:
  `swirlc/compiler/default/compiler.py`.
- Scoped execution, identities, and completion:
  `swirlc/compiler/default/runtime.py`.

Keep CWL field names and interpretation in the translator. Lower them into
explicit execution descriptors rather than teaching command execution to parse
CWL documents. Reuse the existing expression and output-processing paths.
Keep cohesive value/staging helpers together; avoid copying recursive file
handling into each feature. Extend the existing metadata version unless its
compatibility rules require a new one; old descriptors must retain their behavior.

Do not change SWIRL syntax: no grammar changes, new language constructs, or
changes to existing syntax semantics. Implement these features through the
existing SWIRL constructs, metadata, translator, compiler, and runtime.

## Test cadence

Defer writing or updating Python test code until major milestones or the end.
Do not interrupt individual implementation edits to add unit tests or test
harnesses. This does not defer practical verification: throughout implementation,
use the actual translator and compiler on the fixture to check progress, inspect
their outputs, and execute the generated workflow as soon as enough features work.
Use failures to guide the next change; partial progress need not pass the full
fixture. Reuse existing checks such as `check.py` without adding test code.

The `Proof` paragraphs below describe acceptance criteria. Check what is practical
with the real pipeline during implementation; batch Python test-code work and
focused regression runs at these milestones:

1. After stages 1–4: structured values, JavaScript, staging, and output collection.
2. After stages 5–6: process status, content loading, conditions, and selection.
3. At stage 7: end-to-end fixture execution and relevant regression tests.

Python tests remain part of completion; deferring their implementation does not
remove the final checks or replace ongoing translator/compiler verification.

## 1. Preserve typed structured values

Current `_cwl_type_to_swirl` drops null union members and falls back to `file`
for records. `_coerce_cwl_value` stringifies objects or reduces Files to paths.
Fix that contract before adding features that depend on these values.

- Retain record fields, array item schemas, and nullability in metadata. Resolve
  the imported `Item` schema; unsupported unions must produce an explicit error.
- Carry records as mappings, arrays as arrays, null as null, and File/Directory
  objects with their class, identity, basename, contents/listing, and companions.
- Preserve these values through literals/defaults, expression conversion,
  output coercion, scoped storage, and send/receive. Preserve old path-valued
  file inputs through a compatibility boundary rather than breaking existing jobs.
- Introduce one recursive traversal for nested File/Directory values. Use it
  for localization and transport, preserving record/array shape and updating
  execution paths. JSON serialization alone does not transfer nested files.
- Materialize the fixture's File literals (`contents` without a path) in owned
  scratch space. Do not convert missing values to strings or null to an empty list.

Proof: round-trip a record array with literal Files and secondaries; preserve
null, false, zero, and empty strings. Reject invalid field types. Exercise a
transfer between isolated local locations with no shared input paths.

## 2. Supply the JavaScript methods used by the fixture

Reuse `_run_javascript_expression` and its existing dependency packaging. Add
small standards-compatible shims for String `includes`, `Number.isInteger`,
and Array `flat` in the common expression context before evaluating user code.
Do not rewrite the fixture or claim general modern-JavaScript support.

Proof: expression-runtime tests cover the fixture's calls plus false positives:
noninteger numbers, strings/null passed to `Number.isInteger`, absent substrings,
and `flat`'s default one-level depth. Verify expression results preserve structured
objects and primitive types. If Js2Py cannot implement these methods correctly,
resolve that limitation before switching engines; an engine replacement is a
separate dependency/deployment decision, not an incidental change.

## 3. Localize files and materialize InitialWorkDir entries

- Lower inherited/effective `InitialWorkDirRequirement` into per-invocation
  staging descriptors, honoring tool overrides.
- Handle generated text with `entryname`, File entries, arrays of File entries,
  and anonymous Directory objects containing `listing`.
- Evaluate entries with bound invocation inputs. Localize referenced inputs,
  establish the final layout, then expose the correct paths to command argument
  expressions. Keep object-valued expressions distinct from interpolated text.
- Recursively stage Directory listings and primary/secondary groups. Generate
  `generate.py`, `inspect.py`, and `messages.json` inside each invocation's workdir.
- Reject escaping paths and conflicting entries; do not silently reuse an
  unrelated existing entry. Preserve source inputs when creating the workdir.
- Implement the fixture's read-only staging first. Reject unsupported writable
  forms explicitly until implemented rather than silently ignoring them.

Proof: generated scripts execute; `bundle/value.txt` and `bundle/value.txt.meta`
contain the expected bytes. Include path-escape and name-collision failures.

## 4. Collect JSON outputs and preserve secondary files

- After an accepted process exit, detect `cwl.output.json` in the tool workdir.
  Parse its output-ID mapping and use it in place of normal output bindings.
  Keep an explicit mapping between CWL output names and generated output ports.
- Validate declared output types and missing required outputs. Resolve relative
  File paths/locations against the output directory; reject malformed JSON and
  inaccessible or invalid output references. Preserve secondary objects.
- Without the JSON file, retain the existing glob/outputEval path.
- Lower `secondaryFiles` declarations on inputs and outputs. Support suffix
  patterns, extension-removal patterns, requiredness, and expression results
  through the same file traversal. The fixture directly proves only `.meta`.
- Validate required companions and move/stage them beside their primary, including
  inside records and Directory listings. A missing required companion must fail.

Proof: `generate` returns its string and File solely through the JSON mapping;
the next tool reads its companion. Add malformed/missing-output failures and a
regression proving ordinary glob outputs still work. Test pattern/expression
forms separately rather than claiming the fixture covers them.

## 5. Honor exit statuses and input loadContents

- Lower `successCodes` to accepted process statuses; retain the existing default
  of zero when absent. Do not allow an output JSON file to turn a failed command
  into success. Reject unsupported failure-category declarations explicitly.
- Expose the actual integer status as `runtime.exitCode` to output evaluation,
  including expressions with no glob. Do not substitute stdout for this value.
- Preserve stdout capture as a File; check the loader's normalization of the
  `stdout` type shortcut before adding duplicate special handling.
- Lower input `loadContents`, load text from the localized File before the
  consuming expression/tool evaluates, and enforce CWL's 64 KiB limit. Share
  the bounded reader with output loading, correcting existing behavior if needed.

Proof: statuses 0 and 1 succeed with the actual code, status 2 fails, and status
1 still fails for tools without `successCodes`. Content is available to `check`;
oversized content fails with a useful error.

## 6. Implement when, nullable results, and source selection

- Retain extra `step.in` inputs used only by step expressions/conditions. The
  fixture's `enabled` belongs to the step but is not an ExpressionTool input.
- Resolve sources/defaults, scatter if present, evaluate sibling `valueFrom`
  against the same original input snapshot, then evaluate `when` per invocation.
  Require a boolean result.
- On false, do not start the command/ExpressionTool. Publish a null value for
  every output while retaining identity and normal completion signaling.
  Null is data, not a missing message or EOF.
- Remove the translator's current `when` rejection only once this path works.
- Replace the multiple-source rejection in `_tool_trace` with explicit source
  resolution. Implement `all_non_null`, `first_non_null`, and
  `the_only_non_null` with declared source order and correct failure cases.
- Keep `linkMerge`, defaults, and `pickValue` ordered according to CWL. Selection
  must not recursively flatten arrays or discard zero/false/empty strings.

Proof: the skipped branch produces one message; the enabled branch produces
two. Test all-null selection, invalid conditions, and the other selection modes.
Add one small scattered conditional regression proving null positions and clean
gather completion; do not expand the main fixture with scatter.

## 7. Integrate and stop

Extend existing focused tests rather than adding a new test framework:

- `test_cwl_tool_metadata.py`, `test_cwl_literal_defaults.py`: lowering and values.
- `test_metadata_contract.py`, `test_pipeline_contract.py`: descriptors survive
  validation and compilation; old metadata remains accepted.
- `test_cwl_expression_runtime.py`, `test_tool_metadata_runtime.py`: expressions,
  staging, content, output JSON, companions, and process statuses.
- `test_scoped_runtime.py`, `test_trace_contract.py`: skipped values, transport,
  identities, and completion where affected.

Run the fixture through the actual translate → compile → execute pipeline and
check its result with `check.py`. Compare report values and exit behavior with
cwltool for the default, enabled, status-0, and status-2 jobs. Add a timeout to
the integration check so a missing skipped-output signal fails visibly.
Run existing toy-genome and relevant compiler/translator regressions once the
focused tests pass. Consult the bundled CWL conformance cases for each feature;
run only selected self-contained cases and record any remaining unsupported forms.

Done when the fixture runs unchanged, its negative cases fail correctly, nested
file transport and skipped completion are proven, and existing relevant tests
pass. Update the fixture README's unsupported-feature note at that point.
No remote execution, full Montage run, generic union implementation, or broad
JavaScript engine migration is required for this milestone.
