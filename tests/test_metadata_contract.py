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
