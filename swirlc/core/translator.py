from __future__ import annotations

import sys
from abc import abstractmethod
from typing import TextIO

from ruamel.yaml import YAML

from swirlc.core.entity import Workflow, Port


def _add_location(location, locations):
    locations[location.name] = {}
    if location.hostname:
        locations[location.name]["hostname"] = location.hostname
    if location.port:
        locations[location.name]["port"] = location.port
    if location.connection_type:
        locations[location.name]["connectionType"] = location.connection_type
    if location.workdir:
        locations[location.name]["workdir"] = location.workdir
    if location.outdir:
        locations[location.name]["outdir"] = location.outdir


def _add_step(step, steps, workflow, dependencies):
    steps[step.name] = {
        "displayName": step.display_name,
        "command": step.command,
    }
    if step.arguments:
        steps[step.name]["arguments"] = [
            {
                "valueFrom" if isinstance(arg, Port) else "value": (
                    arg.name if isinstance(arg, Port) else arg
                )
            }
            for arg in step.arguments
        ]
    if step.processors:
        steps[step.name]["outputs"] = {}
        for port_name, processor in step.processors.items():
            data_name = next(iter(workflow.ports[port_name].data))
            steps[step.name]["outputs"][port_name] = {"dataName": data_name}
            dependencies[data_name] = {"type": processor.type}
            if processor.glob:
                steps[step.name]["outputs"][port_name]["glob"] = processor.glob


class AbstractTranslator:
    @abstractmethod
    def _translate(self) -> Workflow: ...

    def translate(
        self, workflow_output: TextIO = sys.stdout, metadata_output: TextIO = sys.stdout
    ):
        workflow = self._translate()

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
                        datapair.append(f"({port.name},{data})")
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
                            f"send({data.name}->{port.name},{location.name},{out_loc.name})"
                            for out_loc in workflow.get_output_locations(port)
                            if out_loc.name != location.name
                        ):
                            copying_dataset.add(send)
            parallel_dataset_send = (
                f"({' | '.join(copying_dataset)}) | " if copying_dataset else ""
            )
            workflow_output.write(f"{parallel_dataset_send}")
            nof_steps = len(workflow.get_location_steps(location))
            for j, step in enumerate(workflow.get_location_steps(location)):
                recvs, sends = set(), set()
                _add_step(step, steps, workflow, dependencies)

                for port in workflow.get_input_ports(step):
                    # data from other steps
                    for recv in (
                        f"recv({port.name},{in_loc.name},{location.name})"
                        for in_loc in workflow.get_input_locations(port)
                        if in_loc.name != location.name
                    ):
                        if recv not in trace_recvs:
                            recvs.add(recv)
                            trace_recvs.add(recv)
                    # data from dataset
                    data_name = next(iter(port.data))
                    for loc in workflow.get_locations():
                        if (
                            data_name in loc.data
                            and loc.name != location.name
                            and (
                                recv := f"recv({port.name},{loc.name},{location.name})"
                            )
                            not in trace_recvs
                        ):
                            recvs.add(recv)
                            trace_recvs.add(recv)
                exec = (
                    f"exec({step.name},"
                    f"{{{','.join(workflow.get_input_data(step))}}}->"
                    f"{{{','.join(workflow.get_output_data(step))}}},"
                    f"{{{','.join([loc.name for loc in workflow.get_step_locations(step)])}}})"
                )
                for port in workflow.get_output_ports(step):
                    for d in port.data:
                        for send in (
                            f"send({d}->{port.name},{location.name},{out_loc.name})"
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
