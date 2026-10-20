# Scatter across two workers with a shared finish location

This configuration reuses the CWL and inputs from `../depth-1-split`.
The `/process_items` binding lists two deployments, `worker_a` and `worker_b`,
so both participate in executing the scattered subworkflow's first step, `stage`.
The more specific `/process_items/finish` binding sends every item's second
step to the same `finish` location, regardless of which worker ran `stage`.
Each task has its own work directory.

There are four local locations: source (35690), worker_a (35691), worker_b
(35692), and finish (35693). The scatter still has one level and gathers three
Files in input order. Their contents, minus the trailing newline, match
`../depth-1-split/expected.json`: alpha, beta, alpha markers.

From the repository root:

```sh
rtk mkdir -p build/depth-1-split-two-workers
rtk .venv/bin/swirlc translate -l cwl examples/cwl/pipeline/depth-1-split-two-workers/streamflow.yml -o build/depth-1-split-two-workers
rtk .venv/bin/swirlc compile build/depth-1-split-two-workers/workflow.swirl build/depth-1-split-two-workers/metadata.yml --bundle-dependencies -o build/depth-1-split-two-workers
rtk sh -c 'cd build/depth-1-split-two-workers && ./run.sh'
```
