#!/usr/bin/env bash
# Bootstrap a fresh checkout, then compare Swirl and StreamFlow sequentially.
set -euo pipefail
EXAMPLE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT=$(CDPATH= cd -- "$EXAMPLE/../.." && pwd)
workers=10
repetitions=1
chromosomes=1
settings="$EXAMPLE/config-1chr.yml"
prepare_only=()
while (($#)); do
  case "$1" in
    --workers|--repetitions)
      [[ $# -ge 2 && "$2" =~ ^[0-9]+$ ]] || { echo "Missing numeric value for $1" >&2; exit 2; }
      if [[ "$1" == --workers ]]; then workers=$2; else repetitions=$2; fi
      shift 2 ;;
    --small) chromosomes=1; settings="$EXAMPLE/config-small.yml"; shift ;;
    --full) chromosomes=all; settings="$EXAMPLE/config.yml"; shift ;;
    --prepare-only) prepare_only=(--prepare-only); shift ;;
    -h|--help)
      echo "Usage: bash examples/1000genome/benchmark.sh [--workers 1|2|5|10|20] [--repetitions N] [--small|--full] [--prepare-only]"
      echo "Default: chromosome 1, 10 workers, one Swirl run followed by one StreamFlow run."
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$workers" in 1|2|5|10|20) ;; *) echo "Unsupported worker count: $workers" >&2; exit 2 ;; esac
((repetitions > 0)) || { echo "Repetitions must be positive" >&2; exit 2; }
for program in "${PYTHON:-python3}" sshd ssh ssh-keygen node gawk tar gzip curl; do
  command -v "$program" >/dev/null || { echo "Install required executable: $program" >&2; exit 1; }
done
VENV="$PROJECT/.tools/1000genome-venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  "${PYTHON:-python3}" -m venv "$VENV"
fi
if ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  "$VENV/bin/python" -m ensurepip --upgrade
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check -e "$PROJECT" \
  -r "$EXAMPLE/requirements.txt" 'streamflow==0.2.0rc3'
bash "$EXAMPLE/download_data.sh" "$chromosomes"
exec "$VENV/bin/python" "$EXAMPLE/local-comparison.py" benchmark \
  --locations "$workers" --repetitions "$repetitions" --settings "$settings" "${prepare_only[@]}"
