#!/usr/bin/env python3
"""Prepare and run one local, explicit-transfer comparison without Slurm."""

import argparse
import copy
import csv
import fcntl
import getpass
import json
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ruamel.yaml import YAML

EXAMPLE = Path(__file__).resolve().parent
PROJECT = EXAMPLE.parents[1]
KEYS = PROJECT / ".tools/local-comparison-ssh"
THREADS = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "MPLBACKEND": "Agg",
}


def resolve_inputs(value, base):
    if isinstance(value, list):
        return [resolve_inputs(item, base) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: resolve_inputs(item, base) for key, item in value.items()}
    if result.get("class", result.get("type")) in ("File", "Directory"):
        result["class"] = result.pop("type", result.get("class"))
        for key in ("path", "location"):
            if key in result:
                path = Path(result[key])
                path = (base / path).resolve() if not path.is_absolute() else path
                if not path.exists():
                    raise FileNotFoundError(path)
                result[key] = str(path)
    return result


def prepare(directory, locations, workflow, settings, ssh_port, base_port):
    from streamflow.config.validator import SfValidator

    yaml = YAML()
    inputs = resolve_inputs(yaml.load(settings), settings.parent)
    if directory.exists():
        raise FileExistsError(f"Use a fresh directory: {directory}")
    for program in ("sshd", "ssh", "ssh-keygen", "node", "gawk", "tar"):
        if not shutil.which(program):
            raise RuntimeError(f"Missing executable: {program}")
    KEYS.mkdir(parents=True, exist_ok=True, mode=0o700)
    KEYS.chmod(0o700)
    for name in ("host", "client"):
        key = KEYS / name
        if not key.exists():
            subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                check=True,
            )
    directory.mkdir(parents=True)
    names = [f"worker{i:02}" for i in range(locations)]
    outer = names[:10] if locations == 20 else names
    inner = names[10:] if locations == 20 else names
    bindings = [
        {"step": "/", "target": {"deployment": names[0]}},
        {"step": "/chromosome", "target": [{"deployment": n} for n in outer]},
        {
            "step": "/chromosome/individuals",
            "target": [{"deployment": n} for n in inner],
        },
    ]
    input_file = directory / "inputs.yml"
    with input_file.open("w") as stream:
        yaml.dump(inputs, stream)
    environment = {
        **THREADS,
        "PATH": str(Path(sys.executable).parent) + ":" + os.environ["PATH"],
        "SWIRLC_PYTHON": sys.executable,
    }
    for engine in ("swirl", "streamflow"):
        engine_dir = directory / engine
        engine_dir.mkdir()
        deployments = {}
        for i, name in enumerate(names):
            scratch = engine_dir / "scratch" / name
            scratch.mkdir(parents=True)
            if engine == "swirl":
                deployments[name] = {
                    "type": "local",
                    "config": {},
                    "port": base_port + i,
                    "workdir": str(engine_dir / "workers" / name),
                    "environment": {**environment, "SWIRLC_TMP_DIR": str(scratch)},
                }
            else:
                deployments[name] = {
                    "type": "ssh",
                    "workdir": str(scratch),
                    "config": {
                        "nodes": [f"127.0.0.1:{ssh_port}"],
                        "username": getpass.getuser(),
                        "sshKey": str(KEYS / "client"),
                        "checkHostKey": False,
                        "sharedPaths": [],
                        "services": {"worker": str(engine_dir / "command.sh")},
                    },
                }
        engine_bindings = copy.deepcopy(bindings)
        if engine == "streamflow":
            for binding in engine_bindings:
                binding["filters"] = ["shuffle"]
                targets = binding["target"]
                for target in targets if isinstance(targets, list) else [targets]:
                    target["service"] = "worker"
            exports = "\n".join(
                f"export {key}={shlex.quote(value)}"
                for key, value in environment.items()
                if not key.startswith("SWIRLC_")
            )
            (engine_dir / "command.sh").write_text(
                "#!/bin/sh\n" + exports + "\n{{streamflow_command}}\n"
            )
        config = {
            "version": "v1.0",
            "workflows": {
                "genome": {
                    "type": "cwl",
                    "config": {"file": str(workflow), "settings": str(input_file)},
                    "bindings": engine_bindings,
                }
            },
            "deployments": deployments,
        }
        if engine == "streamflow":
            config["bindingFilters"] = {"shuffle": {"type": "shuffle", "config": {}}}
            config["database"] = {
                "type": "sqlite",
                "config": {"connection": str(engine_dir / "streamflow.sqlite")},
            }
            SfValidator().validate(config)
        config_path = engine_dir / "streamflow.yml"
        with config_path.open("w") as stream:
            yaml.dump(config, stream)
        if engine == "swirl":
            with (engine_dir / "prepare.log").open("w") as log:
                for command in (
                    [
                        "translate",
                        "--language",
                        "cwl",
                        str(config_path),
                        "--outdir",
                        str(engine_dir),
                    ],
                    [
                        "compile",
                        str(engine_dir / "workflow.swirl"),
                        str(engine_dir / "metadata.yml"),
                        "--outdir",
                        str(engine_dir),
                        "--tmpdir",
                        str(engine_dir / "scratch"),
                        "--bundle-dependencies",
                    ],
                ):
                    subprocess.run(
                        [sys.executable, "-m", "swirlc", *command],
                        cwd=PROJECT,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
    ssh_config = directory / "sshd.conf"
    ssh_config.write_text(f"""ListenAddress 127.0.0.1
Port {ssh_port}
HostKey {KEYS / 'host'}
AuthorizedKeysFile {KEYS / 'client.pub'}
# The checkout may be under /tmp; keys remain in a private 0700 directory.
StrictModes no
PidFile {directory / 'sshd.pid'}
AllowUsers {getpass.getuser()}
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM no
DisableForwarding yes
MaxSessions 128
MaxStartups 100:30:200
Subsystem sftp internal-sftp
""")
    subprocess.run([shutil.which("sshd"), "-t", "-f", str(ssh_config)], check=True)
    (directory / "setup.json").write_text(
        json.dumps(
            {"locations": locations, "ssh_port": ssh_port, "python": sys.executable},
            indent=2,
        )
        + "\n"
    )
    print(f"Prepared {locations} logical workers for each engine: {directory}")


def run(directory, engine):
    with (directory / "comparison.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (KEYS / "run.lock").open("a") as host_lock:
            fcntl.flock(host_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return run_engine(directory, engine)


def stop_workers(engine_dir):
    """Tools can start their own sessions, so a launcher process-group kill is insufficient."""
    import psutil

    workers = []
    prefix = str(engine_dir) + os.sep
    for process in psutil.process_iter(["pid", "cmdline", "status"]):
        if process.pid == os.getpid():
            continue
        try:
            cwd = process.cwd()
            if process.info["status"] != psutil.STATUS_ZOMBIE and (
                cwd == str(engine_dir)
                or cwd.startswith(prefix)
                or any(arg.startswith(prefix) for arg in process.info["cmdline"] or [])
            ):
                process.suspend()
                workers.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for process in workers:
        try:
            process.terminate()
            process.resume()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(workers, timeout=3)
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass


def run_engine(directory, engine):
    setup = json.loads((directory / "setup.json").read_text())
    engine_dir = directory / engine
    result = engine_dir / "result.json"
    # Every invocation uses freshly prepared scratch; preserve earlier results.
    with result.open("x") as stream:
        json.dump({"status": "STARTING"}, stream)
    environment = {
        **os.environ,
        **THREADS,
        "PATH": str(Path(setup["python"]).parent) + ":" + os.environ["PATH"],
    }
    daemon = None
    started = None
    record = {"status": "FAILED", "error": "Launcher exited before completion"}
    try:
        if engine == "streamflow":
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", setup["ssh_port"]))
            with (engine_dir / "sshd.log").open("w") as log:
                daemon = subprocess.Popen(
                    [
                        shutil.which("sshd"),
                        "-D",
                        "-e",
                        "-f",
                        str(directory / "sshd.conf"),
                    ],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            for _ in range(50):
                if daemon.poll() is not None:
                    raise RuntimeError(
                        f"Local sshd exited; see {engine_dir / 'sshd.log'}"
                    )
                try:
                    with socket.create_connection(
                        ("127.0.0.1", setup["ssh_port"]), timeout=0.2
                    ):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise TimeoutError("Local SSH server did not become ready")
            subprocess.run(
                [
                    "ssh",
                    "-p",
                    str(setup["ssh_port"]),
                    "-i",
                    str(KEYS / "client"),
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "127.0.0.1",
                    "true",
                ],
                check=True,
            )
            command = [
                setup["python"],
                "-m",
                "streamflow",
                "run",
                "--outdir",
                str(engine_dir / "outputs"),
                str(engine_dir / "streamflow.yml"),
            ]
        else:
            command = ["bash", "run.sh"]
        started = time.monotonic()
        with (engine_dir / "workflow.log").open("w") as log:
            completed = subprocess.run(
                command,
                cwd=engine_dir,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        record = {
            "status": "COMPLETED" if completed.returncode == 0 else "FAILED",
            "exit_code": completed.returncode,
            "execution_seconds": time.monotonic() - started,
        }
    except BaseException as exc:
        record = {
            "status": "CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAILED",
            "error": str(exc),
            "execution_seconds": (
                time.monotonic() - started if started is not None else None
            ),
        }
        raise
    finally:
        if record["status"] != "COMPLETED":
            stop_workers(engine_dir)
        if daemon is not None:
            daemon.terminate()
            daemon.wait(timeout=10)
        result.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
    return completed.returncode


def benchmark(
    directory,
    locations,
    repetitions,
    workflow,
    settings,
    ssh_port,
    base_port,
    prepare_only=False,
):
    """Run fresh, sequential repetitions and retain a single timing table."""
    from importlib.metadata import version

    directory.mkdir(parents=True, exist_ok=False)
    record = {
        "status": "PREPARING",
        "pid": os.getpid(),
        "locations": locations,
        "settings": str(settings),
        "repetitions": repetitions,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "versions": {
            name: version(name)
            for name in ("swirlc", "streamflow", "numpy", "matplotlib")
        },
    }

    def save():
        temporary = directory / "sequence.json.tmp"
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(directory / "sequence.json")

    save()
    print(f"Benchmark results: {directory}", flush=True)
    try:
        with (directory / "results.csv").open("x", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "repetition",
                    "engine",
                    "status",
                    "execution_seconds",
                    "exit_code",
                    "directory",
                ],
            )
            writer.writeheader()
            stream.flush()
            for repetition in range(1, repetitions + 1):
                run_dir = directory / f"run-{repetition:02}"
                record.update(
                    status="PREPARING", repetition=repetition, current_engine=None
                )
                save()
                prepare(run_dir, locations, workflow, settings, ssh_port, base_port)
                if prepare_only:
                    continue
                for engine in ("swirl", "streamflow"):
                    record.update(status="RUNNING", current_engine=engine)
                    save()
                    print(
                        f"Repetition {repetition}/{repetitions}: {engine}", flush=True
                    )
                    try:
                        code = run(run_dir, engine)
                    finally:
                        result_path = run_dir / engine / "result.json"
                        if result_path.exists():
                            result = json.loads(result_path.read_text())
                            writer.writerow(
                                {
                                    "repetition": repetition,
                                    "engine": engine,
                                    **{
                                        key: result.get(key, "")
                                        for key in (
                                            "status",
                                            "execution_seconds",
                                            "exit_code",
                                        )
                                    },
                                    "directory": str(run_dir / engine),
                                }
                            )
                            stream.flush()
                            os.fsync(stream.fileno())
                    if code:
                        raise RuntimeError(
                            f"{engine} failed; see {run_dir / engine / 'workflow.log'}"
                        )
        record["status"] = "PREPARED" if prepare_only else "COMPLETED"
    except BaseException as exc:
        record.update(
            status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAILED",
            error=str(exc),
        )
        raise
    finally:
        record["ended_utc"] = datetime.now(timezone.utc).isoformat()
        save()


def interrupt_run(signum, frame):
    raise KeyboardInterrupt("Stopped by signal")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--locations", type=int, choices=(1, 2, 5, 10, 20), default=20)
    prep.add_argument("--workflow", type=Path, default=EXAMPLE / "main.cwl")
    prep.add_argument("--settings", type=Path, default=EXAMPLE / "config.yml")
    prep.add_argument("--ssh-port", type=int, default=22222)
    prep.add_argument("--base-port", type=int, default=28500)
    bench = commands.add_parser("benchmark")
    bench.add_argument("--locations", type=int, choices=(1, 2, 5, 10, 20), default=10)
    bench.add_argument("--repetitions", type=int, default=1)
    bench.add_argument("--workflow", type=Path, default=EXAMPLE / "main.cwl")
    bench.add_argument("--settings", type=Path, default=EXAMPLE / "config-1chr.yml")
    bench.add_argument(
        "--directory",
        type=Path,
        default=PROJECT
        / "runs/1000genome/local"
        / datetime.now(timezone.utc).strftime("benchmark-%Y%m%dT%H%M%S%fZ"),
    )
    bench.add_argument("--prepare-only", action="store_true")
    bench.add_argument("--ssh-port", type=int, default=22222)
    bench.add_argument("--base-port", type=int, default=28500)
    execute = commands.add_parser("run")
    execute.add_argument("engine", choices=("swirl", "streamflow"))
    for command in (prep, execute):
        command.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.command in ("prepare", "benchmark"):
        if (
            not 1024 <= args.ssh_port <= 65535
            or not 1024 <= args.base_port <= 65536 - args.locations
        ):
            parser.error("Ports must be unprivileged and fit within 1024..65535")
        if args.command == "benchmark":
            if args.repetitions < 1:
                parser.error("Repetitions must be positive")
            benchmark(
                args.directory.resolve(),
                args.locations,
                args.repetitions,
                args.workflow.resolve(),
                args.settings.resolve(),
                args.ssh_port,
                args.base_port,
                args.prepare_only,
            )
            return 0
        prepare(
            args.directory.resolve(),
            args.locations,
            args.workflow.resolve(),
            args.settings.resolve(),
            args.ssh_port,
            args.base_port,
        )
        return 0
    return run(args.directory.resolve(), args.engine)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupt_run)
    raise SystemExit(main())
