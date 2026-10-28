from __future__ import annotations

import ast
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from swirlc.compiler.default import compiler

from swirlc.compiler.default.compiler import (
    _build_dependency_archive,
    _embedded_dependency_bootstrap,
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
from tests.test_pipeline_contract import generated_execs


@pytest.mark.parametrize("scattered", [False, True])
@pytest.mark.parametrize("nested", [False, True])
def test_subworkflow_valuefrom_uses_original_step_inputs(tmp_path, scattered, nested):
    child = {
        "class": "Workflow", "inputs": {"a": "int", "b": "int"},
        "outputs": {"result": {"type": "int", "outputSource": "echo/result"},
                    "unused": {"type": "int", "outputSource": "echo/result"}},
        "steps": {"echo": {"in": {"a": "a", "b": "b"}, "out": ["result"],
                            "run": {"class": "ExpressionTool", "inputs": {"a": "int", "b": "int"},
                                    "outputs": {"result": "int"},
                                    "expression": "${ return {result: inputs.a * 10 + inputs.b}; }"}}},
    }
    step = {"run": child, "in": {"x": "x", "a": {"source": "x", "valueFrom": "$(self.n + 1)"},
                                    "b": {"valueFrom": "$(inputs.a.n + 2)"}}, "out": ["result"]}
    if nested:
        child["inputs"]["a"] = "int[]"
        for output in child["outputs"].values():
            output["type"] = "int[]"
        child["steps"]["echo"]["scatter"] = "a"
        step["in"]["a"]["valueFrom"] = "$([self.n + 1, self.n + 2])"
    if scattered:
        step["scatter"] = ["x", "a"]
        step["scatterMethod"] = "dotproduct"
    workflow = {
        "cwlVersion": "v1.2", "class": "Workflow",
        "requirements": {"InlineJavascriptRequirement": {}, "StepInputExpressionRequirement": {},
                         "SubworkflowFeatureRequirement": {}, "ScatterFeatureRequirement": {}},
        "inputs": {"x": {"type": {"type": "array", "items": {"type": "record", "name": "Item", "fields": {"n": "int"}}} if scattered
                         else {"type": "record", "name": "Item", "fields": {"n": "int"}},
                         "default": [{"n": 1}, {"n": 3}] if scattered else {"n": 1}}},
        "outputs": {"result": {"type": "int" + "[]" * (int(scattered) + int(nested)), "outputSource": "child/result"}},
        "steps": {"child": step},
    }
    yaml = YAML()
    with (tmp_path / "main.cwl").open("w") as stream:
        yaml.dump(workflow, stream)
    with (tmp_path / "streamflow.yml").open("w") as stream:
        yaml.dump({"version": "v1.0", "deployments": {"local": {"type": "local", "port": 0}},
                   "workflows": {"test": {"type": "cwl", "config": {"file": "main.cwl"},
                                          "bindings": [{"step": "/", "target": {"deployment": "local"}}]}}}, stream)
    assert main(["translate", "-l", "cwl", str(tmp_path / "streamflow.yml"), "-o", str(tmp_path)]) == 0
    assert main(["compile", str(tmp_path / "workflow.swirl"), str(tmp_path / "metadata.yml"),
                 "--bundle-dependencies", "-o", str(tmp_path)]) == 0
    run = subprocess.run(["bash", "run.sh"], cwd=tmp_path, timeout=30,
        env=dict(os.environ, SWIRLC_PYTHON=sys.executable, SWIRLC_RUNTIME_TIMEOUT="10",
                 SWIRLC_TMP_DIR=str(tmp_path / "scratch"), PIP_NO_INDEX="1",
                 PIP_DISABLE_PIP_VERSION_CHECK="1"), capture_output=True, text=True)
    assert run.returncode == 0, (run.stdout, run.stderr)
    outputs = json.loads((tmp_path / "l0.outputs.json").read_text())
    values = [record["payload"] for record in outputs if record["id"] == []]
    expected = ([23, 33], [45, 55]) if nested else (23, 45)
    assert (list(expected) if scattered else expected[0]) in values


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
    program = ast.parse(trace)
    metadata = ast.literal_eval(next(
        node.value for node in program.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "METADATA" for target in node.targets)
    ))
    assert "function weightedScore(items, multiplier)" in metadata["steps"]["s_evaluate_0"]["expression"]["source"]
    assert "'displayName': 'evaluate'" in trace
    execs = generated_execs(tmp_path / "l0.py")
    assert len(execs) == 1 and execs[0]["tool"] == "s_evaluate_0"
    assert {port for port, _ in execs[0]["inputs"]} == {
        "p_sample", "p_multiplier", "p_threshold",
    }
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

    assert main([
        "compile", str(tmp_path / "workflow.swirl"), str(tmp_path / "metadata.yml"),
        "--bundle-dependencies", "--outdir", str(tmp_path),
    ]) == 0
    subprocess.run(
        ["bash", "run.sh"], cwd=tmp_path, check=True, timeout=30,
        env=dict(os.environ, SWIRLC_PYTHON=sys.executable, SWIRLC_RUNTIME_TIMEOUT="10",
                 PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1"),
        capture_output=True,
    )
    actual = {
        record["port"]: record["payload"]
        for record in json.loads((tmp_path / "l0.outputs.json").read_text())
        if record["port"].startswith("p_evaluate_") and record["id"] == []
    }
    assert actual == {
        "p_evaluate_prefix": "alpha", "p_evaluate_score": 12,
        "p_evaluate_accepted": True, "p_evaluate_words": ["alpha", "beta", "gamma"],
    }


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


def test_bundled_dependency_bootstrap_concurrent_startup(tmp_path: Path) -> None:
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("bootstrap_probe.py", "VALUE = 'available'\n")
    archive_bytes = archive_buffer.getvalue()
    digest = hashlib.sha256(archive_bytes).hexdigest()
    bootstrap = _embedded_dependency_bootstrap(
        base64.b85encode(archive_bytes).decode("ascii"), digest,
    )
    # Both writers stop after writing their temporary archive. A shared .tmp
    # name would then deterministically leave one writer without a file to rename.
    barrier = """
import base64, hashlib, os, sys, time
from pathlib import Path
write_bytes = Path.write_bytes
def synchronized_write(path, data):
    result = write_bytes(path, data)
    if path.suffix == '.tmp':
        write_bytes(Path(__file__).with_name(f'ready.{os.getpid()}'), b'ready')
        deadline = time.monotonic() + 5
        while len(list(Path(__file__).parent.glob('ready.*'))) < 2:
            if time.monotonic() > deadline:
                raise TimeoutError('dependency bootstrap barrier')
            time.sleep(.01)
    return result
Path.write_bytes = synchronized_write
"""
    scripts = [tmp_path / f"location_{index}.py" for index in range(2)]
    for script in scripts:
        script.write_text(barrier + bootstrap + "\nfrom bootstrap_probe import VALUE\nassert VALUE == 'available'\n")
    processes = [subprocess.Popen([sys.executable, str(script)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for script in scripts]
    try:
        for process in processes:
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 0, (stdout, stderr)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=2)
    assert (tmp_path / f".swirlc-dependencies-{digest}.zip").read_bytes() == archive_bytes


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


@pytest.mark.parametrize("source, expected", [
    ("return ['marker'.includes('ark'), 'marker'.includes('absent'), 'marker'.includes('m', 1)];", [True, False, False]),
    ("return [Number.isInteger(0), Number.isInteger(-2), Number.isInteger(1.5), Number.isInteger('1'), Number.isInteger(null), Number.isInteger(true), Number.isInteger(Infinity)];", [True, True, False, False, False, False, False]),
    ("return [[1, [2, [3]]].flat(), [1, [2, [3]]].flat(0), [1, [2, [3]]].flat(2)];", [[1, 2, [3]], [1, [2, [3]]], [1, 2, 3]]),
    ("return {items: [{file: {class: 'File', contents: 'text'}, value: null}], zero: 0, empty: '', flag: false};", {"items": [{"file": {"class": "File", "contents": "text"}, "value": None}], "zero": 0, "empty": "", "flag": False}),
])
def test_fixture_javascript_shims_preserve_types(source, expected):
    namespace = {}
    exec(compiler.imports, namespace)
    exec(compiler.list_helper, namespace)
    exec(compiler.expression_function, namespace)
    assert namespace["_run_javascript_expression"](source, {}) == expected


@pytest.mark.parametrize("enabled, status", [(False, 1), (True, 1), (False, 0), (False, 2)])
def test_missing_features_unchanged_workflow(tmp_path, enabled, status):
    example = Path(__file__).parent.parent / "examples/cwl/missing-features"
    assert main(["translate", "-l", "cwl", str(example / "streamflow.yml"), "-o", str(tmp_path)]) == 0
    yaml = YAML(typ="safe")
    metadata_path = tmp_path / "metadata.yml"
    metadata = yaml.load(metadata_path.read_text())
    metadata["dependencies"]["d_enabled"]["value"] = enabled
    metadata["dependencies"]["d_status"]["value"] = status
    for location in metadata["locations"].values():
        location["deployment"]["port"] = 0
    with metadata_path.open("w") as stream:
        yaml.dump(metadata, stream)
    assert main(["compile", str(tmp_path / "workflow.swirl"), str(metadata_path),
                 "--bundle-dependencies", "-o", str(tmp_path)]) == 0
    run = subprocess.run(["bash", "run.sh"], cwd=tmp_path, timeout=30,
        env=dict(os.environ, SWIRLC_PYTHON=sys.executable, SWIRLC_RUNTIME_TIMEOUT="10",
                 SWIRLC_TMP_DIR=str(tmp_path / "scratch"), PIP_NO_INDEX="1",
                 PIP_DISABLE_PIP_VERSION_CHECK="1"), capture_output=True, text=True)
    if status == 2:
        assert run.returncode != 0, (run.stdout, run.stderr)
        assert "exit status 2" in run.stdout + run.stderr
        return
    assert run.returncode == 0, (run.stdout, run.stderr)
    records = json.loads((tmp_path / "l0.outputs.json").read_text())
    values = {record["port"]: record["payload"] for record in records if record["id"] == []}
    result = {}
    for step in metadata["steps"].values():
        for name, port in step.get("outputNames", {}).items():
            if name in ("report", "code", "ok"):
                result[name] = values[port]
    assert result["ok"] is True and result["code"] == status
    report = json.loads(Path(result["report"]["path"]).read_text())
    assert report == {"text": "one:seed", "meta": "meta",
                      "messages": ["generated"] * (2 if enabled else 1), "marker": "expected"}
    if not enabled and status == 1:
        manifest = tmp_path / "result.json"
        manifest.write_text(json.dumps(result))
        check = subprocess.run([sys.executable, str(example / "check.py"), str(manifest)],
                               check=True, capture_output=True, text=True, timeout=5)
        assert check.stdout.strip() == "PASS"


@pytest.mark.parametrize("guard, expected", [
    (None, "2"),
    ("$(inputs.x === 2)", "3"),
    ("$(inputs.x === 0)", None),
    ("$(inputs.x)", "invalid"),
])
def test_when_choice_prepares_inputs_once_and_skips_command(tmp_path, guard, expected):
    marker = tmp_path / "command-ran"
    workflow = {
        "cwlVersion": "v1.2", "class": "Workflow",
        "requirements": {"InlineJavascriptRequirement": {}, "StepInputExpressionRequirement": {}},
        "inputs": {"x": {"type": "int", "default": 1}},
        "outputs": {"value": {"type": ["null", "string"], "outputSource": "choose/value"}},
        "steps": {"choose": {
            "in": {"x": {"source": "x", "valueFrom": "$(self + 1)"}},
            "when": guard, "out": ["value"],
            "run": {"class": "CommandLineTool", "baseCommand": ["sh", "-c"],
                    "arguments": [f'touch "{marker}"; printf "%s" "$1"', "command"],
                    "inputs": {"x": {"type": "int", "inputBinding": {
                        "position": 1, "valueFrom": "$(self + 1)"}}},
                    "stdout": "value.txt", "outputs": {"value": {"type": "string", "outputBinding": {
                        "glob": "value.txt", "loadContents": True,
                        "outputEval": "$(self[0].contents)"}}}}}},
    }
    if guard is None:
        step = workflow["steps"]["choose"]
        step.pop("when")
        step["in"] = {"seed": "x", "x": {"valueFrom": "$(inputs.seed + 1)"}}
        step["run"]["inputs"]["x"]["inputBinding"].pop("valueFrom")
    yaml = YAML()
    with (tmp_path / "main.cwl").open("w") as stream:
        yaml.dump(workflow, stream)
    with (tmp_path / "streamflow.yml").open("w") as stream:
        yaml.dump({"version": "v1.0", "deployments": {"local": {"type": "local", "port": 0}},
                   "workflows": {"test": {"type": "cwl", "config": {"file": "main.cwl"},
                                          "bindings": [{"step": "/", "target": {"deployment": "local"}}]}}}, stream)
    assert main(["translate", "-l", "cwl", str(tmp_path / "streamflow.yml"), "-o", str(tmp_path)]) == 0
    metadata = YAML(typ="safe").load((tmp_path / "metadata.yml").read_text())
    assert ("+[" in (tmp_path / "workflow.swirl").read_text()) == (guard is not None)
    assert all("when" not in step for step in metadata["steps"].values())
    assert main(["compile", str(tmp_path / "workflow.swirl"), str(tmp_path / "metadata.yml"),
                 "--bundle-dependencies", "-o", str(tmp_path)]) == 0
    run = subprocess.run(["bash", "run.sh"], cwd=tmp_path, timeout=30,
        env=dict(os.environ, SWIRLC_PYTHON=sys.executable, SWIRLC_RUNTIME_TIMEOUT="10",
                 SWIRLC_TMP_DIR=str(tmp_path / "scratch"), PIP_NO_INDEX="1",
                 PIP_DISABLE_PIP_VERSION_CHECK="1"), capture_output=True, text=True)
    if expected == "invalid":
        assert run.returncode != 0, (run.stdout, run.stderr)
        assert "boolean" in run.stdout + run.stderr
        assert not marker.exists()
        return
    assert run.returncode == 0, (run.stdout, run.stderr)
    assert marker.exists() == (expected is not None)
    outputs = json.loads((tmp_path / "l0.outputs.json").read_text())
    assert [record["payload"] for record in outputs
            if record["port"] == "p_choose_value" and record["id"] == []] == [expected]
