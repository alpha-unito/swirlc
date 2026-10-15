"""CWL command/output descriptors retain their bound invocation contexts."""
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from ruamel.yaml import YAML

from swirlc.translator.cwl.cwl_translator import CWLTranslator, _lower_expression

ROOT = Path(__file__).resolve().parents[1]


def metadata(config):
    source, description = StringIO(), StringIO()
    CWLTranslator(ROOT / config).translate(source, description)
    return source.getvalue(), YAML(typ="safe").load(description.getvalue())


def test_input_self_is_preserved_with_an_explicit_binding():
    translator, tool = render_translator()
    tool.inputs[0].inputBinding.valueFrom = "$(self.nameroot)"
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    step = YAML(typ="safe").load(description.getvalue())["steps"]["s_stage_0"]
    arguments = step["arguments"]
    expression = arguments[1]["expression"]
    assert "self.nameroot" in expression["source"]
    binding = step["bindings"]["inputs"]["object"]["sample"]
    assert step["inputs"][binding["port"]] == {"type": "file"} and set(binding) == {"port"}
    assert expression["bindings"] == {"self": binding}


def render_translator():
    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-0/metadata/streamflow.yml")
    tool = next(tool for uri, tool in translator.cwl_bundle.items() if uri.endswith("/render.cwl"))
    return translator, tool


def test_unsorted_bindings_preserve_negative_positions_and_binding_options():
    translator, tool = render_translator()
    tool.baseCommand = ["printf", "fixed-base-token"]
    tool.arguments = [
        SimpleNamespace(position=4, valueFrom="last", prefix="--last", shellQuote=False),
        SimpleNamespace(position=-5, valueFrom="first", prefix="--first", separate=False),
        SimpleNamespace(position=1, valueFrom="middle", itemSeparator=","),
    ]
    tool.inputs[0].inputBinding = SimpleNamespace(
        position=-2, valueFrom="$(self.nameroot)", prefix="--sample",
        shellQuote=False, separate=False, itemSeparator=":",
    )
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    arguments = YAML(typ="safe").load(description.getvalue())["steps"]["s_stage_0"]["arguments"]
    assert arguments == [
        {"value": "fixed-base-token"},
        {"value": "first", "position": -5, "prefix": "--first", "separate": False},
        {"expression": arguments[2]["expression"], "position": -2,
         "prefix": "--sample", "separate": False, "shellQuote": False, "itemSeparator": ":"},
        {"value": "middle", "position": 1, "itemSeparator": ","},
        {"value": "last", "position": 4, "prefix": "--last", "shellQuote": False},
    ]


@pytest.mark.parametrize("context", ["arguments", "inputBinding"])
def test_expression_argument_positions_fail_explicitly(context):
    translator, tool = render_translator()
    if context == "arguments":
        tool.arguments = [SimpleNamespace(position="$(inputs.sample.size)", valueFrom="value")]
    else:
        tool.inputs[0].inputBinding.position = "$(inputs.sample.size)"
    with pytest.raises(ValueError, match="Expression argument positions are unsupported at /stage"):
        translator.translate(StringIO(), StringIO())


def test_pipeline_metadata_preserves_argument_positions_and_output_processors():
    source, description = metadata("examples/cwl/pipeline/depth-0/metadata/streamflow.yml")
    render = description["steps"]["s_stage_0"]
    binding = render["bindings"]["inputs"]["object"]["sample"]
    assert binding == {"port": next(iter(render["inputs"]))}
    assert render["inputs"] == {binding["port"]: {"type": "file"}}
    arguments = render["arguments"]
    assert [argument["position"] for argument in arguments] == [1, 2]
    assert all(argument["expression"]["language"] == "javascript" for argument in arguments)
    assert '"item=%s\\n"' in arguments[0]["expression"]["source"]
    assert "nameroot" in arguments[1]["expression"]["source"]
    assert render["stdout"] == "result.txt"
    output = render["outputs"]["p_stage_result"]
    assert output["glob"] == "result.txt"
    assert output["readContents"] is True
    assert "self[0].contents.trim()" in output["evaluate"]["source"]
    assert output["evaluate"]["bindings"] == {"self": {"context": "matchedFiles"}}
    import re
    received = re.search(r"recv\(\(\?(\w+), root\) -> " + re.escape(binding["port"]) + r", l0, l1\)", source)
    assert received, "Tool input must be received with its source identity"
    payload = received.group(1)
    assert f"send((d_sample, root) -> {binding['port']}, l0, l1)" in source
    assert f"exec(s_stage_0, {{({binding['port']}, (?{payload}, root))}}" in source


def test_nested_scripts_keep_named_inputs_and_output_self():
    _, description = metadata("examples/cwl/nested/streamflow-split.yml")
    commands = [step for step in description["steps"].values() if "command" in step]
    scripts = [argument["expression"]["source"] for step in commands
               for argument in step["arguments"] if "expression" in argument]
    assert len(scripts) == 3
    assert any("inputs.text" in script and "tr -s" in script for script in scripts)
    assert any("inputs.text" in script and "[:upper:]" in script for script in scripts)
    assert any("inputs.tag" in script and "inputs.text" in script for script in scripts)
    for step in commands:
        assert {binding["port"] for binding in step["bindings"]["inputs"]["object"].values()} <= set(step["inputs"])
        assert step["stdout"] == "stdout.txt"
        assert all("self[0].contents.trim()" in output["evaluate"]["source"]
                   for output in step["outputs"].values())


def test_genome_nameroot_and_dynamic_glob_keep_source_context():
    _, description = metadata("examples/1000genome/streamflow.yml")
    population_steps = [step for step in description["steps"].values()
                        if step.get("displayName") in ("mutation_overlap", "frequency")]
    assert population_steps
    for step in population_steps:
        argument = next(arg for arg in step["arguments"]
                        if "nameroot" in arg.get("expression", {}).get("source", ""))
        assert argument["prefix"] == "-pop"
        assert step["bindings"]["inputs"]["object"]["population"]["port"] in step["inputs"]
        assert "inputs.population.nameroot" in next(iter(step["outputs"].values()))["glob"]["source"]


@pytest.mark.parametrize("source, expected", [
    ("before-$(inputs.text.replace(')', ']'))-after", "before-(value]-after"),
    (r"\$(inputs.text):$(inputs.text)", "$(inputs.text):(value)"),
    ("${ return inputs.count + 1; }", 3),
    ("$([inputs.count, inputs.count])", [2, 2]),
])
def test_translator_lowers_interpolation_to_generic_javascript(source, expected):
    from swirlc.compiler.default import compiler
    namespace = {}
    exec(compiler.imports, namespace)
    exec(compiler.expression_function, namespace)
    descriptor = _lower_expression(source)
    assert descriptor["language"] == "javascript"
    assert namespace["_run_javascript_expression"](
        descriptor["source"], {"inputs": {"text": "(value)", "count": 2}}) == expected


@pytest.mark.parametrize("source", ["$(inputs.text", "$(inputs.text])", "${ return 'open; }"])
def test_translator_rejects_unbalanced_expression_syntax(source):
    with pytest.raises(ValueError, match="Malformed CWL expression"):
        _lower_expression(source)


def test_scatter_policies_are_runtime_invariants():
    from swirlc.config.validator import SwirlValidator

    _, description = metadata("examples/cwl/toy-genome/streamflow.yml")
    assert SwirlValidator().validate(description) is description
    dispatches = [step for step in description["steps"].values()
                  if step.get("type") == "scatter_dispatch"]
    assert dispatches
    for step in dispatches:
        assert set(step["keySpace"]) == {"dispatches"}
    assert "scatterRegions" not in description
    assert all("coordinates" not in step["key"] for step in dispatches)
    gathers = [step for step in description["steps"].values()
               if step.get("type") == "scatter_gather"]
    assert gathers
    for step in gathers:
        assert not ({"order", "validation", "emptyShape", "completion"} & step.keys())
        assert all("eofOwner" not in route for route in step["routes"])

    for field, value in [("cardinalities", "publish_before_peer_wait"),
                         ("validation", "equal_lengths"),
                         ("routing", "synchronized_moves_by_operation_and_full_id")]:
        dispatches[0]["keySpace"][field] = value
        with pytest.raises(Exception, match="configuration is invalid"):
            SwirlValidator().validate(description)
        del dispatches[0]["keySpace"][field]

    for container, field, value in [
        (dispatches[0]["key"], "coordinates", "declaration_order"),
        (gathers[0], "order", "declaration_order_coordinates"),
        (gathers[0], "validation", "expected_keys_without_duplicates"),
        (gathers[0], "emptyShape", "retain_all_dimension_cardinalities"),
        (gathers[0], "completion", "all_source_eofs_then_gather_then_acknowledged_publications"),
        (gathers[0]["routes"][0], "eofOwner", "actual_sender_after_publication_join"),
    ]:
        container[field] = value
        with pytest.raises(Exception, match="configuration is invalid"):
            SwirlValidator().validate(description)
        del container[field]


def test_cwl_when_is_rejected_instead_of_executed_unconditionally():
    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-0/metadata/streamflow.yml")
    translator.cwl_obj.steps[0].when = "$(true)"
    with pytest.raises(NotImplementedError, match="CWL when is not supported"):
        translator.translate(StringIO(), StringIO())


def test_scatter_emits_named_builtin_conditions():
    source, description = metadata("examples/cwl/toy-genome/streamflow.yml")
    assert " has data in " not in source
    assert description["conditions"]
    for name, condition in description["conditions"].items():
        assert condition["type"] == "has_data"
        assert f"+[{name}]" in source
        assert any(condition["port"] in step["outputs"] for step in description["steps"].values())
