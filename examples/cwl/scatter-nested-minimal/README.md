# Minimal nested scatter

This is the smallest distributed nested-scatter example: two batches are
scattered on `coordinator`; each batch's two strings are scattered to
`item_worker`, where `echo` writes one file per string. Each deployment maps to
one SWIRL location, and each scatter selects its locations with a target list.

```sh
swirlc translate --language cwl streamflow.yml --outdir translated
```

The output shape is `File[][]`: `[[one, two], [three, four]]`.  It has no
unzip, merge, tag, or final aggregation steps, so the generated trace contains
only the two scatter regions and the inner `echo` invocation.
