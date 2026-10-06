# Separate scatter producers

`left_source` and `right_source` produce lists on distinct deployments. Each
list is dispatched at its producer; no whole-list transfer to the coordinator
or tuple bundle is required. The left producer also supplies a reusable scalar
invariant. Three workers, including the coordinator, receive matching input
keys through deterministic/synchronized moves.

Expected outputs:

- joined: `["same:x", "same:y"]`
- tagged: `["tag:same", "tag:same"]`

Each output has an independent gather. This fixture reviews translation;
executing the new syntax still requires the future compiler/runtime.
