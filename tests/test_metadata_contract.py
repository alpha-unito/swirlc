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
                "inputPorts": ["p_in"],
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
    with pytest.raises(ValueError, match="outside its inputPorts"):
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
    step.pop("inputPorts")
    step["outputs"] = {"p_root": {"dataName": "d_out", "glob": "result.txt"}}
    assert SwirlValidator().validate(config) is config


def test_gather_cannot_reference_missing_dispatch():
    config = metadata()
    config["steps"]["gather"] = {
        "displayName": "gather", "type": "scatter_gather", "inputPorts": [],
        "outputs": {}, "operationId": "scatter:test", "shapeFrom": ["missing"],
        "scope": "root", "scatterMethod": "dotproduct",
        "order": "declaration_order_coordinates", "validation": "expected_keys_without_duplicates",
        "emptyShape": "retain_all_dimension_cardinalities", "routes": [], "collections": {},
        "completion": "all_source_eofs_then_gather_then_acknowledged_publications",
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
