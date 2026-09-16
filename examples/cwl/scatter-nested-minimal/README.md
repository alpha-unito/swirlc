# Minimal nested scatter

This is the smallest distributed nested-scatter example: two batches are
scattered to `batch_workers`; each batch's two strings are scattered to
`item_workers`, where `echo` writes one file per string. Each pool has one
worker to keep the generated trace short; the batches still make both scatter
levels visible.

```sh
swirlc translate --language cwl streamflow.yml --outdir translated
```

The output shape is `File[][]`: `[[one, two], [three, four]]`.  It has no
unzip, merge, tag, or final aggregation steps, so the generated trace contains
only the two scatter regions and the inner `echo` invocation.
