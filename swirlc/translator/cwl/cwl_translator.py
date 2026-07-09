from __future__ import annotations

# python tmp_main.py translate --language cwl /home/tommo/Coding/ALPHA/swirlc/examples/cwl/basic/main.cwl --outdir /home/tommo/Coding/ALPHA/swirlc/build

import glob
import json
import logging
import os
from collections.abc import MutableMapping, MutableSequence
from pathlib import Path

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


class _EffStep:
    """A flattened leaf step (CommandLineTool / ExpressionTool).

    ``path`` is the slash-joined chain of CWL step names from the root
    workflow down to this leaf (e.g. ``chromosome/individuals``). ``inputs``
    and ``outputs`` carry global producer keys so data flow can be wired
    across subworkflow boundaries.
    """

    __slots__ = ("path", "display_name", "tool_obj", "command", "inputs", "outputs")

    def __init__(self, path, display_name, tool_obj, command, inputs, outputs):
        self.path = path  # e.g. "chromosome/individuals"
        self.display_name = display_name  # leaf step name
        self.tool_obj = tool_obj  # cwl_utils CommandLineTool / ExpressionTool
        self.command = command
        self.inputs = inputs  # list[(param_name, global_source_key | None)]
        self.outputs = outputs  # list[(port_local, global_key)]


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
        root_uri = self.cwl_file.as_uri()
        self.cwl_bundle = load_cwl_workflow_recursive_uri(root_uri)
        self.cwl_obj = self.cwl_bundle[root_uri]

        display_cwl_workflow(self.cwl_obj, bundle=self.cwl_bundle)

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
                    effective.append(
                        _EffStep(
                            spath, sname, run_obj, command, resolved_inputs, outputs
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
        first_wf = next(iter(self.streamflow_config.get("workflows", {}).values()))
        default_target: tuple[str | None, str | None] = (None, None)
        step_to_target: dict[str, tuple[str, str | None]] = {}
        deployment_services: dict[str, set[str | None]] = {}

        for binding in first_wf.get("bindings", []):
            if "step" not in binding:
                continue
            target = binding.get("target") or {}
            dep_name = target.get("deployment")
            if not dep_name:
                continue
            service = target.get("service")
            deployment_services.setdefault(dep_name, set()).add(service)
            step_path: str = binding["step"]
            if step_path == "/":
                default_target = (dep_name, service)
            else:
                step_to_target[step_path.lstrip("/")] = (dep_name, service)

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
        settings_rel = first_wf.get("config", {}).get("settings")
        settings_values: dict = {}
        if settings_rel:
            settings_path = self.cwl_file.parent / settings_rel
            if settings_path.exists():
                with open(settings_path) as f:
                    settings_values = YAML(typ="safe").load(f) or {}

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

            def _coerce(v):
                # A CWL File/Directory value is a {"path": ...} object.
                if isinstance(v, dict) and "path" in v:
                    return v["path"]
                return str(v)

            raw_val = settings_values.get(inp_name)
            if _list_inner_type(data_type) is not None:
                # List input: preserve the list, coercing each element.
                val = [_coerce(v) for v in (raw_val or [])]
            elif raw_val is not None:
                val = _coerce(raw_val)
            else:
                val = ""
            default_loc.data[data_name] = Data(
                name=data_name, type=data_type, value=val
            )

        # 5b. Create a Step per leaf, with its output ports + processors.
        path_to_swirl: dict[str, Step] = {}
        for i, eff in enumerate(effective_steps):
            step = Step(name=f"s{i}", display_name=eff.path, command=eff.command)
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

                if step.processors is None:
                    step.processors = {}
                step.processors[port_name] = Processor(type=out_type, glob=glob_val)

                source_to_port[gkey] = port

        # 5c. Wire leaf-step inputs to the ports that produce their data.
        for eff in effective_steps:
            swirl_step = path_to_swirl[eff.path]
            for _param, gkey in eff.inputs:
                if gkey is not None and gkey in source_to_port:
                    workflow.add_input_port(swirl_step, source_to_port[gkey])

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
