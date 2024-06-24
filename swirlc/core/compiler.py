from __future__ import annotations

from abc import ABC
from typing import Any, MutableMapping, MutableSequence

from swirlc.antlr.SWIRLParser import SWIRLParser
from swirlc.antlr.SWIRLVisitor import SWIRLVisitor
from swirlc.core import utils
from swirlc.core.entity import (
    Location,
    Workflow,
    DistributedWorkflow,
    Step,
    Port,
    Processor,
    Data,
)


class BaseCompiler:
    def begin_choice(self) -> None:
        """Before processing the left operand of a choice operator."""
        pass

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

    def choice(self) -> None:
        """After processing the first operand, but before processing the right operand of a choice operator."""
        pass

    def end_choice(self) -> None:
        """After processing both operands of a choice operator."""
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

    def recv(self, port: str, data_type: str, src: str, dst: str) -> Any:
        """Process the `recv` predicate."""
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
            self.workflow.add_location(
                Location(
                    name,
                    name,
                    {},
                    hostname=settings["hostname"],
                    port=settings["port"],
                    connection_type=settings.get("connectionType", None),
                    workdir=settings.get("workdir", None),
                    outdir=settings.get("outdir", None),
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

    def visitExec(self, ctx: SWIRLParser.ExecContext):
        flow = utils.get_flow(ctx)
        inputs, outputs = flow
        mapping = {utils.get_name(el) for el in ctx.mapping().name()}
        if (name := utils.get_name(ctx.step())) not in self.workflow.steps:
            step_metadata = self.metadata["steps"][name]

            data_port = {d: p for p, d in list(inputs) + list(outputs)}
            outdata_patterns = step_metadata.get("outputs", {})
            step = Step(
                name,
                step_metadata["displayName"],
                command=step_metadata["command"],
                processors={
                    port_name: Processor(
                        self.metadata["dependencies"][value["dataName"]]["type"],
                        value.get("glob", None),
                    )
                    for port_name, value in outdata_patterns.items()
                },
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

            if any(
                "valueFrom" in arg
                and arg["valueFrom"] not in (port_name for port_name, _ in inputs)
                for arg in step_metadata["arguments"]
            ):
                erroneous_port = next(
                    arg["valueFrom"]
                    for arg in step_metadata["arguments"]
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
                for arg in step_metadata["arguments"]
            ]
        for loc in mapping:
            self.workflow.map(self.workflow.steps[name], self.workflow.locations[loc])
        return self.compiler.exec(self.workflow.steps[name], flow, mapping)

    def visitRecv(self, ctx: SWIRLParser.RecvContext):
        port = utils.get_name(ctx.port())
        src = utils.get_name(ctx.src())
        dst = utils.get_name(ctx.dst())
        data_type = None
        port_instance = self.workflow.ports.get(port, None)
        if port_instance and port_instance.data:
            # search in the dataset
            data_name = next(iter(port_instance.data))
            if data_name in self.workflow.locations[src].data:
                data_type = self.workflow.locations[src].data[data_name].type
            else:
                for value in self.metadata["steps"].values():
                    if info := value["outputs"].get(port, None):
                        data_type = self.metadata["dependencies"][info["dataName"]][
                            "type"
                        ]
                        break
        else:
            # search in the output steps
            for value in self.metadata["steps"].values():
                if "outputs" in value and (info := value["outputs"].get(port, None)):
                    data_type = self.metadata["dependencies"][info["dataName"]]["type"]
                    break
        if data_type is None:
            raise ValueError(
                f"From port {port} did not find data source (nor dataset nor step outputs)"
            )
        return self.compiler.recv(port, data_type, src, dst)

    def visitSend(self, ctx: SWIRLParser.SendContext):
        data = utils.get_name(ctx.data())
        port = utils.get_name(ctx.port())
        src = utils.get_name(ctx.src())
        dst = utils.get_name(ctx.dst())
        return self.compiler.send(
            data, port, self.metadata["dependencies"][data]["type"], src, dst
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
            self.compiler.begin_choice()
            self.visit(ctx.trace(0))
            self.compiler.choice()
            self.visit(ctx.trace(1))
            self.compiler.end_choice()
        else:
            raise Exception(f"Unsupported operator {ctx.op.text}")

    def visitTraceParen(self, ctx: SWIRLParser.TraceParenContext):
        self.compiler.begin_paren()
        val = self.visit(ctx.trace())
        self.compiler.end_paren()
        return val

    def visitWorkflow(self, ctx: SWIRLParser.WorkflowContext):
        self.compiler.begin_workflow(self.workflow)
        val = self.visitChildren(ctx)
        self.compiler.end_workflow()
        return val
