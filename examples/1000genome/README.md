# 1000Genomes Workflow - CWL Implementation

This repository contains a [Common Workflow Language](https://www.commonwl.org/) (CWL) implementation of the [1000Genomes Workflow](https://github.com/pegasus-isi/1000genome-workflow), initially implemented for the [Pegasus](https://pegasus.isi.edu/) workflow management system.

Note that all the metadata reported in the `*.cwl` files, particularly the `s:author` and `s:license` fields, concern only the CWL descriptions themselves, not the related script, whose [License](https://github.com/pegasus-isi/1000genome-workflow/blob/ee083a8a55436d437e3cf9f542f12d491b739c21/LICENSE) is reported on the original repository. If you want to give credit to the original 1000Genomes Workflow, please cite the following article:

> Rafael Ferreira da Silva, Rosa Filgueira, Ewa Deelman, Erola Pairo-Castineira, Ian M. Overton, Malcolm P. Atkinson, Using simple PID-inspired controllers for online resilient resource management of distributed scientific workflows, *Future Generation Computer Systems*, 95, 615-628, 2019,
ISSN 0167-739X, https://doi.org/10.1016/j.future.2019.01.015.

## Usage

Running this workflow requires a [CWL runner](https://www.commonwl.org/implementations/). For example, the CWL reference implementation, called [cwltool](https://github.com/common-workflow-language/cwltool), can be installed as follows:

```bash
python3 -m venv venv
source venv/bin/activate
pip install cwlref-runner
```

Two workflow steps require a `Python>=3.6` interpreter and the packages listed in the `requirements.txt` file. Such packages can be installed as follows:

```bash
pip install -r requirements.txt
```

Workflow input data are stored online on the [1000Genomes workflow repository](https://github.com/pegasus-isi/1000genome-workflow) and the [1000Genomes FTP server](https://ftp.1000genomes.ebi.ac.uk). The `download_data.sh` script creates the data directory structure and downloads all the required data in the proper locations.

Once all software and data dependencies are installed, the workflow can be launched using the following command:

```bash
cwl-runner main.cwl config.yml
```

## Running on Fedarcs with swirlc

Run these commands on `fd-coordinator`, logged in as the account that will run the
workflow. Use a prepared checkout containing `streamflow-fedarcs.yml` and the
`ulimit -Sn 4096` adjustment in `scripts/individuals`.

### One-time setup for a different user

Set your checkout path and create a venv on the shared filesystem:

```bash
export RUN_USER="$(id -un)"
export PROJECT="/mnt/shared/$RUN_USER/swirlc"
cd "$PROJECT"
python3 -m venv venv
. venv/bin/activate
python -m pip install -e . -r examples/1000genome/requirements.txt
```

Edit these files:

- `examples/1000genome/streamflow-fedarcs.yml`: replace `tfogliobonda` in every
  `username` and `workdir` with your username. Keep `checkHostKey: accept-new`.
  Choose different ports if someone else is running the workflow on the same nodes.
- `examples/1000genome/clt/frequency.cwl` and `clt/mutation_overlap.cwl`: set
  `baseCommand` to your venv's absolute Python path:

  ```yaml
  baseCommand: ["/mnt/shared/YOUR_USERNAME/swirlc/venv/bin/python"]
  

### Translate, compile, and run

From your checkout:

```bash
. venv/bin/activate

export RUN_DIR="$PROJECT/build/fedarcs"
export SCRATCH="$PROJECT/tmp"

mkdir -p "$RUN_DIR" "$SCRATCH
"
python tmp_main.py translate --language cwl \
    examples/1000genome/streamflow-fedarcs.yml --outdir "$RUN_DIR
    "
python tmp_main.py compile "$RUN_DIR/workflow.swirl" "$RUN_DIR/metadata.yml" \
    --outdir "$RUN_DIR" --tmpdir "$SCRATCH" --bundle-dependencies
    
cd "$RUN_DIR"

./run.sh > workflow-run.log 2>&1

status=$?

printf 'Workflow exit status: %s\n' "$status"
```



## Prepared C3S configurations (swirlc)

Use `streamflow-c3s-1.yml`, `streamflow-c3s-2.yml`,
`streamflow-c3s-5.yml`, `streamflow-c3s-10.yml`, or
`streamflow-c3s-20.yml`. These are input files for the swirlc translator,
using its persistent Slurm-location deployment format.

| Locations | Chromosome workers | Interval workers | Mapping |
| --- | --- | --- | --- |
| 1 | 1 | Same worker | Everything local to one location |
| 2 | 2 | Same workers | Five chromosomes per worker |
| 5 | 5 | Same workers | Two chromosomes per worker |
| 10 | 10 | Same workers | One chromosome per worker |
| 20 | 10 | 10 separate workers | Chromosome preparation/merge and population scatters use the first pool; interval tasks use the extra pool |

The root coordinator shares worker01, avoiding an idle coordinator allocation.
Chromosome ownership is assigned by the translator's scatter distribution.
Non-scattered preparation, merge and sifting steps execute on the owning
chromosome worker. Nested scatters (intervals and the two population analyses)
are distributed over their target pool, not pinned to the outer chromosome
owner. Thus these YAML bindings do not guarantee chromosome-local population
analysis: merged archives and sifted data can cross locations. The 1-location
configuration is the locality baseline. The 20-location layout gives the 80
interval jobs a separate pool while keeping the 140 population-analysis jobs
on the 10 chromosome workers. It is a proposed starting point, not a measured
optimum; strict outer-scatter affinity would require translator support or a
workflow restructure.

Each location requests one exclusive Broadwell node, 8 CPUs, 32 GB and 1 hour.
Exclusive allocation keeps locations on distinct nodes. Command concurrency is unlimited (`SWIRLC_COMMAND_SLOTS=0`) for the new
comparison runs; outgoing payload transfers remain capped at 64. The runtime
default for other workflows remains `os.cpu_count() * 2`. The completed initial
SWIRL baseline used the previous explicit eight-slot override. BLAS/OpenMP threading uses library defaults. Run only one copy of
a given configuration at a time: ports and work directories are fixed, with
separate ranges for each size. Distinct work directories on BeeGFS do not imply
that cross-location transfers are free.

The configs assume checkout `/beegfs/home/tommaso.fogliobonda/swirlc` and its
`venv`. Python tools resolve `python3` through that venv's PATH, rather than a
hardcoded Fedarcs interpreter. Before any execution, prepare the dataset with
`download_data.sh`, verify every input in `config.yml`, install
`requirements.txt` into the shared venv, and ensure Bash, GNU awk, gzip, tar,
pr and the other GNU utilities are available on the compute nodes.

To prepare a build on C3S, without launching it:

```bash
cd /beegfs/home/tommaso.fogliobonda/swirlc
mkdir -p build-genome-c3s-10
venv/bin/swirlc translate --language cwl \
  examples/1000genome/streamflow-c3s-10.yml --outdir build-genome-c3s-10
venv/bin/swirlc compile build-genome-c3s-10/workflow.swirl \
  build-genome-c3s-10/metadata.yml --outdir build-genome-c3s-10 \
  --tmpdir /beegfs/home/tommaso.fogliobonda/swirlc/runs/1000genome/scratch \
  --bundle-dependencies
```

Bundling covers runtime pure-Python dependencies; it does not install NumPy or
Matplotlib for the analysis commands. Executing the generated `run.sh` submits
jobs; the preparation commands above do not execute it.


### Prepare the smaller input with a script

`config-1chr.yml` selects chromosome 1, all seven populations, and eight intervals.
Run on C3S from the checkout root:

```bash
venv/bin/python examples/1000genome/prepare-c3s.py
# Or prepare only selected location counts:
venv/bin/python examples/1000genome/prepare-c3s.py 1 5
# Select another input file explicitly:
venv/bin/python examples/1000genome/prepare-c3s.py 10 --settings examples/1000genome/config.yml
```

The default builds go in `build-genome-c3s-config-1chr/{1,2,5,10,20}`.
Each build has `prepare.log` and its generated `streamflow.yml`, SWIRL,
metadata and launch files. `--build-root PATH` overrides the parent directory.
Preparation stops on a failed translation or compilation. It never runs
`run.sh` or submits jobs. Re-running overwrites generated build files; do not
prepare the same build while it is executing. With just one chromosome, the
chromosome worker pool will be underused; these layouts retain their original
mapping for comparison.


### Benchmark prepared C3S builds

After preparing all requested builds, run from the C3S checkout root:

```bash
venv/bin/python examples/1000genome/benchmark-c3s.py --csv genome-benchmark.csv
# Optional subset or alternate prepared build directory:
venv/bin/python examples/1000genome/benchmark-c3s.py 1 5 --repetitions 10 \
  --build-root build-genome-c3s-config-1chr --csv genome-benchmark-1-5.csv
```

This command **submits jobs**. It runs each requested layout ten times,
sequentially, cycling through the sizes once per repetition. Parallel runs
would share filesystem bandwidth and compete for nodes, so they are excluded.
A project-wide lock prevents simultaneous copies of this benchmark. Do not
manually run these builds or prepare/overwrite them during a benchmark.
Other cluster users can still affect queue times and shared-storage performance.

CSV `execution_seconds` is the Slurm timestamp span from the last location's
start to the last location's end (one-second accounting resolution). Locations
wait at a startup barrier, so this approximates execution after all locations
are allocated; it includes startup overhead and is not pure task CPU time.
`wall_seconds` uses a monotonic clock from launcher invocation until all jobs
finish, including queueing and up to one polling interval (default 15 seconds).
The generated `run.sh` alone is insufficient for timing: it returns after Slurm
startup rather than waiting for location jobs to finish.

The CSV also records repetition, UTC start time, status, job IDs, log path and
errors. Results are flushed after every run; existing CSV files are never
overwritten. A failure or interruption stops the benchmark and cancels only
that run's submitted jobs, waiting until they leave the queue. No later runs
start after a failure. Slurm accounting must be available. There are no
unreported warm-up runs or cache flushing; results reflect normal repeated runs
with potentially warm input filesystem caches. Each invocation uses its own
`SWIRLC_TMP_DIR` under `runs/1000genome/benchmark-tmp`. After all its jobs stop,
the benchmark copies Slurm logs and output manifests to a per-run `.artifacts`
directory beside the CSV, then removes that invocation's scratch (including
generated workflow outputs). Prepared builds, source datasets, CSV and benchmark
logs are retained. Cleanup also follows failed/cancelled runs once job shutdown
is confirmed; if shutdown cannot be confirmed, scratch is retained for safety.
Cleanup is outside the recorded successful-run times. Previous scratch from
manual runs or other invocations is never removed.
