# Scatter method review

Each `streamflow-<method>.yml` selects the matching CWL workflow. The input
binding map intentionally lists `b` before `a`, while scatter dimensions are
declared as `[a, b]`; coordinate ordering must follow the scatter declaration.

| Configuration | Expected joined output |
| --- | --- |
| `streamflow-dotproduct.yml` | `["same:x", "same:y"]` |
| `streamflow-flat_crossproduct.yml` | `["same:x", "same:y", "same:x", "same:y"]` |
| `streamflow-nested_crossproduct.yml` | `[["same:x", "same:y"], ["same:x", "same:y"]]` |
| `streamflow-empty-inner.yml` | `[[], []]` |

Equal `left` values remain distinct coordinate occurrences. The last case has
two outer coordinates and an empty inner dimension: shape cannot be reconstructed
from the zero result messages, so dispatch cardinalities must be retained by the
new runtime. These are translation review fixtures, not execution evidence.
