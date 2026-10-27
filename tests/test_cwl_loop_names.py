"""Scatter bindings distinguish independent and nested loop owners."""
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from swirlc.core.parsing import parse_workflow, validate_bindings
from swirlc.translator.cwl.cwl_translator import CWLTranslator


ROOT = Path(__file__).resolve().parents[1]


def translate(config):
    source, metadata = StringIO(), StringIO()
    CWLTranslator(config).translate(source, metadata)
    trace = source.getvalue()
    validate_bindings(parse_workflow(trace))
    return trace


def test_independent_scatter_bindings_and_gathers_use_distinct_names(tmp_path):
    yaml = YAML()
    workflow = {
        "cwlVersion": "v1.2",
        "class": "Workflow",
        "requirements": {"ScatterFeatureRequirement": {}},
        "inputs": {"samples": "File[]"},
        "outputs": {
            name: {"type": "File[]", "outputSource": f"{name}/result"}
            for name in ("first", "second")
        },
        "steps": {
            name: {
                "run": str(ROOT / "examples/cwl/pipeline/tools/copy.cwl"),
                "in": {"sample": "samples"},
                "out": ["result"],
                "scatter": "sample",
            }
            for name in ("first", "second")
        },
    }
    with (tmp_path / "main.cwl").open("w") as handle:
        yaml.dump(workflow, handle)
    config = tmp_path / "streamflow.yml"
    with config.open("w") as handle:
        yaml.dump({
            "workflows": {"test": {
                "type": "cwl", "config": {"file": "main.cwl"},
                "bindings": [{"step": "/", "target": {"deployment": "local"}}],
            }},
            "deployments": {"local": {"type": "local", "config": {}}},
        }, handle)

    trace = translate(config)
    for index, name in enumerate(("first", "second")):
        identity = f"?scope_{index} / ?iteration_{index + 1}"
        assert f"(?element_d_{name}_result, {identity})" in trace
        assert f"recv((begin, ?scope_{index}) -> p_result_0_{index}_l0" in trace


def test_nested_scatter_preserves_ancestors_and_allocates_new_coordinates():
    trace = translate(ROOT / "examples/cwl/pipeline/depth-3/plain/streamflow.yml")
    assert "?scope_0 / ?iteration_1 / ?iteration_2 / ?iteration_3" in trace
    assert "?iteration_1 / ?iteration_1" not in trace
    assert "?iteration_2 / ?iteration_2" not in trace
