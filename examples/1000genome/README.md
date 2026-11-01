# 1000Genomes Workflow - CWL Implementation

This repository contains a [Common Workflow Language](https://www.commonwl.org/) (CWL) implementation of the [1000Genomes Workflow](https://github.com/pegasus-isi/1000genome-workflow), initially implemented for the [Pegasus](https://pegasus.isi.edu/) workflow management system.

Note that all the metadata reported in the `*.cwl` files, particularly the `s:author` and `s:license` fields, concern only the CWL descriptions themselves, not the related script, whose [License](https://github.com/pegasus-isi/1000genome-workflow/blob/ee083a8a55436d437e3cf9f542f12d491b739c21/LICENSE) is reported on the original repository. If you want to give credit to the original 1000Genomes Workflow, please cite the following article:

> Rafael Ferreira da Silva, Rosa Filgueira, Ewa Deelman, Erola Pairo-Castineira, Ian M. Overton, Malcolm P. Atkinson, Using simple PID-inspired controllers for online resilient resource management of distributed scientific workflows, *Future Generation Computer Systems*, 95, 615-628, 2019,
ISSN 0167-739X, https://doi.org/10.1016/j.future.2019.01.015.

## Local benchmark from a fresh clone

Requires Linux, Python 3.12 or newer with `venv`/`pip`, OpenSSH client **and server**,
Node.js, GNU awk, GNU coreutils, gzip, tar, and curl. On Arch/CachyOS:

```bash
sudo pacman -S --needed python python-pip openssh nodejs gawk coreutils gzip tar curl
```

From the repository root, one command installs the Python dependencies, downloads
missing input files, prepares the deployments, and runs Swirl followed by StreamFlow:

```bash
bash examples/1000genome/benchmark.sh
```

Defaults: **chromosome 1, seven populations, eight intervals, 10 logical workers,
one repetition per engine**. The workflow is still demanding: even one chromosome
can take over an hour and generate tens of gigabytes of temporary files. Watch disk
space and keep other heavy workloads stopped while measuring.

```bash
# Smaller processing range: chromosome 1, 10,000 lines, eight intervals:
bash examples/1000genome/benchmark.sh --small

# Ten sequential repetitions, with five workers per engine:
bash examples/1000genome/benchmark.sh --workers 5 --repetitions 10

# Install/download/prepare only; do not execute the workflow:
bash examples/1000genome/benchmark.sh --prepare-only

# Opt into the original full ten-chromosome input:
bash examples/1000genome/benchmark.sh --full
```

`--small` uses `config-small.yml` for both engines, with `total: 10000` and
`step: 1250`. It still reads the original compressed chromosome input; the
processing range is smaller, rather than the source VCF being truncated.

The bootstrap creates an ignored environment at `.tools/1000genome-venv/`, installs
this checkout in editable mode, installs NumPy/Matplotlib, and pins StreamFlow to
`0.2.0rc3`. Set `PYTHON=/path/to/python3.12` to choose the bootstrap interpreter.
No system services, SSH configuration, or original `config.yml` are changed.
Downloads are cached under `data/`; only the selected chromosomes are fetched.
Interrupted downloads stay in `.part` files and are replaced on the next attempt.

## Results and stopping

Each invocation creates `runs/1000genome/local/benchmark-<UTC timestamp>/`:

- `results.csv`: per-engine execution times, statuses, and run paths.
- `sequence.json`: current stage, process ID, input settings, and package versions.
- `run-01/`, etc.: generated configurations, Swirl build, logs, outputs, and scratch.

Repetitions and engines run sequentially. A failure stops the benchmark; there are
no workflow retries or rollbacks. Press **Ctrl+C** to stop the active engine and its
workers; partial results and scratch are retained for inspection. For a detached
launch, redirect the console output to a log and send SIGTERM to the PID recorded
in `sequence.json` to stop it. Generated data is never automatically deleted; remove
old run directories only after their processes have stopped. Retaining scratch
across repetitions means disk usage accumulates.

## What is being compared

Swirl uses separate local Python processes and transfers file bytes over sockets.
StreamFlow uses separate deployments over loopback SSH with explicit cross-worker
copies and `sharedPaths: []`; read-only staging within one worker may use symlinks.
Its private SSH server listens only on `127.0.0.1:22222`, uses generated keys under
`.tools/local-comparison-ssh/`, and shuts down after its run. It requires no sudo.
Only one local comparison can execute at a time through this launcher.

Both engines use the same Python environment and limit OpenMP, OpenBLAS, and MKL
to one thread per tool. Worker counts are 1, 2, 5, 10, or 20. With 20, chromosome
work uses the first ten workers and interval work uses the other ten; smaller
layouts share a pool. Scheduler behavior remains engine-specific. Workers share
physical CPU, memory, storage, and the loopback network, so this measures local
execution rather than distributed-machine scaling. Timings include runtime startup
and output handling, excluding downloads, preparation, compilation, and SSH server
startup. Filesystem caches are not flushed, and Swirl always runs first.

## Advanced use and smoke test

After bootstrapping, `local-comparison.py` also exposes `prepare` and `run` commands
for inspecting configurations or running one engine. `streamflow.yml` remains the
small generic local mapping for standalone CWL translation examples.

To exercise the entire prepare/run path quickly without the genome dataset:

```bash
.tools/1000genome-venv/bin/python examples/1000genome/local-comparison.py benchmark \
  --locations 2 --workflow examples/cwl/toy-genome/main.cwl \
  --settings examples/cwl/toy-genome/inputs.yml
```

Standalone data download: `bash examples/1000genome/download_data.sh 1` or `all`.
Standalone CWL execution with another runner: `cwl-runner main.cwl config-1chr.yml`
from this example directory, after dependencies and data are installed.
