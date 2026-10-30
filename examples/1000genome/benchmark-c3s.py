#!/usr/bin/env python3
"""Benchmark prepared C3S builds sequentially; never compile them."""

import argparse
import csv
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid


def job_ids(log):
    return list(dict.fromkeys(re.findall(r"Submitted batch job (\d+)", log.read_text())))


def queued(ids):
    result = subprocess.run(
        ["squeue", "--noheader", "--user", str(os.getuid()), "--format=%A"],
        capture_output=True, text=True, check=True,
    )
    return bool(set(ids).intersection(result.stdout.split()))


def accounting(ids):
    result = subprocess.run(
        ["sacct", "-X", "--noheader", "--parsable2", "--jobs", ",".join(ids),
         "--format=JobIDRaw,State,ExitCode,Start,End"],
        capture_output=True, text=True, check=True,
        env={**os.environ, "TZ": "UTC", "SLURM_TIME_FORMAT": "standard"},
    )
    records = {}
    for line in result.stdout.splitlines():
        fields = line.split("|")
        if len(fields) >= 5 and fields[0] in ids:
            records[fields[0]] = fields[1:5]
    return records


def execution_seconds(records):
    """All locations must start before the workflow passes its startup barrier."""
    starts = [datetime.fromisoformat(r[2]) for r in records.values()]
    ends = [datetime.fromisoformat(r[3]) for r in records.values()]
    return (max(ends) - max(starts)).total_seconds()


def run_one(build, count, log, poll):
    started = time.monotonic()
    ids = []
    launcher = None
    stopped = False
    temporary_root = Path(__file__).resolve().parents[2] / "runs/1000genome/benchmark-tmp"
    temporary_root.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="run-", dir=temporary_root))
    try:
        env = {**os.environ, "SWIRLC_RUN_ID": uuid.uuid4().hex,
               "SWIRLC_TMP_DIR": str(scratch),
               "SWIRLC_ADDRESS_GATHER_TIMEOUT": "86400"}
        with log.open("w") as stream:
            launcher = subprocess.Popen(["bash", "run.sh"], cwd=build, env=env,
                                        stdout=stream, stderr=subprocess.STDOUT)
            code = launcher.wait()
        ids = job_ids(log)
        if code or len(ids) != count:
            raise RuntimeError(f"Launcher exit {code}; expected {count} jobs, found {len(ids)}")
        while queued(ids):
            time.sleep(poll)
        stopped = True
        for attempt in range(12):
            records = accounting(ids)
            if (len(records) == count and
                    all(r[3] not in ("Unknown", "None", "") for r in records.values())):
                break
            time.sleep(5)
        else:
            raise RuntimeError("Slurm accounting incomplete after jobs left the queue")
        if any(r[0] != "COMPLETED" or r[1] != "0:0" for r in records.values()):
            raise RuntimeError(f"Slurm job failure: {records}")
        return execution_seconds(records), time.monotonic() - started, ids
    except BaseException:
        if launcher is not None and launcher.poll() is None:
            launcher.terminate()
            launcher.wait()
        ids = job_ids(log) if log.exists() else ids
        # Cancel only this run's jobs, then drain them before releasing the lock.
        if ids:
            subprocess.run(["scancel", *ids], check=False)
            while queued(ids):
                time.sleep(poll)
            stopped = True
        raise
    finally:
        if stopped:
            # Keep diagnostics before deleting only this invocation's scratch.
            from ruamel.yaml import YAML

            metadata = YAML(typ="safe").load(build / "metadata.yml")
            diagnostics = log.with_suffix(".artifacts")
            diagnostics.mkdir(exist_ok=True)
            for name, location in metadata["locations"].items():
                workdir = Path(location["deployment"]["workdir"])
                for suffix in ("slurm.out", "slurm.err"):
                    source = workdir / f"{name}.{suffix}"
                    if source.is_file():
                        shutil.copy2(source, diagnostics / source.name)
            for source in build.glob("l*.outputs.json"):
                shutil.copy2(source, diagnostics / source.name)
            shutil.rmtree(scratch)
        else:
            print(f"Retaining scratch because job shutdown was not confirmed: {scratch}", flush=True)


def main():
    project = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locations", nargs="*", type=int)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--build-root", type=Path,
                        default=project / "build-genome-c3s-config-1chr")
    parser.add_argument("--csv", type=Path, default=project / "genome-benchmark.csv")
    parser.add_argument("--poll-seconds", type=float, default=15)
    args = parser.parse_args()
    counts = list(dict.fromkeys(args.locations or [1, 2, 5, 10, 20]))
    if any(n not in (1, 2, 5, 10, 20) for n in counts):
        parser.error("locations must be selected from 1, 2, 5, 10, 20")
    if args.repetitions < 1 or args.poll_seconds <= 0:
        parser.error("repetitions and poll-seconds must be positive")
    root = args.build_root.resolve()
    for count in counts:
        if not (root / str(count) / "run.sh").is_file():
            parser.error(f"Missing prepared build: {root / str(count) / 'run.sh'}")
    output = args.csv.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = project / "runs/1000genome/benchmark.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another genome benchmark is already running")
        # Exclusive creation protects previous benchmark results.
        with output.open("x", newline="") as stream, ExitStack() as layout_files:
            writer = csv.DictWriter(stream, fieldnames=[
                "locations", "repetition", "started_utc", "execution_seconds",
                "wall_seconds", "status", "job_ids", "log", "error",
            ])
            writer.writeheader()
            stream.flush()
            layouts = {}
            for count in counts:
                path = output.with_name(f"{output.stem}-locations-{count}.csv")
                target = layout_files.enter_context(path.open("x", newline=""))
                layout_writer = csv.DictWriter(target, fieldnames=writer.fieldnames)
                layout_writer.writeheader()
                target.flush()
                layouts[count] = (layout_writer, target)

            def save(row):
                for target_writer, target_stream in ((writer, stream), layouts[row["locations"]]):
                    target_writer.writerow(row)
                    target_stream.flush()
                    os.fsync(target_stream.fileno())
            # Interleave sizes across repetitions to reduce time-of-day bias.
            for repetition in range(1, args.repetitions + 1):
                for count in counts:
                    log = output.with_name(f"{output.stem}-{count}-{repetition}.log")
                    row = dict(locations=count, repetition=repetition,
                               started_utc=datetime.now(timezone.utc).isoformat(), log=str(log))
                    print(f"Run {repetition}/{args.repetitions}, {count} locations", flush=True)
                    attempt_started = time.monotonic()
                    try:
                        execution, wall, ids = run_one(root / str(count), count, log, args.poll_seconds)
                        row.update(execution_seconds=f"{execution:.3f}", wall_seconds=f"{wall:.3f}",
                                   status="COMPLETED", job_ids=";".join(ids), error="")
                    except BaseException as exc:
                        row.update(status="FAILED", wall_seconds=f"{time.monotonic() - attempt_started:.3f}",
                                   error=str(exc) or type(exc).__name__,
                                   job_ids=";".join(job_ids(log)) if log.exists() else "")
                        save(row)
                        raise SystemExit(f"Benchmark stopped: {exc}; see {log}")
                    save(row)
                    print(f"Execution: {execution:.1f}s; wall including queue: {wall:.1f}s", flush=True)


if __name__ == "__main__":
    main()
