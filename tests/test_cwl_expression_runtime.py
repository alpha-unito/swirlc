from __future__ import annotations

import base64
import io
import subprocess
import zipfile
from pathlib import Path

import pytest

from swirlc.compiler.default.compiler import (
    _build_dependency_archive,
    _parallel_shell_block,
    _start_background_shell_commands,
)
from swirlc.core.deployment import (
    Deployment,
    DockerDeployment,
    SlurmDeployment,
    SshDeployment,
)
from swirlc.main import main


def test_expression_tool_uses_self_bootstrapping_javascript_runtime(
    tmp_path: Path,
) -> None:
    example = Path(__file__).parent.parent / "examples" / "cwl" / "expressions"

    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(example / "streamflow.yml"),
                "--outdir",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "compile",
                str(tmp_path / "workflow.swirl"),
                str(tmp_path / "metadata.yml"),
                "--outdir",
                str(tmp_path),
            ]
        )
        == 0
    )

    trace = (tmp_path / "l0.py").read_text()
    assert "import js2py_ as js2py" in trace
    assert "js2py.eval_js(invocation)" in trace
    assert "function weightedScore(items, multiplier)" in trace
    assert '_expression(\n            "evaluate",' in trace
    assert "def _expression_s0(inputs):" not in trace

    requirements = (tmp_path / "l0.requirements.txt").read_text()
    assert 'Js2Py==0.74; python_version < "3.13"' in requirements
    assert 'Js2Py-3.14==0.74.2; python_version >= "3.13"' in requirements
    assert "pyjsparser==2.7.1" in requirements
    assert "six==1.17.0" in requirements
    assert "tzlocal==5.4.4" in requirements

    launcher = (tmp_path / "l0.launch.sh").read_text()
    assert 'python" -m pip install' in launcher
    assert 'exec "$VENV_DIR/bin/python" l0.py' in launcher

    run_script = (tmp_path / "run.sh").read_text()
    assert "./l0.launch.sh --prepare" in run_script
    assert "./l0.launch.sh --run-id $SWIRLC_RUN_ID" in run_script
    assert "Workflow execution started" in run_script
    assert "wait_workflow_processes" not in run_script


def test_runtime_setup_runs_inside_each_deployment() -> None:
    command = "./l0.launch.sh --prepare"

    assert (
        Deployment(workdir="/work").get_setup_command(command, "l0")
        == "cd /work && ./l0.launch.sh --prepare"
    )
    assert SshDeployment(hostname="remote", workdir="/work").get_setup_command(
        command, "l0"
    ) == ('ssh remote "cd /work && ./l0.launch.sh --prepare"')
    assert DockerDeployment(hostname="container", workdir="/work").get_setup_command(
        command, "l0"
    ) == ('docker exec --workdir /work container sh -c "./l0.launch.sh --prepare"')
    assert SlurmDeployment(hostname="login", workdir="/shared").get_setup_command(
        command, "l0"
    ) == ('ssh login "cd /shared && ./l0.launch.sh --prepare"')
    assert SlurmDeployment(hostname="localhost", workdir="/shared").get_setup_command(
        command, "l0"
    ) == ("cd /shared && ./l0.launch.sh --prepare")
    slurm_command = SlurmDeployment(hostname="login", workdir="/shared").get_command(
        "./l0.launch.sh", "l0"
    )
    assert "sbatch --export=ALL,SWIRLC_RUN_ID l0.sbatch" in slurm_command
    assert "--wait" not in slurm_command


def test_compile_can_embed_runtime_dependencies(tmp_path: Path) -> None:
    example = Path(__file__).parent.parent / "examples" / "cwl" / "expressions"
    translated = tmp_path / "translated"
    bundled = tmp_path / "bundled"
    translated.mkdir()
    bundled.mkdir()

    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(example / "streamflow.yml"),
                "--outdir",
                str(translated),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "compile",
                str(translated / "workflow.swirl"),
                str(translated / "metadata.yml"),
                "--outdir",
                str(bundled),
                "--bundle-dependencies",
            ]
        )
        == 0
    )

    trace = (bundled / "l0.py").read_text()
    assert "_BUNDLED_DEPENDENCIES_B85" in trace
    assert "_activate_bundled_dependencies()" in trace
    assert "js2py.eval_js(invocation)" in trace
    assert (bundled / "l0.requirements.txt").read_text() == ""

    launcher = (bundled / "l0.launch.sh").read_text()
    assert 'exec "$PYTHON_BIN" l0.py "$@"' in launcher


def test_dependency_archive_includes_transitive_pure_python_packages() -> None:
    payload, _digest = _build_dependency_archive(("Js2Py-3.14",))
    with zipfile.ZipFile(io.BytesIO(base64.b85decode(payload))) as archive:
        names = set(archive.namelist())

    assert any(name.startswith("js2py_/") for name in names)
    assert any(name.startswith("pyjsparser/") for name in names)
    assert "six.py" in names
    assert any(name.startswith("tzlocal/") for name in names)


def test_dependency_archive_rejects_native_extensions() -> None:
    with pytest.raises(RuntimeError, match="compiled native extension"):
        _build_dependency_archive(("rpds-py",))


def test_auxiliary_wait_does_not_reap_workflow_process() -> None:
    auxiliary_block = _parallel_shell_block(["true", "true"])
    script = f"""
sleep 0.2 &
workflow_pid=$!
{auxiliary_block}
wait "$workflow_pid"
"""

    result = subprocess.run(
        ["sh", "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_workflow_pids_are_captured_as_direct_children() -> None:
    commands = _start_background_shell_commands(["sleep 0.1"], "WORKFLOW_PIDS")
    script = f"""
{commands}
wait "$WORKFLOW_PIDS"
"""

    result = subprocess.run(
        ["sh", "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "jobs -p" not in commands
