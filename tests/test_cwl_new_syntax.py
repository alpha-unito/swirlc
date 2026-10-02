"""Accepted simple-scatter contracts, without the legacy parser/compiler."""

import re
from io import StringIO
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from swirlc.translator.cwl.cwl_translator import CWLTranslator

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "cwl"


def translate(translator):
    trace, metadata = StringIO(), StringIO()
    translator.translate(trace, metadata)
    return trace.getvalue(), YAML(typ="safe").load(metadata.getvalue())


@pytest.mark.parametrize(
    "case,items",
    [
        ("empty", []),
        ("one", ["alpha"]),
        ("duplicate", ["alpha", "alpha"]),
        ("many", ["alpha", "beta", "gamma", "delta", "epsilon"]),
    ],
)
def test_simple_scatter_preserves_inputs_and_collection_contract(case, items):
    trace, metadata = translate(
        CWLTranslator(EXAMPLES / "scatter-new-syntax" / f"streamflow-{case}.yml")
    )
    assert metadata["dependencies"]["d_items"] == {
        "type": "list[string]",
        "value": items,
    }
    pair = metadata["steps"]["_s_scatter_0"]
    assert pair["outputs"] == {
        "p_task_0": {
            "collection": {
                "name": "tasks_0",
                "key": "key_0",
                "fields": {"item": "string"},
            }
        }
    }
    assert pair["key"] == {
        "operation": "scatter:/process",
        "parentCoordinates": [],
        "coordinates": "declaration_order",
    }
    assert "-> {U(p_task_0, tasks_0)}" in trace
    assert trace.count("+[p_task_0 has data]") == 2
    assert "[taskID]" not in trace
    assert "?payload_0" in trace and "?key_0" in trace
    assert all(trace.count(f"<{location},") == 1 for location in metadata["locations"])
    for worker in pair["workers"]:
        assert f"move((?payload_0, ?key_0) -> p_task_0, l0, {worker})" in trace
        assert f"recv(eof -> p_task_0, l0, {worker}) . end()" in trace
        assert re.search(r"\)\s*\.\s*send\(eof -> p_task_0, l0, " + worker, trace)

    gather = metadata["steps"]["_s_gather_0"]
    assert gather["order"] == "declaration_order_coordinates"
    assert gather["shapeFrom"] == "_s_scatter_0"
    assert {value["type"] for value in gather["collections"].values()} == {
        "string",
        "int",
    }
    assert len(gather["outputs"]) == len(gather["collections"]) == 2
    gather_trace = trace.split("// @compiler begin scatter.gather 0\n", 1)[1].split(
        "// @compiler end scatter.gather 0", 1
    )[0]
    # All receiver loops finish as a grouped parallel join before the snapshot read.
    assert re.search(r"\)\)\)\s*\.\s*exec\(_s_gather_0", gather_trace)
    for port, collection in gather["collections"].items():
        assert collection["read"] == "snapshot"
        assert f"U({port}, {collection['name']})" in gather_trace
        for worker in pair["workers"]:
            assert f"recv(eof -> {port}, {worker}, l0) . end()" in gather_trace
            assert f"send(eof -> {port}, {worker}, l0)" in trace
    assert set(metadata["dependencies"]) == {
        "d_items",
        "d_prefix",
        "d_labels",
        "d_process_rendered_0",
        "d_process_invariant_count_0",
    }
    assert all(
        "?" not in name and "eof" not in name for name in metadata["dependencies"]
    )


def test_scalar_and_whole_list_invariants_are_initialized_once_per_worker():
    trace, metadata = translate(
        CWLTranslator(EXAMPLES / "scatter-new-syntax" / "streamflow-many.yml")
    )
    pair = metadata["steps"]["_s_scatter_0"]
    assert pair["scatterPorts"] == ["p_items"]
    assert pair["invariantPorts"] == ["p_prefix", "p_labels"]
    assert "exec(_s_scatter_0, {(p_items, d_items)}" in trace
    assert metadata["steps"]["_s_open_0"]["inputFields"] == {"item": "p_open_data_0_0"}
    for worker in pair["workers"]:
        branch = trace.split(f"<{worker},", 1)[1].split(
            "// @compiler end scatter.worker 0", 1
        )[0]
        for name in ("prefix", "labels"):
            assert trace.count(f"send(d_{name} -> p_{name}, l0, {worker})") == 1
            assert branch.count(f"recv(p_{name} -> d_{name}, l0, {worker})") == 1
            assert branch.index(f"recv(p_{name} -> d_{name}") < branch.index("!(")
            assert f"(p_{name}, d_{name})" in branch


def test_same_source_can_be_scattered_and_passed_as_a_whole_list():
    translator = CWLTranslator(EXAMPLES / "scatter-new-syntax" / "streamflow-many.yml")
    bindings = translator.cwl_obj.steps[0].in_
    next(binding for binding in bindings if binding.id.endswith("/labels")).source = (
        next(binding.source for binding in bindings if binding.id.endswith("/item"))
    )
    trace, metadata = translate(translator)
    pair = metadata["steps"]["_s_scatter_0"]
    assert pair["scatterPorts"] == ["p_items"]
    assert pair["invariantPorts"] == ["p_prefix", "p_items"]
    tool = next(step for step in metadata["steps"].values() if "expression" in step)
    assert tool["expression"]["inputs"]["labels"] == {
        "port": "p_items",
        "type": "list[string]",
    }
    assert metadata["steps"]["_s_open_0"]["inputFields"] == {"item": "p_open_data_0_0"}
    for worker in pair["workers"]:
        assert trace.count(f"send(d_items -> p_items, l0, {worker})") == 1


@pytest.mark.parametrize("output_name", ["item", "input_item"])
def test_exec_output_binds_a_fresh_payload_when_input_and_output_names_match(output_name):
    translator = CWLTranslator(EXAMPLES / "scatter-new-syntax" / "streamflow-one.yml")
    step = translator.cwl_obj.steps[0]
    step.run.outputs[0].id = step.run.outputs[0].id.removesuffix("rendered") + output_name
    step.out[0] = step.out[0].removesuffix("rendered") + output_name
    translator.cwl_obj.outputs[0].outputSource = step.out[0]
    step.run.expression = step.run.expression.replace("rendered:", output_name + ":")
    _, metadata = translate(translator)
    opened = next(iter(metadata["steps"]["_s_open_0"]["outputs"].values()))["binding"]
    tool = next(step for step in metadata["steps"].values() if "expression" in step)
    produced = next(iter(tool["outputs"].values()))["binding"]
    assert opened["payload"] != produced["payload"]
    assert opened["key"] == produced["key"]


def test_ordinary_basic_workflow_keeps_substantive_trace_and_metadata():
    trace, metadata = translate(CWLTranslator(EXAMPLES / "basic" / "streamflow.yml"))
    assert trace == (
        "<l0, {(p_greeting, d_greeting)},\n"
        "exec(s_step1, {(p_greeting, d_greeting)} -> {(p_step1_command_line, d_step1_command_line)}, {l0})\n"
        ".\n"
        "exec(s_step2, {(p_step1_command_line, d_step1_command_line), (p_greeting, d_greeting)} -> {(p_step2_command_line, d_step2_command_line)}, {l0})\n>\n"
    )
    assert metadata["scatterRegions"] == {}
    assert metadata["dependencies"] == {
        "d_greeting": {"type": "string", "value": "hello"},
        "d_step1_command_line": {"type": "string"},
        "d_step2_command_line": {"type": "string"},
    }
    assert metadata["locations"] == {
        "l0": {"deployment": {"hostname": "127.0.0.1", "port": 35050}}
    }
    for index in (1, 2):
        step = metadata["steps"][f"s_step{index}"]
        assert step["command"].startswith("sh -c ")
        assert step["outputs"] == {
            f"p_step{index}_command_line": {
                "dataName": f"d_step{index}_command_line",
                "glob": "stdout.txt",
            }
        }
    assert metadata["steps"]["s_step1"]["arguments"] == [{"valueFrom": "p_greeting"}]
    assert metadata["steps"]["s_step2"]["arguments"] == [
        {"valueFrom": "p_step1_command_line"},
        {"valueFrom": "p_greeting"},
    ]
