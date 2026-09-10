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

    def begin_repl(self, param: str | None = None, domain: str | None = None) -> None:
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
    ) -> None:
        super().__init__()
        self.compiler: BaseCompiler = compiler
        self.metadata: MutableMapping[str, Any] = metadata
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

                    slurm=deployment.get("slurm", settings.get("slurm", None)),
                )
            )

    def visitDataSet(self, ctx: SWIRLParser.DataSetContext):
        dataset = []
        for d in ctx.dataPair():
            port_name, data_name = utils.get_pair(d)
            dataset.append(
                (
                    port_name,
                    Data(
                        data_name,
                        self.metadata["dependencies"][data_name]["type"],
                        self.metadata["dependencies"][data_name]["value"],
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

    def _register_step(self, ctx: SWIRLParser.ExecContext):
        flow = utils.get_flow(ctx)
        inputs, outputs = flow
        mapping = {utils.get_name(el) for el in ctx.mapping().name()}
        name = utils.get_name(ctx.step())
        if name not in self.workflow.steps:
            step_metadata = self.metadata["steps"][name]

            data_port = {d: p for p, d in list(inputs) + list(outputs)}
            outdata_patterns = step_metadata.get("outputs", {})
            expression = step_metadata.get("expression", {})
            expression_source = expression.get("source")
            step_type = step_metadata.get("type")
            if not step_type:
                d_name = step_metadata.get("displayName", "").lower().replace(" ", "_")
                cmd = str(step_metadata.get("command", "")).lower()
                if "pair" in d_name or "pair" in cmd:
                    step_type = "scatter_pairer"
                elif "unpack" in d_name or "open" in d_name or "scatter_open" in d_name:
                    step_type = "scatter_open"
                elif "gather" in d_name or "scatter_gather" in d_name:
                    step_type = "scatter_gather"

            step = Step(
                name,
                step_metadata["displayName"],
                command=step_metadata.get("command"),
                processors={
                    port_name: Processor(
                        self.metadata["dependencies"][value["dataName"]]["type"],
                        value.get("glob", None),
                    )
                    for port_name, value in outdata_patterns.items()
                },
                expression=expression_source,
                step_type=step_type,
                scatter_method=step_metadata.get("scatterMethod"),
                scatter=step_metadata.get("scatter") or step_metadata.get("scatterPorts"),
            )
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
            for data_name, port_name in data_port.items():
                self.workflow.ports[port_name].data.add(data_name)

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
                    else self.workflow.ports[arg["valueFrom"]]
                )
                for arg in step_args
            ]
            expression_inputs = expression.get("inputs", {})
            step.expression_inputs = {
                input_name: self.workflow.ports[value["port"]]
                for input_name, value in expression_inputs.items()
            }
            step.expression_input_types = {
                input_name: value["type"]
                for input_name, value in expression_inputs.items()
            }
            step.expression_outputs = {
                output_name: self.workflow.ports[port_name]
                for output_name, port_name in expression.get("outputs", {}).items()
            }
        for loc in mapping:
            self.workflow.map(self.workflow.steps[name], self.workflow.locations[loc])

    def visitExec(self, ctx: SWIRLParser.ExecContext):
        flow = utils.get_flow(ctx)
        mapping = {utils.get_name(el) for el in ctx.mapping().name()}
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

    def _get_data_type(self, data: str) -> str:
        dep_entry = self.metadata["dependencies"].get(data)
        if not dep_entry and "[" in data:
            dep_entry = self.metadata["dependencies"].get(data.split("[")[0])
        return dep_entry.get("type", "file") if dep_entry else "file"

    def visitRecv(self, ctx: SWIRLParser.RecvContext):
        p_text = utils.get_name(ctx.port())
        d_text = utils.get_name(ctx.data())
        data, port = self._extract_data_and_port(d_text, p_text)
        src = utils.get_name(ctx.src())
        dst = utils.get_name(ctx.dst())

        data_type = self._get_data_type(data)
        return self.compiler.recv(
            port=port, data=data, data_type=data_type, src=src, dst=dst
        )

    def visitSend(self, ctx: SWIRLParser.SendContext):
        p_text = utils.get_name(ctx.port())
        d_text = utils.get_name(ctx.data())
        data, port = self._extract_data_and_port(d_text, p_text)
        src = utils.get_name(ctx.src())
        dst = utils.get_name(ctx.dst())
        data_type = self._get_data_type(data)
        return self.compiler.send(
            data, port, data_type, src, dst
        )

    def visitMove(self, ctx: SWIRLParser.MoveContext):
        p_text = utils.get_name(ctx.port())
        d_text = utils.get_name(ctx.data())
        data, port = self._extract_data_and_port(d_text, p_text)
        src = utils.get_name(ctx.src())
        dst = utils.get_name(ctx.dst())
        data_type = self._get_data_type(data)
        return self.compiler.move(
            data, port, data_type, src, dst
        )

    def _get_first_leaf_pred(self, ctx: SWIRLParser.TraceContext) -> SWIRLParser.PredContext | None:
        while ctx is not None:
            if isinstance(ctx, SWIRLParser.TraceParenContext):
                ctx = ctx.trace()
            elif isinstance(ctx, SWIRLParser.TraceReplContext):
                ctx = ctx.trace()
            elif isinstance(ctx, SWIRLParser.TraceOpContext):
                ctx = ctx.trace(0)
            elif isinstance(ctx, SWIRLParser.TracePredContext):
                return ctx.pred()
            else:
                break
        return None

    def _has_eof_op(self, ctx: SWIRLParser.TraceContext) -> bool:
        if ctx is None:
            return False
        if isinstance(ctx, (SWIRLParser.TraceParenContext, SWIRLParser.TraceReplContext)):
            return self._has_eof_op(ctx.trace())
        elif isinstance(ctx, SWIRLParser.TraceOpContext):
            return self._has_eof_op(ctx.trace(0)) or self._has_eof_op(ctx.trace(1))
        elif isinstance(ctx, SWIRLParser.TracePredContext):
            pred = ctx.pred()
            for op in (pred.send(), pred.recv(), pred.move()):
                if op is not None:
                    d_text = utils.get_name(op.data())
                    p_text = utils.get_name(op.port())
                    data, port = self._extract_data_and_port(d_text, p_text)
                    if data == "eof" or port == "eof":
                        return True
        return False

    def _extract_choice_info(
        self, trace0: SWIRLParser.TraceContext, trace1: SWIRLParser.TraceContext
    ) -> tuple[str, int | None]:
        pred = self._get_first_leaf_pred(trace0)
        guard = "True"
        if pred is not None:
            if pred.move() is not None:
                d_text = utils.get_name(pred.move().data())
                p_text = utils.get_name(pred.move().port())
                data, port = self._extract_data_and_port(d_text, p_text)
                guard = f"not _has_data({port!r})" if data == "eof" else f"_has_data({port!r})"
            elif pred.send() is not None:
                d_text = utils.get_name(pred.send().data())
                p_text = utils.get_name(pred.send().port())
                data, port = self._extract_data_and_port(d_text, p_text)
                guard = f"not _has_data({port!r})" if data == "eof" else f"_has_data({port!r})"
            elif pred.recv() is not None:
                d_text = utils.get_name(pred.recv().data())
                p_text = utils.get_name(pred.recv().port())
                data, port = self._extract_data_and_port(d_text, p_text)
                src = utils.get_name(pred.recv().src())
                guard = f"_peek_is_eof({src!r}, {port!r})" if data == "eof" else f"not _peek_is_eof({src!r}, {port!r})"

        eof_branch = None
        if self._has_eof_op(trace1):
            eof_branch = 1
        elif self._has_eof_op(trace0):
            eof_branch = 0

        return guard, eof_branch

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
            guard, eof_branch = self._extract_choice_info(ctx.trace(0), ctx.trace(1))
            self.compiler.begin_choice(guard=guard, eof_branch=eof_branch)
            self.visit(ctx.trace(0))
            self.compiler.choice()
            self.visit(ctx.trace(1))
            self.compiler.end_choice()
        else:
            raise Exception(f"Unsupported operator {ctx.op.text}")

    def visitTraceRepl(self, ctx: SWIRLParser.TraceReplContext):
        param = None
        domain = None
        if ctx.ID(0) is not None:
            param = ctx.ID(0).getText()
        if ctx.ID(1) is not None:
            domain = ctx.ID(1).getText()
        self.compiler.begin_repl(param=param, domain=domain)
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
            self._register_step(ctx)
        elif hasattr(ctx, "getChildren"):
            for child in ctx.getChildren():
                self._pre_scan_execs(child)

    def visitWorkflow(self, ctx: SWIRLParser.WorkflowContext):
        self._pre_scan_execs(ctx)
        self.compiler.begin_workflow(self.workflow)
        val = self.visitChildren(ctx)
        self.compiler.end_workflow()
        return val

