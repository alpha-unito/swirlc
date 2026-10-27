"""Plain and metadata CWL compiler acceptance; run directly with the installed project Python."""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import signal
import subprocess
import uuid
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from swirlc.config.validator import SwirlValidator

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"


def run_command(arguments, log, *, cwd=ROOT, timeout=60):
    scratch = log.parent / "scratch" / uuid.uuid4().hex
    if log.name == "execution.log":
        (log.parent / "execution-scratch.txt").write_text(str(scratch) + "\n")
    env = dict(os.environ, SWIRLC_PYTHON=str(PYTHON),
               SWIRLC_RUNTIME_TIMEOUT="20", SWIRLC_ADDRESS_BOOK_TIMEOUT="20",
               SWIRLC_ADDRESS_GATHER_TIMEOUT="20",
               SWIRLC_TMP_DIR=str(scratch), PIP_NO_INDEX="1",
               PIP_DISABLE_PIP_VERSION_CHECK="1")
    with log.open("w") as stream:
        process = subprocess.Popen(arguments, cwd=cwd, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
            raise AssertionError(f"Timed out: {arguments}; inspect {log}")
    text = log.read_text()
    assert code == 0, f"Exit {code}: {arguments}; inspect {log}\n{text}"
    assert not re.search(r"Traceback|ERROR|Exception:|line \d+:\d+", text), text
    return text


def inspect_translation(directory, depth, variant="plain"):
    source = (directory / "workflow.swirl").read_text()
    metadata = SwirlValidator().validate_file(str(directory / "metadata.yml"))
    execs = re.findall(r"\bexec\((\w+),", source)
    assert len(execs) == len(set(execs)), "Exec templates share a descriptor"
    assert set(execs) == set(metadata["steps"]), "Missing or unused tool descriptor"
    assert len(metadata["locations"]) == (depth + 1 if depth else 3)
    ports = [value["deployment"]["port"] for value in metadata["locations"].values()]
    assert len(ports) == len(set(ports)), "Locations lost distinct placement"
    for step in metadata["steps"].values():
        for route in step.get("routes", []):
            locations = ([route["controller"], *route["workers"], *route["producers"].values()]
                         if "controller" in route else [route["source"], route["receiver"]])
            assert all(location in metadata["locations"] for location in locations)
    assert "scatterRegions" not in metadata
    assert len({step["operationId"] for step in metadata["steps"].values()
                if step.get("type") == "scatter_dispatch"}) == depth
    if variant == "metadata":
        tools = [step for step in metadata["steps"].values() if "command" in step]
        assert tools
        for step in tools:
            assert step["bindings"]["inputs"]["object"]
            assert {binding["port"] for binding in step["bindings"]["inputs"]["object"].values()} <= set(step["inputs"])
            assert step["stdout"] == "result.txt"
            for output in step["outputs"].values():
                processor = output.get("processor", output)
                assert processor["readContents"] is True
                assert processor["evaluate"]["language"] == "javascript"
                assert "self[0].contents.trim()" in processor["evaluate"]["source"]
                assert processor["evaluate"]["bindings"] == {"self": {"context": "matchedFiles"}}
        render = [step for step in tools if "sample" in step["bindings"]["inputs"]["object"]]
        assert render
        for step in render:
            expressions = [argument["expression"] for argument in step["arguments"] if "expression" in argument]
            assert all(expression["language"] == "javascript" for expression in expressions)
            assert '"item=%s\\n"' in expressions[0]["source"]
            assert "nameroot" in expressions[1]["source"]
            if "self.nameroot" in expressions[1]["source"]:
                assert expressions[1]["bindings"] == {"self": step["bindings"]["inputs"]["object"]["sample"]}
    return metadata


def terminal_ports(example, metadata):
    """Resolve declared CWL aliases to emitted boundary helpers or ordinary tools."""
    workflow = YAML(typ="safe").load((example / "main.cwl").read_text())
    result = {}
    for output, declaration in workflow["outputs"].items():
        source = declaration["outputSource"]
        path = "/" + source
        matches = []
        for step in metadata["steps"].values():
            if step.get("type") == "scatter_gather" and step["displayName"] == path + " ScatterGather":
                receivers = {route["receiver"] for route in step["routes"]}
                assert len(receivers) == 1
                matches += [(next(iter(receivers)), port) for port, descriptor in step["outputs"].items()
                            if descriptor.get("id") == "root"]
        if not matches:
            invocation, name = source.rsplit("/", 1)
            steps = [(tool, step) for tool, step in metadata["steps"].items()
                     if step["displayName"] == invocation]
            assert len(steps) == 1, (source, steps)
            tool, step = steps[0]
            matches = [(None, port) for port in step["outputs"]
                       if port.endswith("_" + name)]
        assert len(matches) == 1, (source, matches)
        result[output] = matches[0]
    return result


def file_path(value):
    """Accept the legacy path and typed File representations at this boundary."""
    if isinstance(value, dict):
        assert value.get("class") == "File", value
        assert isinstance(value.get("basename"), str), value
        value = value.get("path")
    assert isinstance(value, str) and Path(value).is_file(), value
    return Path(value)


def replace_files(value):
    if isinstance(value, list):
        return [replace_files(item) for item in value]
    text = file_path(value).read_text()
    return text[:-1] if text.endswith("\n") else text


def generated_execs(path):
    """Read direct operation calls without executing generated workflow code."""
    source = path.read_text()
    assert "cwl_utils" not in source
    assert "def _evaluate_cwl" not in source
    assert "def _command_tool" not in source
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.Name) and node.id == "TRACE" for node in ast.walk(tree))
    runtime_classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Runtime"]
    for runtime_class in runtime_classes:
        assert not {"_run", "_first", "_branches", "run"} & {
            node.name for node in runtime_class.body if isinstance(node, ast.FunctionDef)
        }, "Generated runtime still contains workflow interpretation"
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute)
             and isinstance(node.func.value, ast.Name) and node.func.value.id == "runtime"]
    assert not any(call.func.attr == "run" for call in calls)
    result = []
    for call in calls:
        if call.func.attr != "execute_step":
            continue
        keywords = {keyword.arg: keyword.value for keyword in call.keywords}
        def argument(name, index, call=call, keywords=keywords):
            return keywords[name] if name in keywords else call.args[index]
        def ports(name, index):
            return [(ast.literal_eval(pair.elts[0]), ast.unparse(pair.elts[1]))
                    for pair in argument(name, index).elts]
        result.append({"tool": ast.literal_eval(argument("tool", 1)),
                       "inputs": ports("inputs", 2), "outputs": ports("outputs", 3),
                       "mapping": ast.literal_eval(argument("mapping", 4))})
    return result


def verify_bundle(directory, metadata, outputs, expected, example, variant="plain"):
    manifests = {location: json.loads((directory / f"{location}.outputs.json").read_text())
                 for location in metadata["locations"]}
    actual = {}
    for name, (location, port) in outputs.items():
        records = [record for owner, records in manifests.items()
                   if location is None or owner == location
                   for record in records if record["port"] == port and record["id"] == []]
        assert len(records) == 1, (name, records)
        actual[name] = (replace_files(records[0]["payload"]) if variant == "plain"
                        else records[0]["payload"])
    assert actual == expected, (actual, expected)

    scratch = Path((directory / "execution-scratch.txt").read_text().strip())
    task_directories = []
    placements = {}
    configuration = YAML(typ="safe").load((example / "streamflow.yml").read_text())
    assert len(configuration["workflows"]) == 1
    bindings = next(iter(configuration["workflows"].values()))["bindings"]
    for location, records in manifests.items():
        execs = generated_execs(directory / f"{location}.py")
        for node in execs:
            tool = node["tool"]
            assert location in node["mapping"], (location, tool, node["mapping"])
            step = metadata["steps"][tool]
            assert set(step["inputs"]) == {port for port, _ in node["inputs"]}
            assert set(step["outputs"]) == {port for port, _ in node["outputs"]}
            if "command" not in step:
                continue
            binding = max((binding for binding in bindings
                           if binding["step"] == "/" or
                           tool.startswith("s_" + binding["step"].strip("/").replace("/", "_") + "_")),
                          key=lambda binding: len(binding["step"]))
            deployment = configuration["deployments"][binding["target"]["deployment"]]
            assert metadata["locations"][location]["deployment"]["port"] == deployment["port"]
            placements[tool] = location
            execution_ids = {tuple(record["id"]) for record in records
                             if record["port"] in step["outputs"]}
            directories = list(scratch.glob(f"exec_{tool}_*"))
            assert len(directories) == len(execution_ids), (tool, execution_ids, directories)
            assert all(path.is_dir() for path in directories)
            task_directories.extend(directories)
            for port in step["outputs"]:
                for record in records:
                    if record["port"] != port:
                        continue
                    if variant == "plain":
                        path = file_path(record["payload"])
                        assert path.is_file()
                        assert path.parent in directories, (tool, path, directories)
                    else:
                        assert isinstance(record["payload"], str)
    assert len(task_directories) == len(set(task_directories)), "Tasks share execution directories"
    assert len(placements) == sum("command" in step for step in metadata["steps"].values())
    return actual, placements, len(task_directories)


@pytest.mark.parametrize("name, base_port, first, shared, last", [
    ("depth-1-split-two-workers", 35690, "stage", "finish", None),
    ("depth-1-round-trip", 35700, "1", "2", "3"),
])
def test_scattered_subworkflow_two_workers(tmp_path, name, base_port, first, shared, last):
    example = ROOT / "examples/cwl/pipeline" / name
    run_command([str(PYTHON), "-m", "swirlc", "translate", "-l", "cwl",
                 str(example / "streamflow.yml"), "-o", str(tmp_path)], tmp_path / "translation.log")
    run_command([str(PYTHON), "-m", "swirlc", "compile", str(tmp_path / "workflow.swirl"),
                 str(tmp_path / "metadata.yml"), "--bundle-dependencies", "-o", str(tmp_path)],
                tmp_path / "compilation.log")
    run_command(["bash", "run.sh"], tmp_path / "execution.log", cwd=tmp_path, timeout=30)
    metadata = SwirlValidator().validate_file(str(tmp_path / "metadata.yml"))
    placements = {}
    for location, details in metadata["locations"].items():
        records = json.loads((tmp_path / f"{location}.outputs.json").read_text())
        placements[details["deployment"]["port"]] = records
    stages = []
    for port in (base_port + 1, base_port + 2):
        ids = {tuple(record["id"]) for record in placements[port]
               if record["port"] == f"p_process_items_{first}_result"}
        assert ids, "Each scatter worker must execute stage tasks"
        if last:
            assert {tuple(record["id"]) for record in placements[port]
                    if record["port"] == f"p_process_items_{last}_result"} == ids
        stages.append(ids)
    assert stages[0].isdisjoint(stages[1])
    assert stages[0] | stages[1] == {(0,), (1,), (2,)}
    assert {tuple(record["id"]) for record in placements[base_port + 3]
            if record["port"] == f"p_process_items_{shared}_result"} == {(0,), (1,), (2,)}
    main_example = example if last else example.parent / "depth-1-split"
    _, final_port = terminal_ports(main_example, metadata)["results"]
    final = [record["payload"] for record in placements[base_port] if record["port"] == final_port]
    assert len(final) == 1
    assert [file_path(path).read_text().rstrip("\n") for path in final[0]] == [
        "item=alpha", "item=beta", "item=alpha"]


def check_depth(depth, root, prepare_only=False, variant="plain"):
    example = ROOT / f"examples/cwl/pipeline/depth-{depth}/{variant}"
    directory = root / f"depth-{depth}" / variant
    directory.mkdir(parents=True, exist_ok=True)
    run_command([str(PYTHON), "-m", "swirlc", "translate", "-l", "cwl",
                 str(example / "streamflow.yml"), "-o", str(directory)], directory / "translation.log")
    metadata = inspect_translation(directory, depth, variant)
    expected = json.loads((example.parent / "expected.json").read_text())
    outputs = terminal_ports(example, metadata)
    source = (directory / "workflow.swirl").read_text()
    hint_free = directory / "workflow-no-hints.swirl"
    hint_free.write_text("\n".join(line for line in source.splitlines() if "// @compiler" not in line) + "\n")
    report = {"depth": depth, "variant": variant, "expected": expected, "runs": {}}
    for hints, workflow in [("hints", directory / "workflow.swirl"), ("no-hints", hint_free)]:
        for target in ("trace", "default"):
            bundle = directory / hints / target
            bundle.mkdir(parents=True, exist_ok=True)
            run_command([str(PYTHON), "-m", "swirlc", "compile", str(workflow),
                         str(directory / "metadata.yml"), "--target", target, *(["--bundle-dependencies"] if target == "default" else []),
                         "-o", str(bundle)],
                        bundle / "compilation.log")
            if target == "trace":
                traces = [(bundle / f"{location}.md").read_text() for location in metadata["locations"]]
                joined = "\n".join(traces)
                assert all(tool in joined for tool in metadata["steps"])
                if depth:
                    assert "fresh=" in joined and "exact=" in joined and "first operation closes owner=" in joined
                    assert "end()" not in joined
                    assert "drain admitted instances and descendants" in joined
                    assert "INVALID" not in joined
            else:
                compiled_tools = []
                for location in metadata["locations"]:
                    for call in generated_execs(bundle / f"{location}.py"):
                        assert location in call["mapping"]
                        compiled_tools.append(call["tool"])
                assert sorted(compiled_tools) == sorted(metadata["steps"])
            if target == "default" and not prepare_only:
                run_command(["bash", "run.sh"], bundle / "execution.log", cwd=bundle, timeout=45)
                actual, placements, isolated = verify_bundle(bundle, metadata, outputs, expected, example, variant)
                report["runs"][hints] = {"actual": actual, "placements": placements,
                                           "isolated_task_directories": isolated}
    (directory / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


@pytest.mark.parametrize("variant", ["plain", "metadata"])
@pytest.mark.parametrize("depth", range(4))
def test_pipeline_contract(depth, variant, tmp_path):
    report = check_depth(depth, tmp_path, variant=variant)
    assert report["runs"]["hints"]["actual"] == report["runs"]["no-hints"]["actual"]


@pytest.mark.parametrize("name, expected", [
    ("lists", "part-1-data\npart-2-data\npart-3-data\n"),
    ("lists-input", "9 merged.dat\n"),
])
def test_ordinary_whole_file_list_transport(name, expected, tmp_path):
    example = ROOT / "examples/cwl" / name
    run_command([str(PYTHON), "-m", "swirlc", "translate", "-l", "cwl",
                 str(example / "streamflow.yml"), "-o", str(tmp_path)], tmp_path / "translation.log")
    metadata = SwirlValidator().validate_file(str(tmp_path / "metadata.yml"))
    assert not metadata.get("scatterRegions")
    outputs = terminal_ports(example, metadata)
    run_command([str(PYTHON), "-m", "swirlc", "compile", str(tmp_path / "workflow.swirl"),
                 str(tmp_path / "metadata.yml"), "--bundle-dependencies", "-o", str(tmp_path)],
                tmp_path / "compilation.log")
    run_command(["bash", "run.sh"], tmp_path / "execution.log", cwd=tmp_path, timeout=30)
    _, final_port = outputs["final"]
    finals = [record["payload"] for location in metadata["locations"]
              for record in json.loads((tmp_path / f"{location}.outputs.json").read_text())
              if record["port"] == final_port and record["id"] == []]
    assert len(finals) == 1
    assert file_path(finals[0]).read_text() == expected


@pytest.mark.parametrize("configuration", ["streamflow.yml", "streamflow-split.yml"])
def test_ordinary_nested_metadata(configuration, tmp_path):
    example = ROOT / "examples/cwl/nested"
    run_command([str(PYTHON), "-m", "swirlc", "translate", "-l", "cwl",
                 str(example / configuration), "-o", str(tmp_path)], tmp_path / "translation.log")
    metadata = SwirlValidator().validate_file(str(tmp_path / "metadata.yml"))
    assert not metadata.get("scatterRegions")
    outputs = terminal_ports(example, metadata)
    for step in metadata["steps"].values():
        if "command" not in step:
            continue
        assert step["bindings"]["inputs"]["object"]
        assert step["arguments"][0] == {"value": "-c"}
        assert len(step["arguments"]) == 2 and "expression" in step["arguments"][1]
        assert step["stdout"] == "stdout.txt"
    # Retain remote descriptor evidence; execute its same placement graph locally.
    execution_metadata = tmp_path / "metadata.yml"
    if any(location["deployment"].get("type", "local") != "local"
           for location in metadata["locations"].values()):
        local_metadata = YAML(typ="safe").load(execution_metadata.read_text())
        for index, location in enumerate(local_metadata["locations"].values()):
            location["deployment"] = {"hostname": "127.0.0.1", "port": 35150 + index}
        execution_metadata = tmp_path / "metadata-local.yml"
        with execution_metadata.open("w") as stream:
            YAML().dump(local_metadata, stream)
    run_command([str(PYTHON), "-m", "swirlc", "compile", str(tmp_path / "workflow.swirl"),
                 str(execution_metadata), "--bundle-dependencies", "-o", str(tmp_path)],
                tmp_path / "compilation.log")
    run_command(["bash", "run.sh"], tmp_path / "execution.log", cwd=tmp_path, timeout=30)
    _, final_port = outputs["final_result"]
    finals = [record["payload"] for location in metadata["locations"]
              for record in json.loads((tmp_path / f"{location}.outputs.json").read_text())
              if record["port"] == final_port and record["id"] == []]
    assert finals == ["[processed] HELLO WORLD"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--variant", choices=["plain", "metadata"], action="append")
    parser.add_argument("--depth", type=int, choices=range(4), action="append")
    parser.add_argument("--output", type=Path, default=ROOT / "build/compiler-contract")
    args = parser.parse_args()
    for depth in args.depth or range(4):
        for variant in args.variant or ["plain", "metadata"]:
            print(json.dumps(check_depth(depth, args.output.resolve(), args.prepare_only, variant)), flush=True)


def test_dependent_remote_steps_finish_before_owner_eof(tmp_path):
    from io import StringIO
    from swirlc.translator.cwl.cwl_translator import CWLTranslator

    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-1-round-trip/streamflow.yml")
    region = translator.build_region_tree()
    steps = region.invocations[0].process.invocations
    steps[2].deployments = steps[1].deployments
    steps[1].process.baseCommand = ["sh", "-c", 'sleep 0.2; cp -T "$1" "$2"', "copy"]
    translator.build_region_tree = lambda: region
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    (tmp_path / "workflow.swirl").write_text(source.getvalue())
    (tmp_path / "metadata.yml").write_text(description.getvalue())
    assert "p_invocation_" not in source.getvalue()
    run_command([str(PYTHON), "-m", "swirlc", "compile", str(tmp_path / "workflow.swirl"),
                 str(tmp_path / "metadata.yml"), "--bundle-dependencies", "-o", str(tmp_path)],
                tmp_path / "compilation.log")
    run_command(["bash", "run.sh"], tmp_path / "execution.log", cwd=tmp_path, timeout=30)
    records = json.loads((tmp_path / "l3.outputs.json").read_text())
    for step in ("2", "3"):
        assert {tuple(record["id"]) for record in records
                if record["port"] == f"p_process_items_{step}_result"} == {(0,), (1,), (2,)}
    results = json.loads((tmp_path / "l0.outputs.json").read_text())
    final = [record["payload"] for record in results if record["port"].startswith("p_gather_data_")]
    assert len(final) == 1
    assert [file_path(path).read_text().strip() for path in final[0]] == [
        "item=alpha", "item=beta", "item=alpha"]
