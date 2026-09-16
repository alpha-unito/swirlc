from __future__ import annotations

# python tmp_main.py translate --language cwl /home/tommo/Coding/ALPHA/swirlc/examples/cwl/basic/main.cwl --outdir /home/tommo/Coding/ALPHA/swirlc/build

import glob
import json
import logging
import os
import sys
from collections.abc import MutableMapping, MutableSequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

import cwl_utils
from ruamel.yaml import YAML

from swirlc.core.entity import (
    Data,
    DistributedWorkflow,
    Location,
    Port,
    Processor,
    Step,
    Workflow,
)
from cwl_utils.parser import load_document_by_uri, save
from swirlc.core.translator import AbstractTranslator

# Fallback used when a CWL type cannot be resolved to a SWIRL type.
DATA_TYPE = "file"
_WRAPPER_DEPLOYMENT_TYPES = {"docker", "singularity", "none"}

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
class DeploymentTarget:
    """A normalized StreamFlow execution target."""

    deployment: str | None
    service: str | None = None
    locations: int | None = None


@dataclass(frozen=True)
class StreamFlowBindings:
    """Normalized bindings, matched against absolute CWL step paths."""

    default: DeploymentTarget | None
    by_path: dict[str, DeploymentTarget]

    def target_for(self, path: str) -> DeploymentTarget | None:
        path = _absolute_cwl_path(path)
        for candidate in sorted(self.by_path, key=len, reverse=True):
            if path == candidate or path.startswith(candidate + "/"):
                return self.by_path[candidate]
        return self.default


@dataclass(frozen=True)
class ScatterSpec:
    inputs: tuple[str, ...]
    method: str
    region_id: str
    parent_region_id: str | None


@dataclass
class Invocation:
    """One CWL workflow step, before SWIRL lowering."""

    path: str
    process: object
    input_bindings: dict[str, tuple[str, ...]]
    outputs: dict[str, str]
    deployment: DeploymentTarget | None
    scatter: ScatterSpec | None = None


@dataclass
class WorkflowRegion:
    """A CWL workflow boundary preserved for recursive lowering."""

    path: str
    inputs: dict[str, str | None]
    outputs: dict[str, tuple[str, ...]]
    invocations: list[Invocation] = field(default_factory=list)
    deployment: DeploymentTarget | None = None
    parent: "WorkflowRegion | None" = None


def _absolute_cwl_path(path: str) -> str:
    """Normalize a StreamFlow/CWL path without losing nested components."""
    stripped = path.strip("/")
    return f"/{stripped}" if stripped else "/"


def _normalize_bindings(streamflow_config: MutableMapping) -> StreamFlowBindings:
    """Normalize StreamFlow bindings once, including shorthand target lists."""
    workflows = streamflow_config.get("workflows", {})
    first_workflow = next(iter(workflows.values()), {})
    default = None
    by_path = {}
    for binding in first_workflow.get("bindings", []):
        step = binding.get("step")
        if step is None:
            continue
        target = binding.get("target") or {}
        # A list describes expanded workers.  The first target remains the
        # effective deployment; expansion is deferred to lowering.
        if isinstance(target, list):
            target = target[0] if target else {}
        if not isinstance(target, dict) or not target.get("deployment"):
            continue
        normalized = DeploymentTarget(
            target["deployment"], target.get("service"), target.get("locations")
        )
        path = _absolute_cwl_path(str(step))
        if path == "/":
            default = normalized
        else:
            by_path[path] = normalized
    return StreamFlowBindings(default, by_path)


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
    if isinstance(value, dict) and "path" in value:
        path = Path(value["path"])
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


class _EffStep:
    """A flattened leaf step (CommandLineTool / ExpressionTool).

    ``path`` is the slash-joined chain of CWL step names from the root
    workflow down to this leaf (e.g. ``chromosome/individuals``). ``inputs``
    and ``outputs`` carry global producer keys so data flow can be wired
    across subworkflow boundaries.
    """

    __slots__ = (
        "path",
        "display_name",
        "tool_obj",
        "command",
        "inputs",
        "outputs",
        "scatter",
        "scatter_method",
    )

    def __init__(
        self,
        path,
        display_name,
        tool_obj,
        command,
        inputs,
        outputs,
        scatter: list[str] | None = None,
        scatter_method: str | None = None,
    ):
        self.path = path  # e.g. "chromosome/individuals"
        self.display_name = display_name  # leaf step name
        self.tool_obj = tool_obj  # cwl_utils CommandLineTool / ExpressionTool
        self.command = command
        self.inputs = inputs  # list[(param_name, global_source_key | None)]
        self.outputs = outputs  # list[(port_local, global_key)]
        self.scatter = scatter
        self.scatter_method = scatter_method


def _local_name(uri: str) -> str:
    """Extract the fragment (local name) from a CWL URI like file:///path#name/port."""
    return uri.split("#", 1)[-1] if "#" in uri else uri


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

        def build(wf, path: str, inputs: dict[str, str | None], parent, parent_scatter):
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
                    deployment=self.bindings.target_for(path),
                    parent=parent,
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
                            parent_scatter,
                        )
                        if scatter_inputs
                        else None
                    )
                    run = step.run
                    process = self.cwl_bundle[run] if isinstance(run, str) else run
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
                            scatter.region_id if scatter else parent_scatter,
                        )
                    region.invocations.append(
                        Invocation(
                            invocation_path,
                            process,
                            bindings,
                            output_paths[name],
                            self.bindings.target_for(invocation_path),
                            scatter,
                        )
                    )

                region.outputs = {
                    _local_name(output.id).split("/")[-1]: tuple(
                        resolve(source) for source in sources(output.outputSource)
                    )
                    for output in wf.outputs
                }
                return region
            finally:
                active_workflows.remove(workflow_id)

        root_inputs = {
            _local_name(workflow_input.id).split("/")[
                -1
            ]: f"/{_local_name(workflow_input.id).split('/')[-1]}"
            for workflow_input in self.cwl_obj.inputs
        }
        return build(self.cwl_obj, "/", root_inputs, None, None)

    def _flatten_leaf_steps(self) -> list[_EffStep]:
        """Recursively inline nested subworkflows into a flat list of leaf steps.

        Each CWL ``Workflow`` step whose ``run`` is itself a ``Workflow`` is
        expanded; its inner steps are emitted with data flow rewired across the
        subworkflow boundary. The global producer namespace is:
        - root workflow inputs -> the bare input name
        - a leaf step output -> ``<step-path>/<output-port>``
        """
        effective: list[_EffStep] = []

        def first_source(sin):
            src = sin.source
            if isinstance(src, list):
                src = src[0] if src else None
            return _local_name(src) if src else None

        def flatten(wf, path_prefix: str, env: dict) -> dict:
            # CWL ids/sources are fully-qualified fragments (e.g.
            # "chromosome/run/snp_file"). ``env`` maps this workflow's input
            # fragments to the global producer key they are bound to.
            input_frags = {_local_name(i.id) for i in wf.inputs}
            steps_by_name = {_local_name(s.id).split("/")[-1]: s for s in wf.steps}
            cache: dict[str, dict] = {}  # short step name -> {out_port: global_key}

            def resolve(src_frag):
                if src_frag is None:
                    return None
                if src_frag in input_frags:
                    return env.get(src_frag)
                # Otherwise it is "<step-fragment>/<output-port>".
                step_frag, _, port = src_frag.rpartition("/")
                out_map = ensure(step_frag.split("/")[-1])
                return out_map.get(port) if out_map else None

            def ensure(sname: str) -> dict:
                if sname in cache:
                    return cache[sname]
                step = steps_by_name.get(sname)
                if step is None:
                    cache[sname] = {}
                    return cache[sname]
                run = step.run
                run_obj = self.cwl_bundle[run] if isinstance(run, str) else run
                spath = f"{path_prefix}{sname}"

                is_subworkflow = hasattr(run_obj, "steps") and not hasattr(
                    run_obj, "baseCommand"
                )
                if is_subworkflow:
                    # Bind subworkflow inputs (matched by short name) to the
                    # producer keys resolved in this (parent) workflow.
                    parent_resolved = {
                        _local_name(sin.id).split("/")[-1]: resolve(first_source(sin))
                        for sin in step.in_
                    }
                    child_env = {}
                    for ci in run_obj.inputs:
                        ci_frag = _local_name(ci.id)
                        child_env[ci_frag] = parent_resolved.get(ci_frag.split("/")[-1])
                    cache[sname] = flatten(run_obj, f"{spath}/", child_env)
                else:
                    bc = getattr(run_obj, "baseCommand", None)
                    command = bc[0] if isinstance(bc, list) and bc else (bc or "")
                    resolved_inputs = [
                        (
                            _local_name(sin.id).split("/")[-1],
                            resolve(first_source(sin)),
                        )
                        for sin in step.in_
                    ]
                    out_map = {}
                    outputs = []
                    for o in step.out:
                        pid = _local_name(o).split("/")[-1]
                        gkey = f"{spath}/{pid}"
                        out_map[pid] = gkey
                        outputs.append((pid, gkey))
                    scatter_raw = getattr(step, "scatter", None)
                    if scatter_raw:
                        if isinstance(scatter_raw, str):
                            scatter_vars = [_local_name(scatter_raw).split("/")[-1]]
                        else:
                            scatter_vars = [
                                _local_name(x).split("/")[-1] for x in scatter_raw
                            ]
                    else:
                        scatter_vars = None
                    scatter_method = getattr(step, "scatterMethod", None)

                    effective.append(
                        _EffStep(
                            spath,
                            sname,
                            run_obj,
                            command,
                            resolved_inputs,
                            outputs,
                            scatter=scatter_vars,
                            scatter_method=scatter_method,
                        )
                    )
                    cache[sname] = out_map
                return cache[sname]

            for sname in steps_by_name:
                ensure(sname)

            # Resolve this workflow's outputs to global producer keys.
            out_res = {}
            for o in wf.outputs:
                oid = _local_name(o.id).split("/")[-1]
                osrc = o.outputSource
                if isinstance(osrc, list):
                    osrc = osrc[0] if osrc else None
                out_res[oid] = resolve(_local_name(osrc) if osrc else None)
            return out_res

        root_env = {_local_name(i.id): _local_name(i.id) for i in self.cwl_obj.inputs}
        flatten(self.cwl_obj, "", root_env)
        return effective

    def _translate(self) -> Workflow:
        workflow = DistributedWorkflow()

        # 1. Parse step→deployment bindings. StreamFlow container wrappers are
        # handled by StreamFlow itself, so only execution deployments become
        # SWIRL locations.
        default_target: tuple[str | None, str | None] = (None, None)
        step_to_target: dict[str, tuple[str, str | None]] = {}
        deployment_services: dict[str, set[str | None]] = {}

        binding_targets = list(self.bindings.by_path.items())
        if self.bindings.default is not None:
            binding_targets.append(("/", self.bindings.default))
        for step_path, target in binding_targets:
            if target.deployment is None:
                continue
            deployment_services.setdefault(target.deployment, set()).add(target.service)
            if step_path == "/":
                default_target = (target.deployment, target.service)
            else:
                step_to_target[step_path.lstrip("/")] = (
                    target.deployment,
                    target.service,
                )

        # 2. Locations from streamflow deployments
        sf_deployments = self.streamflow_config.get("deployments", {})
        deployment_to_loc: dict[tuple[str, str | None], Location] = {}

        if not deployment_services:
            for dep_name, dep_cfg in sf_deployments.items():
                if dep_cfg.get("type", "local") not in _WRAPPER_DEPLOYMENT_TYPES:
                    deployment_services[dep_name] = {None}
                    if default_target[0] is None:
                        default_target = (dep_name, None)
                    break

        def _resolve_hostname(dep_cfg: dict) -> str:
            nodes = dep_cfg.get("config", {}).get("nodes", [])
            return nodes[0] if nodes else "127.0.0.1"

        def _resolve_connection_type(dep_cfg: dict) -> str | None:
            t = dep_cfg.get("type", "local")
            if t == "ssh":
                return "ssh"
            if t == "slurm":
                return "slurm"
            if t in _WRAPPER_DEPLOYMENT_TYPES:
                return None
            return None

        def _resolve_hostname_transitive(dep_cfg: dict) -> str:
            t = dep_cfg.get("type", "local")
            if t == "slurm":
                wraps = dep_cfg.get("wraps")
                if wraps and wraps in sf_deployments:
                    return _resolve_hostname_transitive(sf_deployments[wraps])
            return _resolve_hostname(dep_cfg)

        def _resolve_ssh_config_transitive(dep_cfg: dict) -> dict:
            t = dep_cfg.get("type", "local")
            if t == "slurm":
                wraps = dep_cfg.get("wraps")
                if wraps and wraps in sf_deployments:
                    return _resolve_ssh_config_transitive(sf_deployments[wraps])
                return {}
            if t != "ssh":
                return {}
            config = dep_cfg.get("config", {}) or {}
            return {
                key: value
                for key, value in {
                    "username": config.get("username"),
                    "ssh_key": config.get("sshKey"),
                    "check_host_key": config.get("checkHostKey"),
                }.items()
                if value is not None
            }

        def _resolve_slurm(dep_cfg: dict, service: str | None) -> dict:
            services = dep_cfg.get("config", {}).get("services", {}) or {}
            selected_service = service
            if selected_service is None and len(services) == 1:
                selected_service = next(iter(services))
            options = dict(services.get(selected_service, {}) or {})
            slurm = {"options": options}
            if selected_service:
                slurm["service"] = selected_service
            return slurm

        for i, (dep_name, dep_cfg) in enumerate(sf_deployments.items()):
            dep_type = dep_cfg.get("type", "local")
            if dep_name not in deployment_services:
                continue
            if dep_type in _WRAPPER_DEPLOYMENT_TYPES:
                continue

            services = deployment_services.get(dep_name, {None})
            if dep_type != "slurm":
                services = {None}
            for service in sorted(services, key=lambda item: item or ""):
                ssh_config = _resolve_ssh_config_transitive(dep_cfg)
                loc = Location(
                    name=f"l{len(deployment_to_loc)}",
                    display_name=(
                        dep_name if service is None else f"{dep_name}:{service}"
                    ),
                    data={},
                    hostname=_resolve_hostname_transitive(dep_cfg),
                    port=dep_cfg.get("port", 35050),
                    workdir=dep_cfg.get("workdir"),
                    connection_type=_resolve_connection_type(dep_cfg),
                    username=ssh_config.get("username"),
                    ssh_key=ssh_config.get("ssh_key"),
                    check_host_key=ssh_config.get("check_host_key"),
                    slurm=(
                        _resolve_slurm(dep_cfg, service)
                        if dep_type == "slurm"
                        else None
                    ),
                )
                workflow.add_location(loc)
                deployment_to_loc[(dep_name, service)] = loc

        if not deployment_to_loc:
            loc = Location(
                name="l0",
                display_name="local",
                data={},
                hostname="127.0.0.1",
                port=35050,
            )
            workflow.add_location(loc)
            deployment_to_loc[("local", None)] = loc

        # 3a. Load job settings for workflow input values
        settings_values = self.workflow_inputs

        if default_target[0] is None:
            default_target = next(iter(deployment_to_loc), (None, None))

        default_loc = deployment_to_loc.get(
            default_target, next(iter(deployment_to_loc.values()))
        )

        # 4. Flatten nested subworkflows into leaf steps.
        effective_steps = self._flatten_leaf_steps()

        data_counter = 0
        port_counter = 0
        # Map a global producer key -> the Port that carries its data.
        source_to_port: dict[str, Port] = {}
        unset_optional_sources: set[str] = set()

        # 5a. Root workflow inputs → data at default location.
        for wf_inp in self.cwl_obj.inputs:
            inp_name = _local_name(wf_inp.id)
            data_name = f"d{data_counter}"
            data_counter += 1
            port_name = f"p{port_counter}"
            port_counter += 1
            port = Port(name=port_name, display_name=inp_name, data={data_name})
            source_to_port[inp_name] = port
            data_type = _cwl_type_to_swirl(wf_inp.type_)

            raw_val = settings_values.get(inp_name)
            if raw_val is None and _is_optional_cwl_type(wf_inp.type_):
                unset_optional_sources.add(inp_name)
            if raw_val is not None:
                val = _coerce_cwl_value(raw_val, data_type)
            else:
                val = ""
            default_loc.data[data_name] = Data(
                name=data_name, type=data_type, value=val
            )

        # 5b. Create a Step per leaf, with its output ports + processors.
        path_to_swirl: dict[str, Step] = {}
        for i, eff in enumerate(effective_steps):
            expression = getattr(eff.tool_obj, "expression", None)
            step = Step(
                name=f"s{i}",
                display_name=eff.path,
                command=eff.command,
                expression=expression,
                expression_inputs={} if expression else None,
                expression_input_types={} if expression else None,
                expression_outputs={} if expression else None,
            )
            workflow.add_step(step)
            path_to_swirl[eff.path] = step

            for out_port_id, gkey in eff.outputs:
                glob_val = None
                out_type = DATA_TYPE
                if hasattr(eff.tool_obj, "outputs"):
                    for tool_out in eff.tool_obj.outputs:
                        if _local_name(tool_out.id).split("/")[-1] == out_port_id:
                            binding = getattr(tool_out, "outputBinding", None)
                            if binding and binding.glob:
                                glob_val = binding.glob
                            out_type = _cwl_type_to_swirl(
                                getattr(tool_out, "type_", None)
                            )
                            break

                data_name = f"d{data_counter}"
                data_counter += 1
                port_name = f"p{port_counter}"
                port_counter += 1
                port = Port(name=port_name, display_name=gkey, data={data_name})
                workflow.add_output_port(step, port)
                if step.expression is not None:
                    step.expression_outputs[out_port_id] = port

                if step.processors is None:
                    step.processors = {}
                step.processors[port_name] = Processor(type=out_type, glob=glob_val)

                source_to_port[gkey] = port

        # 5c. Wire leaf-step inputs to the ports that produce their data.
        for eff in effective_steps:
            swirl_step = path_to_swirl[eff.path]
            arg_bindings = []
            tool_inputs = {
                _local_name(tool_in.id).split("/")[-1]: tool_in
                for tool_in in getattr(eff.tool_obj, "inputs", [])
            }
            for _param, gkey in eff.inputs:
                if gkey is not None and gkey in source_to_port:
                    if gkey in unset_optional_sources:
                        continue
                    input_port = source_to_port[gkey]
                    workflow.add_input_port(swirl_step, input_port)
                    tool_in = tool_inputs.get(_param)
                    if swirl_step.expression is not None and tool_in is not None:
                        swirl_step.expression_inputs[_param] = input_port
                        swirl_step.expression_input_types[_param] = _cwl_type_to_swirl(
                            tool_in.type_
                        )
                    binding = (
                        getattr(tool_in, "inputBinding", None) if tool_in else None
                    )
                    if binding is None:
                        continue
                    pos = binding.position if binding.position is not None else 999
                    args: list[str | Port] = []
                    if binding.prefix:
                        args.append(binding.prefix)
                    args.append(input_port)
                    arg_bindings.append((pos, _param, args))
            if arg_bindings:
                swirl_step.arguments = []
                for _pos, _param, args in sorted(
                    arg_bindings, key=lambda item: (item[0], item[1])
                ):
                    swirl_step.arguments.extend(args)

        # 6. Map steps to locations. Streamflow bindings use "/"-separated step
        # paths; match the longest bound prefix of each leaf's path.
        def _target_for(path: str) -> tuple[str | None, str | None]:
            parts = path.split("/")
            for n in range(len(parts), 0, -1):
                prefix = "/".join(parts[:n])
                if prefix in step_to_target:
                    return step_to_target[prefix]
            return default_target

        for eff in effective_steps:
            swirl_step = path_to_swirl[eff.path]
            target = _target_for(eff.path)
            loc = deployment_to_loc.get(target)
            if loc is None and target[0] is not None:
                loc = deployment_to_loc.get((target[0], None))
            if loc is None:
                loc = next(iter(deployment_to_loc.values()))
            workflow.map(swirl_step, loc)

        return workflow

    def _has_scatter(self) -> bool:
        for s in self.cwl_obj.steps:
            if getattr(s, "scatter", None):
                return True
        effective_steps = self._flatten_leaf_steps()
        return any(eff.scatter is not None for eff in effective_steps)

    def translate(
        self, workflow_output: TextIO = sys.stdout, metadata_output: TextIO = sys.stdout
    ) -> None:
        if not self._has_scatter():
            super().translate(workflow_output, metadata_output)
            return

        subwf_scatter_step = None
        for s in self.cwl_obj.steps:
            if getattr(s, "scatter", None):
                run_obj = self.cwl_bundle[s.run] if isinstance(s.run, str) else s.run
                if hasattr(run_obj, "steps") and not hasattr(run_obj, "baseCommand"):
                    subwf_scatter_step = s
                    break

        if subwf_scatter_step:
            self._translate_subworkflow_scatter(
                subwf_scatter_step, workflow_output, metadata_output
            )
            return

        self._translate_scatter(workflow_output, metadata_output)

    def _translate_subworkflow_scatter(
        self, subwf_step, workflow_output: TextIO, metadata_output: TextIO
    ) -> None:
        subwf_name = _local_name(subwf_step.id).split("/")[-1]
        subwf_run = subwf_step.run
        subwf_obj = (
            self.cwl_bundle[subwf_run] if isinstance(subwf_run, str) else subwf_run
        )

        raw_scatter = getattr(subwf_step, "scatter", [])
        if isinstance(raw_scatter, str):
            subwf_scatter_vars = [_local_name(raw_scatter).split("/")[-1]]
        else:
            subwf_scatter_vars = [_local_name(x).split("/")[-1] for x in raw_scatter]
        scatter_method = (
            getattr(subwf_step, "scatterMethod", "dotproduct") or "dotproduct"
        )

        first_wf = next(iter(self.streamflow_config.get("workflows", {}).values()))
        bindings = first_wf.get("bindings", [])
        sf_deployments = self.streamflow_config.get("deployments", {})

        coord_dep_name = "l0"
        for b in bindings:
            if b.get("step") == "/":
                target = b.get("target") or {}
                if target.get("deployment"):
                    coord_dep_name = target["deployment"]

        worker_binding = None
        for b in bindings:
            step_p = b.get("step", "").lstrip("/")
            if step_p in (subwf_name, f"/{subwf_name}"):
                worker_binding = b
                break

        worker_targets: list[dict] = []
        if worker_binding:
            raw_target = worker_binding.get("target")
            if isinstance(raw_target, list):
                worker_targets = raw_target
            elif isinstance(raw_target, dict):
                dep_name = raw_target.get("deployment", "workers")
                loc_cnt = raw_target.get("locations")
                dep_cfg = sf_deployments.get(dep_name, {})
                nodes = dep_cfg.get("config", {}).get("nodes", [])
                if loc_cnt is not None:
                    count = int(loc_cnt)
                elif nodes:
                    count = len(nodes)
                else:
                    count = 2
                for idx in range(count):
                    worker_targets.append({"deployment": dep_name, "index": idx})
        if not worker_targets:
            worker_targets = [
                {"deployment": "workers", "index": 0},
                {"deployment": "workers", "index": 1},
            ]

        def _resolve_hostname(dep_cfg: dict) -> str:
            nodes = dep_cfg.get("config", {}).get("nodes", [])
            return nodes[0] if nodes else "127.0.0.1"

        def _resolve_connection_type(dep_cfg: dict) -> str | None:
            t = dep_cfg.get("type", "local")
            if t == "ssh":
                return "ssh"
            if t == "slurm":
                return "slurm"
            return None

        def _resolve_hostname_transitive(dep_cfg: dict) -> str:
            t = dep_cfg.get("type", "local")
            if t == "slurm":
                wraps = dep_cfg.get("wraps")
                if wraps and wraps in sf_deployments:
                    return _resolve_hostname_transitive(sf_deployments[wraps])
            return _resolve_hostname(dep_cfg)

        def _resolve_ssh_config_transitive(dep_cfg: dict) -> dict:
            t = dep_cfg.get("type", "local")
            if t == "slurm":
                wraps = dep_cfg.get("wraps")
                if wraps and wraps in sf_deployments:
                    return _resolve_ssh_config_transitive(sf_deployments[wraps])
                return {}
            if t != "ssh":
                return {}
            config = dep_cfg.get("config", {}) or {}
            return {
                k: v
                for k, v in {
                    "username": config.get("username"),
                    "ssh_key": config.get("sshKey"),
                    "check_host_key": config.get("checkHostKey"),
                }.items()
                if v is not None
            }

        locations: dict[str, dict] = {}

        coord_cfg = sf_deployments.get(coord_dep_name, {})
        coord_loc: dict = {}
        coord_dep: dict = {}
        conn = _resolve_connection_type(coord_cfg)
        if conn:
            coord_dep["type"] = conn
        coord_dep["hostname"] = _resolve_hostname_transitive(coord_cfg)
        coord_dep["port"] = coord_cfg.get("port", 35050)
        if coord_cfg.get("workdir"):
            coord_dep["workdir"] = coord_cfg["workdir"]
        coord_ssh = _resolve_ssh_config_transitive(coord_cfg)
        if coord_ssh.get("username"):
            coord_dep["username"] = coord_ssh["username"]
        if coord_ssh.get("ssh_key"):
            coord_dep["sshKey"] = coord_ssh["ssh_key"]
        if coord_ssh.get("check_host_key") is not None:
            coord_dep["checkHostKey"] = coord_ssh["check_host_key"]
        coord_loc["deployment"] = coord_dep
        locations["l0"] = coord_loc

        worker_names: list[str] = []
        for i, wt in enumerate(worker_targets):
            w_name = f"l{i + 1}"
            worker_names.append(w_name)
            w_dep_name = wt.get("deployment", "workers")
            w_cfg = sf_deployments.get(w_dep_name, {})
            w_loc: dict = {}
            w_dep: dict = {}
            w_conn = _resolve_connection_type(w_cfg)
            if w_conn:
                w_dep["type"] = w_conn
            nodes = w_cfg.get("config", {}).get("nodes", [])
            w_idx = wt.get("index", i)
            if nodes and w_idx < len(nodes):
                w_dep["hostname"] = nodes[w_idx]
            else:
                w_dep["hostname"] = _resolve_hostname_transitive(w_cfg)
            base_port = w_cfg.get("port", 35051)
            w_dep["port"] = base_port + i
            if w_cfg.get("workdir"):
                w_dep["workdir"] = w_cfg["workdir"]
            w_ssh = _resolve_ssh_config_transitive(w_cfg)
            if w_ssh.get("username"):
                w_dep["username"] = w_ssh["username"]
            if w_ssh.get("ssh_key"):
                w_dep["sshKey"] = w_ssh["ssh_key"]
            if w_ssh.get("check_host_key") is not None:
                w_dep["checkHostKey"] = w_ssh["check_host_key"]
            w_loc["deployment"] = w_dep
            locations[w_name] = w_loc

        settings_values = self.workflow_inputs

        dependencies: dict[str, dict] = {}
        dependencies["id_ID"] = {"type": "file"}
        dependencies["group_ID"] = {"type": "file"}
        dependencies["eof"] = {"type": "string"}

        dataset_pairs: list[tuple[str, str]] = []
        source_to_in_pair: dict[str, tuple[str, str]] = {}
        in_counter = 1
        for wf_inp in self.cwl_obj.inputs:
            inp_name = _local_name(wf_inp.id).split("/")[-1]
            d_name = f"d_in{in_counter}"
            p_name = f"p_in{in_counter}"
            in_counter += 1
            data_type = _cwl_type_to_swirl(wf_inp.type_)
            raw_val = settings_values.get(inp_name, [])
            coerced_val = _coerce_cwl_value(raw_val, data_type, self.cwl_file.parent)
            dependencies[d_name] = {
                "type": data_type,
                "value": coerced_val,
            }
            dataset_pairs.append((p_name, d_name))
            source_to_in_pair[inp_name] = (p_name, d_name)

        subwf_inputs_info: list[tuple[str, str, str, bool, str]] = []
        scatter_in_ports: list[str] = []
        scatter_pair_input_ports: list[tuple[str, str]] = []

        for sin in subwf_step.in_:
            param_name = _local_name(sin.id).split("/")[-1]
            src = sin.source
            if isinstance(src, list):
                src = src[0] if src else None
            src_name = _local_name(src).split("/")[-1] if src else None
            if src_name and src_name in source_to_in_pair:
                p_name, d_name = source_to_in_pair[src_name]
                is_sc = param_name in subwf_scatter_vars
                d_type = dependencies[d_name]["type"]
                subwf_inputs_info.append((param_name, p_name, d_name, is_sc, d_type))
                scatter_pair_input_ports.append((p_name, d_name))
                if is_sc:
                    scatter_in_ports.append(p_name)

        steps: dict[str, dict] = {}

        steps["s_sc"] = {
            "displayName": "ScatterPairer",
            "type": "scatter_pairer",
            "outputs": {
                "p_id": {"dataName": "id_ID"},
                "p_group": {"dataName": "group_ID"},
            },
            "scatterPorts": scatter_in_ports,
            "scatterMethod": scatter_method,
        }

        op_outputs: dict[str, dict] = {}
        unpacked_pairs: list[tuple[str, str]] = []
        env: dict[str, str] = {}

        for param_name, _, _, is_sc, d_type in subwf_inputs_info:
            p_sub = f"p_sub_{param_name}"
            d_sub = f"sub_{param_name}_ID"
            unpacked_pairs.append((p_sub, d_sub))
            inner_t = _list_inner_type(d_type)
            elem_type = inner_t if (is_sc and inner_t) else d_type
            dependencies[d_sub] = {"type": elem_type}
            op_outputs[p_sub] = {"dataName": d_sub}
            env[param_name] = p_sub

        steps["s_op"] = {
            "displayName": "ScatterOpen",
            "type": "scatter_open",
            "outputs": op_outputs,
        }

        def _resolve_token(token: str) -> str:
            p = Path(token)
            if not p.is_absolute():
                cand = (self.cwl_file.parent / p).resolve()
                if cand.exists():
                    return str(cand)
            return token

        def _resolve_glob(tool_obj, glob_pat: str | None) -> str | None:
            if not glob_pat:
                return None
            if "$(" in glob_pat:
                for inp in getattr(tool_obj, "inputs", []):
                    pname = _local_name(inp.id).split("/")[-1]
                    if f"inputs.{pname}" in glob_pat:
                        dval = getattr(inp, "default", None)
                        if dval is not None:
                            return str(dval)
            return glob_pat

        worker_exec_traces: list[str] = []
        for cstep in subwf_obj.steps:
            cname = _local_name(cstep.id).split("/")[-1]
            s_name = f"s_{cname}"
            crun = cstep.run
            c_obj = self.cwl_bundle[crun] if isinstance(crun, str) else crun

            child_in_bindings: dict[str, str] = {}
            for cin in cstep.in_:
                cin_param = _local_name(cin.id).split("/")[-1]
                csrc = cin.source
                if isinstance(csrc, list):
                    csrc = csrc[0] if csrc else None
                csrc_str = _local_name(csrc) if csrc else None
                if csrc_str:
                    if csrc_str in env:
                        child_in_bindings[cin_param] = env[csrc_str]
                    elif "/" in csrc_str:
                        step_part, _, port_part = csrc_str.rpartition("/")
                        short_key = f"{step_part.split('/')[-1]}/{port_part}"
                        if short_key in env:
                            child_in_bindings[cin_param] = env[short_key]
                    else:
                        short_key = csrc_str.split("/")[-1]
                        if short_key in env:
                            child_in_bindings[cin_param] = env[short_key]

            expr = getattr(c_obj, "expression", None)
            if expr:
                expr_inputs = {}
                for tin in getattr(c_obj, "inputs", []):
                    pname = _local_name(tin.id).split("/")[-1]
                    if pname in child_in_bindings:
                        expr_inputs[pname] = {
                            "port": child_in_bindings[pname],
                            "type": _cwl_type_to_swirl(tin.type_),
                        }
                expr_outputs = {}
                step_outputs = {}
                flow_outs = []
                for tout in getattr(c_obj, "outputs", []):
                    oname = _local_name(tout.id).split("/")[-1]
                    out_port = f"p_{cname}_{oname}"
                    out_data = f"{cname}_{oname}_ID"
                    out_type = _cwl_type_to_swirl(tout.type_)
                    dependencies[out_data] = {"type": out_type}
                    expr_outputs[oname] = out_port
                    step_outputs[out_port] = {"dataName": out_data}
                    flow_outs.append(f"({out_port}, {out_data})")
                    env[f"{cname}/{oname}"] = out_port
                    env[oname] = out_port

                steps[s_name] = {
                    "displayName": cname,
                    "expression": {
                        "source": expr,
                        "inputs": expr_inputs,
                        "outputs": expr_outputs,
                    },
                    "outputs": step_outputs,
                }
                flow_in_tuples = []
                for p in expr_inputs:
                    in_port = child_in_bindings[p]
                    d_found = in_port.replace("p_", "") + "_ID"
                    for dp, dn in unpacked_pairs:
                        if dp == in_port:
                            d_found = dn
                            break
                    flow_in_tuples.append(f"({in_port}, {d_found})")

                worker_exec_traces.append(
                    f"exec({s_name}, {{{', '.join(flow_in_tuples)}}} -> {{{', '.join(flow_outs)}}}, {{{'{w}'}}})"
                )
            else:
                c_scatter = getattr(cstep, "scatter", None)
                if c_scatter:
                    c_scatter_vars = [
                        _local_name(x).split("/")[-1]
                        for x in (
                            c_scatter if isinstance(c_scatter, list) else [c_scatter]
                        )
                    ]
                else:
                    c_scatter_vars = []
                c_scatter_method = (
                    getattr(cstep, "scatterMethod", "dotproduct") or "dotproduct"
                )

                cmd_args: list[dict] = []
                bc = getattr(c_obj, "baseCommand", None)
                if isinstance(bc, list) and len(bc) > 1:
                    for extra in bc[1:]:
                        cmd_args.append({"value": _resolve_token(str(extra))})

                tool_in_bindings: list[tuple[int, dict]] = []
                flow_in_tuples = []
                for tin in getattr(c_obj, "inputs", []):
                    pname = _local_name(tin.id).split("/")[-1]
                    b = getattr(tin, "inputBinding", None)
                    if pname in child_in_bindings:
                        in_port = child_in_bindings[pname]
                        d_found = in_port.replace("p_", "") + "_ID"
                        for dp, dn in unpacked_pairs:
                            if dp == in_port:
                                d_found = dn
                                break
                        for prev_s in steps.values():
                            if in_port in prev_s.get("outputs", {}):
                                d_found = prev_s["outputs"][in_port]["dataName"]
                                break
                        flow_in_tuples.append(f"({in_port}, {d_found})")
                        if b:
                            pos = b.position if b.position is not None else 999
                            if b.prefix:
                                tool_in_bindings.append((pos, {"value": b.prefix}))
                            tool_in_bindings.append((pos, {"valueFrom": in_port}))
                    elif getattr(tin, "default", None) is not None and b:
                        pos = b.position if b.position is not None else 999
                        if b.prefix:
                            tool_in_bindings.append((pos, {"value": b.prefix}))
                        tool_in_bindings.append((pos, {"value": str(tin.default)}))

                tool_in_bindings.sort(key=lambda item: item[0])
                cmd_args.extend([item[1] for item in tool_in_bindings])

                step_outputs = {}
                flow_outs = []
                for tout in getattr(c_obj, "outputs", []):
                    oname = _local_name(tout.id).split("/")[-1]
                    out_port = f"p_{cname}_{oname}"
                    out_data = f"{cname}_{oname}_ID"
                    out_type = _cwl_type_to_swirl(tout.type_)
                    if c_scatter_vars:
                        out_type = f"list[{out_type}]"
                    ob = getattr(tout, "outputBinding", None)
                    glob_v = _resolve_glob(c_obj, ob.glob if ob else None)
                    dependencies[out_data] = {"type": out_type}
                    step_outputs[out_port] = {"dataName": out_data, "glob": glob_v}
                    flow_outs.append(f"({out_port}, {out_data})")
                    env[f"{cname}/{oname}"] = out_port
                    env[oname] = out_port

                base_cmd_0 = bc[0] if isinstance(bc, list) and bc else (bc or "")
                step_entry = {
                    "displayName": cname,
                    "command": base_cmd_0,
                    "arguments": cmd_args,
                    "outputs": step_outputs,
                }
                if c_scatter_vars:
                    step_entry["scatter"] = [
                        child_in_bindings[v]
                        for v in c_scatter_vars
                        if v in child_in_bindings
                    ]
                    step_entry["scatterMethod"] = c_scatter_method

                steps[s_name] = step_entry
                worker_exec_traces.append(
                    f"exec({s_name}, {{{', '.join(flow_in_tuples)}}} -> {{{', '.join(flow_outs)}}}, {{{'{w}'}}})"
                )

        subwf_output_ports = []
        subwf_output_data_names = []
        gather_output_specs = {}
        gather_in_flow = []
        gather_out_flow = []

        for sout in subwf_obj.outputs:
            out_id = _local_name(sout.id).split("/")[-1]
            osrc = sout.outputSource
            if isinstance(osrc, list):
                osrc = osrc[0] if osrc else None
            osrc_str = _local_name(osrc) if osrc else ""
            step_part, _, port_part = osrc_str.rpartition("/")
            src_key = f"{step_part.split('/')[-1]}/{port_part}"
            res_port = env.get(src_key) or env.get(port_part)
            res_data = None
            for s in steps.values():
                if res_port in s.get("outputs", {}):
                    res_data = s["outputs"][res_port]["dataName"]
                    break
            if not res_data:
                res_data = f"{out_id}_ID"

            subwf_output_ports.append(res_port)
            subwf_output_data_names.append(res_data)

            gathered_port = f"p_out_{out_id}"
            gathered_data = f"d_out_{out_id}"
            elem_type = dependencies.get(res_data, {}).get("type", "file")
            gathered_type = f"list[{elem_type}]"
            dependencies[gathered_data] = {"type": gathered_type}

            gather_output_specs[gathered_port] = {"dataName": gathered_data}
            gather_in_flow.append(f"({res_port}, {res_data})")
            gather_out_flow.append(f"({gathered_port}, {gathered_data})")
            env[f"{subwf_name}/{out_id}"] = gathered_port
            env[out_id] = gathered_port

        steps["s_G"] = {
            "displayName": "ScatterGather",
            "type": "scatter_gather",
            "outputs": gather_output_specs,
        }

        post_exec_traces = []
        for step in self.cwl_obj.steps:
            if step == subwf_step:
                continue
            pname = _local_name(step.id).split("/")[-1]
            s_name = f"s_{pname}"
            prun = step.run
            ptool = self.cwl_bundle[prun] if isinstance(prun, str) else prun

            p_in_bindings: list[tuple[int, dict]] = []
            flow_in_tuples = []
            for tin in getattr(ptool, "inputs", []):
                param_n = _local_name(tin.id).split("/")[-1]
                b = getattr(tin, "inputBinding", None)
                matching_sin = next(
                    (
                        si
                        for si in step.in_
                        if _local_name(si.id).split("/")[-1] == param_n
                    ),
                    None,
                )
                if matching_sin:
                    src = matching_sin.source
                    if isinstance(src, list):
                        src = src[0] if src else None
                    src_str = _local_name(src) if src else ""
                    step_p, _, port_p = src_str.rpartition("/")
                    key1 = f"{step_p.split('/')[-1]}/{port_p}"
                    in_port = env.get(key1) or env.get(port_p)
                    if in_port:
                        d_name = steps["s_G"]["outputs"][in_port]["dataName"]
                        flow_in_tuples.append(f"({in_port}, {d_name})")
                        if b:
                            pos = b.position if b.position is not None else 999
                            if b.prefix:
                                p_in_bindings.append((pos, {"value": b.prefix}))
                            p_in_bindings.append((pos, {"valueFrom": in_port}))

            tool_args: list[dict] = []
            p_bc = getattr(ptool, "baseCommand", None)
            if isinstance(p_bc, list) and len(p_bc) > 1:
                for extra in p_bc[1:]:
                    tool_args.append({"value": _resolve_token(str(extra))})
            p_in_bindings.sort(key=lambda item: item[0])
            tool_args.extend([item[1] for item in p_in_bindings])

            step_outputs = {}
            flow_outs = []
            for tout in getattr(ptool, "outputs", []):
                oname = _local_name(tout.id).split("/")[-1]
                out_port = f"p_{pname}_{oname}"
                out_data = f"d_{pname}_{oname}"
                out_type = _cwl_type_to_swirl(tout.type_)
                ob = getattr(tout, "outputBinding", None)
                glob_v = _resolve_glob(ptool, ob.glob if ob else None)
                dependencies[out_data] = {"type": out_type}
                step_outputs[out_port] = {"dataName": out_data, "glob": glob_v}
                flow_outs.append(f"({out_port}, {out_data})")

            base_cmd = p_bc[0] if isinstance(p_bc, list) and p_bc else (p_bc or "")
            steps[s_name] = {
                "displayName": pname,
                "command": base_cmd,
                "arguments": tool_args,
                "outputs": step_outputs,
            }
            post_exec_traces.append(
                f"exec({s_name}, {{{', '.join(flow_in_tuples)}}} -> {{{', '.join(flow_outs)}}}, {{l0}})"
            )

        worker_set_str = "{" + ", ".join(worker_names) + "}"
        send_eof_workers = " |\n        ".join(
            [f"send(eof -> p_id, l0, {w})" for w in worker_names]
        )

        dataset_str = ", ".join([f"({p}, {d})" for p, d in dataset_pairs])
        scatter_in_str = ", ".join([f"({p}, {d})" for p, d in scatter_pair_input_ports])

        recv_workers_branches = []
        for w in worker_names:
            recv_res = " . ".join(
                [
                    f"recv({d} -> {p}, {w}, l0)"
                    for p, d in zip(subwf_output_ports, subwf_output_data_names)
                ]
            )
            recv_eof = " . ".join(
                [f"recv(eof -> {p}, {w}, l0)" for p in subwf_output_ports]
            )
            recv_workers_branches.append(
                f"!(\n      ({recv_res})\n      +\n      ({recv_eof})\n    )"
            )
        recv_workers_str = " |\n    ".join(recv_workers_branches)

        post_trace_str = ""
        if post_exec_traces:
            post_trace_str = " .\n  " + " .\n  ".join(post_exec_traces)

        l0_trace = f"""<l0, {{{dataset_str}}},
  exec(s_sc, {{{scatter_in_str}}} -> {{(p_id, id_ID), (p_group, group_ID)}}, {{l0}})
  .
  (
    !(
      (
        move(id_ID -> p_id, l0, {worker_set_str}) .
        move(group_ID -> p_group, l0, {worker_set_str})
      )
      +
      (
        {send_eof_workers}
      )
    )
  )
  .
  (
    {recv_workers_str}
  )
  .
  exec(s_G, {{{', '.join(gather_in_flow)}}} -> {{{', '.join(gather_out_flow)}}}, {{l0}}){post_trace_str}
>"""

        unpacked_out_str = ", ".join([f"({p}, {d})" for p, d in unpacked_pairs])
        inner_worker_trace_body = " .\n      ".join(worker_exec_traces)

        worker_traces: list[str] = []
        for w in worker_names:
            send_outs = " .\n      ".join(
                [
                    f"send({d} -> {p}, {w}, l0)"
                    for p, d in zip(subwf_output_ports, subwf_output_data_names)
                ]
            )
            send_eofs = " .\n      ".join(
                [f"send(eof -> {p}, {w}, l0)" for p in subwf_output_ports]
            )
            w_trace_formatted = inner_worker_trace_body.replace("{w}", w)
            w_trace = f"""<{w}, {{}},
  !(
    (
      recv(id_ID -> p_id, l0, {w}) .
      recv(group_ID -> p_group, l0, {w}) .
      exec(s_op, {{(p_group, group_ID)}} -> {{{unpacked_out_str}}}, {{{w}}}) .
      {w_trace_formatted} .
      {send_outs}
    )
    +
    (
      recv(eof -> p_id, l0, {w}) .
      {send_eofs}
    )
  )
>"""
            worker_traces.append(w_trace)

        full_swirl_trace = l0_trace + " |\n\n" + " |\n\n".join(worker_traces) + "\n"
        workflow_output.write(full_swirl_trace)

        YAML().dump(
            {
                "version": "v1.0",
                "steps": steps,
                "locations": locations,
                "dependencies": dependencies,
            },
            metadata_output,
        )

    def _translate_scatter(
        self, workflow_output: TextIO, metadata_output: TextIO
    ) -> None:
        effective_steps = self._flatten_leaf_steps()
        scatter_eff = next((s for s in effective_steps if s.scatter), None)
        if not scatter_eff:
            super().translate(workflow_output, metadata_output)
            return

        post_effs = [s for s in effective_steps if s != scatter_eff]

        # 1. Parse deployments & worker count
        first_wf = next(iter(self.streamflow_config.get("workflows", {}).values()))
        bindings = first_wf.get("bindings", [])
        sf_deployments = self.streamflow_config.get("deployments", {})

        coord_dep_name = "l0"
        for b in bindings:
            if b.get("step") == "/":
                target = b.get("target") or {}
                if target.get("deployment"):
                    coord_dep_name = target["deployment"]

        worker_binding = None
        for b in bindings:
            step_p = b.get("step", "").lstrip("/")
            if step_p == scatter_eff.path or step_p == scatter_eff.display_name:
                worker_binding = b
                break

        worker_targets: list[dict] = []
        if worker_binding:
            raw_target = worker_binding.get("target")
            if isinstance(raw_target, list):
                worker_targets = raw_target
            elif isinstance(raw_target, dict):
                dep_name = raw_target.get("deployment", "workers")
                loc_cnt = raw_target.get("locations")
                dep_cfg = sf_deployments.get(dep_name, {})
                nodes = dep_cfg.get("config", {}).get("nodes", [])
                if loc_cnt is not None:
                    count = int(loc_cnt)
                elif nodes:
                    count = len(nodes)
                else:
                    count = 3
                for idx in range(count):
                    worker_targets.append({"deployment": dep_name, "index": idx})
        if not worker_targets:
            worker_targets = [
                {"deployment": "workers", "index": 0},
                {"deployment": "workers", "index": 1},
                {"deployment": "workers", "index": 2},
            ]

        def _resolve_hostname(dep_cfg: dict) -> str:
            nodes = dep_cfg.get("config", {}).get("nodes", [])
            return nodes[0] if nodes else "127.0.0.1"

        def _resolve_connection_type(dep_cfg: dict) -> str | None:
            t = dep_cfg.get("type", "local")
            if t == "ssh":
                return "ssh"
            if t == "slurm":
                return "slurm"
            return None

        def _resolve_hostname_transitive(dep_cfg: dict) -> str:
            t = dep_cfg.get("type", "local")
            if t == "slurm":
                wraps = dep_cfg.get("wraps")
                if wraps and wraps in sf_deployments:
                    return _resolve_hostname_transitive(sf_deployments[wraps])
            return _resolve_hostname(dep_cfg)

        def _resolve_ssh_config_transitive(dep_cfg: dict) -> dict:
            t = dep_cfg.get("type", "local")
            if t == "slurm":
                wraps = dep_cfg.get("wraps")
                if wraps and wraps in sf_deployments:
                    return _resolve_ssh_config_transitive(sf_deployments[wraps])
                return {}
            if t != "ssh":
                return {}
            config = dep_cfg.get("config", {}) or {}
            return {
                k: v
                for k, v in {
                    "username": config.get("username"),
                    "ssh_key": config.get("sshKey"),
                    "check_host_key": config.get("checkHostKey"),
                }.items()
                if v is not None
            }

        locations: dict[str, dict] = {}

        # Coordinator location l0
        coord_cfg = sf_deployments.get(coord_dep_name, {})
        coord_loc: dict = {}
        coord_dep: dict = {}
        conn = _resolve_connection_type(coord_cfg)
        if conn:
            coord_dep["type"] = conn
        coord_dep["hostname"] = _resolve_hostname_transitive(coord_cfg)
        coord_dep["port"] = coord_cfg.get("port", 35050)
        if coord_cfg.get("workdir"):
            coord_dep["workdir"] = coord_cfg["workdir"]
        coord_ssh = _resolve_ssh_config_transitive(coord_cfg)
        if coord_ssh.get("username"):
            coord_dep["username"] = coord_ssh["username"]
        if coord_ssh.get("ssh_key"):
            coord_dep["sshKey"] = coord_ssh["ssh_key"]
        if coord_ssh.get("check_host_key") is not None:
            coord_dep["checkHostKey"] = coord_ssh["check_host_key"]
        coord_loc["deployment"] = coord_dep
        locations["l0"] = coord_loc

        # Worker locations l1, l2, ...
        worker_names: list[str] = []
        for i, wt in enumerate(worker_targets):
            w_name = f"l{i + 1}"
            worker_names.append(w_name)
            w_dep_name = wt.get("deployment", "workers")
            w_cfg = sf_deployments.get(w_dep_name, {})
            w_loc: dict = {}
            w_dep: dict = {}
            w_conn = _resolve_connection_type(w_cfg)
            if w_conn:
                w_dep["type"] = w_conn
            nodes = w_cfg.get("config", {}).get("nodes", [])
            w_idx = wt.get("index", i)
            if nodes and w_idx < len(nodes):
                w_dep["hostname"] = nodes[w_idx]
            else:
                w_dep["hostname"] = _resolve_hostname_transitive(w_cfg)
            base_port = w_cfg.get("port", 35051)
            w_dep["port"] = base_port + i
            if w_cfg.get("workdir"):
                w_dep["workdir"] = w_cfg["workdir"]
            w_ssh = _resolve_ssh_config_transitive(w_cfg)
            if w_ssh.get("username"):
                w_dep["username"] = w_ssh["username"]
            if w_ssh.get("ssh_key"):
                w_dep["sshKey"] = w_ssh["ssh_key"]
            if w_ssh.get("check_host_key") is not None:
                w_dep["checkHostKey"] = w_ssh["check_host_key"]
            w_loc["deployment"] = w_dep
            locations[w_name] = w_loc

        # 2. Workflow inputs & settings
        settings_values = self.workflow_inputs

        dependencies: dict[str, dict] = {}
        dependencies["id_ID"] = {"type": "file"}
        dependencies["group_ID"] = {"type": "file"}
        dependencies["res_ID"] = {"type": "file"}
        dependencies["d_out"] = {"type": "list[file]"}
        dependencies["eof"] = {"type": "string"}

        dataset_pairs: list[tuple[str, str]] = []
        scatter_input_pairs: list[tuple[str, str]] = []

        in_counter = 1
        source_to_in_pair: dict[str, tuple[str, str]] = {}
        for wf_inp in self.cwl_obj.inputs:
            inp_name = _local_name(wf_inp.id)
            d_name = f"d_in{in_counter}"
            p_name = f"p_in{in_counter}"
            in_counter += 1
            data_type = _cwl_type_to_swirl(wf_inp.type_)
            raw_val = settings_values.get(inp_name, [])
            coerced_val = _coerce_cwl_value(raw_val, data_type, self.cwl_file.parent)
            dependencies[d_name] = {
                "type": data_type,
                "value": coerced_val,
            }
            dataset_pairs.append((p_name, d_name))
            source_to_in_pair[inp_name] = (p_name, d_name)

        for param_name, src_key in scatter_eff.inputs:
            if src_key and src_key in source_to_in_pair:
                scatter_input_pairs.append(source_to_in_pair[src_key])

        # 3. Setup steps
        steps: dict[str, dict] = {}

        # s_sc
        steps["s_sc"] = {
            "displayName": "ScatterPairer",
            "type": "scatter_pairer",
            "outputs": {
                "p_id": {"dataName": "id_ID"},
                "p_group": {"dataName": "group_ID"},
            },
        }
        if scatter_eff.scatter_method:
            steps["s_sc"]["scatterMethod"] = scatter_eff.scatter_method

        # s_op
        op_outputs: dict[str, dict] = {}
        unpacked_ports: list[str] = []
        unpacked_port_map: dict[str, str] = {}
        unpacked_pairs: list[tuple[str, str]] = []
        for k, (param_name, _) in enumerate(scatter_eff.inputs):
            char_id = chr(ord("a") + k)
            p_name = f"p_{char_id}"
            d_name = f"{char_id}_ID"
            unpacked_ports.append(p_name)
            unpacked_port_map[param_name] = p_name
            unpacked_pairs.append((p_name, d_name))
            dependencies[d_name] = {"type": "file"}
            op_outputs[p_name] = {"dataName": d_name}

        steps["s_op"] = {
            "displayName": "ScatterOpen",
            "type": "scatter_open",
            "outputs": op_outputs,
        }

        def _resolve_token(token: str) -> str:
            p = Path(token)
            if not p.is_absolute():
                candidate = (self.cwl_file.parent / p).resolve()
                if candidate.exists():
                    return str(candidate)
            return token

        def _resolve_glob(tool_obj, glob_pat: str | None) -> str | None:
            if not glob_pat:
                return None
            if "$(" in glob_pat:
                for inp in getattr(tool_obj, "inputs", []):
                    pname = _local_name(inp.id).split("/")[-1]
                    if f"inputs.{pname}" in glob_pat:
                        dval = getattr(inp, "default", None)
                        if dval is not None:
                            return str(dval)
            return glob_pat

        # s_work
        work_tool = scatter_eff.tool_obj
        work_args: list[dict] = []
        bc = getattr(work_tool, "baseCommand", None)
        if isinstance(bc, list) and len(bc) > 1:
            for extra in bc[1:]:
                work_args.append({"value": _resolve_token(str(extra))})

        tool_in_bindings: list[tuple[int, dict]] = []
        for tin in getattr(work_tool, "inputs", []):
            pname = _local_name(tin.id).split("/")[-1]
            b = getattr(tin, "inputBinding", None)
            if not b:
                continue
            pos = b.position if b.position is not None else 999
            if pname in ("id", "p_id"):
                if b.prefix:
                    tool_in_bindings.append((pos, {"value": b.prefix}))
                tool_in_bindings.append((pos, {"valueFrom": "p_id"}))
            elif pname in unpacked_port_map:
                if b.prefix:
                    tool_in_bindings.append((pos, {"value": b.prefix}))
                tool_in_bindings.append((pos, {"valueFrom": unpacked_port_map[pname]}))
            elif getattr(tin, "default", None) is not None:
                if b.prefix:
                    tool_in_bindings.append((pos, {"value": b.prefix}))
                tool_in_bindings.append((pos, {"value": str(tin.default)}))

        tool_in_bindings.sort(key=lambda item: item[0])
        work_args.extend([item[1] for item in tool_in_bindings])

        work_glob = "result.txt"
        for tout in getattr(work_tool, "outputs", []):
            ob = getattr(tout, "outputBinding", None)
            if ob and ob.glob:
                work_glob = _resolve_glob(work_tool, ob.glob) or "result.txt"
                break

        steps["s_work"] = {
            "displayName": scatter_eff.display_name,
            "command": scatter_eff.command,
            "arguments": work_args,
            "outputs": {
                "p_res": {
                    "dataName": "res_ID",
                    "glob": work_glob,
                }
            },
        }

        # s_G
        steps["s_G"] = {
            "displayName": "ScatterGather",
            "type": "scatter_gather",
            "outputs": {
                "p_out": {
                    "dataName": "d_out",
                }
            },
        }

        # Post-scatter steps (e.g. analyze)
        post_exec_traces: list[str] = []
        for post_idx, peff in enumerate(post_effs):
            s_name = f"s_post{post_idx if len(post_effs) > 1 else ''}"
            ptool = peff.tool_obj
            p_args: list[dict] = []
            p_bc = getattr(ptool, "baseCommand", None)
            if isinstance(p_bc, list) and len(p_bc) > 1:
                for extra in p_bc[1:]:
                    p_args.append({"value": _resolve_token(str(extra))})

            p_in_bindings: list[tuple[int, dict]] = []
            for tin in getattr(ptool, "inputs", []):
                pname = _local_name(tin.id).split("/")[-1]
                b = getattr(tin, "inputBinding", None)
                if not b:
                    continue
                pos = b.position if b.position is not None else 999
                is_scatter_out = any(
                    src and src.startswith(f"{scatter_eff.path}/")
                    for pin_name, src in peff.inputs
                    if pin_name == pname
                )
                if is_scatter_out:
                    if b.prefix:
                        p_in_bindings.append((pos, {"value": b.prefix}))
                    p_in_bindings.append((pos, {"valueFrom": "p_out"}))
                elif getattr(tin, "default", None) is not None:
                    if b.prefix:
                        p_in_bindings.append((pos, {"value": b.prefix}))
                    p_in_bindings.append((pos, {"value": str(tin.default)}))

            p_in_bindings.sort(key=lambda item: item[0])
            p_args.extend([item[1] for item in p_in_bindings])

            p_glob = "analysis_report.txt"
            p_out_port = "p_report"
            p_out_data = "d_report"
            for tout in getattr(ptool, "outputs", []):
                ob = getattr(tout, "outputBinding", None)
                if ob and ob.glob:
                    p_glob = _resolve_glob(ptool, ob.glob) or "analysis_report.txt"
                    break

            steps[s_name] = {
                "displayName": peff.display_name,
                "command": peff.command,
                "arguments": p_args,
                "outputs": {
                    p_out_port: {
                        "dataName": p_out_data,
                        "glob": p_glob,
                    }
                },
            }
            dependencies[p_out_data] = {"type": "file"}
            post_exec_traces.append(
                f"exec({s_name}, {{(p_out, d_out)}} -> {{({p_out_port}, {p_out_data})}}, {{l0}})"
            )

        # 4. Generate SWIRL trace string
        worker_set_str = "{" + ", ".join(worker_names) + "}"
        send_eof_workers = " |\n        ".join(
            [f"send(eof -> p_id, l0, {w})" for w in worker_names]
        )
        recv_workers = " |\n    ".join(
            [
                f"!(recv(res_ID -> p_res, {w}, l0) + recv(eof -> p_res, {w}, l0))"
                for w in worker_names
            ]
        )

        dataset_str = ", ".join([f"({p}, {d})" for p, d in dataset_pairs])
        scatter_in_str = ", ".join([f"({p}, {d})" for p, d in scatter_input_pairs])

        post_trace_str = ""
        if post_exec_traces:
            post_trace_str = " .\n  " + " .\n  ".join(post_exec_traces)

        # Controller l0
        l0_trace = f"""<l0, {{{dataset_str}}},
  exec(s_sc, {{{scatter_in_str}}} -> {{(p_id, id_ID), (p_group, group_ID)}}, {{l0}})
  .
  (
    !(
      (
        move(id_ID -> p_id, l0, {worker_set_str}) .
        move(group_ID -> p_group, l0, {worker_set_str})
      )
      +
      (
        {send_eof_workers}
      )
    )
  )
  .
  (
    {recv_workers}
  )
  .
  exec(s_G, {{(p_res, res_ID)}} -> {{(p_out, d_out)}}, {{l0}}){post_trace_str}
>"""

        # Workers
        unpacked_out_str = ", ".join([f"({p}, {d})" for p, d in unpacked_pairs])
        work_in_str = (
            "{(p_id, id_ID), "
            + ", ".join([f"({p}, {d})" for p, d in unpacked_pairs])
            + "}"
        )

        worker_traces: list[str] = []
        for w in worker_names:
            w_trace = f"""<{w}, {{}},
  !(
    (
      recv(id_ID -> p_id, l0, {w}) .
      recv(group_ID -> p_group, l0, {w}) .
      exec(s_op, {{(p_group, group_ID)}} -> {{{unpacked_out_str}}}, {{{w}}}) .
      exec(s_work, {work_in_str} -> {{(p_res, res_ID)}}, {{{w}}}) .
      send(res_ID -> p_res, {w}, l0)
    )
    +
    (
      recv(eof -> p_id, l0, {w}) .
      send(eof -> p_res, {w}, l0)
    )
  )
>"""
            worker_traces.append(w_trace)

        full_swirl_trace = l0_trace + " |\n\n" + " |\n\n".join(worker_traces) + "\n"
        workflow_output.write(full_swirl_trace)

        # 5. Output metadata YAML
        YAML().dump(
            {
                "version": "v1.0",
                "steps": steps,
                "locations": locations,
                "dependencies": dependencies,
            },
            metadata_output,
        )
