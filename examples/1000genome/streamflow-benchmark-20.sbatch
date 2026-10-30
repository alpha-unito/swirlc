#!/bin/bash
#SBATCH --job-name=genome-streamflow-20
#SBATCH --partition=broadwell
#SBATCH --exclude=broadwell-052
#SBATCH --nodes=20
#SBATCH --ntasks=20
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --exclusive
#SBATCH --time=01:00:00
set -euo pipefail
ulimit -Sn 65536
PROJECT=/beegfs/home/tommaso.fogliobonda/swirlc
cd "$PROJECT"
exec "$PROJECT/.venv-streamflow/bin/python" examples/1000genome/streamflow-benchmark-20.py "$1" "$2"
