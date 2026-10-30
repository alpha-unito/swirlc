#!/bin/bash
# Submit 10 sequential Slurm jobs. Each run starts only if its predecessor succeeds.
set -euo pipefail
PROJECT=/beegfs/home/tommaso.fogliobonda/swirlc
cd "$PROJECT"
BENCHMARK="$PROJECT/runs/1000genome/streamflow-20-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir "$BENCHMARK"
printf 'repetition,job_id,execution_seconds,wall_seconds,status,error,run_directory\n' > "$BENCHMARK/results.csv"
previous=''
for repetition in {1..10}; do
    dependency=()
    if [[ -n "$previous" ]]; then
        dependency=(--dependency="afterok:$previous" --kill-on-invalid-dep=yes)
    fi
    previous=$(sbatch --parsable "${dependency[@]}" \
        --output="$BENCHMARK/slurm-$repetition-%j.out" \
        --error="$BENCHMARK/slurm-$repetition-%j.err" \
        examples/1000genome/streamflow-benchmark-20.sbatch "$BENCHMARK" "$repetition")
    previous=${previous%%;*}
    printf '%s,%s\n' "$repetition" "$previous" >> "$BENCHMARK/jobs.csv"
    echo "Submitted repetition $repetition as job $previous"
done
echo "Results: $BENCHMARK/results.csv"
