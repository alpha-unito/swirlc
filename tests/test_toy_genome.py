"""Local genome-shaped acceptance with bundled Python-only expression support."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ruamel.yaml import YAML

from swirlc.config.validator import SwirlValidator
from tests.test_pipeline_contract import (
    PYTHON, ROOT, generated_execs, replace_files, run_command, terminal_ports,
)

EXAMPLE = ROOT / "examples/cwl/toy-genome"


def check_toy_genome(directory):
    directory.mkdir(parents=True, exist_ok=True)
    configuration = YAML(typ="safe").load((EXAMPLE / "streamflow.yml").read_text())
    assert all(deployment["type"] == "local"
               for deployment in configuration["deployments"].values())
    run_command([str(PYTHON), "-m", "swirlc", "translate", "-l", "cwl",
                 str(EXAMPLE / "streamflow.yml"), "-o", str(directory)],
                directory / "translation.log")
    metadata = SwirlValidator().validate_file(str(directory / "metadata.yml"))
    source = (directory / "workflow.swirl").read_text()
    execs = re.findall(r"\bexec\((\w+),", source)
    assert len(execs) == len(set(execs))
    assert set(execs) == set(metadata["steps"])
    assert len(metadata["locations"]) == 6
    ports = {location["deployment"]["port"] for location in metadata["locations"].values()}
    assert ports == {deployment["port"] for deployment in configuration["deployments"].values()}
    assert "scatterRegions" not in metadata
    dispatches = [step for step in metadata["steps"].values() if step.get("type") == "scatter_dispatch"]
    assert {step["operationId"].removeprefix("scatter:") for step in dispatches} == {
        "/chromosome", "/chromosome/individuals",
        "/chromosome/mutation_overlap", "/chromosome/frequency",
    }
    assert all(step["scatterMethod"] == "dotproduct" for step in dispatches)
    for step in metadata["steps"].values():
        if "command" not in step:
            continue
        assert step["stdout"]["language"] == "javascript"
        variables = step["bindings"]["inputs"]["object"]
        assert {binding["port"] for binding in variables.values()} <= set(step["inputs"])
        if "population" in variables:
            argument = next(arg for arg in step["arguments"] if arg.get("prefix") == "--population")
            assert argument["expression"]["bindings"]["self"] == variables["population"]
            assert "self.nameroot" in argument["expression"]["source"]
        for output in step["outputs"].values():
            assert output["glob"]["language"] == "javascript"
            if "evaluate" in output:
                assert output["readContents"] is True
                assert output["evaluate"]["bindings"] == {"self": {"context": "matchedFiles"}}

    outputs = terminal_ports(EXAMPLE, metadata)
    expected = json.loads((EXAMPLE / "expected.json").read_text())
    declarations = YAML(typ="safe").load((EXAMPLE / "main.cwl").read_text())["outputs"]
    without_hints = directory / "workflow-no-hints.swirl"
    without_hints.write_text("\n".join(line for line in source.splitlines()
                                      if "// @compiler" not in line) + "\n")
    report = {"expected": expected, "runs": {}}
    bindings = configuration["workflows"]["toy_genome"]["bindings"]
    for mode, workflow in [("hints", directory / "workflow.swirl"), ("no-hints", without_hints)]:
        for target in ("trace", "default"):
            bundle = directory / mode / target
            bundle.mkdir(parents=True, exist_ok=True)
            run_command([str(PYTHON), "-m", "swirlc", "compile", str(workflow),
                         str(directory / "metadata.yml"), "--target", target,
                         *(["--bundle-dependencies"] if target == "default" else []),
                         "-o", str(bundle)], bundle / "compilation.log")
            if target == "trace":
                text = "\n".join((bundle / f"{location}.md").read_text()
                                 for location in metadata["locations"])
                assert all(tool in text for tool in metadata["steps"])
                assert "fresh=" in text and "exact=" in text and "first operation closes owner=" in text
                assert "drain admitted instances and descendants" in text
                assert "INVALID" not in text
                continue
            compiled = []
            placements = {}
            for location in metadata["locations"]:
                for call in generated_execs(bundle / f"{location}.py"):
                    tool = call["tool"]
                    step = metadata["steps"][tool]
                    compiled.append(tool)
                    assert location in call["mapping"]
                    assert set(step["inputs"]) == {port for port, _ in call["inputs"]}
                    assert set(step["outputs"]) == {port for port, _ in call["outputs"]}
                    if "command" not in step:
                        continue
                    invocation = "/chromosome/" + step["displayName"]
                    binding = max((binding for binding in bindings
                                   if binding["step"] == "/" or invocation == binding["step"]
                                   or invocation.startswith(binding["step"] + "/")),
                                  key=lambda binding: len(binding["step"]))
                    targets = binding["target"] if isinstance(binding["target"], list) else [binding["target"]]
                    allowed_ports = {configuration["deployments"][target["deployment"]]["port"]
                                     for target in targets}
                    assert metadata["locations"][location]["deployment"]["port"] in allowed_ports
                    placements[tool] = location
            assert sorted(compiled) == sorted(metadata["steps"])
            run_command(["bash", "run.sh"], bundle / "execution.log", cwd=bundle, timeout=90)
            manifests = {location: json.loads((bundle / f"{location}.outputs.json").read_text())
                         for location in metadata["locations"]}
            actual = {}
            for name, (location, port) in outputs.items():
                records = [record for owner, records in manifests.items()
                           if location is None or owner == location
                           for record in records if record["port"] == port and record["id"] == []]
                assert len(records) == 1, (name, records)
                actual[name] = (replace_files(records[0]["payload"])
                                if "File" in json.dumps(declarations[name]["type"])
                                else records[0]["payload"])
                assert records[0]["type"] == ("list[list[file]]" if name.endswith("files")
                                             else "list[list[string]]")
            assert actual == expected, (actual, expected)
            scratch = Path((bundle / "execution-scratch.txt").read_text().strip())
            isolated = []
            tasks = {}
            for tool, location in placements.items():
                step = metadata["steps"][tool]
                directories = list(scratch.glob(f"exec_{tool}_*"))
                # Different exec templates may publish the same port at one location.
                ids = {tuple(record["id"]) for record in manifests[location]
                       if record["port"] in step["outputs"]
                       and isinstance(record["payload"], str)
                       and Path(record["payload"]).parent in directories}
                assert len(directories) == len(ids), (tool, ids, directories)
                assert all(path.is_dir() and any(path.glob("*.txt")) for path in directories)
                isolated.extend(directories)
                tasks[tool] = len(ids)
            assert len(isolated) == len(set(isolated)) == 29
            report["runs"][mode] = {"actual": actual, "placements": placements,
                                    "tasks": tasks, "isolated_task_directories": len(isolated)}
    assert report["runs"]["hints"]["actual"] == report["runs"]["no-hints"]["actual"]
    (directory / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def test_toy_genome_contract(tmp_path):
    check_toy_genome(tmp_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/toy-genome")
    args = parser.parse_args()
    print(json.dumps(check_toy_genome(args.output.resolve()), indent=2))
