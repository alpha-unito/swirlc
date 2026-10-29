from __future__ import annotations

import json
from collections.abc import MutableMapping
from typing import TYPE_CHECKING

from importlib_resources import files
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from ruamel.yaml import YAML

if TYPE_CHECKING:
    from typing import Any


def handle_errors(errors):
    errors = list(sorted(errors, key=str))
    if not errors:
        return
    raise Exception(
        "The SWIRL configuration is invalid because:\n{error_msgs}".format(
            error_msgs="\n".join([f" - {err}" for err in errors])
        )
    )


_CONFIGS = {
    "v1.0": "schemas/config/v1.0/config_schema.json",
    "v1.1": "schemas/config/v1.1/config_schema.json",
}


class SwirlSchema:
    def __init__(self):
        self.registry: Registry = Registry()
        for version in _CONFIGS.keys():
            self.add_schema(
                files(__package__)
                .joinpath("schemas")
                .joinpath(version)
                .joinpath("config_schema.json")
                .read_text("utf-8")
            )
        self.registry = self.registry.crawl()

    def add_schema(self, schema: str) -> Resource:
        resource = Resource.from_contents(json.loads(schema))
        self.registry = resource @ self.registry
        return resource

    def get_config(self, version: str) -> Resource:
        if version not in _CONFIGS:
            raise Exception(
                f"Version {version} is unsupported."
            )
        return self.registry.get(_CONFIGS[version])


class SwirlValidator:
    def __init__(self) -> None:
        super().__init__()
        self.schema: SwirlSchema = SwirlSchema()
        self.yaml = YAML(typ="safe")

    def validate_file(self, streamflow_file: str) -> MutableMapping[str, Any]:
        with open(streamflow_file) as f:
            streamflow_config = self.yaml.load(f)
        return self.validate(streamflow_config)

    def validate(self, swirl_file: MutableMapping[str, Any]):
        if not isinstance(swirl_file, MutableMapping):
            raise Exception("The SWIRL configuration must be a mapping.")
        if "version" not in swirl_file:
            raise Exception(
                "The `version` clause is mandatory."
            )
        config = self.schema.get_config(swirl_file["version"]).contents
        cls = validator_for(config)
        validator = cls(config, registry=self.schema.registry)
        handle_errors(validator.iter_errors(swirl_file))
        if swirl_file["version"] == "v1.1":
            self._validate_references(swirl_file)
        return swirl_file

    @staticmethod
    def _validate_references(config):
        steps = config.get("steps", {})
        dependencies = config.get("dependencies", {})
        descriptors = list(steps.items()) + [(f"condition {name}", spec) for name, spec in config.get("conditions", {}).items() if spec.get("type") == "expression"]
        for name, step in descriptors:
            inputs = step.get("inputs")
            referenced = [argument["valueFrom"] for argument in step.get("arguments", [])
                          if "valueFrom" in argument]
            def binding_ports(value):
                if isinstance(value, dict):
                    for field, item in value.items():
                        if field == "bindings":
                            yield from ports_in_bindings(item)
                        elif field not in ("value", "schema", "inputSchemas", "default"):
                            yield from binding_ports(item)
                elif isinstance(value, list):
                    for item in value:
                        yield from binding_ports(item)
            def ports_in_bindings(bindings):
                for spec in bindings.values():
                    if "port" in spec:
                        yield spec["port"]
                    elif "object" in spec:
                        yield from ports_in_bindings(spec["object"])
                    elif "items" in spec:
                        for item in spec["items"]:
                            yield from ports_in_bindings({"item": item})
            binding_references = list(binding_ports(step))
            if binding_references and inputs is None and config.get("version") == "v1.1":
                raise ValueError(f"Step {name} expression bindings require typed inputs declarations.")
            referenced += binding_references
            if inputs is not None and any(port not in inputs for port in referenced):
                raise ValueError(f"Step {name} references an input outside its inputs.")
            if "prepare" in step:
                output = step["prepare"]["output"]
                if set(step.get("outputs", {})) != {output}:
                    raise ValueError(f"Step {name} preparation must declare exactly its output {output}.")
                if any(field in step for field in ("command", "expression", "when", "type")):
                    raise ValueError(f"Step {name} preparation cannot also execute another operation.")
            for port in step.get("outputNames", {}).values():
                if port not in step.get("outputs", {}):
                    raise ValueError(f"Step {name} outputNames references an unknown output {port}.")
            names = set(step.get("bindings", {}).get("inputs", {}).get("object", {}))
            names.update(step.get("expression", {}).get("bindings", {}).get("inputs", {}).get("object", {}))
            names.update(step.get("inputSchemas", {}))
            if any(argument["input"] not in names for argument in step.get("arguments", []) if "input" in argument):
                raise ValueError(f"Step {name} argument references an unknown input name.")
            for field in ("inputOptions", "inputTransforms"):
                if any(input_name not in names for input_name in step.get(field, {})):
                    raise ValueError(f"Step {name} {field} references an unknown input name.")
            for output in step.get("outputs", {}).values():
                if "dataName" in output and output["dataName"] not in dependencies:
                    raise ValueError(f"Step {name} references unknown dependency {output['dataName']}.")
            for helper in step.get("shapeFrom", []) + step.get("keySpace", {}).get("dispatches", []):
                descriptor = steps.get(helper)
                if descriptor is None or descriptor.get("type") != "scatter_dispatch":
                    raise ValueError(f"Step {name} references unknown dispatch {helper}.")
                if descriptor.get("operationId") != step.get("operationId"):
                    raise ValueError(f"Step {name} references a dispatch owned by another operation.")
