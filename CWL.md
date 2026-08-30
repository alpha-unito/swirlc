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

## JavaScript expression example

The example in `examples/cwl/expressions` uses a CWL `ExpressionTool` with
JavaScript expressions and a helper function. Use `streamflow.yml` for local
execution or `streamflow-slurm.yml` for the configured Slurm cluster:

```sh
python ./tmp_main.py translate --language cwl \
  examples/cwl/expressions/streamflow.yml --outdir build
python ./tmp_main.py compile build/workflow.swirl build/metadata.yml \
  --outdir build
cd build
./run.sh
```

Compiled locations that contain JavaScript receive a launcher and a pinned
requirements file. The launcher creates a location-specific virtual environment
and installs a pure-Python JavaScript engine before starting the trace, so Node.js
is not required. SSH and Docker locations prepare inside the target environment.
Slurm locations prepare on the login node first and repeat the check inside the
job, allowing either a shared or node-local work directory.

`run.sh` returns after every location has started, advertised its address, and
received the shared address book. It does not wait for the workflow or Slurm jobs
to finish; Slurm output and errors remain in the generated `*.slurm.out` and
`*.slurm.err` files.

For offline or restricted locations, embed the pure-Python runtime packages
directly in each generated expression trace:

```sh
python ./tmp_main.py compile build/workflow.swirl build/metadata.yml \
  --outdir build --bundle-dependencies
```

Additional installed pure-Python distributions can be included with repeatable
`--bundle-dependency` options. Their active transitive dependencies are included
automatically:

```sh
python ./tmp_main.py compile build/workflow.swirl build/metadata.yml \
  --outdir build --bundle-dependencies \
  --bundle-dependency my-python-library
```

Native extension modules are platform-specific and are rejected by bundled mode;
use deployment-time requirements or platform-specific environments for them.
