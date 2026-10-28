"""CWL command/output descriptors retain their bound invocation contexts."""
import re
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from ruamel.yaml import YAML

from swirlc.translator.cwl.cwl_translator import CWLTranslator, EmittedFragment, _lower_expression

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


def test_remote_scatter_results_are_sent_from_the_exec_output_port():
    source, description = metadata("examples/cwl/pipeline/depth-1/plain/streamflow.yml")
    assert not any(name.startswith("_s_route_") for name in description["steps"])
    data = "(?element_d_process_items_result, ?scope_0 / ?iteration_1)"
    assert f"-> {{(p_process_items_result, {data})}}, {{l1}})" in source
    assert f"send({data} -> p_process_items_result, l1, l0)" in source
    assert f"recv({data} -> p_process_items_result, l1, l0)" in source


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
    assert f"{{(p_sample, (d_sample, root))}} -> {{({binding['port']}, (?route_d_" in source
    assert re.search(r"move\(\(\?route_d_\w+, root\) -> " + re.escape(binding['port']) + r", l0, l1\)", source)
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
    ('${\n return {"chromosome": inputs.count};\n}\n', {"chromosome": 2}),
    (" \n$(inputs.count)\t", 2),
    ("\n$([inputs.count])\n", [2]),
    (" before-$(inputs.count)-after\n", " before-2-after\n"),
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


def test_cwl_when_uses_named_choice_with_nullable_outputs():
    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-0/metadata/streamflow.yml")
    translator.cwl_obj.steps[0].when = "$(true)"
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    config = YAML(typ="safe").load(description.getvalue())
    step = config["steps"]["s_stage_0"]
    condition_id, condition = next(iter(config["conditions"].items()))
    assert condition["expression"] == {"language": "javascript", "source": "return (true);"}
    assert f"+[{condition_id}]" in source.getvalue()
    assert all("when" not in descriptor for descriptor in config["steps"].values())
    preparation = next(descriptor for descriptor in config["steps"].values() if "prepare" in descriptor)
    prepared_port = preparation["prepare"]["output"]
    assert step["bindings"] == {"inputs": {"port": prepared_port}}
    assert condition["bindings"]["inputs"] == {"port": prepared_port}
    skip = next(descriptor for descriptor in config["steps"].values()
                if descriptor["displayName"].startswith("Skip "))
    assert set(skip["outputs"]) == set(step["outputs"])
    assert all(output["schema"]["nullable"] for output in step["outputs"].values())
    assert "exec(s_stage_0," in source.getvalue()


def test_missing_features_lower_to_execution_descriptors_without_rewriting_fixture():
    _, description = metadata("examples/cwl/missing-features/streamflow.yml")
    from swirlc.config.validator import SwirlValidator

    SwirlValidator().validate(description)
    steps = description["steps"]
    generate = steps["s_generate_0"]
    assert generate["inputSchemas"]["items"] == {
        "type": "array", "items": {"type": "record", "fields": {
            "name": {"type": "string"}, "source": {"type": "file"}}}}
    assert generate["outputNames"] == {
        "message": "p_generate_message", "artifact": "p_generate_artifact"}
    assert generate["outputs"]["p_generate_artifact"]["secondaryFiles"] == [
        {"pattern": ".meta", "required": True}]
    assert generate["staging"][1]["name"] == "generate.py"
    assert "cwl.output.json" in generate["staging"][1]["entry"]
    optional = steps["s_optional_0"]
    condition = description["conditions"]["c_when_s_optional_0"]
    assert condition["expression"]["source"] == "return (inputs.enabled);"
    preparation = next(step for step in steps.values() if step.get("displayName") == "Prepare optional")
    assert "enabled" in preparation["bindings"]["inputs"]["object"]
    assert "enabled" not in optional["inputSchemas"]
    inspect = steps["s_inspect_0"]
    assert inspect["acceptedExitCodes"] == [0, 1]
    assert inspect["outputs"]["p_inspect_report"]["schema"] == {"type": "file"}
    assert inspect["outputs"]["p_inspect_report"]["glob"] == "report.json"
    assert "runtime.exitCode" in inspect["outputs"]["p_inspect_code"]["evaluate"]["source"]
    assert inspect["inputTransforms"]["messages"] == {"select": "all_non_null"}
    assert "[[inputs.file]].flat()" in inspect["inputTransforms"]["bundle"]["evaluate"]["source"]
    assert len(inspect["bindings"]["inputs"]["object"]["messages"]["items"]) == 2
    assert steps["s_check_0"]["inputOptions"]["log"] == {"readContents": True}


@pytest.mark.parametrize("schema", [["string", "int"], ["null"], ["File", "Directory", "null"]])
def test_unsupported_unions_fail_instead_of_selecting_first_member(schema):
    from swirlc.translator.cwl.cwl_translator import _cwl_type_to_swirl, _value_schema

    for convert in (_cwl_type_to_swirl, _value_schema):
        with pytest.raises(ValueError, match="Unsupported CWL union"):
            convert(schema)


def test_scatter_uses_operation_readiness_and_eof_termination():
    source, description = metadata("examples/cwl/toy-genome/streamflow.yml")
    assert description["conditions"] == {}
    assert "+[" not in source
    assert "end()" not in source
    for kind, operation, control, element in [
        ("scatter", "dispatch", "send", "move"),
        ("gather", "gather", "recv", "recv"),
    ]:
        hints = re.findall(rf"// @compiler begin ({kind}_stream [^\n]+)\n", source)
        assert hints
        for hint in hints:
            block = source.split(f"// @compiler begin {hint}\n", 1)[1].split(
                f"// @compiler end {hint}", 1,
            )[0]
            _, collection, location, port = hint.split()
            endpoints = rf"[^,\n]+, {location}" if kind == "scatter" else rf"{location}, [^\n]+"
            begin = re.search(rf"{control}\(\(begin, [^\n]+ -> {port}, {endpoints}\)", block)
            loop = re.search(rf"!\(\s*{element}\([^\n]+ -> {port}, [^\n]+\)\s*\+\s*{control}\(\(eof,", block)
            assert begin and loop
            assert begin.start() < loop.start()
            assert re.fullmatch(r"\s*\.\s*\(", block[begin.end():loop.start()])
            assert block.count(f"{control}((begin,") == 1
            assert block.count("!(") == 1
            assert "// @compiler" not in block
            assert "exec(" not in block
            execution = re.search(rf"exec\(_s_{operation}_[^\n]*{collection}[^\n]*", source)
            assert execution
            opening = source.index(f"// @compiler begin {hint}\n")
            closing = source.index(f"// @compiler end {hint}", opening)
            if kind == "scatter":
                assert execution.start() < opening
            else:
                assert closing < execution.start()



@pytest.mark.parametrize("config", [
    "examples/cwl/toy-genome/streamflow.yml",
    "examples/cwl/scatter-nested/streamflow.yml",
    "examples/cwl/pipeline/depth-1-split/streamflow.yml",
])
def test_worker_termination_keeps_all_eof_receives(config):
    source, _ = metadata(config)
    assert "end()" not in source
    assert "+[" not in source
    closures = re.findall(
        r"\+\s*(?:\(\s*)?(recv\(\(eof, [^\n]+\)(?:\n\.\nrecv\(\(eof, [^\n]+\))*)",
        source,
    )
    assert closures
    if "toy-genome" in config:
        assert any(len(closure.split("\n.\n")) == 2 for closure in closures)


def test_single_operation_branches_omit_grouping_parentheses():
    from swirlc.translator.cwl.cwl_translator import EmittedFragment, _sequence
    from swirlc.core.parsing import parse_workflow

    receive = "recv((?item, root / ?iteration) -> p, source, worker)"
    eof = "recv((eof, root) -> p, source, worker)"
    single = str(EmittedFragment("replication", [receive, _sequence([eof])]))
    assert single == f"(!(\n{receive}\n+\n{eof}\n))"
    multiple = str(EmittedFragment("replication", [receive, _sequence([eof, eof])]))
    assert f"(\n{eof}\n.\n{eof}\n)" in multiple
    parallel = str(EmittedFragment("parallel", [receive, eof]))
    assert parallel == f"(\n{receive}\n|\n{eof}\n)"
    for trace in (single, multiple, parallel):
        parse_workflow(f"<worker, {{}}, {trace}>")


@pytest.mark.parametrize("kind", ["scatter", "gather"])
def test_parallel_stream_hints_do_not_add_redundant_parentheses(kind):
    hint = f"{kind}_stream stream_d l1 p_stream"
    branch = EmittedFragment("marked", [
        f"// @compiler begin {hint}",
        EmittedFragment("sequence", ["send(begin)", "!(move(data) + send(eof))"]),
        f"// @compiler end {hint}",
    ])
    assert str(EmittedFragment("parallel", [branch, branch])) == (
        f"(\n{branch}\n|\n{branch}\n)"
    )


def test_worker_loop_reuses_existing_body_grouping():
    body = EmittedFragment("parallel", ["exec(first)", "exec(second)"])
    loop = EmittedFragment("replication", [body, "recv(eof)"])
    assert str(loop) == "(!(\n(\nexec(first)\n|\nexec(second)\n)\n+\nrecv(eof)\n))"
    sequence = EmittedFragment("sequence", [body, "send(result)"])
    loop.parts[0] = sequence
    assert str(loop) == f"(!(\n(\n{sequence}\n)\n+\nrecv(eof)\n))"


@pytest.mark.parametrize("config", [
    "examples/cwl/pipeline/depth-1-round-trip/streamflow.yml",
    "examples/cwl/pipeline/depth-2/plain/streamflow.yml",
    "examples/cwl/toy-genome/streamflow.yml",
])
def test_remote_services_use_data_admission_instead_of_inner_begin(config):
    source, _ = metadata(config)
    assert "p_invocation_" not in source
    assert not re.search(r"p_owner_\w+_invocation", source)
    assert "recv((begin," in source
    assert "!(" in source


def test_remote_default_only_task_receives_an_iteration_value(tmp_path):
    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-1-round-trip/streamflow.yml")
    region = translator.build_region_tree()
    remote = region.invocations[0].process.invocations[1]
    remote.input_bindings = {}
    remote.defaults["sample"] = {"class": "File", "path": str(ROOT / "README.md")}
    translator.build_region_tree = lambda: region
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    trace = source.getvalue()
    assert "p_invocation_" not in trace
    assert "recv((?iteration_d_p_iteration_process_items_2, ?scope_0 / ?iteration_1) -> p_iteration_process_items_2" in trace
    assert "{(p_scatter_0_0, (?element_d_samples, ?scope_0 / ?iteration_1))} -> {(p_iteration_process_items_2," in trace
    assert "move((?route_d__s_route_p_iteration_process_items_2_0, ?scope_0 / ?iteration_1) -> p_iteration_process_items_2" in trace
    from swirlc.main import main

    workflow = tmp_path / "workflow.swirl"
    metadata_file = tmp_path / "metadata.yml"
    workflow.write_text(trace)
    metadata_file.write_text(description.getvalue())
    assert main(["compile", str(workflow), str(metadata_file), "-o", str(tmp_path)]) == 0


def test_nested_remote_gather_with_multiple_routes_has_data_admission(tmp_path):
    from swirlc.main import main

    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-2/plain/streamflow.yml")
    region = translator.build_region_tree()
    outer = region.invocations[0]
    outer.process.invocations[0].deployments += outer.deployments
    translator.build_region_tree = lambda: region
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    workflow = tmp_path / "workflow.swirl"
    metadata_file = tmp_path / "metadata.yml"
    workflow.write_text(source.getvalue())
    metadata_file.write_text(description.getvalue())
    assert "p_invocation_" not in source.getvalue()
    assert main(["compile", str(workflow), str(metadata_file), "-o", str(tmp_path)]) == 0


def test_scattered_condition_retains_null_positions_and_completes(tmp_path):
    import json
    from tests.test_pipeline_contract import PYTHON, run_command

    workflow = {
        "cwlVersion": "v1.2", "class": "Workflow",
        "requirements": {"ScatterFeatureRequirement": {}, "InlineJavascriptRequirement": {}},
        "inputs": {"xs": {"type": "int[]", "default": [0, 1, 2]}},
        "outputs": {"ys": {"type": {"type": "array", "items": ["null", "int"]},
                            "outputSource": "choose/y"}},
        "steps": {"choose": {
            "in": {"x": "xs"}, "scatter": "x", "when": "$(inputs.x > 0)", "out": ["y"],
            "run": {"class": "ExpressionTool", "inputs": {"x": "int"}, "outputs": {"y": "int"},
                    "expression": "${ return {y: inputs.x}; }"}}},
    }
    yaml = YAML()
    with (tmp_path / "main.cwl").open("w") as stream:
        yaml.dump(workflow, stream)
    with (tmp_path / "streamflow.yml").open("w") as stream:
        yaml.dump({"version": "v1.0", "deployments": {"local": {"type": "local", "port": 0}},
                   "workflows": {"test": {"type": "cwl", "config": {"file": "main.cwl"},
                                          "bindings": [{"step": "/", "target": {"deployment": "local"}}]}}}, stream)
    source, description = StringIO(), StringIO()
    CWLTranslator(tmp_path / "streamflow.yml").translate(source, description)
    (tmp_path / "workflow.swirl").write_text(source.getvalue())
    (tmp_path / "metadata.yml").write_text(description.getvalue())
    run_command([str(PYTHON), "-m", "swirlc", "compile", str(tmp_path / "workflow.swirl"),
                 str(tmp_path / "metadata.yml"), "--bundle-dependencies", "-o", str(tmp_path)],
                tmp_path / "compilation.log")
    run_command(["bash", "run.sh"], tmp_path / "execution.log", cwd=tmp_path, timeout=30)
    metadata = YAML(typ="safe").load(description.getvalue())
    gather = next(step for step in metadata["steps"].values() if step.get("type") == "scatter_gather")
    port = next(iter(gather["outputs"]))
    outputs = json.loads((tmp_path / "l0.outputs.json").read_text())
    assert [record["payload"] for record in outputs if record["port"] == port and record["id"] == []] == [[None, 1, 2]]


def test_nested_record_file_field_retains_secondary_declarations():
    from swirlc.translator.cwl.cwl_translator import _value_schema

    field = SimpleNamespace(name="Item/source", type_="File", secondaryFiles=[".meta"])
    schema = SimpleNamespace(type_="array", items=SimpleNamespace(type_="record", fields=[field]))
    assert _value_schema(schema) == {"type": "array", "items": {"type": "record", "fields": {
        "source": {"type": "file", "secondaryFiles": [{"pattern": ".meta", "required": True}]}}}}


def test_repeated_step_input_source_has_one_exec_input():
    translator = CWLTranslator(ROOT / "examples/cwl/missing-features/streamflow.yml")
    region = translator.build_region_tree()
    invocation = next(item for item in region.invocations if item.path == "/optional")
    invocation.input_bindings["enabled"] = invocation.input_bindings["message"]
    translator.build_region_tree = lambda: region
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    metadata = YAML(typ="safe").load(description.getvalue())
    prepare_id, step = next((name, descriptor) for name, descriptor in metadata["steps"].items()
                            if descriptor.get("displayName") == "Prepare optional")
    assert len(step["inputs"]) == 1
    assert step["bindings"]["inputs"]["object"]["message"] == step["bindings"]["inputs"]["object"]["enabled"]
    execution = re.search(rf"exec\({prepare_id}, \{{([^}}]+)\}}", source.getvalue()).group(1)
    assert execution.count("root)") == 1


@pytest.mark.parametrize("selection", ["first_non_null", "all_non_null", "the_only_non_null"])
def test_single_source_selection_keeps_source_sequence(selection):
    translator = CWLTranslator(ROOT / "examples/cwl/missing-features/streamflow.yml")
    region = translator.build_region_tree()
    invocation = next(item for item in region.invocations if item.path == "/inspect")
    invocation.input_bindings["messages"] = ("/generate/message",)
    invocation.transforms["messages"]["select"] = selection
    translator.build_region_tree = lambda: region
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    step = YAML(typ="safe").load(description.getvalue())["steps"]["s_inspect_0"]
    binding = step["bindings"]["inputs"]["object"]["messages"]
    assert binding == {"items": [{"port": "p_input_inspect_generate_message_l0"}]}
    from swirlc.compiler.default import compiler
    namespace = {}
    exec(compiler.imports, namespace)
    exec(compiler.list_helper, namespace)
    exec(compiler.expression_function, namespace)
    exec(compiler.command_tool_function, namespace)
    values = {"p_input_inspect_generate_message_l0": "hello"}
    resolved = namespace["_resolve_bindings"]({"inputs": {"object": {"messages": binding}}}, values,
                                              input_types=step["inputs"])
    assert resolved["inputs"]["messages"] == ["hello"]


def test_docker_requirement_propagates_to_step_metadata():
    translator = CWLTranslator(ROOT / "examples/montage/streamflow.yml")
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    metadata = YAML(typ="safe").load(description.getvalue())
    get_diff_step = next(
        descriptor for descriptor in metadata["steps"].values()
        if descriptor.get("displayName") == "get_diff"
    )
    assert get_diff_step.get("container") == {
        "type": "docker",
        "image": "opencadc/astropy:3.9-slim",
    }

