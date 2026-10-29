import os
import subprocess
import time
from threading import BoundedSemaphore, Timer
from types import SimpleNamespace

import pytest

from swirlc.compiler.default.compiler import SCOPED_MAIN


def test_command_preserves_stdout_and_exit_status():
    namespace = {"__name__": "test", "os": os, "subprocess": subprocess,
                 "BoundedSemaphore": BoundedSemaphore}
    exec(SCOPED_MAIN, namespace)
    result = namespace["_run_command"]("printf preserved")
    assert result.returncode == 0
    assert result.stdout == b"preserved"


def test_scoped_failure_cancels_active_shell_and_child():
    namespace = {"__name__": "test", "os": os, "subprocess": subprocess,
                 "BoundedSemaphore": BoundedSemaphore}
    exec(SCOPED_MAIN, namespace)
    runtime = SimpleNamespace(error=None)
    namespace["ACTIVE_RUNTIME"] = runtime
    failure = Timer(.2, lambda: setattr(runtime, "error", ValueError("failed sibling")))
    started = time.monotonic()
    failure.start()
    try:
        with pytest.raises(RuntimeError, match="failed sibling"):
            namespace["_run_command"]("sleep 30")
    finally:
        failure.cancel()
    assert time.monotonic() - started < 2


def test_selected_slurm_service_options_survive_generation(tmp_path):
    from swirlc.compiler.default.compiler import DefaultTarget
    from swirlc.core.entity import Location

    target = DefaultTarget(str(tmp_path))
    target._write_slurm_script(Location("worker", "worker", {}, slurm={
        "partition": "broadwell", "nodes": 2, "ntasks": 4, "time": "00:10:00"}))
    script = (tmp_path / "worker.sbatch").read_text()
    for option in ("partition=broadwell", "nodes=2", "ntasks=4", "time=00:10:00"):
        assert f"#SBATCH --{option}" in script


def test_generated_launcher_reports_location_failure(tmp_path):
    import signal
    from pathlib import Path

    from ruamel.yaml import YAML

    from swirlc.main import main

    root = Path(__file__).resolve().parents[1]
    example = root / "examples/cwl/pipeline/depth-0/plain/streamflow.yml"
    assert main(["translate", "-l", "cwl", str(example), "-o", str(tmp_path)]) == 0
    yaml = YAML(typ="safe")
    metadata_path = tmp_path / "metadata.yml"
    metadata = yaml.load(metadata_path.read_text())
    leaf = next(step for step in metadata["steps"].values() if step["displayName"] == "finish")
    leaf["command"] = "false"
    with metadata_path.open("w") as stream:
        yaml.dump(metadata, stream)
    assert main(["compile", str(tmp_path / "workflow.swirl"), str(metadata_path),
                 "-o", str(tmp_path), "--bundle-dependencies"]) == 0
    env = dict(os.environ, SWIRLC_PYTHON=str(root / ".venv/bin/python"),
               SWIRLC_RUNTIME_TIMEOUT="2", SWIRLC_ADDRESS_BOOK_TIMEOUT="2",
               SWIRLC_ADDRESS_GATHER_TIMEOUT="2")
    process = subprocess.Popen(["sh", "run.sh"], cwd=tmp_path, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, text=True)
    try:
        stdout, stderr = process.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        process.communicate(timeout=2)
        raise
    assert process.returncode != 0, (stdout, stderr)
    assert "failed with exit status 1" in stderr
    assert "Workflow execution terminated" not in stdout
