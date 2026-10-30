#!/bin/bash
#SBATCH --job-name=genome-streamflow-1
#SBATCH --partition=broadwell
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --exclusive
#SBATCH --time=01:00:00
#SBATCH --output=/beegfs/home/tommaso.fogliobonda/swirlc/runs/1000genome/streamflow-1/slurm-%j.out
#SBATCH --error=/beegfs/home/tommaso.fogliobonda/swirlc/runs/1000genome/streamflow-1/slurm-%j.err
set -euo pipefail
PROJECT=/beegfs/home/tommaso.fogliobonda/swirlc
cd "$PROJECT"
export PATH="$PROJECT/.tools/node-streamflow/bin:$PROJECT/venv/bin:/usr/local/bin:/usr/bin:/bin"
unset MPLBACKEND OPENBLAS_NUM_THREADS OMP_NUM_THREADS
ulimit -Sn 65536
exec "$PROJECT/.venv-streamflow/bin/python" - <<'PY'
import csv
import os
from pathlib import Path
import subprocess
import time

root = Path.cwd()
run = root / 'runs/1000genome' / ('streamflow-1-' + os.environ['SLURM_JOB_ID'])
run.mkdir(parents=True, exist_ok=False)
print('Host:', os.uname().nodename, flush=True)
command = [str(root / '.venv-streamflow/bin/streamflow'), 'run', '--outdir',
           str(run / 'outputs'), str(root / 'examples/1000genome/streamflow-native-c3s-1.yml')]
from ruamel.yaml import YAML
yaml = YAML()
config = yaml.load(root / 'examples/1000genome/streamflow-native-c3s-1.yml')
config['workflows']['genome']['config']['file'] = str(root / 'examples/1000genome/main.cwl')
config['workflows']['genome']['config']['settings'] = str(root / 'examples/1000genome/config-1chr.yml')
config['deployments']['local']['workdir'] = str(run / 'scratch')
config['database']['config']['connection'] = str(run / 'streamflow.sqlite')
with (run / 'streamflow.yml').open('w') as stream:
    yaml.dump(config, stream)
command[-1] = str(run / 'streamflow.yml')
start = time.monotonic()
result = subprocess.run(command)
elapsed = time.monotonic() - start
with (run / 'timing.csv').open('w', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['job_id', 'execution_seconds', 'exit_code'])
    writer.writerow([os.environ['SLURM_JOB_ID'], f'{elapsed:.3f}', result.returncode])
print('StreamFlow execution seconds:', elapsed, 'exit:', result.returncode, flush=True)
raise SystemExit(result.returncode)
PY
