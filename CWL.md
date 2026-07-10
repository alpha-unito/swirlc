# how to run CWL example:

## to install
```sh
python -m venv .venv 
# or
uv venv .venv
```

```sh
source .venv/bin/activate
```

```sh
pip install -r requirements.txt
# or 
uv pip install -r requirements.txt
```


## to run the basic cwl example


```sh
source .venv/bin/activate
```

the example is at `examples/cwl/basic/streamflow-slurm.yml`


edit the streamflow file (the slurm config) to your needs, then translate to swirl:

```sh
python ./tmp_main.py translate --language cwl examples/cwl/basic/streamflow-slurm.yml --outdir build
```

the output will be in `build/`

to compile the traces:

```sh
python ./tmp_main.py compile build/workflow.swirl build/metadata.yml --outdir build/
```

to run the workflow on hpc:

```sh
cd build
./run.sh
```

# What was added in the CWL branch:
- Added support for CWL workflows, including translation from a streamflow YAML file to a CWL workflow
- Support for list types in CWL workflows
- Groundwork for more advanced deployments
- SLURM deployment

# What is missing:
- Scatter operations
- Optional types (& choices)
- Nested deployements (like streamflow)
- Communication graph between locations (ex: a node on broadwell cannot be reached from outside, needs a bridge on login node or some other tunnel system)
- a lot of CWL things (javascript, expressions, requirements, etc)
- probably a thousand other things and edge cases

# examples:
- **examples/cwl/basic/streamflow.yml**: Simple CWL workflow running on local nodes.
- **examples/cwl/basic/streamflow-slurm.yml**: Simple CWL workflow running on slurm nodes.
- **examples/cwl/basic/streamflow-split.yml**: Simple CWL workflow running one step on local and one on slurm. Does **NOT** work yet.

- **examples/cwl/lists/streamflow.yml**: Simple CWL workflow with list types running on local nodes.
- **examples/cwl/lists-input/streamflow.yml**: Simple CWL workflow with list types as workflow inputs running on local nodes.

- **examples/cwl/nested/streamflow.yml**: Simple CWL workflow with nested workflows running on local nodes.

- **examples/1000-genome-cpp/streamflow.yml**: 1000 genome workflow. does not work yet.