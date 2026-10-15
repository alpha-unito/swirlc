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

`run.sh` coordinates location startup/address discovery and waits for launched
workflow processes, propagating their failures. Actual Slurm execution remains
unverified; generated Slurm logs use `*.slurm.out` and `*.slurm.err` files.

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

## Expression translation boundary

The CWL translator lowers `$()`/`${}` and interpolation into generic JavaScript
function bodies with explicit bindings. Generated runtime code uses Js2Py and
contains no CWL expression parser or `cwl_utils` import. For example, an input
transformation becomes:

```yaml
inputs:
  p_population:
    type: file
expression:
  language: javascript
  source: return (self.nameroot);
  bindings:
    self:
      port: p_population
```

The variable name `self` is specified by the translator; the evaluator supports
arbitrary binding names. Port types are declared once in the step `inputs` map;
file staging derives from those declarations, independently of expression bindings.
Output processors can bind a variable to `matchedFiles`
after generic `readContents` loading. Dynamic stdout/globs use the same expression
descriptors. Re-translate older metadata to obtain this contract; literals and
ordinary direct-port commands remain compatible. Node is not needed.

## Conditions

CWL scatter distribution now emits named guards such as `+[items_ready]`.
Metadata supplies built-in checks without JavaScript:

```yaml
conditions:
  items_ready:
    type: has_data
    port: p_items
    scope: root
```

The false branch means exhausted, not temporarily empty. Generic Boolean
expression checks use `type: expression`, typed `inputs`, optional `bindings`,
and a generic `expression` descriptor. Inputs must already be bound in the
invocation. CWL `when` is explicitly rejected pending skipped/null output support.
