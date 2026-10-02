# Three-level scatter review

Translate `streamflow-shared.yml` or `streamflow-separate.yml` with the CWL
translator. The shared configuration uses the same two workers at every level;
the separate configuration uses two workers per level. All deployments are local
review locations; the generated new syntax is not yet executable by the old
compiler.

`groups` is `[[], [[], [a, a]], [[b]]]`. Only group/batch/item are scattered.
Every invocation also uses the scalar prefix and complete labels list. The leaf
ExpressionTool returns a string and an integer, so both outputs traverse all
three gathers.

Expected outputs after the new runtime is implemented:

```yaml
rendered:
  - []
  - - []
    - ["item:a:red,blue", "item:a:red,blue"]
  - - ["item:b:red,blue"]
counts:
  - []
  - - []
    - [2, 2]
  - - [2]
```

These examples exercise empty middle/leaf invocations, varying cardinalities,
duplicates, invariant reuse, two outputs, and full parent-key paths. Expected
values describe the CWL contract; translation alone does not execute it.
