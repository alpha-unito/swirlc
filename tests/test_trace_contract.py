from __future__ import annotations

from pathlib import Path

from swirlc.compiler.trace.compiler import TraceTarget
from swirlc.core.compiler import CompileVisitor
from swirlc.core.parsing import parse_workflow

SOURCE = """
<l0, {},
  recv((begin, ?scope) -> p, l1, l0) .
  !(
    (recv(((?left, ?right), ?scope / ?iteration) -> p, l1, l0)
     . send(((?left, ?right), ?scope / ?iteration) -> q, l0, l1))
    + (recv((eof, ?scope) -> p, l1, l0))
  ) . 0
>
"""


def compile_trace(directory: Path, source: str, conditions: dict | None = None) -> str:
    directory.mkdir()
    compiler = TraceTarget(str(directory))
    visitor = CompileVisitor(compiler, {
        "locations": {"l0": {}, "l1": {}},
        "dependencies": {}, "steps": {}, "conditions": conditions or {},
    })
    visitor.visit(parse_workflow(source))
    return (directory / "l0.md").read_text()


def test_trace_exposes_envelope_patterns_owners_and_completion(tmp_path: Path) -> None:
    trace = compile_trace(tmp_path / "trace", SOURCE)
    assert "(begin, ?scope)" in trace
    assert "((?left, ?right), ?scope / ?iteration)" in trace
    assert "fresh=['iteration', 'left', 'right'] exact=['scope']" in trace
    assert "(eof, ?scope)" in trace
    assert "first operation closes owner=" in trace
    assert "drain admitted instances and descendants" in trace
    assert "join activated descendants" in trace
    assert "zero (null process)" in trace


def test_hints_are_advisory_for_trace_structure(tmp_path: Path) -> None:
    hinted = "// @compiler begin arbitrary ignored hint\n" + SOURCE
    assert compile_trace(tmp_path / "hinted", hinted) == compile_trace(tmp_path / "plain", SOURCE)


def test_trace_preserves_named_condition_reference(tmp_path: Path) -> None:
    trace = compile_trace(tmp_path / "named", "<l0,{},0 +[ready] 0>", {
        "ready": {"type": "has_data", "port": "p", "scope": "root"},
    })
    assert "guard=[ready]" in trace


def test_trace_rejects_unknown_condition(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="Unknown condition missing"):
        compile_trace(tmp_path / "missing", "<l0,{},0 +[missing] 0>")


def test_multi_location_destination_is_structured_and_ordered(tmp_path: Path) -> None:
    from swirlc.compiler.standard.compiler import StructuredCompiler

    class CaptureCompiler(StructuredCompiler):
        def render_location(self, location, dataset, root):
            self.result = self.serialize(root)

    compiler = CaptureCompiler(str(tmp_path))
    visitor = CompileVisitor(compiler, {
        "locations": {"l0": {}, "l1": {}, "l2": {}},
        "dependencies": {"d": {"type": "string", "value": "hello"}},
        "steps": {},
    })
    visitor.visit(parse_workflow("<l0,{(p,(d,root))},send((d,root)->q,l0,{l2,l1})>"))
    assert compiler.result["children"][0]["dst"] == ["l2", "l1"]


def test_output_binding_identity_must_match_metadata(tmp_path: Path) -> None:
    import pytest

    compiler = TraceTarget(str(tmp_path))
    visitor = CompileVisitor(compiler, {
        "locations": {"l0": {}}, "dependencies": {},
        "steps": {"s": {"displayName": "s", "inputs": {}, "outputs": {
            "p": {"binding": {"payload": "answer", "id": "root / 0", "type": "string"}},
        }}},
    })
    with pytest.raises(ValueError, match="output binding p does not match metadata"):
        visitor.visit(parse_workflow("<l0,{},exec(s,{}->{(p,(?answer,root))},{l0})>"))


def test_ports_register_payload_dependencies_without_identity_expressions(tmp_path: Path) -> None:
    compiler = TraceTarget(str(tmp_path))
    visitor = CompileVisitor(compiler, {
        "locations": {"l0": {}},
        "dependencies": {"d": {"type": "string", "value": "hello"}},
        "steps": {"s": {"displayName": "s", "inputs": {"p": {"type": "string"}}, "outputs": {
            "q": {"binding": {"payload": "answer", "id": "root", "type": "string"}},
        }}},
    })
    visitor.visit(parse_workflow("<l0,{(p,(d,root))},exec(s,{(p,(d,root))}->{(q,(?answer,root))},{l0})>"))
    assert visitor.workflow.ports["p"].data == {"d"}
    assert visitor.workflow.ports["q"].data == set()


def test_typed_input_rejects_literal_dependency_type_mismatch(tmp_path: Path) -> None:
    import pytest

    visitor = CompileVisitor(TraceTarget(str(tmp_path)), {
        "locations": {"l0": {}},
        "dependencies": {"d": {"type": "string", "value": "hello"}},
        "steps": {"s": {"displayName": "s", "inputs": {"p": {"type": "int"}}, "outputs": {}}},
    })
    with pytest.raises(ValueError, match="type"):
        visitor.visit(parse_workflow("<l0,{(p,(d,root))},exec(s,{(p,(d,root))}->{},{l0})>"))


def test_typed_input_rejects_producer_output_type_mismatch(tmp_path: Path) -> None:
    import pytest

    visitor = CompileVisitor(TraceTarget(str(tmp_path)), {
        "locations": {"l0": {}}, "dependencies": {},
        "steps": {
            "producer": {"displayName": "producer", "inputs": {}, "outputs": {
                "p": {"binding": {"payload": "answer", "id": "root", "type": "string"}},
            }},
            "consumer": {"displayName": "consumer", "inputs": {"p": {"type": "int"}}, "outputs": {}},
        },
    })
    with pytest.raises(ValueError, match="type"):
        visitor.visit(parse_workflow(
            "<l0,{},exec(producer,{}->{(p,(?answer,root))},{l0}) . "
            "exec(consumer,{(p,(?answer,root))}->{},{l0})>"))
