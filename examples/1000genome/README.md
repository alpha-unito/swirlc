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

