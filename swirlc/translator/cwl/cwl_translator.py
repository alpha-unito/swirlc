from __future__ import annotations

# python tmp_main.py translate --language cwl /home/tommo/Coding/ALPHA/swirlc/examples/cwl/basic/main.cwl --outdir /home/tommo/Coding/ALPHA/swirlc/build
import re
import sys
from collections import Counter
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO
from urllib.parse import unquote, urlsplit

import cwl_utils
from cwl_utils.parser import load_document_by_uri
from ruamel.yaml import YAML

from swirlc.core.translator import AbstractTranslator

# Fallback used when a CWL type cannot be resolved to a SWIRL type.
DATA_TYPE = "file"

# Map CWL scalar type names to SWIRL base types.
_CWL_SCALAR_TO_SWIRL = {
    "File": "file",
    "Directory": "directory",
    "string": "string",
    "int": "int",
    "long": "int",
    "boolean": "bool",
}
_SCATTER_METHODS = {"dotproduct", "flat_crossproduct", "nested_crossproduct"}


def _keyed_data(name: str, task_id: str) -> str:
    """Render a payload reference retaining its replica's bound task key."""
    return f"(?{name}, ?{task_id})"


def _generated_name(*parts: str) -> str:
    """Build a grammar-safe name from CWL names."""
    return "_".join(re.sub(r"[^a-zA-Z0-9_]", "_", part) for part in parts)


def _output_descriptor(data: str, data_type: str) -> dict:
    """Keep replica bindings separate from concrete dependency names."""
    if data.startswith("(?"):
        payload, key = data[1:-1].split(", ")
        return {"binding": {"payload": payload[1:], "key": key[1:], "type": data_type}}
    return {"dataName": data}


def _scoped_port(port: str, parent_keys: tuple[str, ...]) -> str:
    """Identify a logical channel by its operation and full parent key path."""
    base = port.split("[", 1)[0]
    return f"{base}[{', '.join('?' + key for key in parent_keys)}]" if parent_keys else base


@dataclass(frozen=True)
class DeploymentTarget:
    """A normalized StreamFlow execution target."""

    deployment: str | None
    service: str | None = None


@dataclass(frozen=True)
class StreamFlowBindings:
    """Normalized bindings, matched against absolute CWL step paths."""

    default: tuple[DeploymentTarget, ...]
    by_path: dict[str, tuple[DeploymentTarget, ...]]

    def targets_for(self, path: str) -> tuple[DeploymentTarget, ...]:
        path = _absolute_cwl_path(path)
        for candidate in sorted(self.by_path, key=len, reverse=True):
            if path == candidate or path.startswith(candidate + "/"):
                return self.by_path[candidate]
        return self.default

    def target_for(self, path: str) -> DeploymentTarget | None:
        return next(iter(self.targets_for(path)), None)


@dataclass(frozen=True)
class ScatterSpec:
    inputs: tuple[str, ...]
    method: str
    region_id: str


@dataclass
class Invocation:
    """One CWL workflow step, before SWIRL lowering."""

    path: str
    process: object
    input_bindings: dict[str, tuple[str, ...]]
    outputs: dict[str, str]
    deployments: tuple[DeploymentTarget, ...]
    scatter: ScatterSpec | None = None
    input_types: dict[str, str] = field(default_factory=dict)
    output_types: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, object] = field(default_factory=dict)


@dataclass
class WorkflowRegion:
    """A CWL workflow boundary preserved for recursive lowering."""

    path: str
    inputs: dict[str, str | None]
    outputs: dict[str, tuple[str, ...]]
    invocations: list[Invocation] = field(default_factory=list)
    deployments: tuple[DeploymentTarget, ...] = ()
    parent: "WorkflowRegion | None" = None
    input_types: dict[str, str] = field(default_factory=dict)
    output_types: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, object] = field(default_factory=dict)


@dataclass
class LoweringContext:
    """Mutable state shared by recursive CWL lowering."""

    region: WorkflowRegion
    controller: str = "l0"
    task_id: str | None = None
    task_keys: tuple[str, ...] = ()
    available: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    value_locations: dict[str, str] = field(default_factory=dict)
    fragments: dict[str, list[str]] = field(default_factory=dict)
    steps: dict[str, dict] = field(default_factory=dict)
    dependencies: dict[str, dict] = field(default_factory=dict)
    locations: dict[str, dict] = field(default_factory=dict)
    location_by_deployment: dict[str, str] = field(default_factory=dict)
    datasets: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    scatter_regions: list[Invocation] = field(default_factory=list)
    scatter_scopes: dict[str, dict] = field(default_factory=dict)

    def child(
        self,
        region: WorkflowRegion,
        *,
        controller: str | None = None,
        task_id: str | None = None,
    ) -> "LoweringContext":
        return LoweringContext(
            region=region,
            controller=controller or self.controller,
            task_id=self.task_id if task_id is None else task_id,
            task_keys=(
                self.task_keys + (task_id,)
                if task_id is not None and task_id != self.task_id else self.task_keys
            ),
            available=self.available.copy(),
            value_locations=self.value_locations.copy(),
            fragments=self.fragments,
            steps=self.steps,
            dependencies=self.dependencies,
            locations=self.locations,
            location_by_deployment=self.location_by_deployment,
            datasets=self.datasets,
            scatter_regions=self.scatter_regions,
            scatter_scopes=self.scatter_scopes,
        )


def _absolute_cwl_path(path: str) -> str:
    """Normalize a StreamFlow/CWL path without losing nested components."""
    stripped = path.strip("/")
    return f"/{stripped}" if stripped else "/"


def _normalize_bindings(streamflow_config: MutableMapping) -> StreamFlowBindings:
    """Normalize every binding to an ordered tuple of deployment targets."""
    workflows = streamflow_config.get("workflows", {})
    first_workflow = next(iter(workflows.values()), {})
    default = ()
    by_path = {}
    for binding in first_workflow.get("bindings", []):
        step = binding.get("step")
        if step is None:
            continue
        raw_targets = binding.get("target") or []
        if isinstance(raw_targets, dict):
            raw_targets = [raw_targets]
        if not isinstance(raw_targets, list):
            continue
        if any(
            "locations" in target for target in raw_targets if isinstance(target, dict)
        ):
            raise ValueError(
                f"Binding {step!r} uses 'locations'; list each deployment explicitly"
            )
        normalized = tuple(
            DeploymentTarget(target["deployment"], target.get("service"))
            for target in raw_targets
            if isinstance(target, dict) and target.get("deployment")
        )
        if not normalized:
            continue
        path = _absolute_cwl_path(str(step))
        if path == "/":
            default = normalized
        else:
            by_path[path] = normalized
    return StreamFlowBindings(default, by_path)


def _scatter_locations(
    coordinator: str,
    deployments: list[str],
    config: MutableMapping,
) -> tuple[dict[str, dict], dict[str, str]]:
    """Create exactly one SWIRL location for each selected deployment."""
    source = config.get("deployments", {})
    selected = list(dict.fromkeys([coordinator, *deployments]))
    missing = [name for name in selected if name not in source]
    if missing:
        raise ValueError(f"Unknown deployment(s): {', '.join(missing)}")

    def hostname(deployment: dict) -> str:
        if deployment.get("type", "local") == "slurm":
            wrapped = deployment.get("wraps")
            if wrapped in source:
                return hostname(source[wrapped])
        nodes = deployment.get("config", {}).get("nodes", [])
        return nodes[0] if nodes else "127.0.0.1"

    def ssh_config(deployment: dict) -> dict:
        if deployment.get("type", "local") == "slurm":
            wrapped = deployment.get("wraps")
            return ssh_config(source[wrapped]) if wrapped in source else {}
        return deployment.get("config", {}) if deployment.get("type") == "ssh" else {}

    locations = {}
    location_by_deployment = {}
    for index, name in enumerate(selected):
        location = f"l{index}"
        deployment = source[name]
        details = {
            "hostname": hostname(deployment),
            "port": deployment.get("port", 35050),
        }
        if deployment.get("type") in {"ssh", "slurm"}:
            details["type"] = deployment["type"]
        if deployment.get("workdir"):
            details["workdir"] = deployment["workdir"]
        ssh = ssh_config(deployment)
        for source_key, target_key in (
            ("username", "username"),
            ("sshKey", "sshKey"),
            ("checkHostKey", "checkHostKey"),
        ):
            if source_key in ssh:
                details[target_key] = ssh[source_key]
        locations[location] = {"deployment": details}
        location_by_deployment[name] = location
    return locations, location_by_deployment


def _render_location_traces(
    locations: MutableMapping[str, dict],
    fragments: MutableMapping[str, list[str]],
    datasets: MutableMapping[str, str] | None = None,
) -> str:
    """Emit one location declaration, with parallel fragments when needed."""
    datasets = datasets or {}
    rendered = []
    for location in locations:
        bodies = fragments.get(location, [])
        if not bodies:
            continue
        trace = (
            bodies[0] if len(bodies) == 1 else "(\n" + "\n) |\n(\n".join(bodies) + "\n)"
        )
        rendered.append(f"<{location}, {{{datasets.get(location, '')}}},\n{trace}\n>")
    return " |\n\n".join(rendered) + "\n"


def _load_workflow_inputs(cwl_file: Path, streamflow_config: MutableMapping) -> dict:
    """Load the configured CWL job object, if present."""
    workflows = streamflow_config.get("workflows", {})
    first_workflow = next(iter(workflows.values()), {})
    settings = first_workflow.get("config", {}).get("settings")
    if not settings:
        return {}
    path = cwl_file.parent / settings
    if not path.exists():
        return {}
    with open(path) as input_file:
        return YAML(typ="safe").load(input_file) or {}


def _coerce_cwl_value(value, value_type: str, base_dir: Path | None = None):
    """Coerce a CWL job value into the scalar/list form used by SWIRL."""
    if isinstance(value, dict) and (
        raw_path := value.get("path") or value.get("location")
    ):
        parsed = urlsplit(raw_path)
        if parsed.scheme and parsed.scheme != "file":
            raise ValueError(f"Unsupported CWL file URI: {raw_path}")
        path = Path(unquote(parsed.path) if parsed.scheme == "file" else raw_path)
        if base_dir is not None and not path.is_absolute():
            path = (base_dir / path).resolve()
        return str(path)
    inner_type = _list_inner_type(value_type)
    if inner_type is not None:
        return [_coerce_cwl_value(item, inner_type, base_dir) for item in (value or [])]
    if value_type == "int":
        return int(value)
    if value_type == "bool":
        return value if isinstance(value, bool) else str(value).lower() == "true"
    return str(value)


def _list_inner_type(data_type: str) -> str | None:
    """Return the inner type of a generic ``list[...]`` type string, else None."""
    if data_type.startswith("list[") and data_type.endswith("]"):
        return data_type[len("list[") : -1]
    return None


def _cwl_type_to_swirl(cwl_type) -> str:
    """Convert a cwl_utils type to a SWIRL type string.

    Handles scalars (``File`` -> ``file``), optional types (``File?``), arrays in
    every cwl form -- the ``File[]`` string shorthand, ``{type: array, items: ...}``
    dicts, and ``CommandInputArraySchema`` objects -- mapping them to the generic
    ``list[<inner>]`` form. Arrays nest recursively (``list[list[file]]``). Unions
    resolve to their first non-null member. Falls back to :data:`DATA_TYPE`.
    """
    if cwl_type is None:
        return DATA_TYPE

    # Union types: list of alternatives, e.g. ['null', 'File'].
    if isinstance(cwl_type, (list, tuple)):
        for member in cwl_type:
            if member not in ("null", None):
                return _cwl_type_to_swirl(member)
        return DATA_TYPE

    # Array schema object (cwl_utils CommandInput/OutputArraySchema).
    items = getattr(cwl_type, "items", None)
    obj_type = getattr(cwl_type, "type_", None) or getattr(cwl_type, "type", None)
    if items is not None and obj_type == "array":
        return f"list[{_cwl_type_to_swirl(items)}]"

    # Array schema dict, e.g. {"type": "array", "items": "File"}.
    if isinstance(cwl_type, dict):
        if cwl_type.get("type") == "array":
            return f"list[{_cwl_type_to_swirl(cwl_type.get('items'))}]"
        return DATA_TYPE

    if isinstance(cwl_type, str):
        t = cwl_type.rstrip("?")  # strip optional marker
        if t.endswith("[]"):
            return f"list[{_cwl_type_to_swirl(t[:-2])}]"
        return _CWL_SCALAR_TO_SWIRL.get(t, DATA_TYPE)

    return DATA_TYPE


def _is_optional_cwl_type(cwl_type) -> bool:
    if isinstance(cwl_type, list):
        return any(_is_optional_cwl_type(member) for member in cwl_type)
    if isinstance(cwl_type, str):
        return cwl_type == "null" or cwl_type.endswith("?")
    if isinstance(cwl_type, dict):
        return _is_optional_cwl_type(cwl_type.get("type"))
    obj_type = getattr(cwl_type, "type_", None) or getattr(cwl_type, "type", None)
    return _is_optional_cwl_type(obj_type) if obj_type is not None else False


def _command(tool: object) -> tuple[str, list[str]]:
    base = getattr(tool, "baseCommand", None)
    if isinstance(base, list):
        return (base[0] if base else "", [str(item) for item in base[1:]])
    return (base or "", [])


def _resolve_token(token: str, base_dir: Path) -> str:
    path = Path(token)
    candidate = (base_dir / path).resolve()
    return str(candidate) if not path.is_absolute() and candidate.exists() else token


def _resolve_glob(tool: object, pattern: str | None) -> str | None:
    if not pattern or "$(" not in pattern:
        return pattern
    for tool_input in getattr(tool, "inputs", []):
        name = _local_name(tool_input.id).split("/")[-1]
        default = getattr(tool_input, "default", None)
        if f"inputs.{name}" in pattern and default is not None:
            return str(default)
    return pattern


def _local_name(uri: str) -> str:
    """Extract the fragment (local name) from a CWL URI like file:///path#name/port."""
    return uri.split("#", 1)[-1] if "#" in uri else uri


def _workflow_local_source(source: str) -> str:
    """Strip cwl_utils' synthetic path for an inline ``run: Workflow`` input."""
    return source.rsplit("/run/", 1)[-1]


def load_cwl_workflow_recursive_uri(
    uri: Path | str | cwl_utils.parser.cwl_v1_2.Workflow,
    _visited: MutableMapping[Path | str, object] | None = None,
) -> MutableMapping[Path | str, object]:
    """Load a CWL document and all tools/subworkflows it references.

    Returns a flat dict mapping each document URI to its cwl_utils parsed object.
    """

    if _visited is None:
        _visited = {}

    if uri in _visited:
        return _visited

    print(f"Loading CWL document: {uri}")

    doc = load_document_by_uri(uri)
    _visited[uri] = doc

    if hasattr(doc, "steps"):  # Workflow — recurse into each step's run target
        for step in doc.steps:
            if isinstance(step.run, str):
                # A string `run` is a URI to another document (tool or
                # subworkflow); load it through the URI loader.
                load_cwl_workflow_recursive_uri(step.run, _visited)
            if isinstance(step.run, cwl_utils.parser.cwl_v1_2.Workflow):
                # Step: chromosome  run: <cwl_utils.parser.cwl_v1_2.Workflow object at 0x7b0493fecd70
                # Already loaded, but we can still recurse into its steps
                print(f"Recursing into subworkflow: {step.run.id}")
                load_cwl_workflow_recursive(step.run, _visited)

    return _visited


def load_cwl_workflow_recursive(
    workflow: cwl_utils.parser.cwl_v1_2.Workflow,
    _visited: MutableMapping[Path | str, object] | None = None,
) -> MutableMapping[Path | str, object]:
    """Load a CWL document and all tools/subworkflows it references.

    Returns a flat dict mapping each document URI to its cwl_utils parsed object.
    """

    if _visited is None:
        _visited = {}

    print(f"Loading CWL workflow: {workflow.id}")

    if workflow.id in _visited:
        return _visited

    _visited[workflow.id] = workflow

    for step in workflow.steps:
        if isinstance(step.run, str):
            load_cwl_workflow_recursive_uri(step.run, _visited)
            # Step: chromosome  run: <cwl_utils.parser.cwl_v1_2.Workflow object at 0x7b0493fecd70
        if isinstance(step.run, cwl_utils.parser.cwl_v1_2.Workflow):
            # Step: chromosome  run: <cwl_utils.parser.cwl_v1_2.Workflow object at 0x7b0493fecd70
            # Already loaded, but we can still recurse into its steps
            print(f"Recursing into subworkflow: {step.run.id}")
            load_cwl_workflow_recursive(step.run, _visited)

    return _visited


def _format_command(tool_obj) -> str:
    """Build a human-readable command string from a CommandLineTool."""
    base = tool_obj.baseCommand
    if isinstance(base, list):
        parts = list(base)
    elif base:
        parts = [base]
    else:
        parts = []

    bindings = []
    for inp in tool_obj.inputs:
        b = inp.inputBinding
        if b is None:
            continue
        port = _local_name(inp.id)
        prefix = b.prefix or ""
        pos = b.position if b.position is not None else 999
        if b.valueFrom:
            token = f"{prefix} <expr>" if prefix else "<expr>"
        else:
            token = f"{prefix} <{port}>" if prefix else f"<{port}>"
        bindings.append((pos, token.strip()))

    if tool_obj.arguments:
        for arg in tool_obj.arguments:
            if isinstance(arg, str):
                bindings.append((0, arg))
            elif hasattr(arg, "valueFrom") and arg.valueFrom:
                pos = arg.position if arg.position is not None else 0
                bindings.append((pos, f"<expr:{arg.valueFrom[:20]}>"))

    bindings.sort(key=lambda x: x[0])
    parts += [token for _, token in bindings]

    cmd = " ".join(parts)
    if tool_obj.stdout:
        cmd += f" > {tool_obj.stdout}"
    return cmd


def display_cwl_tool(tool_obj, indent: str = "      ") -> None:
    """Print inputs, outputs, and reconstructed command for a CommandLineTool."""
    print(f"{indent}command: {_format_command(tool_obj)}")

    print(f"{indent}inputs:")
    for inp in tool_obj.inputs:
        port = _local_name(inp.id)
        b = inp.inputBinding
        binding_info = ""
        if b:
            if b.prefix:
                binding_info = f"  prefix={b.prefix}"
            if b.position is not None:
                binding_info += f"  pos={b.position}"
        print(f"{indent}  {port}: {inp.type_}{binding_info}")

    print(f"{indent}outputs:")
    for out in tool_obj.outputs:
        port = _local_name(out.id)
        glob = out.outputBinding.glob if out.outputBinding else None
        print(f"{indent}  {port}: {out.type_}  glob={glob}")

    if tool_obj.stdout:
        print(f"{indent}stdout: {tool_obj.stdout}")


def _display_cwl_workflow_indented(
    cwl_obj, bundle: MutableMapping | None, indent: str
) -> None:
    p = lambda s: print(f"{indent}{s}")  # noqa: E731
    p(f"Subworkflow: {_local_name(cwl_obj.id) if cwl_obj.id else '(unnamed)'}")

    p("  Inputs:")
    for inp in cwl_obj.inputs:
        p(f"    {_local_name(inp.id)}: {inp.type_}")

    p("  Outputs:")
    for out in cwl_obj.outputs:
        src = (
            _local_name(out.outputSource)
            if isinstance(out.outputSource, str)
            else out.outputSource
        )
        p(f"    {_local_name(out.id)}: {out.type_}  (from {src})")

    p("  Steps:")
    for step in cwl_obj.steps:
        name = _local_name(step.id)
        if isinstance(step.run, str):
            tool_label = _local_name(step.run).split("/")[-1]
        else:
            tool_label = type(step.run).__name__
        p(f"    [{name}]  run: {tool_label}")
        for inp in step.in_:
            port = _local_name(inp.id)
            src = _local_name(inp.source) if isinstance(inp.source, str) else inp.source
            p(f"      in  {port} <- {src}")
        for out_id in step.out:
            p(f"      out {_local_name(out_id)}")

        if bundle and isinstance(step.run, str) and step.run in bundle:
            run_obj = bundle[step.run]
            if hasattr(run_obj, "baseCommand"):
                display_cwl_tool(run_obj, indent=indent + "      | ")
            elif hasattr(run_obj, "steps"):
                _display_cwl_workflow_indented(
                    run_obj, bundle, indent=indent + "      | "
                )


def display_cwl_workflow(cwl_obj, bundle: MutableMapping | None = None) -> None:
    """Print a human-readable summary of a cwl_utils Workflow object."""
    print(f"Workflow: {_local_name(cwl_obj.id) if cwl_obj.id else '(unnamed)'}")
    print(f"  CWL version: {cwl_obj.cwlVersion}")

    print("\n  Inputs:")
    for inp in cwl_obj.inputs:
        print(f"    {_local_name(inp.id)}: {inp.type_}")

    print("\n  Outputs:")
    for out in cwl_obj.outputs:
        src = (
            _local_name(out.outputSource)
            if isinstance(out.outputSource, str)
            else out.outputSource
        )
        print(f"    {_local_name(out.id)}: {out.type_}  (from {src})")

    print("\n  Steps:")
    for step in cwl_obj.steps:
        name = _local_name(step.id)
        if isinstance(step.run, str):
            tool_label = _local_name(step.run).split("/")[-1]
        else:
            tool_label = type(step.run).__name__
        print(f"    [{name}]  run: {tool_label}")
        for inp in step.in_:
            port = _local_name(inp.id)
            src = _local_name(inp.source) if isinstance(inp.source, str) else inp.source
            print(f"      in  {port} <- {src}")
        for out_id in step.out:
            print(f"      out {_local_name(out_id)}")

        if bundle and isinstance(step.run, str) and step.run in bundle:
            run_obj = bundle[step.run]
            if hasattr(run_obj, "baseCommand"):
                display_cwl_tool(run_obj, indent="      | ")
            elif hasattr(run_obj, "steps"):
                _display_cwl_workflow_indented(run_obj, bundle, indent="      | ")


class CWLTranslator(AbstractTranslator):
    def __init__(self, streamflow_yml: Path):
        streamflow_path = Path(streamflow_yml).resolve()
        yaml = YAML()
        with open(streamflow_path) as f:
            sf_config = yaml.load(f)

        workflows = sf_config.get("workflows", {})
        if not workflows:
            raise ValueError(f"No workflows defined in {streamflow_path}")
        first_workflow = next(iter(workflows.values()))
        cwl_file_rel = first_workflow["config"]["file"]
        self.cwl_file = (streamflow_path.parent / cwl_file_rel).resolve()

        self.streamflow_config = sf_config
        self.bindings = _normalize_bindings(sf_config)
        self.workflow_inputs = _load_workflow_inputs(self.cwl_file, sf_config)
        root_uri = self.cwl_file.as_uri()
        self.cwl_bundle = load_cwl_workflow_recursive_uri(root_uri)
        self.cwl_obj = self.cwl_bundle[root_uri]

        display_cwl_workflow(self.cwl_obj, bundle=self.cwl_bundle)

    def build_region_tree(self) -> WorkflowRegion:
        """Build the recursive CWL IR without generating SWIRL text.

        Source references are normalized to full CWL paths here.  This keeps
        later lowering independent of CWL's locally-scoped step identifiers.
        """

        active_workflows: set[str] = set()

        def sources(value) -> tuple[str, ...]:
            if value is None:
                return ()
            if not isinstance(value, list):
                value = [value]
            return tuple(_local_name(source) for source in value)

        def build(wf, path: str, inputs: dict[str, str | None], parent):
            path = _absolute_cwl_path(path)
            workflow_id = str(getattr(wf, "id", id(wf)))
            if workflow_id in active_workflows:
                raise ValueError(f"Cyclic subworkflow reference at {path}")
            active_workflows.add(workflow_id)
            try:
                region = WorkflowRegion(
                    path=path,
                    inputs=inputs,
                    outputs={},
                    deployments=self.bindings.targets_for(path),
                    parent=parent,
                    input_types={
                        _local_name(workflow_input.id).split("/")[
                            -1
                        ]: _cwl_type_to_swirl(workflow_input.type_)
                        for workflow_input in wf.inputs
                    },
                    defaults={
                        _local_name(workflow_input.id).split("/")[
                            -1
                        ]: workflow_input.default
                        for workflow_input in wf.inputs
                        if getattr(workflow_input, "default", None) is not None
                    },
                )
                steps = {_local_name(step.id).split("/")[-1]: step for step in wf.steps}
                output_paths = {
                    name: {
                        _local_name(output).split("/")[
                            -1
                        ]: f"{path.rstrip('/')}/{name}/{_local_name(output).split('/')[-1]}"
                        for output in step.out
                    }
                    for name, step in steps.items()
                }

                def resolve(source: str) -> str:
                    source = _workflow_local_source(source)
                    if source in inputs:
                        return f"{path.rstrip('/')}/{source}" or f"/{source}"
                    step_name, separator, output_name = source.rpartition("/")
                    if not separator or step_name.split("/")[-1] not in output_paths:
                        raise ValueError(f"Unresolved source {source!r} at {path}")
                    producer = output_paths[step_name.split("/")[-1]]
                    if output_name not in producer:
                        raise ValueError(f"Unresolved source {source!r} at {path}")
                    return producer[output_name]

                for name, step in steps.items():
                    invocation_path = f"{path.rstrip('/')}/{name}" or f"/{name}"
                    bindings = {
                        _local_name(step_input.id).split("/")[-1]: tuple(
                            resolve(source) for source in sources(step_input.source)
                        )
                        for step_input in step.in_
                    }
                    raw_scatter = getattr(step, "scatter", None)
                    scatter_inputs = ()
                    if raw_scatter:
                        raw_scatter = (
                            [raw_scatter]
                            if isinstance(raw_scatter, str)
                            else raw_scatter
                        )
                        scatter_inputs = tuple(
                            _local_name(item).split("/")[-1] for item in raw_scatter
                        )
                        missing = set(scatter_inputs).difference(bindings)
                        if missing:
                            raise ValueError(
                                f"Scatter input(s) {sorted(missing)} missing at {invocation_path}"
                            )
                    method = getattr(step, "scatterMethod", None) or "dotproduct"
                    if scatter_inputs and method not in _SCATTER_METHODS:
                        raise ValueError(
                            f"Unsupported scatter method {method!r} at {invocation_path}"
                        )
                    scatter = (
                        ScatterSpec(
                            scatter_inputs,
                            method,
                            f"scatter:{invocation_path}",
                        )
                        if scatter_inputs
                        else None
                    )
                    run = step.run
                    process = self.cwl_bundle[run] if isinstance(run, str) else run
                    process_definition = process
                    invocation_inputs = {
                        _local_name(child_input.id).split("/")[-1]: next(
                            iter(
                                bindings.get(
                                    _local_name(child_input.id).split("/")[-1], ()
                                )
                            ),
                            None,
                        )
                        for child_input in getattr(process, "inputs", [])
                    }
                    if hasattr(process, "steps") and not hasattr(
                        process, "baseCommand"
                    ):
                        process = build(
                            process,
                            invocation_path,
                            invocation_inputs,
                            region,
                        )
                    region.invocations.append(
                        Invocation(
                            invocation_path,
                            process,
                            bindings,
                            output_paths[name],
                            self.bindings.targets_for(invocation_path),
                            scatter,
                            {
                                _local_name(process_input.id).split("/")[
                                    -1
                                ]: _cwl_type_to_swirl(process_input.type_)
                                for process_input in getattr(
                                    process_definition, "inputs", []
                                )
                            },
                            {
                                _local_name(process_output.id).split("/")[
                                    -1
                                ]: _cwl_type_to_swirl(process_output.type_)
                                for process_output in getattr(
                                    process_definition, "outputs", []
                                )
                            },
                            {
                                _local_name(process_input.id).split("/")[
                                    -1
                                ]: process_input.default
                                for process_input in getattr(
                                    process_definition, "inputs", []
                                )
                                if getattr(process_input, "default", None) is not None
                            },
                        )
                    )

                region.outputs = {
                    _local_name(output.id).split("/")[-1]: tuple(
                        resolve(source) for source in sources(output.outputSource)
                    )
                    for output in wf.outputs
                }
                region.output_types = {
                    _local_name(output.id).split("/")[-1]: _cwl_type_to_swirl(
                        output.type_
                    )
                    for output in wf.outputs
                }
                produced = {
                    output
                    for invocation in region.invocations
                    for output in invocation.outputs.values()
                }
                ordered: list[Invocation] = []
                pending = list(region.invocations)
                while pending:
                    ready = [
                        invocation
                        for invocation in pending
                        if all(
                            source not in produced
                            or any(source in done.outputs.values() for done in ordered)
                            for sources in invocation.input_bindings.values()
                            for source in sources
                        )
                    ]
                    if not ready:
                        paths = ", ".join(invocation.path for invocation in pending)
                        raise ValueError(f"Cyclic CWL step dependencies at {paths}")
                    ordered.extend(ready)
                    pending = [item for item in pending if item not in ready]
                region.invocations = ordered
                return region
            finally:
                active_workflows.remove(workflow_id)

        root_inputs = {
            _local_name(workflow_input.id).split("/")[
                -1
            ]: f"/{_local_name(workflow_input.id).split('/')[-1]}"
            for workflow_input in self.cwl_obj.inputs
        }
        return build(self.cwl_obj, "/", root_inputs, None)

    # Workflow boundaries are aliases; these methods handle every nesting depth.

    def _scatter_regions(self, region: WorkflowRegion) -> list[Invocation]:
        return [
            invocation
            for invocation in self._walk_invocations(region)
            if invocation.scatter
        ]

    def _scatter_hint(
        self, context: LoweringContext, region_id: str, phase: str, start: bool
    ) -> str:
        region = next(
            index
            for index, invocation in enumerate(context.scatter_regions)
            if invocation.scatter.region_id == region_id
        )
        return f"// @compiler {'begin' if start else 'end'} scatter.{phase} {region}"

    def _new_context(self, region: WorkflowRegion) -> LoweringContext:
        scatters = self._scatter_regions(region)
        coordinator = self.bindings.target_for("/")
        deployments = [
            target.deployment
            for invocation in self._walk_invocations(region)
            for target in invocation.deployments
            if target.deployment
        ]
        if coordinator and coordinator.deployment:
            coordinator_name = coordinator.deployment
        elif deployments:
            coordinator_name = deployments[0]
        else:
            coordinator_name = next(iter(self.streamflow_config.get("deployments", {})))
        locations, by_deployment = _scatter_locations(
            coordinator_name,
            list(dict.fromkeys(deployments)),
            self.streamflow_config,
        )
        return LoweringContext(
            region=region,
            controller=by_deployment[coordinator_name],
            fragments={location: [] for location in locations},
            locations=locations,
            location_by_deployment=by_deployment,
            datasets={location: [] for location in locations},
            scatter_regions=scatters,
        )

    def _walk_invocations(self, region: WorkflowRegion):
        for invocation in region.invocations:
            yield invocation
            if isinstance(invocation.process, WorkflowRegion):
                yield from self._walk_invocations(invocation.process)

    def _region_number(self, context: LoweringContext, invocation: Invocation) -> int:
        return context.scatter_regions.index(invocation)

    def _value(self, context: LoweringContext, source: str):
        try:
            return context.available[source]
        except KeyError as error:
            raise ValueError(f"Unavailable source {source!r} while lowering {context.region.path}") from error

    def _bind_region_inputs(
        self, region: WorkflowRegion, invocation: Invocation, context: LoweringContext
    ) -> None:
        for name, sources in invocation.input_bindings.items():
            if sources:
                context.available[f"{region.path.rstrip('/')}/{name}"] = self._value(
                    context, sources[0]
                )
                context.value_locations[f"{region.path.rstrip('/')}/{name}"] = context.value_locations.get(sources[0], context.controller)

    def _tool_trace(
        self,
        invocation: Invocation,
        context: LoweringContext,
        input_values: dict[str, tuple[str, str, str]] | None = None,
    ) -> str:
        tool = invocation.process
        local = invocation.path.rsplit("/", 1)[-1]
        follows_scatter = any(
            source in context.available
            and context.available[source][0].startswith("p_gather_data_")
            for sources in invocation.input_bindings.values()
            for source in sources
        )
        follows_scattered_subworkflow = any(
            item.scatter
            and isinstance(item.process, WorkflowRegion)
            and any(
                source in item.outputs.values()
                for sources in invocation.input_bindings.values()
                for source in sources
            )
            for item in context.region.invocations
        )
        step_name = (
            "s_post"
            if follows_scatter
            and not follows_scattered_subworkflow
            and context.task_id is None
            else (
                f"s_{_generated_name(invocation.path.strip('/'))}"
                if context.task_id else f"s_{local}"
            )
        )
        input_flow: list[str] = []
        arguments: list[tuple[int, str, dict]] = []
        expression_inputs = {}
        for tool_input in getattr(tool, "inputs", []):
            name = _local_name(tool_input.id).split("/")[-1]
            values = (
                [input_values[name]]
                if input_values is not None and name in input_values
                else [
                    self._value(context, source)
                    for source in invocation.input_bindings.get(name, ())
                    if source in context.available
                ]
            )
            for port, data, _ in values:
                input_flow.append(f"({port}, {data})")
            if not values:
                default = invocation.defaults.get(name)
                binding = getattr(tool_input, "inputBinding", None)
                if default is not None and binding is not None:
                    arguments.append(
                        (binding.position if binding.position is not None else 999, name, {"value": str(default)})
                    )
                continue
            port, _, data_type = values[0]
            binding = getattr(tool_input, "inputBinding", None)
            if getattr(tool, "expression", None) is not None:
                expression_inputs[name] = {"port": port, "type": data_type}
            if binding is not None:
                position = binding.position if binding.position is not None else 999
                if binding.prefix:
                    arguments.append((position, name, {"value": binding.prefix}))
                arguments.append((position, name, {"valueFrom": port}))

        outputs = {}
        output_flow = []
        expression_outputs = {}
        for tool_output in getattr(tool, "outputs", []):
            name = _local_name(tool_output.id).split("/")[-1]
            identity = (
                _generated_name(invocation.path.strip('/'), name)
                if context.task_id else f"{local}_{name}"
            )
            port = _scoped_port(f"p_{identity}", context.task_keys[:-1])
            base_data = (
                _generated_name(invocation.path.strip('/'), name)
                if context.task_id else identity
            )
            data = (
                _keyed_data(f"element_d_{base_data}", context.task_id)
                if context.task_id else f"d_{base_data}"
            )
            data_type = invocation.output_types.get(name, DATA_TYPE)
            binding = getattr(tool_output, "outputBinding", None)
            output = _output_descriptor(data, data_type)
            glob = _resolve_glob(tool, binding.glob if binding else None)
            if glob:
                output["glob"] = glob
            outputs[port] = output
            if not context.task_id:
                context.dependencies[data] = {"type": data_type}
            context.available[invocation.outputs[name]] = (port, data, data_type)
            context.value_locations[invocation.outputs[name]] = context.controller
            output_flow.append(f"({port}, {data})")
            expression_outputs[name] = port

        command, extras = _command(tool)
        step = {
            "displayName": local,
            "command": command,
            "arguments": [
                {"value": _resolve_token(extra, self.cwl_file.parent)} for extra in extras
            ]
            + [item[2] for item in sorted(arguments, key=lambda item: (item[0], item[1]))],
            "outputs": outputs,
        }
        expression = getattr(tool, "expression", None)
        if expression is not None:
            step.pop("command")
            step.pop("arguments")
            step["expression"] = {
                "source": expression,
                "inputs": expression_inputs,
                "outputs": expression_outputs,
            }
        context.steps[step_name] = step
        return (
            f"exec({step_name}, {{{', '.join(input_flow)}}} -> "
            f"{{{', '.join(output_flow)}}}, {{{context.controller}}})"
        )

    def _lower_invocation_body(
        self, invocation: Invocation, context: LoweringContext
    ) -> list[str]:
        if isinstance(invocation.process, WorkflowRegion):
            child = context.child(invocation.process)
            self._bind_region_inputs(invocation.process, invocation, child)
            traces = self.lower_region(invocation.process, child)
            for output_name, output_path in invocation.outputs.items():
                sources = invocation.process.outputs.get(output_name, ())
                if sources:
                    context.available[output_path] = self._value(child, sources[0])
                    context.value_locations[output_path] = child.value_locations.get(sources[0], child.controller)
            context.available.update(child.available)
            context.value_locations.update(child.value_locations)
            return traces
        # Ordinary producers may be placed independently of the scatter that
        # consumes their lists. Keep the value's location beside its binding.
        target = next(iter(invocation.deployments), None)
        location = (
            context.location_by_deployment.get(target.deployment, context.controller)
            if target and not context.task_id else context.controller
        )
        child = context.child(context.region, controller=location)
        receives = []
        for sources in invocation.input_bindings.values():
            for source in sources:
                producer = context.value_locations.get(source, context.controller)
                if producer == location:
                    continue
                port, data, _ = self._value(context, source)
                receive = (
                    f"recv({data} -> {port}, {producer}, {location})"
                    if data.startswith("(?")
                    else f"recv({port} -> {data}, {producer}, {location})"
                )
                if receive not in receives:
                    context.fragments[producer].append(
                        f"send({data} -> {port}, {producer}, {location})"
                    )
                    receives.append(receive)
        trace = self._tool_trace(invocation, child)
        if receives:
            setup = " | ".join(receives)
            trace = (f"({setup})" if len(receives) > 1 else setup) + "\n.\n" + trace
        context.available.update(child.available)
        context.value_locations.update(child.value_locations)
        if location != context.controller:
            context.fragments[location].append(trace)
            return []
        return [trace]

    def lower_invocation(
        self, invocation: Invocation, context: LoweringContext
    ) -> list[str]:
        if invocation.scatter:
            self.lower_scatter(invocation, context)
            return []
        return self._lower_invocation_body(invocation, context)

    def lower_region(
        self,
        region: WorkflowRegion,
        context: LoweringContext,
        workflow_output: TextIO | None = None,
        metadata_output: TextIO | None = None,
    ) -> list[str]:
        traces = []
        for invocation in region.invocations:
            traces.extend(self.lower_invocation(invocation, context))
        return traces

    def lower_scatter(self, invocation: Invocation, context: LoweringContext) -> None:
        index = self._region_number(context, invocation)
        task_id = f"key_{index}"
        inputs = []
        invariants = []
        for name, sources in invocation.input_bindings.items():
            if not sources:
                if name in invocation.scatter.inputs:
                    raise ValueError(
                        f"Scatter input {name!r} has no source at {invocation.path}"
                    )
                continue
            if len(sources) != 1:
                raise ValueError(
                    f"Multiple scatter input sources are not supported at {invocation.path}/{name}"
                )
            value = self._value(context, sources[0])
            (inputs if name in invocation.scatter.inputs else invariants).append(
                (name, value)
            )
        by_name = dict(inputs)
        if not invocation.scatter.inputs or any(
            name not in by_name for name in invocation.scatter.inputs
        ):
            raise ValueError(f"Scatter dimensions require input sources at {invocation.path}")
        inputs = [(name, by_name[name]) for name in invocation.scatter.inputs]
        fields = {}
        for name, (_, _, data_type) in inputs:
            inner_type = _list_inner_type(data_type)
            if inner_type is None:
                raise ValueError(
                    f"Scatter input {name!r} must be a list at {invocation.path}"
                )
            fields[name] = inner_type
        targets = [
            context.location_by_deployment[target.deployment]
            for target in invocation.deployments
            if target.deployment in context.location_by_deployment
        ]
        workers = list(dict.fromkeys(targets))
        descendant_workers = (
            {
                context.location_by_deployment[target.deployment]
                for item in self._walk_invocations(invocation.process)
                if item.scatter
                for target in item.deployments
                if target.deployment in context.location_by_deployment
            }
            if isinstance(invocation.process, WorkflowRegion)
            else set()
        )
        unreserved = [worker for worker in workers if worker not in descendant_workers]
        if unreserved:
            workers = unreserved
        if not workers:
            raise ValueError(
                f"Scatter step {invocation.path} requires deployment targets"
            )
        streams = []
        worker_values_base = dict(invariants)
        scope = context.scatter_scopes.setdefault(
            str(index),
            {
                "operation": invocation.scatter.region_id,
                "parentKeys": list(context.task_keys),
                **({"parentOperation": context.scatter_regions[
                    int(context.task_id.removeprefix("key_"))
                ].scatter.region_id} if context.task_id else {}),
                "activation": "parent_task_admission" if context.task_keys else "workflow_start",
                "routing": "synchronized_moves_by_full_key",
                "missingKey": "error_when_input_closed",
                "routes": [],
                "inputChannels": {},
            },
        )
        route = {"controller": context.controller, "workers": workers, "producers": {
            name: context.value_locations.get(invocation.input_bindings[name][0], context.controller)
            for name, _ in inputs
        }}
        if route not in scope["routes"]:
            scope["routes"].append(route)
        source_counts = Counter(value[1] for _, value in inputs)
        for input_index, (name, value) in enumerate(inputs):
            source = invocation.input_bindings[name][0]
            producer = context.value_locations.get(source, context.controller)
            port = _scoped_port(f"p_scatter_{input_index}_{index}", context.task_keys)
            source_name = value[1][2:].split(",", 1)[0] if value[1].startswith("(?") else value[1]
            if source_counts[value[1]] > 1:
                source_name = _generated_name(source_name, name)
            element = f"element_{source_name}"
            data = f"(?{element}, ?{task_id})"
            dispatch = f"_s_dispatch_{input_index}_{index}"
            collection = f"stream_{source_name}"
            streams.append((dispatch, port, data, producer, collection, value))
            worker_values_base[name] = (port, data, fields[name])
            scope["inputChannels"][name] = port
            context.steps[dispatch] = {
                "displayName": f"{invocation.path}/{name} ScatterDispatch",
                "type": "scatter_dispatch",
                "operationId": invocation.scatter.region_id,
                "dimension": name,
                "dimensions": list(invocation.scatter.inputs),
                "scatterMethod": invocation.scatter.method,
                "routes": scope["routes"],
                "key": {
                    "operation": invocation.scatter.region_id,
                    "parentKeys": list(context.task_keys),
                    "coordinates": "declaration_order",
                },
                # No payload transfer between dispatch helpers: share cardinalities
                # to expand Cartesian coordinates and validate aligned lengths.
                "keySpace": {
                    "dispatches": [f"_s_dispatch_{i}_{index}" for i in range(len(inputs))],
                    "cardinalities": "publish_before_expansion",
                    "validation": "equal_lengths" if invocation.scatter.method == "dotproduct" else "cartesian_shape",
                    "routing": "synchronized_moves_by_full_key",
                },
                "outputs": {
                    port: {"collection": {
                        "name": collection, "key": task_id, "type": fields[name],
                    }}
                },
            }
        worker_results = {}
        for worker in workers:
            worker_values = worker_values_base.copy()
            for name, (port, data, data_type) in invariants:
                producer = context.value_locations.get(invocation.input_bindings[name][0], context.controller)
                if producer != worker or context.task_keys:
                    worker_values[name] = (
                        _scoped_port(port, context.task_keys),
                        data,
                        data_type,
                    )
            child = context.child(
                (
                    invocation.process
                    if isinstance(invocation.process, WorkflowRegion)
                    else context.region
                ),
                controller=worker,
                task_id=task_id,
            )
            if isinstance(invocation.process, WorkflowRegion):
                for name, value in worker_values.items():
                    child.available[f"{invocation.process.path.rstrip('/')}/{name}"] = (
                        value
                    )
                    child.value_locations[f"{invocation.process.path.rstrip('/')}/{name}"] = worker
            body = (
                self.lower_region(invocation.process, child)
                if isinstance(invocation.process, WorkflowRegion)
                else [self._tool_trace(invocation, child, worker_values)]
            )
            results = {}
            if isinstance(invocation.process, WorkflowRegion):
                for name, sources in invocation.process.outputs.items():
                    if len(sources) != 1:
                        raise ValueError(
                            f"Scatter output {name!r} requires one source at {invocation.path}"
                        )
                    results[name] = self._value(child, sources[0])
            else:
                results = {
                    name: self._value(child, path)
                    for name, path in invocation.outputs.items()
                }
            if any(
                not data.startswith("(?") or not data.endswith(f", ?{task_id})")
                for _, data, _ in results.values()
            ):
                raise ValueError(
                    f"Scatter outputs must carry the current task key {task_id!r} at {invocation.path}; "
                    "ancestor-keyed or concrete passthrough outputs are not supported"
                )
            if not results:
                raise ValueError(
                    f"Scatter step {invocation.path} requires at least one output"
                )
            worker_results = results
            source_counts = Counter(port for port, _, _ in results.values())
            result_ports = {
                name: _scoped_port(
                    (
                        port
                        if source_counts[port] == 1
                        else f"p_result_{output_index}_{index}"
                    ),
                    context.task_keys,
                )
                for output_index, (name, (port, _, _)) in enumerate(results.items())
            }
            sends = [
                f"send({data} -> {result_ports[name]}, {worker}, {context.controller})"
                for name, (_, data, _) in results.items()
            ]
            eof_sends = [
                f"send(eof -> {port}, {worker}, {context.controller})"
                for port in result_ports.values()
            ]
            body_trace = "\n.\n".join(body + sends)
            eof_trace = " | ".join(eof_sends)
            if len(eof_sends) > 1:
                eof_trace = f"({eof_trace})"
            _, master_port, master_data, master_producer, _, _ = streams[0]
            matching = [
                f"recv({data} -> {port}, {producer}, {worker})"
                for _, port, data, producer, _, _ in streams[1:]
            ]
            matching_trace = " | ".join(matching)
            if len(matching) > 1:
                matching_trace = f"({matching_trace})"
            if matching_trace:
                matching_trace += " . "
            input_eofs = [
                f"recv(eof -> {port}, {producer}, {worker})"
                for _, port, _, producer, _, _ in streams
            ]
            closing = " . ".join(input_eofs + ["end()"])
            branch = (
                f"!(\n  (recv({master_data} -> {master_port}, {master_producer}, {worker}) . "
                f"{matching_trace}{body_trace})\n  +\n  "
                f"({closing})\n)"
                f"\n.\n{eof_trace}"
            )
            invariant_recvs = []
            invariant_transfers = []
            for port, data, _ in dict.fromkeys(value for _, value in invariants):
                producer = next(
                    context.value_locations.get(invocation.input_bindings[name][0], context.controller)
                    for name, value in invariants if value[:2] == (port, data)
                )
                if producer == worker and not context.task_keys:
                    continue
                port = _scoped_port(port, context.task_keys)
                send = f"send({data} -> {port}, {producer}, {worker})"
                invariant_transfers.append((producer, send))
                invariant_recvs.append(
                    f"recv({data} -> {port}, {producer}, {worker})"
                    if data.startswith("(?")
                    else f"recv({port} -> {data}, {producer}, {worker})"
                )
            if invariant_recvs:
                invariant_trace = " | ".join(invariant_recvs)
                if len(invariant_recvs) > 1:
                    invariant_trace = f"({invariant_trace})"
                branch = f"{invariant_trace}\n.\n{branch}"
            fragment = (
                f"{self._scatter_hint(context, invocation.scatter.region_id, 'worker', True)}\n"
                f"{branch}\n"
                f"{self._scatter_hint(context, invocation.scatter.region_id, 'worker', False)}"
            )
            if fragment not in context.fragments[worker]:
                context.fragments[worker].append(fragment)
                for producer, send in invariant_transfers:
                    context.fragments[producer].append(send)
        for output_index, (name, (_, source_data, source_type)) in enumerate(
            worker_results.items()
        ):
            source_port = result_ports[name]
            port = _scoped_port(f"p_gather_data_{output_index}_{index}", context.task_keys)
            base_data = _generated_name("d", invocation.path.strip("/"), name)
            data = (_keyed_data(base_data, context.task_id)
                    if context.task_id else base_data)
            depth = len(inputs) if invocation.scatter.method == "nested_crossproduct" else 1
            data_type = "list[" * depth + source_type + "]" * depth
            if not context.task_id:
                context.dependencies[data] = {"type": data_type}
            collection = f"stream_{base_data}"
            gather = f"_s_gather_{output_index}_{index}"
            context.steps[gather] = {
                "displayName": f"{invocation.path}/{name} ScatterGather",
                "type": "scatter_gather",
                "operationId": invocation.scatter.region_id,
                "scatterMethod": invocation.scatter.method,
                "order": "declaration_order_coordinates",
                "shapeFrom": [stream[0] for stream in streams],
                "collections": {source_port: {
                    "name": collection, "output": port,
                    "type": source_type, "read": "snapshot",
                }},
                "outputs": {port: _output_descriptor(data, data_type)},
            }
            scope.setdefault("resultChannels", {})[name] = source_port
            context.available[invocation.outputs[name]] = (port, data, data_type)
            context.value_locations[invocation.outputs[name]] = context.controller
            receives = [
                f"// @compiler begin gather_stream {collection} {worker} {source_port}\n(\n"
                f"!(\n  (recv({source_data} -> {source_port}, {worker}, {context.controller}))\n  +\n"
                f"  (recv(eof -> {source_port}, {worker}, {context.controller}) . end())\n)\n)\n"
                f"// @compiler end gather_stream {collection} {worker} {source_port}"
                for worker in workers
            ]
            receive_trace = "\n|\n".join(receives)
            if len(receives) > 1:
                receive_trace = f"(\n{receive_trace}\n)"
            fragment = (
                f"{receive_trace}\n.\n"
                f"exec({gather}, {{U({source_port}, {collection})}} -> {{({port}, {data})}}, {{{context.controller}}})"
            )
            if fragment not in context.fragments[context.controller]:
                context.fragments[context.controller].append(fragment)
        # Each dispatch is an independent producer-side continuation. Nested
        # templates inherit their enclosing parent's key bindings at admission.
        for dispatch, port, data, producer, collection, (source_port, source_data, _) in streams:
            distributors = [
                f"// @compiler begin scatter_stream {collection} {worker} {port}\n(\n"
                f"!(\n  (move({data} -> {port}, {producer}, {worker}))\n"
                f"  +[{port} has data]\n  (end())\n)\n.\n"
                f"send(eof -> {port}, {producer}, {worker})\n)\n"
                f"// @compiler end scatter_stream {collection} {worker} {port}"
                for worker in workers
            ]
            distribution = distributors[0] if len(distributors) == 1 else (
                "(\n" + "\n|\n".join(distributors) + "\n)"
            )
            fragment = (
                f"exec({dispatch}, {{({source_port}, {source_data})}} -> {{U({port}, {collection})}}, {{{producer}}})"
                f"\n.\n{distribution}"
            )
            if fragment not in context.fragments[producer]:
                context.fragments[producer].append(fragment)

    def translate(
        self, workflow_output: TextIO = sys.stdout, metadata_output: TextIO = sys.stdout
    ) -> None:
        region = self.build_region_tree()

        for invocation in self._scatter_regions(region):
            if invocation.scatter.method != "dotproduct" or len(invocation.scatter.inputs) < 2:
                continue
            lengths = []
            for name in invocation.scatter.inputs:
                sources = invocation.input_bindings.get(name, ())
                if len(sources) != 1 or sources[0].count("/") != 1:
                    break
                value = self.workflow_inputs.get(sources[0].lstrip("/"))
                if not isinstance(value, list):
                    break
                lengths.append(len(value))
            else:
                if len(set(lengths)) > 1:
                    raise ValueError(
                        f"dotproduct scatter inputs must have equal lengths at {invocation.path}"
                    )

        context = self._new_context(region)
        for workflow_input in self.cwl_obj.inputs:
            name = _local_name(workflow_input.id).split("/")[-1]
            port = f"p_{name}"
            data = f"d_{name}"
            data_type = _cwl_type_to_swirl(workflow_input.type_)
            raw = self.workflow_inputs.get(name, getattr(workflow_input, "default", ""))
            value = _coerce_cwl_value(raw, data_type, self.cwl_file.parent)
            context.dependencies[data] = {"type": data_type, "value": value}
            context.available[f"/{name}"] = (port, data, data_type)
            context.value_locations[f"/{name}"] = context.controller
            context.datasets[context.controller].append((port, data))

        main_trace = "\n.\n".join(self.lower_region(region, context))
        if main_trace:
            context.fragments[context.controller].append(main_trace)
        workflow_output.write(
            _render_location_traces(
                context.locations,
                context.fragments,
                {
                    location: ", ".join(f"({port}, {data})" for port, data in values)
                    for location, values in context.datasets.items()
                },
            )
        )
        YAML().dump(
            {
                "version": "v1.1",
                "steps": context.steps,
                "locations": context.locations,
                "dependencies": context.dependencies,
                "scatterRegions": {
                    str(index): {
                        "name": item.path,
                        "method": item.scatter.method,
                        "scatterPorts": list(item.scatter.inputs),
                        "scope": context.scatter_scopes[str(index)],
                    }
                    for index, item in enumerate(context.scatter_regions)
                },
            },
            metadata_output,
        )
