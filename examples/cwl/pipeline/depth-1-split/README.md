# Scatter with a shared finish location

Like `../depth-1/plain`, this workflow scatters over three input Files, including
a repeated alpha. Each scatter invocation runs `item.cwl`, a two-step pipeline:

1. `stage` inherits the scatter's `worker` location and writes `staged.txt`.
2. `finish` consumes that File on the third location, `finish`, and writes
   `result.txt`.

The `/process_items/finish` binding applies to every scatter invocation. All
three finish tasks use the same location, each with its own task work directory.
This is a per-item dependency, with one scatter level; there is no gather between
`stage` and `finish`. The outer workflow gathers the three final Files in input
order. Their contents, minus the trailing newline, match `expected.json`.

All three deployments are local and use ports 35680–35682. Only GNU `cp` is needed.
From the repository root:

```sh
rtk mkdir -p build/depth-1-split
rtk .venv/bin/swirlc translate -l cwl examples/cwl/pipeline/depth-1-split/streamflow.yml -o build/depth-1-split
rtk .venv/bin/swirlc compile build/depth-1-split/workflow.swirl build/depth-1-split/metadata.yml --bundle-dependencies -o build/depth-1-split
rtk sh -c 'cd build/depth-1-split && ./run.sh'
```
