# Scatter with a worker → shared → worker round trip

Each scattered item runs `item.cwl`, with three dependent steps:

1. `1` runs on the worker assigned to that item (`worker_a` or `worker_b`).
2. `2` runs on `shared`, the same location for every item.
3. `3` runs back on the original worker for that item.

The `/process_items` binding lists both workers. Steps `1` and `3` inherit it;
only `/process_items/2` overrides it. No gather occurs between these steps.
Each task uses its own directory; the workflow gathers the final Files in
input order. Inputs and expected marker contents are reused from
`../depth-1-split`: alpha, beta, alpha.

All four deployments are local, using ports 35700–35703. From the repository root:

```sh
rtk mkdir -p build/depth-1-round-trip
rtk .venv/bin/swirlc translate -l cwl examples/cwl/pipeline/depth-1-round-trip/streamflow.yml -o build/depth-1-round-trip
rtk .venv/bin/swirlc compile build/depth-1-round-trip/workflow.swirl build/depth-1-round-trip/metadata.yml --bundle-dependencies -o build/depth-1-round-trip
rtk sh -c 'cd build/depth-1-round-trip && ./run.sh'
```
