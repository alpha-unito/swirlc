# Single scatter review fixtures

`main.cwl` scatters only `items`. Every invocation also receives the scalar
`prefix` and the complete `labels` list. The inline ExpressionTool returns two
outputs, gathered in input order as `rendered` and `invariant_counts` arrays.
Only `worker1` and `worker2` execute `/process`; the workflow root is bound to
`coordinator`. All three deployments use the existing local-worker convention.

Each `streamflow-<case>.yml` selects its matching `inputs-<case>.yml`:

| Case | Scattered items | Expected `rendered` | Expected `invariant_counts` |
| --- | --- | --- | --- |
| empty | `[]` | `[]` | `[]` |
| one | `[alpha]` | `["item:alpha:red,blue,green"]` | `[3]` |
| duplicate | `[alpha, alpha]` | `["item:alpha:red,blue,green", "item:alpha:red,blue,green"]` | `[3, 3]` |
| many | `[alpha, beta, gamma, delta, epsilon]` | One corresponding string per input item | `[3, 3, 3, 3, 3]` |

The empty case checks empty gathering, the duplicate case checks preservation
of repeated values, and the five-item case exceeds the two worker locations.
These are review examples, not automated tests.
