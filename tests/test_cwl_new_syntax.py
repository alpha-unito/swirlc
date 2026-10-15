"""Accepted simple-scatter contracts, without the legacy parser/compiler."""

import re
from io import StringIO
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from swirlc.translator.cwl.cwl_translator import CWLTranslator

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "cwl"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cwl"


def translate(translator):
    trace, metadata = StringIO(), StringIO()
    translator.translate(trace, metadata)
    return trace.getvalue(), YAML(typ="safe").load(metadata.getvalue())


@pytest.mark.parametrize("config", [
    "scatter/streamflow.yml",
    "scatter-methods-new-syntax/streamflow-dotproduct.yml",
    "scatter-methods-new-syntax/streamflow-nested_crossproduct.yml",
    "scatter-methods-new-syntax/streamflow-empty-inner.yml",
    "scatter-distributed-new-syntax/streamflow.yml",
    "scatter-nested-new-syntax/streamflow-shared.yml",
    "scatter-nested-new-syntax/streamflow-separate.yml",
])
def test_worker_termination_receives_all_input_eofs_before_end(config):
    trace, metadata = translate(CWLTranslator(FIXTURES / config))
    blocks = re.findall(
        r"// @compiler begin scatter.worker (\d+)\n(.*?)"
        r"// @compiler end scatter.worker \1", trace, re.S,
    )
    assert blocks
    for region, block in blocks:
        termination = re.search(
            r"\+\s*\((recv\(eof.*?end\(\))\)\s*\)\s*\.\s*(.*)",
            block, re.S,
        )
        assert termination
        closing, after_join = termination.groups()
        inputs = list(metadata["scatterRegions"][region]["scope"]["inputChannels"].items())
        eofs = re.findall(r"recv\(eof -> (.*?), (l\d+), (l\d+)\)", closing)
        assert [port for port, _, _ in eofs] == [port for _, port in inputs]
        worker = eofs[0][2]
        routes = metadata["scatterRegions"][region]["scope"]["routes"]
        assert any(
            worker in route["workers"]
            and [source for _, source, _ in eofs] == [route["producers"][name] for name, _ in inputs]
            for route in routes
        )
        assert closing == " . ".join(
            [f"recv(eof -> {port}, {source}, {worker})" for port, source, _ in eofs]
            + ["end()"]
        )
        assert "recv(eof" not in after_join
        assert "send(eof" in after_join


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
        CWLTranslator(FIXTURES / "scatter-new-syntax" / f"streamflow-{case}.yml")
    )
    assert metadata["dependencies"]["d_items"] == {
        "type": "list[string]",
        "value": items,
    }
    dispatch = metadata["steps"]["_s_dispatch_0_0"]
    assert dispatch["type"] == "scatter_dispatch"
    assert dispatch["dimension"] == "item"
    assert dispatch["outputs"] == {
        "p_scatter_0_0": {"collection": {
            "name": "stream_d_items", "key": "key_0", "type": "string",
        }}
    }
    assert dispatch["key"] == {
        "operation": "scatter:/process", "parentKeys": [],
    }
    assert "exec(_s_dispatch_0_0, {(p_items, d_items)} -> {U(p_scatter_0_0, stream_d_items)}" in trace
    assert trace.count("+[p_scatter_0_0 has data]") == 2
    assert "scatter_open" not in str(metadata)
    assert "_s_open_" not in trace and "p_task_" not in trace
    assert "[taskID]" not in trace
    assert "_key_0" not in trace
    assert all(trace.count(f"<{location},") == 1 for location in metadata["locations"])
    workers = metadata["scatterRegions"]["0"]["scope"]["routes"][0]["workers"]
    payload = "(?element_d_items, ?key_0)"
    for worker in workers:
        hint = f"scatter_stream stream_d_items {worker} p_scatter_0_0"
        stream_trace = trace.split(f"// @compiler begin {hint}\n", 1)[1].split(
            f"// @compiler end {hint}", 1
        )[0]
        assert f"move({payload} -> p_scatter_0_0, l0, {worker})" in stream_trace
        assert stream_trace.startswith("(\n!(")
        assert stream_trace.rstrip().endswith(f"send(eof -> p_scatter_0_0, l0, {worker})\n)")
        assert f"move({payload} -> p_scatter_0_0, l0, {worker})" in trace
        assert f"recv(eof -> p_scatter_0_0, l0, {worker}) . end()" in trace
        assert re.search(r"\)\s*\.\s*send\(eof -> p_scatter_0_0, l0, " + worker, trace)
    gathers = [step for step in metadata["steps"].values() if step.get("type") == "scatter_gather"]
    assert len(gathers) == 2
    assert {next(iter(step["collections"].values()))["type"] for step in gathers} == {"string", "int"}
    for output_index, gather in enumerate(gathers):
        assert "order" not in gather
        assert gather["shapeFrom"] == ["_s_dispatch_0_0"]
        assert len(gather["outputs"]) == len(gather["collections"]) == 1
        port, collection = next(iter(gather["collections"].items()))
        assert collection["read"] == "snapshot"
        assert f"exec(_s_gather_{output_index}_0, {{U({port}, {collection['name']})}}" in trace
        for worker in workers:
            hint = f"gather_stream {collection['name']} {worker} {port}"
            receive_trace = trace.split(f"// @compiler begin {hint}\n", 1)[1].split(
                f"// @compiler end {hint}", 1
            )[0]
            assert receive_trace.startswith("(\n!(")
            assert receive_trace.rstrip().endswith("\n)\n)")
            assert f"recv(eof -> {port}, {worker}, l0) . end()" in receive_trace
            assert f"recv(eof -> {port}, {worker}, l0) . end()" in trace
            assert f"send(eof -> {port}, {worker}, l0)" in trace
    assert set(metadata["dependencies"]) == {
        "d_items",
        "d_prefix",
        "d_labels",
        "d_process_rendered",
        "d_process_invariant_count",
    }
    assert all(
        "?" not in name and "eof" not in name for name in metadata["dependencies"]
    )


def test_scalar_and_whole_list_invariants_are_initialized_once_per_worker():
    trace, metadata = translate(
        CWLTranslator(FIXTURES / "scatter-new-syntax" / "streamflow-many.yml")
    )
    dispatch = metadata["steps"]["_s_dispatch_0_0"]
    assert dispatch["dimension"] == "item"
    assert "exec(_s_dispatch_0_0, {(p_items, d_items)}" in trace
    workers = metadata["scatterRegions"]["0"]["scope"]["routes"][0]["workers"]
    for worker in workers:
        branch = trace.split(f"<{worker},", 1)[1].split(
            "// @compiler end scatter.worker 0", 1
        )[0]
        for name in ("prefix", "labels"):
            assert trace.count(f"send(d_{name} -> p_{name}, l0, {worker})") == 1
            assert branch.count(f"recv(p_{name} -> d_{name}, l0, {worker})") == 1
            assert branch.index(f"recv(p_{name} -> d_{name}") < branch.index("!(")
            assert f"(p_{name}, d_{name})" in branch


def test_same_source_can_be_scattered_and_passed_as_a_whole_list():
    translator = CWLTranslator(FIXTURES / "scatter-new-syntax" / "streamflow-many.yml")
    bindings = translator.cwl_obj.steps[0].in_
    next(binding for binding in bindings if binding.id.endswith("/labels")).source = (
        next(binding.source for binding in bindings if binding.id.endswith("/item"))
    )
    trace, metadata = translate(translator)
    dispatch = metadata["steps"]["_s_dispatch_0_0"]
    assert dispatch["dimension"] == "item"
    tool = next(step for step in metadata["steps"].values() if "expression" in step)
    assert tool["expression"]["inputs"]["labels"] == {
        "port": "p_items", "type": "list[string]",
    }
    workers = metadata["scatterRegions"]["0"]["scope"]["routes"][0]["workers"]
    for worker in workers:
        assert trace.count(f"send(d_items -> p_items, l0, {worker})") == 1


@pytest.mark.parametrize("output_name", ["item", "input_item"])
def test_exec_output_binds_a_fresh_payload_when_input_and_output_names_match(output_name):
    translator = CWLTranslator(FIXTURES / "scatter-new-syntax" / "streamflow-one.yml")
    step = translator.cwl_obj.steps[0]
    step.run.outputs[0].id = step.run.outputs[0].id.removesuffix("rendered") + output_name
    step.out[0] = step.out[0].removesuffix("rendered") + output_name
    translator.cwl_obj.outputs[0].outputSource = step.out[0]
    step.run.expression = step.run.expression.replace("rendered:", output_name + ":")
    _, metadata = translate(translator)
    stream = next(iter(metadata["steps"]["_s_dispatch_0_0"]["outputs"]))
    tool = next(step for step in metadata["steps"].values() if "expression" in step)
    produced = next(iter(tool["outputs"].values()))["binding"]
    assert stream in tool["expression"]["inputs"]["item"]["port"]
    assert produced["payload"] == f"element_d_process_{output_name}"
    assert produced["key"] == "key_0"


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
