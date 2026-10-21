from __future__ import annotations

import pytest

from swirlc.core.parsing import parse_workflow


def test_phase5_surface() -> None:
    parse_workflow(
        "<l0,{(p,d)},!(!((exec(s,{(p,(a,b))}->{(q,r[k])},{l0,l1}) "
        ". move((a,b)->p,l0,{l0,l1})) + (recv(eof->p,l1,l0) . 0)))>"
    )


@pytest.mark.parametrize(
    "source",
    [
        "<l0,{(p,d)},!x exec(s,{(p,d)}->{(q,r)},l0)>",
        "<l0,{(p,d)},exec(s,{(p,(a,b)}->{(q,r)},l0)>",
        "<l0,{(p,d)},exec(s,{(p,d)}->{(q,r)},l0) +foo 0>",
    ],
)
def test_rejects_old_or_malformed_syntax(source: str) -> None:
    with pytest.raises(ValueError, match="Invalid SWIRL"):
        parse_workflow(source)


def test_structured_envelopes_scopes_collections_and_guard() -> None:
    from swirlc.core.utils import get_flow, get_term
    tree = parse_workflow(
        "<l0,{(p,(d,root))},exec(s,{(p,(d,root))}"
        "->{U(q,(stream,root))},{l0}) . "
        "!(move((?value,root / ?iteration)->q,l0,l1)"
        "+ send((eof,root)->q,l0,l1))>"
    )
    location = tree.location(0)
    envelope = get_term(location.dataSet().dataPair(0).data())
    assert envelope.payload.name == "d"
    assert envelope.identity.name == "root"
    trace = location.trace()
    action = trace.trace(0).pred().exec()
    inputs, outputs = get_flow(action)
    assert inputs[0][0] == "p"
    assert outputs[0][1].kind == "collection"
    assert outputs[0][1].items[0].name == "stream"


def test_sequence_binds_more_tightly_than_parallel() -> None:
    tree = parse_workflow("<l0,{},0 . 0 | 0>")
    trace = tree.location(0).trace()
    assert trace.op.text == "|"
    assert trace.trace(0).op.text == "."


def test_named_guard_preserves_identifier_and_choice_structure() -> None:
    tree = parse_workflow("<l0,{},0 . 0 +[items_available] 0>")
    trace = tree.location(0).trace()
    assert trace.op.text == "+"
    assert trace.guard().port().getText() == "items_available"
    assert trace.guard().data() is None
    assert trace.trace(0).op.text == "."


def test_named_guard_validates_descriptor_scope_bindings() -> None:
    from swirlc.core.parsing import validate_bindings

    tree = parse_workflow("<l0,{},0 +[items_available] 0>")
    with pytest.raises(ValueError, match="Unknown condition items_available"):
        validate_bindings(tree, {})
    with pytest.raises(ValueError, match="Unbound variables.*parent"):
        validate_bindings(tree, {"items_available": {
            "type": "has_data", "port": "p", "scope": "?parent",
        }})
    validate_bindings(tree, {"items_available": {
        "type": "has_data", "port": "p", "scope": "root",
    }})


@pytest.mark.parametrize("guard", ["[]", "[ready extra]", "[?ready]", "[ready has data]"])
def test_rejects_malformed_named_guards(guard: str) -> None:
    with pytest.raises(ValueError, match="Invalid SWIRL"):
        parse_workflow(f"<l0,{{}},0 +{guard} 0>")


@pytest.mark.parametrize("source", [
    "<l0,{},end()>",
    "<l0,{},!(end())>",
    "<l0,{},recv((?payload,?scope / ?iteration)->p,l1,l0)>",
    "<l0,{},send((?payload,root)->p,l0,l1)>",
    "<l0,{},recv((?payload,root)->p,l1,l0) | send((?payload,root)->q,l0,l1)>",
])
def test_rejects_unbound_construction_and_unowned_end(source: str) -> None:
    from swirlc.core.parsing import validate_bindings
    with pytest.raises(ValueError):
        validate_bindings(parse_workflow(source))


def test_parallel_receive_bindings_available_after_join() -> None:
    from swirlc.core.parsing import validate_bindings
    validate_bindings(parse_workflow(
        "<l0,{},(recv((?a,root)->p,l1,l0) | recv((?b,root)->q,l1,l0))"
        " . send(((?a,?b),root)->r,l0,l1)>"
    ))


@pytest.mark.parametrize("identity", ["root", "?scope", "?scope / ?iteration", "root / ?outer / ?inner"])
def test_collection_pairs_preserve_identity_and_flow_order(identity: str) -> None:
    from swirlc.core.utils import get_flow
    source = f"<l0,{{}},exec(s,{{U(z,(last,{identity})),U(a,(first,{identity}))}}->{{}},{{l0}})>"
    tree = parse_workflow(source)
    inputs, outputs = get_flow(tree.location(0).trace().pred().exec())
    assert [port for port, _ in inputs] == ["z", "a"]
    assert outputs == []
    for port, term in inputs:
        assert term.kind == "collection"
        assert term.name == port
        assert str(term.items[1]).replace(" ", "") == identity.replace(" ", "")
        assert str(term) == f"U({port}, ({term.items[0]}, {term.items[1]}))"
        assert term.to_dict()["items"][1] == term.items[1].to_dict()


@pytest.mark.parametrize("collection", [
    "U(p,stream,root)", "U(p,stream)", "U(p,(stream))",
    "U(p,(stream,))", "U(p,(,root))", "U(p,(stream,root,extra))",
    "U(p,(stream,root /))", "U(p,(stream,?))",
])
def test_rejects_old_or_malformed_collection_pairs(collection: str) -> None:
    with pytest.raises(ValueError, match="Invalid SWIRL"):
        parse_workflow(f"<l0,{{}},exec(s,{{{collection}}}->{{}},{{l0}})>")
