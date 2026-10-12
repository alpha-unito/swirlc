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
        "->{U(q,stream,root)},{l0}) . "
        "!(move((?value,root / ?iteration)->q,l0,l1)"
        "+[q has data in root] end())>"
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


@pytest.mark.parametrize("source", [
    "<l0,{},end()>",
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
