"""Generated Python must express the workflow as native control flow."""
from __future__ import annotations

import ast
from pathlib import Path

from swirlc.compiler.default.compiler import DefaultTarget
from swirlc.core.compiler import CompileVisitor
from swirlc.core.parsing import parse_workflow
from tests.test_pipeline_contract import generated_execs


def generated_modules(directory: Path, source: str):
    compiler = DefaultTarget(str(directory))
    visitor = CompileVisitor(compiler, {
        "locations": {"l0": {}, "l1": {}}, "dependencies": {}, "steps": {},
    })
    visitor.visit(parse_workflow(source))
    return {path.stem: ast.parse(path.read_text()) for path in directory.glob("l*.py")}


def test_scoped_replication_compiles_to_direct_python_control_flow(tmp_path):
    source = """
    <l0, {},
      recv((begin, ?scope) -> p, l1, l0) .
      !(
        (recv((?item, ?scope / ?iteration) -> p, l1, l0)
         . (send((?item, ?scope / ?iteration) -> q, l0, l1)
            | send((?item, ?scope / ?iteration) -> r, l0, l1)))
        + (recv((eof, ?scope) -> p, l1, l0) . end())
      ) . 0
    >
    """
    tree = generated_modules(tmp_path, source)["l0"]
    program = tmp_path / "l0.py"
    assert generated_execs(program) == []
    workflow = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "workflow")
    nodes = list(ast.walk(workflow))
    assert any(isinstance(node, ast.While) for node in nodes), "Replication lacks a Python admission loop"
    assert any(isinstance(node, ast.If) for node in nodes), "Choice lacks a Python conditional"
    assert sum(isinstance(node, ast.FunctionDef) for node in nodes) >= 3, "Parallel branches need explicit functions"
    calls = [node for node in nodes if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
    assert any(call.func.attr == "recv" for call in calls)
    assert sum(call.func.attr == "send" for call in calls) == 2
    assert any("join" in call.func.attr for call in calls), "Generated branch and owner joins are missing"


def test_parallel_bindings_join_before_generated_continuation(tmp_path) -> None:
    source = """
    <l0, {},
      (recv((?left,root)->p,l1,l0) | recv((?right,root)->q,l1,l0))
      . send(((?left,?right),root)->r,l0,l1)
    > | <l1,{},0>
    """
    compiler = DefaultTarget(str(tmp_path))
    visitor = CompileVisitor(compiler, {
        "locations": {"l0": {}, "l1": {}}, "dependencies": {}, "steps": {},
    })
    visitor.visit(parse_workflow(source))
    module = ast.parse((tmp_path / "l0.py").read_text())
    workflow = next(node for node in module.body
                    if isinstance(node, ast.FunctionDef) and node.name == "workflow")
    calls = [node.value for node in workflow.body
             if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)]
    methods = [call.func.attr for call in calls
               if isinstance(call.func, ast.Attribute)]
    assert methods == ["parallel", "send"]
    branches = [node for node in workflow.body if isinstance(node, ast.FunctionDef)]
    assert len(branches) == 2
    for branch in branches:
        assert [argument.arg for argument in branch.args.args] == ["env", "owner"]


def test_guarded_move_admission_sends_claim_and_closes_generated_owner(tmp_path) -> None:
    source = """
    <l0, {},
      !(move((?item,root / ?iteration)->p,l0,l1)
        +[p has data in root] end())
    >
    """
    workflow = next(node for node in generated_modules(tmp_path, source)["l0"].body
                    if isinstance(node, ast.FunctionDef) and node.name == "workflow")
    calls = [node for node in ast.walk(workflow)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
    methods = [call.func.attr for call in calls]
    assert {"has_data", "exhausted", "try_move", "move", "admit", "spawn", "join", "end"} <= set(methods)
    assert methods.count("try_move") == 1
    assert methods.count("move") == 1
    closures = [call for call in calls if call.func.attr == "end"]
    assert any(isinstance(call.args[0], ast.Name)
               and call.args[0].id.startswith("replication_owner_") for call in closures)


def test_collection_codegen_uses_port_and_envelope(tmp_path) -> None:
    from swirlc.compiler.default.compiler import TERM_CONSTRUCTORS
    from swirlc.compiler.trace.compiler import TraceTarget

    source = "<l0,{(p,(d,root))},exec(s,{(p,(d,root))}->{U(q,(stream,root))},{l0})>"
    metadata = {
        "locations": {"l0": {}},
        "dependencies": {"d": {"type": "list[string]", "value": ["a", "a"]}},
        "steps": {"s": {"displayName": "Dispatch", "inputs": {"p": {"type": "list[string]"}},
                        "outputs": {"q": {"collection": {
                            "name": "stream", "scope": "root", "elementId": "root / ?i", "type": "string"}}}}},
    }
    for target in (DefaultTarget, TraceTarget):
        CompileVisitor(target(str(tmp_path)), metadata).visit(parse_workflow(source))
    assert " -> {U(q, (stream, root))}" in (tmp_path / "l0.md").read_text()
    tree = ast.parse((tmp_path / "l0.py").read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "collection"]
    assert len(calls) == 1 and len(calls[0].args) == 2
    envelope = calls[0].args[1]
    assert isinstance(envelope, ast.Call) and envelope.func.id == "tuple_term"
    namespace = {}
    exec(TERM_CONSTRUCTORS, namespace)
    actual = eval(compile(ast.Expression(calls[0]), "generated collection", "eval"), namespace)
    assert actual == {"kind": "collection", "name": "q", "items": [
        {"kind": "literal", "name": "stream", "items": []},
        {"kind": "literal", "name": "root", "items": []},
    ]}
