#!/usr/bin/env python3
"""Execute one 20-location StreamFlow repetition inside a Slurm allocation."""
import csv
import getpass
import os
import re
from pathlib import Path
import subprocess
import sys
import time

from ruamel.yaml import YAML

project = Path('/beegfs/home/tommaso.fogliobonda/swirlc')
custom_tmp = project / 'tmp'
benchmark = Path(sys.argv[1]).resolve()
repetition = int(sys.argv[2])
run = benchmark / f'run-{repetition:02d}'
run.mkdir(parents=True, exist_ok=False)
job = os.environ['SLURM_JOB_ID']
started = time.monotonic()
status = 'FAILED'
error = ''
execution_seconds = ''
try:
    # Ensure custom tmp exists and is clean before each run
    if custom_tmp.exists():
        for entry in custom_tmp.iterdir():
            if entry.is_dir() and not entry.is_symlink():
                subprocess.run(['rm', '-rf', str(entry)], check=True)
            else:
                entry.unlink(missing_ok=True)
    custom_tmp.mkdir(parents=True, exist_ok=True)

    # Broadwell allocations use Slurm's node-list syntax, e.g. broadwell-[001-020].
    node_list = os.environ['SLURM_JOB_NODELIST']
    match = re.fullmatch(r'([^\[\],]+)(?:\[([0-9,\-]+)\])?', node_list)
    if not match:
        raise RuntimeError(f'Unsupported Slurm node list: {node_list}')
    prefix, groups = match.groups()
    nodes = []
    for item in (groups or '').split(','):
        if '-' in item:
            start, end = item.split('-', 1)
            nodes.extend(f'{prefix}{i:0{len(start)}d}' for i in range(int(start), int(end) + 1))
        elif item:
            nodes.append(prefix + item)
    if groups is None:
        nodes = [prefix]
    if len(nodes) != 20 or len(set(nodes)) != 20:
        raise RuntimeError(f'Expected 20 distinct allocated nodes, got {nodes}')
    # Fail before starting the workflow if the allocation cannot be reached.
    for node in nodes:
        subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=15', node, 'true'], check=True)
    template = run / 'ssh-template.sh'
    template.write_text('#!/bin/sh\nexport TMPDIR="' + str(custom_tmp) + '"\nexport PATH="' + str(project / '.tools/node-streamflow/bin') + ':' + str(project / 'venv/bin') + ':$PATH"\n{{streamflow_command}}\n')
    deployments = {}
    for i, node in enumerate(nodes):
        deployments[f'worker{i:02}'] = {
            'type': 'ssh', 'workdir': str(run / 'scratch' / f'worker{i:02}'),
            'config': {'nodes': [node], 'username': getpass.getuser(),
                       'checkHostKey': False, 'file': str(template),
                       'sharedPaths': [str(project)]},
        }
    targets = lambda indexes: [{'deployment': f'worker{i:02}'} for i in indexes]
    yaml = YAML()
    with (project / 'examples/1000genome/config.yml').open('r') as stream:
        raw_config = yaml.load(stream)

    base_dir = project / 'examples/1000genome'
    def resolve_paths(val):
        if isinstance(val, dict):
            return {k: resolve_paths(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [resolve_paths(v) for v in val]
        elif isinstance(val, str) and not val.startswith('/'):
            candidate = base_dir / val
            if candidate.exists():
                return str(candidate)
        return val

    resolved_config = resolve_paths(raw_config)
    resolved_settings_path = run / 'config-resolved.yml'
    with resolved_settings_path.open('w') as stream:
        yaml.dump(resolved_config, stream)

    config = {
        'version': 'v1.0',
        'workflows': {'genome': {
            'type': 'cwl',
            'config': {'file': str(project / 'examples/1000genome/main.cwl'),
                       'settings': str(resolved_settings_path)},
            'bindings': [
                {'step': '/', 'target': targets(range(10))},
                {'step': '/chromosome', 'target': targets(range(10))},
                {'step': '/chromosome/individuals', 'target': targets(range(10, 20))},
            ],
        }},
        'deployments': deployments,
        'database': {'type': 'sqlite', 'config': {'connection': str(run / 'streamflow.sqlite')}},
    }
    with (run / 'streamflow.yml').open('w') as stream:
        yaml.dump(config, stream)
    env = os.environ.copy()
    for key in ('MPLBACKEND', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'):
        env.pop(key, None)
    env['TMPDIR'] = str(custom_tmp)
    env['PATH'] = f'{project}/.tools/node-streamflow/bin:{project}/venv/bin:' + env.get('PATH', '')
    command = [str(project / '.venv-streamflow/bin/streamflow'), 'run',
               '--outdir', str(run / 'outputs'), str(run / 'streamflow.yml')]
    execution_started = time.monotonic()
    with (run / 'workflow.log').open('w') as log:
        result = subprocess.run(command, cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT)
    execution_seconds = f'{time.monotonic() - execution_started:.3f}'
    if result.returncode:
        raise RuntimeError(f'StreamFlow exited {result.returncode}; see {run / "workflow.log"}')
    status = 'COMPLETED'
except BaseException as exc:
    error = str(exc) or type(exc).__name__
    print(error, file=sys.stderr, flush=True)
finally:
    elapsed = time.monotonic() - started
    with (benchmark / 'results.csv').open('a', newline='') as stream:
        csv.writer(stream).writerow([repetition, job, execution_seconds, f'{elapsed:.3f}', status, error, str(run)])
        stream.flush()
        os.fsync(stream.fileno())
    print(f'repetition={repetition} job={job} status={status} elapsed={elapsed:.3f}', flush=True)
if status != 'COMPLETED':
    raise SystemExit(1)
