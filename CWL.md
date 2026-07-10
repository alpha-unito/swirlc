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
