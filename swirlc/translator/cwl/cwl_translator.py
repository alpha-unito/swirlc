from __future__ import annotations

# python tmp_main.py translate --language cwl /home/tommo/Coding/ALPHA/swirlc/examples/cwl/basic/main.cwl --outdir /home/tommo/Coding/ALPHA/swirlc/build
import re
import json
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


@dataclass(frozen=True)
class DataReference:
    """A payload dependency or binding, with its identity kept separately."""

    payload: str
    identity: str = "root"
    bound: bool = False

    def __str__(self) -> str:
        payload = f"?{self.payload}" if self.bound else self.payload
        return f"({payload}, {self.identity})"


def _keyed_data(name: str, task_id: str) -> DataReference:
    return DataReference(name, task_id, True)


def _generated_name(*parts: str) -> str:
    """Build a grammar-safe name from CWL names."""
    return "_".join(re.sub(r"[^a-zA-Z0-9_]", "_", part) for part in parts)


def _output_descriptor(data: DataReference, data_type: str) -> dict:
    """Keep payload dependencies separate from identity expressions."""
    if data.bound:
        return {"binding": {"payload": data.payload, "id": data.identity, "type": data_type}}
    return {"dataName": data.payload, "id": data.identity}


@dataclass
class EmittedFragment:
    """Owner-local composition; mutable tails hold acknowledged publications."""

    kind: str
    parts: list = field(default_factory=list)

    def __str__(self) -> str:
        parts = [str(part) for part in self.parts if part]
        parts = [part for part in parts if part]
        def grouped(part):
            if re.match(r"(?:exec|send|recv|move)\(", part):
                depth = 0
                for index in range(part.index("("), len(part)):
                    character = part[index]
                    depth += (character == "(") - (character == ")")
                    if depth == 0:
                        if index == len(part) - 1:
                            return part
                        break
            return f"(\n{part}\n)"

        if self.kind == "marked":
            return f"{parts[0]}\n{grouped(parts[1])}\n{parts[2]}\n"
        if self.kind == "hint":
            return "\n".join(parts) + "\n"
        if self.kind == "sequence":
            return "\n.\n".join(parts)
        if self.kind == "replication":
            return f"!(\n{grouped(parts[0])}\n+\n{grouped(parts[1])}\n)"
        if len(parts) == 1:
            return parts[0]
        return "(\n" + "\n|\n".join(grouped(part) for part in parts) + "\n)" if parts else ""

    def __bool__(self) -> bool:
        return bool(self.parts)


def _sequence(parts: list) -> EmittedFragment:
    return EmittedFragment("sequence", parts)


def _parallel(parts: list) -> EmittedFragment:
    return EmittedFragment("parallel", parts)


@dataclass
class OutputOccurrence:
    """One symbolic worker source, never a statically unrolled job occurrence."""

    context: "LoweringContext"
    value: tuple[str, DataReference, str]
    location: str
    publisher: EmittedFragment
    pending: "PendingGather | None" = None


@dataclass
class PendingGather:
    """An explicit scatter boundary awaiting materialization at a consumer."""

    invocation: "Invocation"
    index: int
    name: str
    output_index: int
    scope: tuple[str, ...]
    coordinate: str
    dispatches: list[str]
    sources: list[OutputOccurrence]
    value: tuple[str, DataReference, str]
    materialized: dict[str, OutputOccurrence] = field(default_factory=dict)


@dataclass
class ScatterWorker:
    """Fragments and source closure obligations owned by one worker scope."""

    context: "LoweringContext"
    parent: "LoweringContext"
    invocation: "Invocation"
    index: int
    scope: tuple[str, ...]
    prefix: tuple[str, ...]
    body: EmittedFragment
    openings: EmittedFragment
    closings: EmittedFragment
    result_begins: EmittedFragment
    result_eofs: EmittedFragment
    remote_controls: dict[str, tuple[list[str], list[str]]] = field(default_factory=dict)


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
    """Recursive owner state, ready values, pending boundaries and shared metadata.

    bound_path is the lexical binding environment, not a rendered-ID alias.
    Only pending materialization and explicit receives make streamed values ready.
    Publishers acknowledge copies; worker/service joins own their source EOFs.
    """

    region: WorkflowRegion
    controller: str = "l0"
    task_id: str | None = None
    available: dict[str, tuple[str, DataReference, str]] = field(default_factory=dict)
    value_locations: dict[str, str] = field(default_factory=dict)
    fragments: dict[str, list[str | EmittedFragment]] = field(default_factory=dict)
    steps: dict[str, dict] = field(default_factory=dict)
    conditions: dict[str, dict] = field(default_factory=dict)
    dependencies: dict[str, dict] = field(default_factory=dict)
    locations: dict[str, dict] = field(default_factory=dict)
    location_by_deployment: dict[DeploymentTarget, str] = field(default_factory=dict)
    datasets: dict[str, list[tuple[str, DataReference]]] = field(default_factory=dict)
    scatter_regions: list[Invocation] = field(default_factory=list)
    bound_path: tuple[str, ...] = ()
    pending: dict[str, PendingGather] = field(default_factory=dict)
    publishers: dict[str, EmittedFragment] = field(default_factory=dict)
    workers: list[ScatterWorker] = field(default_factory=list)
    worker_owner: ScatterWorker | None = None
    tool_counts: dict[str, int] = field(default_factory=dict)

    def child(
        self,
        region: WorkflowRegion,
        *,
        controller: str | None = None,
        task_id: str | None = None,
        fragments: dict[str, list[str | EmittedFragment]] | None = None,
    ) -> "LoweringContext":
        return LoweringContext(
            region=region,
            controller=controller or self.controller,
            task_id=self.task_id if task_id is None else task_id,
            available=self.available.copy(),
            value_locations=self.value_locations.copy(),
            fragments=self.fragments if fragments is None else fragments,
            steps=self.steps,
            conditions=self.conditions,
            dependencies=self.dependencies,
            locations=self.locations,
            location_by_deployment=self.location_by_deployment,
            datasets=self.datasets,
            scatter_regions=self.scatter_regions,
            bound_path=self.bound_path,
            pending=self.pending.copy(),
            publishers=self.publishers.copy(),
            workers=self.workers,
            worker_owner=self.worker_owner,
            tool_counts=self.tool_counts,
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
    coordinator: DeploymentTarget,
    deployments: list[DeploymentTarget],
    config: MutableMapping,
) -> tuple[dict[str, dict], dict[DeploymentTarget, str]]:
    """Keep selected deployment/service targets distinct, preserving SSH wrapping."""
    source = config.get("deployments", {})
    selected = list(dict.fromkeys([coordinator, *deployments]))
    missing = [target.deployment for target in selected if target.deployment not in source]
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
    for index, target in enumerate(selected):
        name = target.deployment
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
        if target.service is not None:
            services = deployment.get("config", {}).get("services", {})
            if target.service not in services:
                raise ValueError(f"Unknown service {target.service!r} in deployment {name!r}")
            details["service"] = target.service
            if deployment.get("type") == "slurm":
                details["slurm"] = dict(services[target.service])
        locations[location] = {"deployment": details}
        location_by_deployment[target] = location
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
            bodies[0] if len(bodies) == 1 else "(\n" + "\n) |\n(\n".join(map(str, bodies)) + "\n)"
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
        t = _local_name(cwl_type).rstrip("?")  # cwl_utils also URI-qualifies array item shorthand
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
    # Dynamic globs are evaluated with invocation inputs, never tool defaults.
    return pattern


def _lower_expression(source: str, bindings: dict | None = None) -> dict:
    """Translate CWL substitutions to an ordinary JavaScript function body."""
    pieces = []
    literal = []
    index = 0
    while index < len(source):
        if source[index] == "\\" and index + 1 < len(source) and source[index + 1] in "\\$":
            literal.append(source[index + 1])
            index += 2
            continue
        if source[index:index + 2] not in ("$(", "${"):
            literal.append(source[index])
            index += 1
            continue
        if literal:
            pieces.append((False, "".join(literal)))
            literal = []
        start = index
        stack = [")" if source[index + 1] == "(" else "}"]
        index += 2
        quote = None
        while index < len(source) and stack:
            char = source[index]
            if quote:
                if char == "\\":
                    index += 2
                    continue
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
            elif char in "([{":
                stack.append({"(": ")", "[": "]", "{": "}"}[char])
            elif char in ")]}":
                if char != stack.pop():
                    raise ValueError("Malformed CWL expression: mismatched delimiter")
            index += 1
        if stack or quote:
            raise ValueError("Malformed CWL expression: unterminated substitution")
        body = source[start + 2:index - 1]
        body = "return (" + body + ");" if source[start + 1] == "(" else body
        pieces.append((True, body))
    if literal:
        pieces.append((False, "".join(literal)))
    # YAML block scalars commonly surround standalone expressions with whitespace.
    significant = [(expression, value) for expression, value in pieces
                   if expression or value.strip()]
    if len(significant) == 1 and significant[0][0]:
        body = significant[0][1]
    else:
        terms = ["_text((function(){" + value + "})())" if expression else json.dumps(value)
                 for expression, value in pieces]
        body = ("function _text(value){return typeof value === 'string' ? value : "
                "JSON.stringify(value);} return " + (" + ".join(terms) or "''") + ";")
    result = {"language": "javascript", "source": body}
    if bindings is not None:
        result["bindings"] = bindings
    return result


def _lower_value(value):
    if isinstance(value, list):
        return [_lower_value(item) for item in value]
    if isinstance(value, str) and ("$(" in value or "${" in value):
        return _lower_expression(value)
    return value


def _argument_descriptor(binding: object, value: dict, position: int) -> dict:
    descriptor = {**value, "position": position}
    for field_name in ("prefix", "separate", "shellQuote", "itemSeparator"):
        field_value = getattr(binding, field_name, None)
        if field_value is not None:
            descriptor[field_name] = field_value
    return descriptor


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
                    if not separator or step_name not in output_paths:
                        raise ValueError(f"Unresolved source {source!r} at {path}")
                    producer = output_paths[step_name]
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
                    if getattr(step, "when", None) is not None:
                        raise NotImplementedError(f"CWL when is not supported at {invocation_path}; conditional skipped outputs require nullable payload support")
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
                            } | {
                                _local_name(step_input.id).split("/")[-1]: step_input.default
                                for step_input in step.in_
                                if getattr(step_input, "default", None) is not None
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
            target
            for invocation in self._walk_invocations(region)
            for target in invocation.deployments
            if target.deployment
        ]
        if coordinator and coordinator.deployment:
            coordinator_name = coordinator
        elif deployments:
            coordinator_name = deployments[0]
        else:
            coordinator_name = DeploymentTarget(next(iter(self.streamflow_config.get("deployments", {}))))
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

    def _default_value(
        self, path: str, name: str, raw: object, data_type: str,
        context: LoweringContext,
    ) -> tuple[str, DataReference, str]:
        identity = _generated_name("default", path.strip("/"), name)
        port, data = f"p_{identity}", DataReference(f"d_{identity}")
        context.dependencies[data.payload] = {
            "type": data_type,
            "value": _coerce_cwl_value(raw, data_type, self.cwl_file.parent),
        }
        if (port, data) not in context.datasets[context.controller]:
            context.datasets[context.controller].append((port, data))
        return port, data, data_type

    def _bind_region_inputs(
        self, region: WorkflowRegion, invocation: Invocation, context: LoweringContext
    ) -> None:
        for name in region.inputs:
            sources = invocation.input_bindings.get(name, ())
            if len(sources) > 1:
                raise ValueError(f"Multiple input sources are not supported at {region.path}/{name}")
            path = f"{region.path.rstrip('/')}/{name}"
            if sources:
                context.available[path] = self._value(context, sources[0])
                context.value_locations[path] = context.value_locations.get(sources[0], context.controller)
                if sources[0] in context.pending:
                    context.pending[path] = context.pending[sources[0]]
                if sources[0] in context.publishers:
                    context.publishers[path] = context.publishers[sources[0]]
            elif name in invocation.defaults:
                context.available[path] = self._default_value(
                    invocation.path, name, invocation.defaults[name],
                    region.input_types[name], context,
                )
                context.value_locations[path] = context.controller

    def _exec_name(self, context: LoweringContext, base: str) -> str:
        """Allocate once per emitted exec, including replicated worker templates."""
        count = context.tool_counts.get(base, 0)
        context.tool_counts[base] = count + 1
        name = f"{base}_{count}"
        if name in context.steps:
            raise ValueError(f"Duplicate exec descriptor {name}")
        return name

    def _tool_trace(
        self,
        invocation: Invocation,
        context: LoweringContext,
        input_values: dict[str, tuple[str, DataReference, str]] | None = None,
    ) -> str:
        tool = invocation.process
        local = invocation.path.rsplit("/", 1)[-1]
        step_name = self._exec_name(context, f"s_{_generated_name(invocation.path.strip('/'))}")
        input_flow: list[str] = []
        arguments: list[tuple[int, str, dict]] = []
        named_inputs = {}
        input_types = {}
        expression_inputs = {}
        for tool_input in getattr(tool, "inputs", []):
            name = _local_name(tool_input.id).split("/")[-1]
            if len(invocation.input_bindings.get(name, ())) > 1:
                raise ValueError(f"Multiple input sources are not supported at {invocation.path}/{name}")
            values = (
                [input_values[name]]
                if input_values is not None and name in input_values
                else [
                    self._value(context, source)
                    for source in invocation.input_bindings.get(name, ())
                    if source in context.available
                ]
            )
            if not values and name in invocation.defaults:
                values = [self._default_value(
                    invocation.path, name, invocation.defaults[name],
                    invocation.input_types[name], context,
                )]
            for port, data, _ in values:
                input_flow.append(f"({port}, {data})")
            if not values:
                continue
            port, _, data_type = values[0]
            named_inputs[name] = port
            input_types[name] = data_type
            binding = getattr(tool_input, "inputBinding", None)
            if getattr(tool, "expression", None) is not None:
                expression_inputs[name] = {"port": port}
            if binding is not None:
                position = binding.position if binding.position is not None else 0
                if not isinstance(position, int):
                    raise ValueError(f"Expression argument positions are unsupported at {invocation.path}/{name}")
                transformation = getattr(binding, "valueFrom", None)
                value = (
                    {"expression": _lower_expression(transformation, {"self": {"port": port}})}
                    if isinstance(transformation, str) and ("$(" in transformation or "${" in transformation)
                    else {"value": transformation} if transformation is not None
                    else {"valueFrom": port}
                )
                arguments.append((position, name, _argument_descriptor(binding, value, position)))

        for index, argument in enumerate(getattr(tool, "arguments", None) or []):
            if isinstance(argument, str):
                position = 0
                value = {"expression": _lower_expression(argument)} if "$(" in argument or "${" in argument else {"value": argument}
                descriptor = {**value, "position": position}
            else:
                position = getattr(argument, "position", None)
                position = 0 if position is None else position
                if not isinstance(position, int):
                    raise ValueError(f"Expression argument positions are unsupported at {invocation.path}")
                source = getattr(argument, "valueFrom", None)
                if source is None:
                    raise ValueError(f"Command argument requires valueFrom at {invocation.path}")
                value = {"expression": _lower_expression(source)} if isinstance(source, str) and ("$(" in source or "${" in source) else {"value": source}
                descriptor = _argument_descriptor(argument, value, position)
            arguments.append((position, f"{index:09d}", descriptor))

        outputs = {}
        output_flow = []
        expression_outputs = {}
        for tool_output in getattr(tool, "outputs", []):
            name = _local_name(tool_output.id).split("/")[-1]
            identity = _generated_name(invocation.path.strip('/'), name)
            port = f"p_{identity}"
            base_data = identity
            data = (
                _keyed_data(f"element_d_{base_data}", context.task_id)
                if context.task_id else DataReference(f"d_{base_data}")
            )
            data_type = invocation.output_types.get(name, DATA_TYPE)
            binding = getattr(tool_output, "outputBinding", None)
            output = _output_descriptor(data, data_type)
            glob = _resolve_glob(tool, binding.glob if binding else None)
            if glob:
                output["glob"] = _lower_value(glob)
            if binding is not None:
                for field_name in ("loadContents", "outputEval"):
                    field_value = getattr(binding, field_name, None)
                    if field_value is not None:
                        output["readContents" if field_name == "loadContents" else "evaluate"] = (
                            field_value if field_name == "loadContents" else
                            _lower_expression(field_value, {"self": {"context": "matchedFiles"}})
                        )
            outputs[port] = output
            if not context.task_id:
                context.dependencies[data.payload] = {"type": data_type}
            context.available[invocation.outputs[name]] = (port, data, data_type)
            context.value_locations[invocation.outputs[name]] = context.controller
            output_flow.append(f"({port}, {data})")
            expression_outputs[name] = port

        command, extras = _command(tool)
        step = {
            "displayName": local,
            "inputs": {port: {"type": input_types[name]} for name, port in named_inputs.items()},
            "bindings": {"inputs": {"object": {
                name: {"port": port}
                for name, port in named_inputs.items()
            }}},
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
            step.pop("bindings")
            step["expression"] = {
                **_lower_expression(expression, {"inputs": {"object": expression_inputs}}),
                "outputs": expression_outputs,
            }
        elif getattr(tool, "stdout", None) is not None:
            step["stdout"] = _lower_value(tool.stdout)
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
                if len(sources) != 1:
                    raise ValueError(f"Workflow output {output_name!r} requires one source at {invocation.path}")
                if sources:
                    context.available[output_path] = self._value(child, sources[0])
                    context.value_locations[output_path] = child.value_locations.get(sources[0], child.controller)
                    if sources[0] in child.pending:
                        context.pending[output_path] = child.pending[sources[0]]
                    if sources[0] in child.publishers:
                        context.publishers[output_path] = child.publishers[sources[0]]
            return traces
        # Ordinary producers may be placed independently of the scatter that
        # consumes their lists. Keep the value's location beside its binding.
        target = next(iter(invocation.deployments), None)
        location = (
            context.location_by_deployment.get(target, context.controller)
            if target else context.controller
        )
        # Keep a scatter body on its assigned worker when that worker is eligible.
        if context.task_id and context.controller in {
            context.location_by_deployment.get(candidate)
            for candidate in invocation.deployments
        }:
            location = context.controller
        child = context.child(context.region, controller=location)
        pending_inputs = set(child.pending)
        receives = self._ready_inputs(invocation, child, location)
        admission = ""
        admission_receive = ""
        if context.task_id and location != context.controller:
            control = f"p_invocation_{_generated_name(invocation.path.strip('/'))}"
            admission_receive = (
                f"recv((begin, {context.task_id}) -> {control}, {context.controller}, {location})"
            )
            admission = (
                f"send((begin, {context.task_id}) -> {control}, {context.controller}, {location})"
            )
        for sources in invocation.input_bindings.values():
            for source in sources:
                if source in pending_inputs:
                    continue
                producer = child.value_locations.get(source, context.controller)
                if producer == location and source not in child.publishers:
                    continue
                port, data, data_type = self._value(child, source)
                port = _generated_name("p_input", invocation.path.strip("/"), source.strip("/"), location)
                # Each consumer binds its own transported File path, even for a shared source.
                received = DataReference(
                    _generated_name("input_d", invocation.path.strip("/"), source.strip("/"), location),
                    data.identity, True,
                )
                child.available[source] = (port, received, data_type)
                receive = f"recv({received} -> {port}, {producer}, {location})"
                if receive not in receives:
                    send = f"send({data} -> {port}, {producer}, {location})"
                    if source in context.publishers:
                        context.publishers[source].parts.append(send)
                    else:
                        context.fragments[producer].append(send)
                    receives.append(receive)
        trace = self._tool_trace(invocation, child)
        if receives:
            setup = " | ".join(receives)
            trace = (f"({setup})" if len(receives) > 1 else setup) + "\n.\n" + trace
        trace = _sequence([admission_receive, trace])
        publisher = _parallel([])
        trace.parts.append(publisher)
        for output_path in invocation.outputs.values():
            context.available[output_path] = child.available[output_path]
            context.value_locations[output_path] = child.value_locations[output_path]
            context.publishers[output_path] = publisher
        if location != context.controller:
            context.fragments[location].append(trace)
            if admission:
                context.fragments[context.controller].append(admission)
            return []
        return [trace]

    def lower_invocation(
        self, invocation: Invocation, context: LoweringContext
    ) -> list[str]:
        if invocation.scatter:
            return self.lower_scatter(invocation, context)
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

    def _materialize(
        self, stage: PendingGather, destination: str,
    ) -> OutputOccurrence:
        """Consume one boundary at its dependency destination, inside-out."""
        if destination in stage.materialized:
            return stage.materialized[destination]
        scope = " / ".join(stage.scope) if stage.scope else "root"
        collector_scope = " / ".join(stage.scope) if stage.scope else "?scope_0"
        task_id = f"{collector_scope} / {stage.coordinate}"
        suffix = f"{stage.output_index}_{stage.index}_{destination}"
        source_port = f"p_result_{suffix}"
        port = f"p_gather_data_{suffix}"
        base = _generated_name("d", stage.invocation.path.strip("/"), stage.name, destination)
        data = DataReference(base, scope, bool(stage.scope))
        collection = f"stream_{base}"
        gather = self._exec_name(stage.sources[0].context, f"_s_gather_{suffix}")
        loops, begins, routes = [], [], []
        for source_index, occurrence in enumerate(stage.sources):
            actual = (
                self._materialize(occurrence.pending, destination)
                if occurrence.pending else occurrence
            )
            worker = occurrence.context.worker_owner
            assert worker is not None
            location = actual.location
            route_port = source_port if len(stage.sources) == 1 else f"{source_port}_{source_index}"
            actual.publisher.parts.append(
                f"send({actual.value[1]} -> {route_port}, {location}, {destination})"
            )
            sender_scope = scope if stage.scope else "?scope_0"
            begin = f"send((begin, {sender_scope}) -> {route_port}, {location}, {destination})"
            eof = f"send((eof, {sender_scope}) -> {route_port}, {location}, {destination})"
            if location == worker.context.controller:
                worker.result_begins.parts.append(begin)
                worker.result_eofs.parts.append(eof)
            else:
                controls = worker.remote_controls.setdefault(location, ([], []))
                controls[0].append(begin)
                controls[1].append(eof)
            begins.append(f"recv((begin, {collector_scope}) -> {route_port}, {location}, {destination})")
            received = DataReference(actual.value[1].payload, task_id, True)
            loops.append(EmittedFragment("marked", [
                f"// @compiler begin gather_stream {collection}_{source_index} {location} {route_port}",
                EmittedFragment("replication", [
                    f"recv({received} -> {route_port}, {location}, {destination})",
                    f"recv((eof, {collector_scope}) -> {route_port}, {location}, {destination})",
                ]),
                f"// @compiler end gather_stream {collection}_{source_index} {location} {route_port}",
            ]))
            result_route = {"port": route_port, "source": location, "receiver": destination,
                            "scope": scope, "operation": stage.invocation.scatter.region_id,
                            "output": stage.name, "elementId": actual.value[1].identity}
            routes.append(result_route)
        publisher = _parallel([])
        gather_inputs = ", ".join(f"U({route['port']}, ({collection}_{i}, {collector_scope}))" for i, route in enumerate(routes))
        fragment = _sequence([
            begins[0],
            _parallel(begins[1:]),
            _parallel(loops),
            f"exec({gather}, {{{gather_inputs}}} -> {{({port}, {data})}}, {{{destination}}})",
            publisher,
        ])
        context = stage.sources[0].context.worker_owner.parent
        context.fragments[destination].append(fragment)
        value = (port, data, stage.value[2])
        output = OutputOccurrence(context, value, destination, publisher)
        stage.materialized[destination] = output
        context.steps[gather] = {
            "displayName": f"{stage.invocation.path}/{stage.name} ScatterGather",
            "type": "scatter_gather",
            "inputs": {route["port"]: {"type": stage.sources[0].value[2]} for route in routes},
            "operationId": stage.invocation.scatter.region_id,
            "scope": scope,
            "scatterMethod": stage.invocation.scatter.method,
            "shapeFrom": stage.dispatches,
            "routes": routes,
            "collections": {
                route["port"]: {"name": f"{collection}_{i}", "scope": collector_scope,
                                "output": port, "type": stage.sources[0].value[2], "read": "snapshot"}
                for i, route in enumerate(routes)
            },
            "outputs": {port: _output_descriptor(data, value[2])},
        }
        if not data.bound:
            context.dependencies[data.payload] = {"type": value[2]}
        return output

    def _ready_inputs(self, invocation: Invocation, context: LoweringContext, location: str) -> list:
        """Bind completed lists visibly in the owner that will execute/dispatch."""
        receives = []
        for sources in invocation.input_bindings.values():
            for source in sources:
                if source not in context.pending:
                    continue
                output = self._materialize(context.pending[source], location)
                port = _generated_name("p_ready", invocation.path.strip("/"), source.strip("/"), location)
                output.publisher.parts.append(f"send({output.value[1]} -> {port}, {location}, {location})")
                received = DataReference(
                    _generated_name("ready_d", invocation.path.strip("/"), source.strip("/"), location),
                    output.value[1].identity, True,
                )
                receives.append(f"recv({received} -> {port}, {location}, {location})")
                context.available[source] = (port, received, output.value[2])
                context.value_locations[source] = location
                context.publishers[source] = output.publisher
                del context.pending[source]
        return receives

    def lower_scatter(
        self, invocation: Invocation, context: LoweringContext
    ) -> list:
        """One recursive rule: append a coordinate, lower the process, expose streams."""
        index = self._region_number(context, invocation)
        prefix = context.bound_path
        scope_id = " / ".join(prefix) if prefix else "root"
        worker_prefix = prefix or ("?scope_0",)
        depth = len(prefix) if prefix else 1
        siblings = [item for item in context.region.invocations if item.scatter]
        coordinate = f"?iteration_{depth}" + (f"_{index}" if len(siblings) > 1 else "")
        task_path = (*worker_prefix, coordinate)
        worker_id = " / ".join(task_path)
        inputs, invariants, producers, input_publishers = [], [], {}, {}
        for name, bindings in invocation.input_bindings.items():
            if len(bindings) > 1:
                raise ValueError(f"Multiple scatter input sources are not supported at {invocation.path}/{name}")
            if bindings:
                source = bindings[0]
                if source in context.pending:
                    target = next(iter(invocation.deployments), None)
                    destination = context.location_by_deployment.get(target, context.controller) if target else context.controller
                    output = self._materialize(context.pending[source], destination)
                    value = output.value
                    producers[name] = destination
                    input_publishers[name] = output.publisher
                else:
                    value = self._value(context, source)
                    producers[name] = context.value_locations.get(source, context.controller)
                    if source in context.publishers:
                        input_publishers[name] = context.publishers[source]
            elif name in invocation.defaults:
                data_type = invocation.input_types[name]
                if name in invocation.scatter.inputs:
                    data_type = f"list[{data_type}]"
                value = self._default_value(invocation.path, name, invocation.defaults[name], data_type, context)
                producers[name] = context.controller
            elif name in invocation.scatter.inputs:
                raise ValueError(f"Scatter input {name!r} has no source at {invocation.path}")
            else:
                continue
            (inputs if name in invocation.scatter.inputs else invariants).append((name, value))
        dimensions = dict(inputs)
        if not invocation.scatter.inputs or any(name not in dimensions for name in invocation.scatter.inputs):
            raise ValueError(f"Scatter dimensions require input sources at {invocation.path}")
        inputs = [(name, dimensions[name]) for name in invocation.scatter.inputs]
        fields = {name: _list_inner_type(value[2]) for name, value in inputs}
        if any(value is None for value in fields.values()):
            raise ValueError(f"Scatter inputs must be lists at {invocation.path}")
        workers = list(dict.fromkeys(context.location_by_deployment[target]
                                    for target in invocation.deployments if target in context.location_by_deployment))
        descendants = {context.location_by_deployment[target]
                       for item in self._walk_invocations(invocation.process)
                       if item.scatter for target in item.deployments
                       if target in context.location_by_deployment} if isinstance(invocation.process, WorkflowRegion) else set()
        workers = [worker for worker in workers if worker not in descendants] or workers
        if not workers:
            raise ValueError(f"Scatter step {invocation.path} requires deployment targets")
        route = {"controller": context.controller, "workers": workers,
                 "producers": {name: producers[name] for name, _ in inputs}}
        streams = []
        dispatch_names = [self._exec_name(context, f"_s_dispatch_{i}_{index}") for i in range(len(inputs))]
        counts = Counter(value[1] for _, value in inputs)
        for dimension, (name, value) in enumerate(inputs):
            port = f"p_scatter_{dimension}_{index}"
            base = value[1].payload if counts[value[1]] == 1 else _generated_name(value[1].payload, name)
            element, collection = f"element_{base}", f"stream_{base}_{index}_{dimension}"
            dispatch = dispatch_names[dimension]
            producer = producers[name]
            activation = []
            dispatch_scope = scope_id
            if context.task_id and producer != context.controller:
                control = f"p_dispatch_owner_{dimension}_{index}"
                context.fragments[context.controller].append(f"send((begin, {scope_id}) -> {control}, {context.controller}, {producer})")
                activation.append(f"recv((begin, {scope_id}) -> {control}, {context.controller}, {producer})")
            source_port, source_data, _ = value
            if name in input_publishers:
                source_port = f"p_dispatch_input_{dimension}_{index}"
                input_publishers[name].parts.append(f"send({source_data} -> {source_port}, {producer}, {producer})")
                activation.append(f"recv({source_data} -> {source_port}, {producer}, {producer})")
            dispatch_id = f"{dispatch_scope} / {coordinate}"
            context.steps[dispatch] = {
                "displayName": f"{invocation.path}/{name} ScatterDispatch", "type": "scatter_dispatch",
                "inputs": {source_port: {"type": value[2]}},
                "operationId": invocation.scatter.region_id, "dimension": name,
                "dimensions": list(invocation.scatter.inputs), "scatterMethod": invocation.scatter.method,
                "routes": [route], "scope": dispatch_scope,
                "key": {"operation": invocation.scatter.region_id, "scope": dispatch_scope,
                        "id": dispatch_id},
                "keySpace": {"dispatches": dispatch_names},
                "outputs": {port: {"collection": {"name": collection, "scope": dispatch_scope,
                                                  "elementId": dispatch_id, "type": fields[name]}}},
            }
            streams.append((name, dispatch, port, element, producer))
            distributors = []
            for worker in workers:
                distributors.append(EmittedFragment("marked", [
                    f"// @compiler begin scatter_stream {collection} {worker} {port}",
                    EmittedFragment("replication", [
                        f"move({DataReference(element, dispatch_id, True)} -> {port}, {producer}, {worker})",
                        f"send((eof, {dispatch_scope}) -> {port}, {producer}, {worker})",
                    ]),
                    f"// @compiler end scatter_stream {collection} {worker} {port}",
                ]))
            fragment = _sequence([
                *activation,
                _parallel([f"send((begin, {dispatch_scope}) -> {port}, {producer}, {worker})" for worker in workers]),
                f"exec({dispatch}, {{({source_port}, {source_data})}} -> {{U({port}, ({collection}, {dispatch_scope}))}}, {{{producer}}})",
                _parallel(distributors),
            ])
            context.fragments[producer].append(fragment)
        outputs = {name: [] for name in invocation.outputs}
        for worker in workers:
            child = context.child(invocation.process if isinstance(invocation.process, WorkflowRegion) else context.region,
                                  controller=worker, task_id=worker_id,
                                  fragments={location: [] for location in context.locations})
            child.bound_path = task_path
            openings, closings, result_begins, result_eofs = (_parallel([]) for _ in range(4))
            body = _parallel([])
            owner = ScatterWorker(child, context, invocation, index, task_path, worker_prefix,
                                  body, openings, closings, result_begins, result_eofs)
            child.worker_owner = owner
            context.workers.append(owner)
            values = {name: (port, DataReference(element, worker_id, True), fields[name])
                      for name, _, port, element, _ in streams}
            invariant_receives = []
            for name, value in invariants:
                producer = producers[name]
                port, data, data_type = value
                if producer != worker or name in input_publishers:
                    transfer = f"p_invariant_{name}_{index}_{worker}"
                    send = f"send({data} -> {transfer}, {producer}, {worker})"
                    if name in input_publishers:
                        input_publishers[name].parts.append(send)
                    else:
                        context.fragments[producer].append(send)
                    received = DataReference(
                        _generated_name("invariant_d", name, str(index), worker, producer),
                        data.identity, True,
                    )
                    invariant_receives.append(f"recv({received} -> {transfer}, {producer}, {worker})")
                    value = (transfer, received, data_type)
                values[name] = value
            if isinstance(invocation.process, WorkflowRegion):
                for name, value in values.items():
                    path = f"{invocation.process.path.rstrip('/')}/{name}"
                    child.available[path] = value
                    child.value_locations[path] = worker
                body.parts.extend(self.lower_region(invocation.process, child))
                result_paths = {name: sources[0] for name, sources in invocation.process.outputs.items() if len(sources) == 1}
                if len(result_paths) != len(invocation.process.outputs):
                    raise ValueError(f"Scatter outputs require one source at {invocation.path}")
            else:
                publication = _parallel([])
                body.parts.append(_sequence([self._tool_trace(invocation, child, values), publication]))
                for path in invocation.outputs.values():
                    child.publishers[path] = publication
                result_paths = invocation.outputs
            for name, path in result_paths.items():
                value = self._value(child, path)
                if path not in child.pending and value[1].identity != worker_id:
                    # An exposed reusable input needs a visible occurrence copy.
                    source_port, source_data, data_type = value
                    output_port = _generated_name("p_publish", invocation.path.strip("/"), name)
                    output_data = DataReference(_generated_name("element_d_publish", invocation.path.strip("/"), name), worker_id, True)
                    publish = self._exec_name(context, _generated_name("_s_publish", invocation.path.strip("/"), name))
                    context.steps[publish] = {
                        "displayName": f"{invocation.path}/{name} OutputOccurrence",
                        "inputs": {source_port: {"type": data_type}},
                        "expression": {
                            **_lower_expression("${ return {value: inputs.value}; }", {
                                "inputs": {"object": {"value": {"port": source_port}}}
                            }),
                            "outputs": {"value": output_port},
                        },
                        "outputs": {output_port: _output_descriptor(output_data, data_type)},
                    }
                    publication = _parallel([])
                    body.parts.append(_sequence([f"exec({publish}, {{({source_port}, {source_data})}} -> {{({output_port}, {output_data})}}, {{{worker}}})", publication]))
                    value = (output_port, output_data, data_type)
                    child.value_locations[path] = worker
                    child.publishers[path] = publication
                publisher = child.publishers.get(path, body)
                outputs[name].append(OutputOccurrence(child, value,
                    child.value_locations.get(path, worker), publisher, child.pending.get(path)))
            work = _sequence([
                *[f"recv({DataReference(element, worker_id, True)} -> {port}, {producer}, {worker})"
                  for _, _, port, element, producer in streams],
                body,
            ])
            close = _sequence([*[f"recv((eof, {' / '.join(worker_prefix)}) -> {port}, {producer}, {worker})"
                                  for _, _, port, _, producer in streams]])
            branch = _sequence([
                f"recv((begin, {' / '.join(worker_prefix)}) -> {streams[0][2]}, {streams[0][4]}, {worker})",
                _parallel([*[f"recv((begin, {' / '.join(worker_prefix)}) -> {port}, {producer}, {worker})"
                  for _, _, port, _, producer in streams[1:]], *invariant_receives, openings]),
                result_begins,
                EmittedFragment("replication", [work, close]), closings, result_eofs,
            ])
            context.fragments[worker].append(EmittedFragment("hint", [
                self._scatter_hint(context, invocation.scatter.region_id, "worker", True), branch,
                self._scatter_hint(context, invocation.scatter.region_id, "worker", False),
            ]))
        for output_index, (name, occurrences) in enumerate(outputs.items()):
            if not occurrences:
                raise ValueError(f"Scatter step {invocation.path} requires declared outputs")
            item_type = occurrences[0].value[2]
            rank = len(inputs) if invocation.scatter.method == "nested_crossproduct" else 1
            data_type = "list[" * rank + item_type + "]" * rank
            port = f"p_pending_{output_index}_{index}"
            data = DataReference(_generated_name("d", invocation.path.strip("/"), name), scope_id, bool(prefix))
            value = (port, data, data_type)
            path = invocation.outputs[name]
            context.available[path] = value
            context.value_locations[path] = context.controller
            context.pending[path] = PendingGather(invocation, index, name, output_index, prefix, coordinate,
                                                  [stream[1] for stream in streams], occurrences, value)
        return []

    def _finish_owners(self, context: LoweringContext) -> None:
        """Close each distributed source after that owner's actual publications."""
        for owner in reversed(context.workers):
            child, parent = owner.context, owner.parent
            worker = child.controller
            prefix = " / ".join(owner.prefix)
            for location, parts in child.fragments.items():
                if location == worker:
                    if parts:
                        owner.body.parts[:] = [_parallel([_parallel(owner.body.parts.copy()), *parts])]
                    continue
                if not parts:
                    continue
                control = f"p_owner_{owner.index}_{worker}_{location}"
                owner.openings.parts.append(f"send((begin, {prefix}) -> {control}, {worker}, {location})")
                owner.closings.parts.append(f"send((eof, {prefix}) -> {control}, {worker}, {location})")
                begins, eofs = owner.remote_controls.get(location, ([], []))
                invocation_control = f"{control}_invocation"
                child_id = " / ".join(owner.scope)
                owner.body.parts.insert(0, f"send((begin, {child_id}) -> {invocation_control}, {worker}, {location})")
                service = _sequence([
                    f"recv((begin, {prefix}) -> {control}, {worker}, {location})",
                    _parallel(begins),
                    EmittedFragment("replication", [
                        _sequence([
                            f"recv((begin, {child_id}) -> {invocation_control}, {worker}, {location})",
                            _parallel(parts),
                        ]),
                        f"recv((eof, {prefix}) -> {control}, {worker}, {location})",
                    ]), _parallel(eofs),
                ])
                parent.fragments[location].append(service)

    def translate(
        self, workflow_output: TextIO = sys.stdout, metadata_output: TextIO = sys.stdout
    ) -> None:
        region = self.build_region_tree()
        scatters = self._scatter_regions(region)
        for invocation in scatters:
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
            data = DataReference(f"d_{name}")
            data_type = _cwl_type_to_swirl(workflow_input.type_)
            raw = self.workflow_inputs.get(name, getattr(workflow_input, "default", ""))
            value = _coerce_cwl_value(raw, data_type, self.cwl_file.parent)
            context.dependencies[data.payload] = {"type": data_type, "value": value}
            context.available[f"/{name}"] = (port, data, data_type)
            context.value_locations[f"/{name}"] = context.controller
            context.datasets[context.controller].append((port, data))

        main_trace = _parallel(self.lower_region(region, context))
        if main_trace:
            context.fragments[context.controller].append(main_trace)
        for sources in region.outputs.values():
            if len(sources) != 1:
                raise ValueError("Workflow outputs require exactly one declared source")
            if sources[0] in context.pending:
                self._materialize(context.pending[sources[0]], context.controller)
        self._finish_owners(context)
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
                "conditions": context.conditions,
                "locations": context.locations,
                "dependencies": context.dependencies,
            },
            metadata_output,
        )
