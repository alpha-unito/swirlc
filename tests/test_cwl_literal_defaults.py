"""Tool constants belong to metadata; workflow inputs still carry data."""
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from swirlc.config.validator import SwirlValidator
from swirlc.translator.cwl.cwl_translator import CWLTranslator

ROOT = Path(__file__).resolve().parents[1]


def translate(translator):
    source, description = StringIO(), StringIO()
    translator.translate(source, description)
    metadata = YAML(typ="safe").load(description.getvalue())
    SwirlValidator().validate(metadata)
    return source.getvalue(), metadata


def test_scattered_tool_default_is_literal_and_workflow_input_remains_data():
    source, metadata = translate(CWLTranslator(
        ROOT / "examples/cwl/pipeline/depth-1/plain/streamflow.yml"))
    step = metadata["steps"]["s_process_items_0"]
    assert "default_process_items_destination" not in source
    assert "d_default_process_items_destination" not in metadata["dependencies"]
    assert step["bindings"]["inputs"]["object"]["destination"] == {"value": "result.txt"}
    assert step["arguments"][-1] == {"value": "result.txt", "position": 2}
    assert len(step["inputs"]) == 1
    assert "d_samples" in metadata["dependencies"]
    assert "(p_samples, (d_samples, root))" in source


def test_literal_default_is_available_to_self_and_named_input_expressions():
    from swirlc.compiler.default import compiler

    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-1/plain/streamflow.yml")
    tool = next(tool for uri, tool in translator.cwl_bundle.items() if uri.endswith("/copy.cwl"))
    destination = next(value for value in tool.inputs if value.id.split("#")[-1].split("/")[-1] == "destination")
    destination.inputBinding.valueFrom = "$(self + inputs.destination)"
    _, metadata = translate(translator)
    step = metadata["steps"]["s_process_items_0"]
    expression = step["arguments"][-1]["expression"]
    assert expression["bindings"] == {"self": {"value": "result.txt"}}
    namespace = {}
    exec(compiler.imports, namespace)
    exec(compiler.list_helper, namespace)
    exec(compiler.expression_function, namespace)
    exec(compiler.command_tool_function, namespace)
    values = {port: str(ROOT / "README.md") for port in step["inputs"]}
    bindings = namespace["_resolve_bindings"](step["bindings"], values, input_types=step["inputs"])
    assert namespace["_evaluate_value"](expression, bindings, values, input_types=step["inputs"]) == "result.txtresult.txt"


def test_file_defaults_still_have_data_for_staging():
    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-1/plain/streamflow.yml")
    region = translator.build_region_tree()
    invocation = region.invocations[0]
    invocation.defaults["destination"] = {"class": "File", "path": str(ROOT / "README.md")}
    invocation.input_types["destination"] = "file"
    translator.build_region_tree = lambda: region
    source, metadata = translate(translator)
    assert "d_default_process_items_destination" in metadata["dependencies"]
    assert "p_default_process_items_destination" in source


def test_default_used_as_scatter_dimension_remains_data():
    from dataclasses import replace

    translator = CWLTranslator(ROOT / "examples/cwl/pipeline/depth-1/plain/streamflow.yml")
    region = translator.build_region_tree()
    invocation = region.invocations[0]
    invocation.scatter = replace(invocation.scatter, inputs=("sample", "destination"))
    invocation.input_bindings["destination"] = ()
    invocation.defaults["destination"] = ["first.txt", "second.txt"]
    translator.build_region_tree = lambda: region
    source, metadata = translate(translator)
    dependency = metadata["dependencies"]["d_default_process_items_destination"]
    assert dependency == {"type": "list[string]", "value": ["first.txt", "second.txt"]}
    assert "p_default_process_items_destination" in source
    step = metadata["steps"]["s_process_items_0"]
    assert "port" in step["bindings"]["inputs"]["object"]["destination"]
