"""Named guards preserve native control flow and invocation-local values."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading

import pytest

from swirlc.compiler.default.compiler import DefaultTarget
from swirlc.compiler.default.runtime import Runtime, _frame, _unframe
from swirlc.compiler.trace.compiler import TraceTarget
from swirlc.config.validator import SwirlValidator
from swirlc.core.compiler import CompileVisitor
from swirlc.core.parsing import parse_workflow
from tests.test_scoped_runtime import ROOT, envelope, term


def expression_condition(source="return count > 0;"):
    return {"type": "expression", "inputs": {"p_count": {"type": "int"}},
            "bindings": {"count": {"port": "p_count"}},
            "expression": {"language": "javascript", "source": source}}


def runtime_for(request, conditions, evaluator=None):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    runtime = Runtime({"steps": {}, "dependencies": {}, "conditions": conditions},
                      "local", {"local": listener.getsockname()}, listener,
                      lambda sock, kind, value: _frame(sock, value),
                      lambda sock, kind: _unframe(sock), lambda name, inputs: {}, evaluator)
    runtime.timeout = .2
    runtime.start()
    request.addfinalizer(runtime.close)
    return runtime


def test_has_data_distinguishes_pending_available_and_exhausted(request):
    runtime = runtime_for(request, {"ready": {"type": "has_data", "port": "p", "scope": "root"}})
    assert runtime.condition_value("ready", {}, ROOT) is None
    runtime._store("p", (0,), "value", "string")
    runtime.finite.add(("p", ()))
    assert runtime.condition_value("ready", {}, ROOT) is True
    runtime.values.clear()
    assert runtime.condition_value("ready", {}, ROOT) is False


def test_expression_conditions_use_invocation_local_received_values(request):
    barrier = threading.Barrier(2)
    def evaluate(descriptor, bound):
        barrier.wait(timeout=1)
        return bound["p_count"] > 0
    runtime = runtime_for(request, {"positive": expression_condition()}, evaluate)
    pattern = envelope(term("variable", "value"), term("path", "", ROOT, term("variable", "i")))
    for i, value in enumerate([-1, 2]):
        runtime.offers.append({"src": "source", "port": "p_count", "id": (i,),
                               "value": value, "type": "int", "event": threading.Event()})
    environments = [{"i": 0}, {"i": 1}]
    for env in environments:
        assert runtime.try_receive(env, "p_count", pattern, "source")
    results = {}
    threads = [threading.Thread(target=lambda i=i: results.update(
        {i: runtime.condition_value("positive", environments[i])})) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(2)
        assert not thread.is_alive()
    assert results == {0: False, 1: True}
    assert environments[0]["_condition_inputs"] != environments[1]["_condition_inputs"]


@pytest.mark.parametrize("value", [0, 1, "true", None, [], {}])
def test_expression_condition_requires_a_boolean(request, value):
    runtime = runtime_for(request, {"positive": expression_condition()}, lambda spec, bound: value)
    with pytest.raises(TypeError, match="must return a boolean"):
        runtime.condition_value("positive", {"_condition_inputs": {"p_count": 1}})


def test_expression_condition_requires_previously_bound_input(request):
    runtime = runtime_for(request, {"positive": expression_condition()}, lambda spec, bound: True)
    with pytest.raises(ValueError, match="already-bound inputs"):
        runtime.condition_value("positive", {})


def test_expression_condition_receives_initialized_input_without_actions(request):
    runtime = runtime_for(request, {"positive": expression_condition()},
                          lambda descriptor, bound: bound["p_count"] > 0)
    env = runtime.initialize([{"name": "count", "port": "p_count", "payload": 3,
                               "type": "int", "identity": ROOT}], {})
    assert runtime.condition_value("positive", env) is True
    assert not runtime.offers


def test_parallel_branch_can_update_inherited_condition_input(request):
    runtime = runtime_for(request, {"positive": expression_condition()},
                          lambda descriptor, bound: bound["p_count"] > 0)
    env = {"_condition_inputs": {"p_count": 0}}
    def changed(local, owner):
        runtime._bind_condition_input(local, "p_count", 1)
    def unrelated(local, owner):
        local["other"] = "done"
    runtime.parallel(env, None, changed, unrelated)
    assert env["other"] == "done"
    assert runtime.condition_value("positive", env) is True


def test_parallel_branches_reject_conflicting_condition_input_updates(request):
    runtime = runtime_for(request, {"positive": expression_condition()},
                          lambda descriptor, bound: bound["p_count"] > 0)
    env = {"_condition_inputs": {"p_count": 0}}
    with pytest.raises(ValueError, match="conflicting condition inputs"):
        runtime.parallel(env, None,
                         lambda local, owner: runtime._bind_condition_input(local, "p_count", 1),
                         lambda local, owner: runtime._bind_condition_input(local, "p_count", 2))


def config(source="return count > 0;", count=1):
    steps = {}
    for name, marker in [("yes", "accepted"), ("no", "rejected")]:
        steps[name] = {"displayName": name, "inputs": {}, "expression": {
            "language": "javascript", "source": "return {result: " + json.dumps(marker) + "};",
            "outputs": {"result": "p_" + name}}, "outputs": {
                "p_" + name: {"binding": {"payload": name, "id": "root", "type": "string"}}}}
    return {"version": "v1.1", "locations": {"l0": {"hostname": "127.0.0.1", "port": 0}},
            "dependencies": {"d_count": {"type": "int", "value": count}},
            "steps": steps, "conditions": {"positive": expression_condition(source)}}


SOURCE = """<l0,{(p_count,(d_count,root))},
 (exec(yes,{}->{(p_yes,(?yes,root))},{l0})
  +[positive] exec(no,{}->{(p_no,(?no,root))},{l0}))>"""


def run_bundle(directory):
    return subprocess.run(["bash", "run.sh"], cwd=directory, capture_output=True,
                          text=True, timeout=10, env=dict(
                              os.environ, SWIRLC_TMP_DIR=str(directory / "scratch"),
                              SWIRLC_PYTHON=sys.executable, SWIRLC_RUNTIME_TIMEOUT="2",
                              SWIRLC_ADDRESS_BOOK_TIMEOUT="2", SWIRLC_ADDRESS_GATHER_TIMEOUT="2",
                              PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1"))


@pytest.mark.parametrize("count, selected", [(1, "accepted"), (0, "rejected")])
def test_named_expression_compiles_both_targets_and_runs_both_branches(tmp_path, count, selected):
    metadata = SwirlValidator().validate(config(count=count))
    CompileVisitor(TraceTarget(str(tmp_path)), metadata).visit(parse_workflow(SOURCE))
    CompileVisitor(DefaultTarget(str(tmp_path), bundle_dependencies=True), metadata).visit(parse_workflow(SOURCE))
    assert "guard=[positive]" in (tmp_path / "l0.md").read_text()
    generated = (tmp_path / "l0.py").read_text()
    assert "condition_value('positive'" in generated
    result = run_bundle(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    records = json.loads((tmp_path / "l0.outputs.json").read_text())
    assert [record["payload"] for record in records if record["port"] in {"p_yes", "p_no"}] == [selected]


@pytest.mark.parametrize("source, message", [
    ("return 1;", "must return a boolean"),
    ("throw new Error('condition failed');", "condition failed"),
])
def test_generated_expression_failure_terminates_with_error(tmp_path, source, message):
    CompileVisitor(DefaultTarget(str(tmp_path), bundle_dependencies=True), config(source)).visit(parse_workflow(SOURCE))
    result = run_bundle(tmp_path)
    assert result.returncode != 0
    assert message in result.stdout + result.stderr


def test_nested_conditions_short_circuit_unselected_expression(tmp_path):
    metadata = config(count=0)
    metadata["conditions"]["unsafe"] = expression_condition("throw new Error('must not evaluate');")
    source = SOURCE.replace("exec(yes,{}->{(p_yes,(?yes,root))},{l0})", "(0 +[unsafe] 0)")
    CompileVisitor(DefaultTarget(str(tmp_path), bundle_dependencies=True), metadata).visit(parse_workflow(source))
    result = run_bundle(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    records = json.loads((tmp_path / "l0.outputs.json").read_text())
    assert [record["payload"] for record in records if record["port"] == "p_no"] == ["rejected"]


def test_condition_rejects_foreign_binding_port():
    metadata = config()
    metadata["conditions"]["positive"]["bindings"]["count"]["port"] = "foreign"
    with pytest.raises(ValueError, match="outside its inputs"):
        SwirlValidator().validate(metadata)


def test_unknown_condition_reference_is_rejected(tmp_path):
    metadata = config()
    metadata["conditions"].clear()
    with pytest.raises(ValueError, match="Unknown condition positive"):
        CompileVisitor(DefaultTarget(str(tmp_path)), metadata).visit(parse_workflow(SOURCE))


@pytest.mark.parametrize("descriptor", [
    {"type": "has_data", "port": "p"},
    {"type": "has_data", "port": "p", "scope": "root", "expression": {}},
    {"type": "expression", "inputs": {}, "expression": "$(true)"},
    {"type": "unsupported"},
])
def test_condition_schema_rejects_incomplete_and_unsupported_forms(descriptor):
    metadata = config()
    metadata["conditions"]["positive"] = descriptor
    with pytest.raises(Exception, match="configuration is invalid"):
        SwirlValidator().validate(metadata)
