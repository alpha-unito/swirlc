"""CWL dispatch and gather collections retain their explicit scope envelope."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from swirlc.antlr.SWIRLParser import SWIRLParser
from swirlc.core.parsing import parse_workflow
from swirlc.core.utils import get_flow, get_name
from swirlc.translator.cwl.cwl_translator import CWLTranslator

ROOT = Path(__file__).resolve().parents[1]


def exec_contexts(node):
    if isinstance(node, SWIRLParser.ExecContext):
        yield node
    for child in node.getChildren() if hasattr(node, "getChildren") else ():
        yield from exec_contexts(child)


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_translated_collections_pair_names_with_their_metadata_scope(depth):
    trace, descriptors = io.StringIO(), io.StringIO()
    CWLTranslator(ROOT / f"examples/cwl/pipeline/depth-{depth}/plain/streamflow.yml").translate(
        trace, descriptors,
    )
    metadata = YAML(typ="safe").load(descriptors.getvalue())
    actual = set()
    for action in exec_contexts(parse_workflow(trace.getvalue())):
        tool = get_name(action.step())
        for side, flow in zip(("input", "output"), get_flow(action), strict=True):
            for port, term in flow:
                if term.kind == "collection":
                    name, scope = term.items
                    actual.add((tool, side, port, name.name, str(scope)))
                    assert f"U({port}, ({name}, {scope}))" in trace.getvalue()
    expected = set()
    for tool, descriptor in metadata["steps"].items():
        for port, output in descriptor.get("outputs", {}).items():
            if "collection" in output:
                collection = output["collection"]
                expected.add((tool, "output", port, collection["name"], collection["scope"]))
        for port, collection in descriptor.get("collections", {}).items():
            expected.add((tool, "input", port, collection["name"], collection["scope"]))
    assert actual == expected
    assert len(actual) == trace.getvalue().count("U(")


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_maintained_concrete_scatter_references_parse(depth):
    source = (ROOT / f"examples/swirl/{depth}-nested-scatter.swirl").read_text()
    parse_workflow(source)
