"""Plain CWL compiler acceptance; run directly with the installed project Python."""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import signal
import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from swirlc.config.validator import SwirlValidator

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"


def run_command(arguments, log, *, cwd=ROOT, timeout=60):
    env = dict(os.environ, SWIRLC_PYTHON=str(PYTHON),
               SWIRLC_RUNTIME_TIMEOUT="20", SWIRLC_ADDRESS_BOOK_TIMEOUT="20",
               SWIRLC_ADDRESS_GATHER_TIMEOUT="20")
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


def inspect_translation(directory, depth):
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
    assert len(metadata.get("scatterRegions", {})) == depth
    return metadata


def terminal_ports(example, metadata):
    """Resolve declared CWL aliases to emitted boundary helpers or ordinary tools."""
    workflow = YAML(typ="safe").load((example / "main.cwl").read_text())
    result = {}
    for output, declaration in workflow["outputs"].items():
        source = declaration["outputSource"]
        path = "/" + source
        matches = []
        for region in metadata.get("scatterRegions", {}).values():
            boundaries = region["scope"].get("outputBoundaries", {})
            for name, boundary in boundaries.items():
                if boundary["path"] == path:
                    matches += [(materialization["receiver"], port)
                                for materialization in region["scope"].get("materializations", [])
                                if materialization["output"] == name
                                for port in metadata["steps"][materialization["helper"]]["outputs"]]
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


def replace_files(value):
    if isinstance(value, list):
        return [replace_files(item) for item in value]
    assert isinstance(value, str) and Path(value).is_file(), value
    text = Path(value).read_text()
    return text[:-1] if text.endswith("\n") else text


def generated_execs(path):
    """Read direct operation calls without executing generated workflow code."""
    tree = ast.parse(path.read_text())
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


def verify_bundle(directory, metadata, outputs, expected, example):
    manifests = {location: json.loads((directory / f"{location}.outputs.json").read_text())
                 for location in metadata["locations"]}
    actual = {}
    for name, (location, port) in outputs.items():
        records = [record for owner, records in manifests.items()
                   if location is None or owner == location
                   for record in records if record["port"] == port and record["id"] == []]
        assert len(records) == 1, (name, records)
        actual[name] = replace_files(records[0]["payload"])
    assert actual == expected, (actual, expected)

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
            assert set(step["inputPorts"]) == {port for port, _ in node["inputs"]}
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
            for port in step["outputs"]:
                emitted = [record for record in records if record["port"] == port]
                for record in emitted:
                    assert isinstance(record["payload"], str)
                    path = Path(record["payload"])
                    assert path.is_file()
                    assert path.parent.name.startswith(f"exec_{tool}_"), (tool, path)
                    task_directories.append(path.parent)
    assert len(task_directories) == len(set(task_directories)), "Tasks share execution directories"
    assert len(placements) == sum("command" in step for step in metadata["steps"].values())
    return actual, placements, len(task_directories)


def check_depth(depth, root, prepare_only=False):
    example = ROOT / f"examples/cwl/pipeline/depth-{depth}/plain"
    directory = root / f"depth-{depth}"
    directory.mkdir(parents=True, exist_ok=True)
    run_command([str(PYTHON), "-m", "swirlc", "translate", "-l", "cwl",
                 str(example / "streamflow.yml"), "-o", str(directory)], directory / "translation.log")
    metadata = inspect_translation(directory, depth)
    expected = json.loads((example.parent / "expected.json").read_text())
    outputs = terminal_ports(example, metadata)
    source = (directory / "workflow.swirl").read_text()
    hint_free = directory / "workflow-no-hints.swirl"
    hint_free.write_text("\n".join(line for line in source.splitlines() if "// @compiler" not in line) + "\n")
    report = {"depth": depth, "expected": expected, "runs": {}}
    for variant, workflow in [("hints", directory / "workflow.swirl"), ("no-hints", hint_free)]:
        for target in ("trace", "default"):
            bundle = directory / variant / target
            bundle.mkdir(parents=True, exist_ok=True)
            run_command([str(PYTHON), "-m", "swirlc", "compile", str(workflow),
                         str(directory / "metadata.yml"), "--target", target, "-o", str(bundle)],
                        bundle / "compilation.log")
            if target == "trace":
                traces = [(bundle / f"{location}.md").read_text() for location in metadata["locations"]]
                joined = "\n".join(traces)
                assert all(tool in joined for tool in metadata["steps"])
                if depth:
                    assert "fresh=" in joined and "exact=" in joined and "close owner=" in joined
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
                actual, placements, isolated = verify_bundle(bundle, metadata, outputs, expected, example)
                report["runs"][variant] = {"actual": actual, "placements": placements,
                                           "isolated_task_directories": isolated}
    (directory / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


@pytest.mark.parametrize("depth", range(4))
def test_plain_pipeline_contract(depth, tmp_path):
    report = check_depth(depth, tmp_path)
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
                 str(tmp_path / "metadata.yml"), "-o", str(tmp_path)], tmp_path / "compilation.log")
    run_command(["bash", "run.sh"], tmp_path / "execution.log", cwd=tmp_path, timeout=30)
    _, final_port = outputs["final"]
    finals = [record["payload"] for location in metadata["locations"]
              for record in json.loads((tmp_path / f"{location}.outputs.json").read_text())
              if record["port"] == final_port and record["id"] == []]
    assert len(finals) == 1
    assert Path(finals[0]).read_text() == expected


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--depth", type=int, choices=range(4), action="append")
    parser.add_argument("--output", type=Path, default=ROOT / "build/compiler-contract")
    args = parser.parse_args()
    for depth in args.depth or range(4):
        print(json.dumps(check_depth(depth, args.output.resolve(), args.prepare_only)), flush=True)
