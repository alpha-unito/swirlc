from __future__ import annotations

import sys
from abc import abstractmethod
from typing import TextIO

from ruamel.yaml import YAML

from swirlc.core.entity import Port, Workflow


def _add_location(location, locations):
    locations[location.name] = {}
    if location.outdir:
        locations[location.name]["outdir"] = location.outdir

    deployment = {}
    if location.connection_type:
        deployment["type"] = location.connection_type
    if location.hostname:
        deployment["hostname"] = location.hostname
    if location.port:
        deployment["port"] = location.port
    if location.workdir:
        deployment["workdir"] = location.workdir
    if location.username:
        deployment["username"] = location.username
    if location.ssh_key:
        deployment["sshKey"] = location.ssh_key
    if location.check_host_key is not None:
        deployment["checkHostKey"] = location.check_host_key
    if location.slurm:
        deployment["slurm"] = location.slurm
    if deployment:
        locations[location.name]["deployment"] = deployment


def _add_step(step, steps, workflow, dependencies):
    steps[step.name] = {
        "displayName": step.display_name,
    }
    if step.step_type:
        steps[step.name]["type"] = step.step_type
        if step.scatter_method:
            steps[step.name]["scatterMethod"] = step.scatter_method
    else:
        steps[step.name]["command"] = step.command
        steps[step.name]["arguments"] = [
            arg if isinstance(arg, dict) else {
                "valueFrom" if isinstance(arg, Port) else "value": (
                    arg.name if isinstance(arg, Port) else arg
                )
            }
            for arg in (step.arguments or [])
        ]
    if step.expression is not None:
        if not isinstance(step.expression, dict):
            raise ValueError("Expression steps require a generic language/source descriptor")
        steps[step.name]["expression"] = step.expression
    for field in ("inputs", "bindings", "stdout"):
        if field in step.metadata:
            steps[step.name][field] = step.metadata[field]
    if step.processors:
        steps[step.name]["outputs"] = {}
        for port_name, processor in step.processors.items():
            data_name = next(iter(workflow.ports[port_name].data))
            steps[step.name]["outputs"][port_name] = {"dataName": data_name, "id": "root"}
            dependencies[data_name] = {"type": processor.type}
            if processor.glob:
                steps[step.name]["outputs"][port_name]["glob"] = processor.glob
            if processor.read_contents:
                steps[step.name]["outputs"][port_name]["readContents"] = True
            if processor.evaluate is not None:
                steps[step.name]["outputs"][port_name]["evaluate"] = processor.evaluate


class AbstractTranslator:
    @abstractmethod
    def _translate(self) -> Workflow: ...

    def translate(
        self, workflow_output: TextIO = sys.stdout, metadata_output: TextIO = sys.stdout
    ):
        self.render(self._translate(), workflow_output, metadata_output)

    def render(
        self,
        workflow: Workflow,
        workflow_output: TextIO = sys.stdout,
        metadata_output: TextIO = sys.stdout,
    ):
        """Render a lowered workflow without selecting a translation path."""

        # Dictionaries to generate metadata file
        dependencies = {}
        locations = {}
        steps = {}
        version = "v1.0"
        nof_locations = len(workflow.get_locations())
        for i, location in enumerate(workflow.get_locations()):
            trace_recvs = set()
            datapair = []
            for data in sorted(location.data.keys()):
                for port in workflow.ports.values():
                    if data in port.data:
                        datapair.append(f"({port.name},({data}, root))")
                        break
            workflow_output.write(f"<{location.name}, {{{','.join(datapair)}}},\n\t")

            _add_location(location, locations)
            for data_name, data in location.data.items():
                dependencies[data_name] = {"type": data.type, "value": data.value}

            # Add send data from dataset to other locations
            copying_dataset = set()
            for data in location.data.values():
                for port in workflow.ports.values():
                    if data.name in port.data:
                        for send in (
                            f"send(({data.name}, root)->{port.name},{location.name},{out_loc.name})"
                            for out_loc in workflow.get_output_locations(port)
                            if out_loc.name != location.name
                        ):
                            copying_dataset.add(send)
            nof_steps = len(workflow.get_location_steps(location))
            parallel_dataset_send = (
                f"({' | '.join(sorted(copying_dataset))})" if copying_dataset else ""
            )
            if parallel_dataset_send and nof_steps:
                parallel_dataset_send += " | "
            workflow_output.write(parallel_dataset_send)
            for j, step in enumerate(workflow.get_location_steps(location)):
                recvs, sends = set(), set()
                _add_step(step, steps, workflow, dependencies)

                for port in workflow.get_input_ports(step):
                    data_name = next(iter(port.data))
                    # data from other steps
                    for recv in (
                        f"recv(({data_name}, root) -> {port.name},{in_loc.name},{location.name})"
                        for in_loc in workflow.get_input_locations(port)
                        if in_loc.name != location.name
                    ):
                        if recv not in trace_recvs:
                            recvs.add(recv)
                            trace_recvs.add(recv)
                    # data from dataset
                    for loc in workflow.get_locations():
                        if (
                            data_name in loc.data
                            and loc.name != location.name
                            and (
                                recv
                                := f"recv(({data_name}, root) -> {port.name},{loc.name},{location.name})"
                            )
                            not in trace_recvs
                        ):
                            recvs.add(recv)
                            trace_recvs.add(recv)
                input_data = sorted(
                    f"({port.name},({data}, root))"
                    for port in workflow.get_input_ports(step)
                    for data in port.data
                )
                output_data = sorted(
                    f"({port.name},({data}, root))"
                    for port in workflow.get_output_ports(step)
                    for data in port.data
                )
                exec = (
                    f"exec({step.name},"
                    f"{{{','.join(input_data)}}}->"
                    f"{{{','.join(output_data)}}},"
                    f"{{{','.join([loc.name for loc in workflow.get_step_locations(step)])}}})"
                )
                for port in workflow.get_output_ports(step):
                    for d in port.data:
                        for send in (
                            f"send(({d}, root)->{port.name},{location.name},{out_loc.name})"
                            for out_loc in workflow.get_output_locations(port)
                            if out_loc.name != location.name
                        ):
                            sends.add(send)
                step_sep = " | " if j < nof_steps - 1 else ""
                parallel_recvs = f"({' | '.join(recvs)})." if recvs else ""
                parallel_sends = f".({' | '.join(sends)})" if sends else ""
                workflow_output.write(
                    f"({parallel_recvs}{exec}{parallel_sends}){step_sep}"
                )
            location_sep = " |" if i < nof_locations - 1 else ""
            workflow_output.write(f">{location_sep}\n")
        YAML().dump(
            {
                "version": version,
                "steps": steps,
                "locations": locations,
                "dependencies": dependencies,
            },
            metadata_output,
        )
