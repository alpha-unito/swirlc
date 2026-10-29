import copy

import pytest

from swirlc.config.validator import SwirlValidator


def metadata():
    return {
        "version": "v1.1",
        "dependencies": {"d_out": {"type": "file"}},
        "steps": {
            "s_copy": {
                "displayName": "copy",
                "inputs": {"p_in": {"type": "file"}},
                "command": "cp",
                "arguments": [{"valueFrom": "p_in"}],
                "outputs": {
                    "p_out": {"binding": {"payload": "item", "id": "root / ?iteration_1", "type": "file"}, "glob": "result.txt"},
                    "p_root": {"dataName": "d_out", "id": "root"},
                },
            }
        },
    }


def test_structured_outputs_and_owned_input_ports():
    config = metadata()
    assert SwirlValidator().validate(config) is config
    config["steps"]["s_copy"]["arguments"][0]["valueFrom"] = "p_other"
    with pytest.raises(ValueError, match="outside its inputs"):
        SwirlValidator().validate(config)


@pytest.mark.parametrize("mutate", [
    lambda step: step["outputs"]["p_out"]["binding"].pop("id"),
    lambda step: step["outputs"]["p_out"]["binding"].update(type="anything"),
    lambda step: step.update(unknownOption=True),
    lambda step: step["arguments"][0].update(expression="$(inputs.foo)"),
])
def test_unknown_and_incomplete_descriptors_are_rejected(mutate):
    config = copy.deepcopy(metadata())
    mutate(config["steps"]["s_copy"])
    with pytest.raises(Exception, match="configuration is invalid"):
        SwirlValidator().validate(config)


def test_missing_payload_dependency_is_rejected():
    config = metadata()
    config["dependencies"].clear()
    with pytest.raises(ValueError, match="unknown dependency"):
        SwirlValidator().validate(config)


def test_non_mapping_metadata_is_rejected():
    with pytest.raises(Exception, match="must be a mapping"):
        SwirlValidator().validate(None)


def test_ordinary_v10_descriptor_remains_valid():
    config = metadata()
    config["version"] = "v1.0"
    step = config["steps"]["s_copy"]
    step.pop("inputs")
    step["outputs"] = {"p_root": {"dataName": "d_out", "glob": "result.txt"}}
    assert SwirlValidator().validate(config) is config


def test_gather_cannot_reference_missing_dispatch():
    config = metadata()
    config["steps"]["gather"] = {
        "displayName": "gather", "type": "scatter_gather", "inputs": {},
        "outputs": {}, "operationId": "scatter:test", "shapeFrom": ["missing"],
        "scope": "root", "scatterMethod": "dotproduct",
        "routes": [], "collections": {},
    }
    with pytest.raises(ValueError, match="unknown dispatch"):
        SwirlValidator().validate(config)


def test_selected_slurm_service_options_are_preserved():
    config = metadata()
    config["locations"] = {"l0": {"deployment": {
        "type": "slurm", "hostname": "compute", "service": "copy",
        "slurm": {"partition": "cpu", "nodes": 1, "ntasks": 2, "time": "00:10:00"},
    }}}
    assert SwirlValidator().validate(config) is config


def expression(source):
    return {"language": "javascript", "source": source}


def test_named_tool_input_map_and_expression_descriptors_are_valid():
    config = metadata()
    step = config["steps"]["s_copy"]
    step.update(bindings={"inputs": {"object": {"source": {"port": "p_in"}}}},
                stdout=expression("return inputs.source.nameroot + '.txt';"), arguments=[
                    {"value": "--first", "position": -1},
                    {"expression": expression("return inputs.source.nameroot;"), "position": 0,
                     "prefix": "--name=", "separate": False, "shellQuote": True},
                    {"valueFrom": "p_in", "position": 1},
                ])
    step["outputs"]["p_out"].update(glob=[expression("return inputs.source.nameroot + '.txt';")],
                                     readContents=True, evaluate=expression("return self[0];"))
    assert SwirlValidator().validate(config) is config


@pytest.mark.parametrize("mutate, message", [
    (lambda binding: binding.update(port="p_foreign"), "outside its inputs"),
    (lambda binding: binding.pop("port"), "configuration is invalid"),
    (lambda binding: binding.update(unknown=True), "configuration is invalid"),
    (lambda binding: binding.update(type="unsupported"), "configuration is invalid"),
])
def test_named_tool_input_map_is_strict(mutate, message):
    config = metadata()
    step = config["steps"]["s_copy"]
    binding = {"port": "p_in"}
    step.update(bindings={"inputs": {"object": {"source": binding}}})
    mutate(binding)
    with pytest.raises(Exception, match=message):
        SwirlValidator().validate(config)


@pytest.mark.parametrize("argument", [
    {"value": "literal", "expression": "$(inputs.source)"},
    {"valueFrom": "p_in", "expression": "$(inputs.source)"},
    {"value": "literal", "valueFrom": "p_in"},
    {"value": "literal", "valueFrom": "p_in", "expression": "$(inputs.source)"},
    {"position": 0}, {"expression": ""},
])
def test_argument_requires_exactly_one_value_descriptor(argument):
    config = metadata()
    config["steps"]["s_copy"]["arguments"] = [argument]
    with pytest.raises(Exception, match="configuration is invalid"):
        SwirlValidator().validate(config)


@pytest.mark.parametrize("inputs", [
    {"p_in": {}},
    {"p_in": {"type": "unsupported"}},
    {"p_in": {"type": "file", "unknown": True}},
])
def test_input_declarations_require_a_supported_type(inputs):
    config = metadata()
    config["steps"]["s_copy"]["inputs"] = inputs
    with pytest.raises(Exception, match="configuration is invalid"):
        SwirlValidator().validate(config)


@pytest.mark.parametrize("field, value", [
    ("inputPorts", ["p_in"]), ("fileInputs", {"p_in": "file"}),
])
def test_duplicate_legacy_input_declarations_are_rejected(field, value):
    config = metadata()
    config["steps"]["s_copy"][field] = value
    with pytest.raises(Exception, match="configuration is invalid"):
        SwirlValidator().validate(config)


def test_test_only_scatter_region_metadata_is_rejected():
    config = metadata()
    config["scatterRegions"] = {}
    with pytest.raises(Exception, match="configuration is invalid"):
        SwirlValidator().validate(config)


def test_expression_port_binding_requires_an_input_declaration():
    config = metadata()
    step = config["steps"]["s_copy"]
    step.pop("inputs")
    step["bindings"] = {"sample": {"port": "p_in"}}
    with pytest.raises(ValueError, match="require typed inputs declarations"):
        SwirlValidator().validate(config)


def structured_metadata():
    config = metadata()
    schema = {"type": "array", "items": {"type": "record", "fields": {
        "file": {"type": "file"}, "note": {"type": "string", "nullable": True},
    }}}
    config["dependencies"]["d_records"] = {"type": "list[file]", "schema": schema,
        "value": [{"file": {"class": "File", "contents": "data"}, "note": None}]}
    step = config["steps"]["s_copy"]
    step.update(
        bindings={"inputs": {"object": {"source": {"items": [
            {"port": "p_in"}, {"value": None}, {"object": {"nested": {"port": "p_in"}}},
        ]}}}},
        inputSchemas={"source": schema},
        inputOptions={"source": {"readContents": True, "secondaryFiles": [
            {"pattern": ".meta", "required": True},
            {"pattern": expression("return '.index';"), "required": expression("return true;")},
        ]}},
        inputTransforms={"source": {"select": "all_non_null", "merge": "merge_nested",
                                    "evaluate": expression("return self;")}},
        staging=[{"entry": expression("return inputs.source;"), "name": "bundle"},
                 {"entry": "generated text", "name": expression("return 'script.py';")},
                 {"entry": {"class": "Directory", "listing": []}}],
        acceptedExitCodes=[0, 1], when=expression("return true;"),
        outputNames={"result": "p_out"},
    )
    step["outputs"]["p_out"].update(schema=schema, secondaryFiles=[{"pattern": ".meta", "required": True}])
    return config


def test_structured_cwl_execution_descriptors_are_valid():
    config = structured_metadata()
    assert SwirlValidator().validate(config) is config


@pytest.mark.parametrize("field, value", [
    ("inputSchemas", {"source": {"type": "array"}}),
    ("inputSchemas", {"source": {"type": "record"}}),
    ("inputSchemas", {"source": {"type": "string", "items": {"type": "int"}}}),
    ("inputSchemas", {"source": {"type": "record", "fields": {"x": {"type": "unknown"}}}}),
    ("inputSchemas", {"source": {"type": "file", "nullable": "true"}}),
    ("acceptedExitCodes", [True]),
    ("acceptedExitCodes", [0, 0]),
    ("staging", [{"name": "missing-entry"}]),
    ("staging", [{"entry": "text", "writable": "true"}]),
    ("when", "$(true)"),
    ("inputTransforms", {"source": {"select": "unknown"}}),
    ("inputTransforms", {"source": {"merge": "unknown"}}),
    ("inputOptions", {"source": {"secondaryFiles": [{"pattern": ".meta"}]}}),
])
def test_structured_cwl_execution_descriptors_are_strict(field, value):
    config = structured_metadata()
    config["steps"]["s_copy"][field] = value
    with pytest.raises(Exception, match="configuration is invalid"):
        SwirlValidator().validate(config)


@pytest.mark.parametrize("field, value, message", [
    ("outputNames", {"result": "p_missing"}, "unknown output"),
    ("inputOptions", {"missing": {"readContents": True}}, "unknown input name"),
    ("inputTransforms", {"missing": {"select": "first_non_null"}}, "unknown input name"),
    ("bindings", {"inputs": {"items": [{"object": {"nested": {"port": "p_missing"}}}]}}, "outside its inputs"),
])
def test_structured_cwl_references_are_owned(field, value, message):
    config = structured_metadata()
    config["steps"]["s_copy"][field] = value
    with pytest.raises(ValueError, match=message):
        SwirlValidator().validate(config)


def test_literal_record_field_names_are_not_expression_references(tmp_path):
    from ruamel.yaml import YAML

    from swirlc.main import main

    config = {
        "version": "v1.1", "locations": {"l0": {}},
        "dependencies": {"d_in": {"type": "file", "value": {"port": "data", "bindings": {"port": "also data"}},
            "schema": {"type": "record", "fields": {"port": {"type": "string"},
                        "bindings": {"type": "record", "fields": {"port": {"type": "string"}}}}}},
            "d_out": {"type": "file"}},
        "steps": {"s_copy": {"displayName": "copy", "inputs": {"p_in": {"type": "file"}},
            "bindings": {"inputs": {"object": {"value": {"value": {"port": "literal", "bindings": {"port": "literal"}}}}}},
            "expression": {"language": "javascript", "source": "return {value: inputs.value};", "outputs": {"value": "p_out"}},
            "outputs": {"p_out": {"dataName": "d_out", "id": "root", "schema": {"type": "record", "fields": {"port": {"type": "string"}}}}}}},
    }
    SwirlValidator().validate(config)
    source = tmp_path / "workflow.swirl"
    source.write_text("<l0, {(p_in,(d_in,root))}, exec(s_copy,{(p_in,(d_in,root))}->{(p_out,(d_out,root))},{l0})>")
    description = tmp_path / "metadata.yml"
    with description.open("w") as stream:
        YAML().dump(config, stream)
    assert main(["compile", str(source), str(description), "--outdir", str(tmp_path)]) == 0


def test_nested_secondary_declaration_survives_metadata_validation():
    config = structured_metadata()
    schema = {"type": "array", "items": {"type": "record", "fields": {
        "source": {"type": "file", "secondaryFiles": [{"pattern": ".meta", "required": True}]}}}}
    config["steps"]["s_copy"]["inputSchemas"]["record"] = schema
    assert SwirlValidator().validate(config) is config


def test_preparation_descriptor_and_field_binding_are_valid():
    config = metadata()
    step = config["steps"]["s_copy"]
    step.pop("command")
    step.pop("arguments")
    step["outputs"].pop("p_root")
    step["prepare"] = {"output": "p_out"}
    step["bindings"] = {"inputs": {"object": {"item": {"port": "p_in", "field": "item"}}}}
    assert SwirlValidator().validate(config) is config


@pytest.mark.parametrize("mutation,message", [
    ({"prepare": {"output": "missing"}}, "exactly its output"),
    ({"prepare": {"output": "p_out"}, "command": "true"}, "cannot also execute"),
])
def test_preparation_rejects_inconsistent_execution_descriptors(mutation, message):
    config = metadata()
    step = config["steps"]["s_copy"]
    step.pop("command")
    step.pop("arguments")
    step["outputs"].pop("p_root")
    step.update(mutation)
    with pytest.raises(ValueError, match=message):
        SwirlValidator().validate(config)
