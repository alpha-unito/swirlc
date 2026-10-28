from __future__ import annotations

import os
from abc import ABC
from collections.abc import MutableMapping, MutableSequence
from typing import Any

from swirlc.antlr.SWIRLParser import SWIRLParser
from swirlc.antlr.SWIRLVisitor import SWIRLVisitor
from swirlc.core import utils
from swirlc.core.entity import (
    Data,
    DistributedWorkflow,
    Location,
    Port,
    Processor,
    Step,
    Workflow,
)


class BaseCompiler:
    def __init__(self, outdir: str, tmpdir: str | None = None) -> None:
        self.outdir: str = outdir
        self.tmpdir: str | None = tmpdir
        if not os.path.exists(self.outdir):
            raise Exception(f"Output directory `{self.outdir}` does not exist")


    def begin_dataset(
        self,
        dataset: MutableSequence[tuple[str, Data]],
    ) -> None:
        """Start processing the dataset on current location."""
        pass

    def begin_paren(
        self,
    ) -> None:
        """Starts processing of a trace enclosed in brackets"""
        pass

    def end_paren(
        self,
    ) -> None:
        """After processing of a trace enclosed in brackets"""
        pass

    def begin_location(self, location: Location) -> None:
        """Start processing a new location configuration."""
        pass

    def begin_par(self) -> None:
        """Before processing the left operand of a par operator."""
        pass

    def begin_seq(self) -> None:
        """Before processing the left operand of a seq operator."""
        pass

    def begin_workflow(self, workflow: Workflow) -> None:
        """Start the compilation process."""
        pass

    def end_dataset(self) -> None:
        """Finish processing the dataset on current location."""
        pass

    def end_location(self) -> None:
        """Finish processing a new location configuration."""
        pass

    def end_par(self) -> None:
        """After processing both operands of a par operator."""
        pass

    def end_seq(self) -> None:
        """After processing both operands of a seq operator."""
        pass

    def end_workflow(self) -> None:
        """Finish the compilation process."""
        pass

    def exec(
        self,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ) -> None:
        """Process the `exec` predicate."""
        pass

    def par(self) -> None:
        """After processing the first operand, but before processing the right operand of a par operator."""
        pass

    def recv(self, port: str, data: str, data_type: str, src: str, dst: str) -> Any:
        """Process the `recv` predicate."""
        pass

    def begin_choice(self, guard: str = "True", eof_branch: int | None = None) -> None:
        """Before processing the left operand of a choice operator."""
        pass

    def choice(self) -> None:
        """After processing the first operand, but before processing the right operand of a choice operator."""
        pass

    def end_choice(self) -> None:
        """After processing both operands of a choice operator."""
        pass

    def begin_repl(self) -> None:
        """Before processing the body of a replication operator."""
        pass

    def end_repl(self) -> None:
        """After processing the body of a replication operator."""
        pass

    def zero(self) -> None:
        """Process the zero (0) null-process trace."""
        pass

    def move(self, data: str, port: str, data_type: str, src: str, dst: str) -> Any:
        """Process the `move` predicate."""
        pass

    def send(self, data: str, port: str, data_type: str, src: str, dst: str) -> Any:
        """Process the `send` predicate."""
        pass

    def seq(self) -> Any:
        """After processing the first operand, but before processing the right operand of a seq operator."""
        pass



class CompileVisitor(SWIRLVisitor, ABC):

    def __init__(
        self,
        compiler: BaseCompiler,
        metadata: MutableMapping[str, Any],
        hints: list[Any] | None = None,
    ) -> None:
        super().__init__()
        self.compiler: BaseCompiler = compiler
        self.compiler.metadata = metadata
        self.metadata: MutableMapping[str, Any] = metadata
        self.hints = hints or []
        self.workflow: DistributedWorkflow = DistributedWorkflow()
        for name, settings in self.metadata["locations"].items():
            deployment = settings.get("deployment", {})
            connection_type = deployment.get(
                "type",
                deployment.get("connectionType", settings.get("connectionType", None)),
            )
            self.workflow.add_location(
                Location(
                    name,
                    name,
                    {},
                    hostname=deployment.get("hostname", settings.get("hostname", None)),
                    port=deployment.get("port", settings.get("port", None)),
                    username=deployment.get("username", settings.get("username", None)),
                    ssh_key=deployment.get("sshKey", settings.get("sshKey", None)),
                    check_host_key=deployment.get(
                        "checkHostKey", settings.get("checkHostKey", None)
                    ),
                    connection_type=connection_type,
                    workdir=deployment.get(
                        "workdir",
                        deployment.get(
                            "tmpdir",
                            settings.get(
                                "workdir",
                                settings.get(
                                    "tmpdir",
                                    self.metadata.get(
                                        "tmpdir", self.metadata.get("workdir", None)
                                    ),
                                ),
                            ),
                        ),
                    ),
                    outdir=settings.get("outdir", None),
                    environment=deployment.get("environment", settings.get("environment", {})),

                    slurm=deployment.get("slurm", settings.get("slurm", None)),
                )
            )

    def visitDataSet(self, ctx: SWIRLParser.DataSetContext):
        dataset = []
        for d in ctx.dataPair():
            port_name, term = utils.get_pair(d, self.metadata["dependencies"])
            data_name = term.payload.name
            dataset.append(
                (
                    port_name,
                    Data(
                        data_name,
                        self.metadata["dependencies"][data_name]["type"],
                        self.metadata["dependencies"][data_name]["value"],
                        term.identity,
                    ),
                )
            )
            port = self.workflow.ports.setdefault(
                port_name, Port(port_name, port_name, set())
            )
            port.data.add(data_name)
        self.compiler.begin_dataset(dataset)
        val = self.visitChildren(ctx)
        self.compiler.end_dataset()
        return val

    def visitLocation(self, ctx: SWIRLParser.LocationContext):
        name = utils.get_name(ctx.name())
        location = self.workflow.locations[name]
        self.compiler.begin_location(location)
        val = self.visitChildren(ctx)
        self.compiler.end_location()
        return val

    def _descriptor_type(self, descriptor):
        if "dataName" in descriptor:
            return self.metadata["dependencies"][descriptor["dataName"]]["type"]
        for kind in ("binding", "collection"):
            if kind in descriptor:
                return descriptor[kind]["type"]
        raise ValueError(f"Output descriptor has no payload type: {descriptor}")

    def _register_step(self, ctx: SWIRLParser.ExecContext):
        flow = utils.get_flow(ctx, self.metadata["dependencies"])
        inputs, outputs = flow
        mapping = utils.get_location_set(ctx.mapping().locationSet())
        name = utils.get_name(ctx.step())
        if name not in self.metadata["steps"]:
            raise ValueError(f"Exec {name} has no metadata descriptor")
        unknown_locations = mapping - set(self.workflow.locations)
        if unknown_locations:
            raise ValueError(f"Step {name}: unknown mapped locations {sorted(unknown_locations)}")
        step_metadata = self.metadata["steps"][name]
        declared_inputs = step_metadata.get("inputs")
        if declared_inputs is not None and set(declared_inputs) != {p for p, _ in inputs}:
            raise ValueError(f"Step {name}: exec inputs do not match metadata inputs")
        if declared_inputs is not None:
            for port, term in inputs:
                actual_type = self._get_data_type(term, port)
                expected_type = declared_inputs[port]["type"]
                if actual_type != "dynamic" and actual_type != expected_type:
                    raise ValueError(f"Step {name}: input {port} type {actual_type} does not match declared type {expected_type}")
        def binding_ports(spec):
            if "port" in spec:
                yield spec["port"]
            elif "object" in spec:
                for child in spec["object"].values():
                    yield from binding_ports(child)
            elif "items" in spec:
                for child in spec["items"]:
                    yield from binding_ports(child)

        def referenced_ports(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "bindings":
                        for spec in item.values():
                            yield from binding_ports(spec)
                    elif key not in ("value", "schema", "inputSchemas", "default"):
                        yield from referenced_ports(item)
            elif isinstance(value, list):
                for item in value:
                    yield from referenced_ports(item)
        if any(port not in {p for p, _ in inputs} for port in referenced_ports(step_metadata)):
            raise ValueError(f"Step {name}: expression binding references a port outside exec inputs")
        if set(step_metadata.get("outputs", {})) != {p for p, _ in outputs}:
            raise ValueError(f"Step {name}: exec outputs do not match metadata outputs")
        def same_identity(left, right):
            return "".join(str(left).split()) == "".join(str(right).split())

        for port_name, term in outputs:
            descriptor = step_metadata["outputs"][port_name]
            if "collection" in descriptor:
                collection = descriptor["collection"]
                if (term.kind != "collection" or term.items[0].name != collection["name"]
                        or not same_identity(term.items[1], collection["scope"])):
                    raise ValueError(f"Step {name}: output collection {port_name} does not match metadata")
            elif "binding" in descriptor:
                binding = descriptor["binding"]
                if (term.payload.kind != "variable" or term.payload.name != binding["payload"]
                        or not same_identity(term.identity, binding["id"])):
                    raise ValueError(f"Step {name}: output binding {port_name} does not match metadata")
            elif (term.payload.kind != "literal" or term.payload.name != descriptor["dataName"]
                    or not same_identity(term.identity, descriptor.get("id", "root"))):
                raise ValueError(f"Step {name}: output dependency {port_name} does not match metadata")
        if step_metadata.get("type") in ("scatter_pair", "scatter_pairer", "scatter_open"):
            raise ValueError("Legacy pair/open scatter is unsupported; use independent scoped streams")
        if name not in self.workflow.steps:

            data_port = {d: p for p, d in list(inputs) + list(outputs)}
            outdata_patterns = step_metadata.get("outputs", {})
            expression = step_metadata.get("expression", {})
            if expression and "language" not in expression:
                raise ValueError(f"Step {name}: legacy expression metadata requires retranslating to a language/source descriptor")
            step_type = step_metadata.get("type")

            step = Step(
                name,
                step_metadata["displayName"],
                command=step_metadata.get("command"),
                processors={
                    port_name: Processor(
                        self._descriptor_type(value),
                        value.get("glob", None),
                        value.get("readContents", False),
                        value.get("evaluate"),
                    )
                    for port_name, value in outdata_patterns.items()
                },
                expression=expression or None,
                step_type=step_type,
                scatter_method=step_metadata.get("scatterMethod"),
                scatter=step_metadata.get("scatter") or step_metadata.get("scatterPorts"),
            )
            step.metadata = step_metadata
            self.workflow.add_step(step)
            for port_name, _ in inputs:
                port = self.workflow.ports.get(
                    port_name,
                    Port(
                        port_name,
                        port_name,
                        set(),
                    ),
                )
                self.workflow.add_input_port(step, port)
            for port_name, _ in outputs:
                port = self.workflow.ports.get(
                    port_name,
                    Port(
                        port_name,
                        port_name,
                        set(),
                    ),
                )
                self.workflow.add_output_port(step, port)
            for term, port_name in data_port.items():
                if term.kind != "collection" and term.payload.kind == "literal":
                    payload = term.payload.name
                    if payload not in self.metadata["dependencies"]:
                        raise ValueError(f"Step {name}: unknown payload dependency {payload}")
                    self.workflow.ports[port_name].data.add(payload)

            step_args = step_metadata.get("arguments") or []
            if any(
                "valueFrom" in arg
                and arg["valueFrom"] not in (port_name for port_name, _ in inputs)
                for arg in step_args
            ):
                erroneous_port = next(
                    arg["valueFrom"]
                    for arg in step_args
                    if "valueFrom" in arg
                    and arg["valueFrom"] not in (port_name for port_name, _ in inputs)
                )
                raise Exception(
                    f"Step {step.name} has invalid port name {erroneous_port} in the `valueFrom` field in the metadata file"
                )
            step.arguments = [
                (
                    arg["value"]
                    if "value" in arg
                    else (arg if "expression" in arg else self.workflow.ports[arg["valueFrom"]])
                )
                for arg in step_args
            ]
            step.expression_outputs = {
                output_name: self.workflow.ports[port_name]
                for output_name, port_name in expression.get("outputs", {}).items()
            }
        for loc in mapping:
            self.workflow.map(self.workflow.steps[name], self.workflow.locations[loc])

    def visitExec(self, ctx: SWIRLParser.ExecContext):
        flow = utils.get_flow(ctx, self.metadata["dependencies"])
        mapping = utils.get_location_set(ctx.mapping().locationSet())
        name = utils.get_name(ctx.step())
        if name not in self.workflow.steps:
            self._register_step(ctx)
        return self.compiler.exec(self.workflow.steps[name], flow, mapping)

    def _extract_data_and_port(self, text_a: str, text_b: str) -> tuple[str, str]:
        deps = self.metadata.get("dependencies", {})
        if text_a in deps or text_a in ("eof", "0"):
            return text_a, text_b
        if text_b in deps or text_b in ("eof", "0"):
            return text_b, text_a
        return text_a, text_b

    def _endpoints(self, ctx):
        src = utils.get_name(ctx.src())
        destination = ctx.dst().locationSet()
        names = [utils.get_name(name) for name in destination.name()]
        if not names:
            names = [destination.getText()]
        unknown = {src, *names} - set(self.workflow.locations)
        if unknown:
            raise ValueError(f"Unknown communication locations {sorted(unknown)}")
        return src, names[0] if len(names) == 1 else names

    def _action_data(self, ctx):
        term = utils.get_term(ctx.data())
        port = utils.get_name(ctx.port())
        # Legacy bare receives allowed port-to-data spelling; envelopes never do.
        if term.kind == "literal" and port in self.metadata["dependencies"] and term.name not in self.metadata["dependencies"]:
            term, port = utils.Term("literal", port), term.name
        if term.kind == "indexed":
            raise ValueError("Legacy indexed scatter is unsupported; use scoped identity envelopes")
        return utils.normalize_envelope(term), port

    def _get_data_type(self, data: utils.Term, port: str | None = None) -> str:
        payload = data.payload
        if payload.kind == "literal" and payload.name in ("begin", "eof", "0"):
            return "control"
        dep = self.metadata["dependencies"].get(payload.name)
        if dep:
            return dep["type"]
        if port is not None:
            for descriptor in self.metadata["steps"].values():
                output = descriptor.get("outputs", {}).get(port)
                if output:
                    return self._descriptor_type(output)
                collection = descriptor.get("collections", {}).get(port)
                if collection:
                    return collection["type"]
        if port is not None:
            for step in self.metadata["steps"].values():
                descriptor = step.get("inputs", {}).get(port)
                if descriptor:
                    return descriptor["type"]
        types = set()
        for step in self.metadata["steps"].values():
            for descriptor in step.get("outputs", {}).values():
                binding = descriptor.get("binding", {})
                if binding.get("payload") == payload.name:
                    types.add(binding["type"])
        if len(types) == 1:
            return types.pop()
        # Input stream bindings take their types from dispatch collections.
        if payload.kind in ("variable", "tuple"):
            return "dynamic"
        raise ValueError(f"Unknown payload {payload}")

    def visitRecv(self, ctx: SWIRLParser.RecvContext):
        data, port = self._action_data(ctx)
        src, dst = self._endpoints(ctx)

        data_type = self._get_data_type(data, port)
        return self.compiler.recv(
            port=port, data=data, data_type=data_type, src=src, dst=dst
        )

    def visitSend(self, ctx: SWIRLParser.SendContext):
        data, port = self._action_data(ctx)
        src, dst = self._endpoints(ctx)
        data_type = self._get_data_type(data, port)
        return self.compiler.send(
            data, port, data_type, src, dst
        )

    def visitMove(self, ctx: SWIRLParser.MoveContext):
        data, port = self._action_data(ctx)
        src, dst = self._endpoints(ctx)
        data_type = self._get_data_type(data, port)
        return self.compiler.move(
            data, port, data_type, src, dst
        )

    def visitTraceOp(self, ctx: SWIRLParser.TraceOpContext):
        if ctx.op.type == SWIRLParser.PAR:
            self.compiler.begin_par()
            self.visit(ctx.trace(0))
            self.compiler.par()
            self.visit(ctx.trace(1))
            self.compiler.end_par()
        elif ctx.op.type == SWIRLParser.SEQ:
            self.compiler.begin_seq()
            self.visit(ctx.trace(0))
            self.compiler.seq()
            self.visit(ctx.trace(1))
            self.compiler.end_seq()
        elif ctx.op.type == SWIRLParser.CHOICE:
            guard = None
            if ctx.guard():
                name = utils.get_name(ctx.guard().port())
                if ctx.guard().data():
                    guard = {"port": name, "scope": utils.get_term(ctx.guard().data())}
                else:
                    if name not in self.metadata.get("conditions", {}):
                        raise ValueError(f"Unknown condition {name}")
                    guard = {"id": name}
                    descriptor = self.metadata["conditions"][name]
                    if descriptor["type"] == "has_data":
                        from swirlc.core.parsing import parse_term
                        guard["scope"] = parse_term(descriptor["scope"])
            self.compiler.begin_choice(
                guard
            )
            self.visit(ctx.trace(0))
            self.compiler.choice()
            self.visit(ctx.trace(1))
            self.compiler.end_choice()
        else:
            raise Exception(f"Unsupported operator {ctx.op.text}")

    def visitTraceRepl(self, ctx: SWIRLParser.TraceReplContext):
        self.compiler.begin_repl()
        val = self.visit(ctx.trace())
        self.compiler.end_repl()
        return val


    def visitTraceZero(self, ctx: SWIRLParser.TraceZeroContext):
        return self.compiler.zero()

    def visitTraceParen(self, ctx: SWIRLParser.TraceParenContext):
        self.compiler.begin_paren()
        val = self.visit(ctx.trace())
        self.compiler.end_paren()
        return val

    def _pre_scan_execs(self, ctx):
        if isinstance(ctx, SWIRLParser.ExecContext):
            name = utils.get_name(ctx.step())
            if self.metadata.get("version") == "v1.1" and name in self.workflow.steps:
                raise ValueError(f"Step {name}: each emitted exec requires its own metadata descriptor")
            self._register_step(ctx)
        elif hasattr(ctx, "getChildren"):
            for child in ctx.getChildren():
                self._pre_scan_execs(child)

    def visitWorkflow(self, ctx: SWIRLParser.WorkflowContext):
        from swirlc.core.parsing import validate_bindings

        validate_bindings(ctx, self.metadata.get("conditions", {}))
        self._pre_scan_execs(ctx)
        self.compiler.begin_workflow(self.workflow)
        val = self.visitChildren(ctx)
        self.compiler.end_workflow()
        return val
