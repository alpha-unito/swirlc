from __future__ import annotations

from collections.abc import MutableMapping, MutableSequence
from pathlib import PurePath
from typing import Any

from swirlc.core.deployment import Deployment, make_deployment
from swirlc.core.utils import flatten_list


class Data:
    __slots__ = ("name", "type", "value")

    def __init__(self, name: str, type: str, value: Any):
        self.name = name
        self.type = type
        self.value = value


class Location:
    __slots__ = (
        "name",
        "display_name",
        "data",
        "connection_type",
        "workdir",
        "outdir",
        "hostname",
        "port",
        "slurm",
        "username",
        "ssh_key",
        "check_host_key",
        "deployment",
    )

    def __init__(
        self,
        name: str,
        display_name: str,
        data: MutableMapping[str, Any],
        connection_type: str | None = None,
        hostname: str | None = None,
        port: str | None = None,
        workdir: str | None = None,
        outdir: str | None = None,
        slurm: MutableMapping[str, Any] | None = None,
        username: str | None = None,
        ssh_key: str | None = None,
        check_host_key: bool | None = None,
        deployment: Deployment | None = None,
    ):
        self.data: MutableMapping[str, Any] = data
        self.display_name: str = display_name
        self.name: str = name
        self.deployment = deployment or make_deployment(
            connection_type=connection_type,
            hostname=hostname,
            port=port,
            workdir=workdir,
            username=username,
            ssh_key=ssh_key,
            check_host_key=check_host_key,
            slurm=slurm,
        )
        self.connection_type: str | None = self.deployment.connection_type
        self.hostname: str | None = self.deployment.hostname
        self.port: str | None = self.deployment.port
        self.outdir: str | None = str(PurePath(outdir)) if outdir else outdir
        self.workdir: str | None = self.deployment.workdir
        self.slurm: MutableMapping[str, Any] | None = self.deployment.slurm
        self.username: str | None = self.deployment.username
        self.ssh_key: str | None = self.deployment.ssh_key
        self.check_host_key: bool | None = self.deployment.check_host_key

    def get_command(self, cmd: str) -> str:
        return self.deployment.get_command(cmd, self.name)

    def get_prepare_command(self) -> str:
        return self.deployment.get_prepare_command()

    def get_copy_command(self, src, dst):
        return self.deployment.get_copy_command(src, dst)

    def get_fetch_command(self, src, dst):
        return self.deployment.get_fetch_command(src, dst)

    def get_setup_command(self, cmd: str) -> str:
        return self.deployment.get_setup_command(cmd, self.name)

    def get_bind_host(self) -> str:
        return self.deployment.get_bind_host()

    def get_advertise_command(self) -> str:
        return self.deployment.get_advertise_command()


class Port:
    __slots__ = ("name", "display_name", "data")

    def __init__(self, name: str, display_name: str, data: set[str]):
        self.name: str = name
        self.display_name: str = display_name
        self.data: set[str] = data


class Processor:
    __slots__ = ("type", "glob")

    def __init__(self, type: str, glob: str | None):
        self.type: str = type
        self.glob: str | None = glob


class Step:
    __slots__ = (
        "name",
        "display_name",
        "command",
        "arguments",
        "processors",
        "expression",
        "expression_inputs",
        "expression_input_types",
        "expression_outputs",
    )

    def __init__(
        self,
        name: str,
        display_name: str,
        command: str | None = None,
        arguments: MutableSequence[str | Port] | None = None,
        processors: MutableMapping[str, Processor] | None = None,
        expression: str | None = None,
        expression_inputs: MutableMapping[str, Port] | None = None,
        expression_input_types: MutableMapping[str, str] | None = None,
        expression_outputs: MutableMapping[str, Port] | None = None,
    ):
        self.name: str = name
        self.display_name: str = display_name
        self.command: str | None = command
        self.arguments: MutableSequence[str | Port] | None = arguments
        self.processors: MutableMapping[str, Processor] | None = processors
        self.expression = expression
        self.expression_inputs = expression_inputs
        self.expression_input_types = expression_input_types
        self.expression_outputs = expression_outputs


class Workflow:
    __slots__ = ("steps", "ports", "dependencies", "__location")

    def __init__(self):
        self.steps: MutableMapping[str, Step] = {}
        self.ports: MutableMapping[str, Port] = {}
        self.dependencies: set[tuple[str, str]] = set()
        self.__location: Location = Location(name="l", display_name="local", data={})

    def add_input_port(self, step: Step, port: Port):
        if port.name not in self.ports:
            self.ports[port.name] = port
        self.dependencies.add((port.name, step.name))

    def add_output_port(self, step: Step, port: Port):
        if port.name not in self.ports:
            self.ports[port.name] = port
        self.dependencies.add((step.name, port.name))

    def add_step(self, step: Step) -> None:
        self.steps[step.name] = step

    def get_input_data(self, step: Step) -> MutableSequence[str]:
        return sorted(
            flatten_list(
                [f"({p.name},{d})" for p in self.get_input_ports(step) for d in p.data]
            )
        )

    def get_input_locations(self, port: Port) -> MutableSequence[Location]:
        return [self.__location]

    def get_input_ports(self, step: Step) -> MutableSequence[Port]:
        return sorted(
            [self.ports[d[0]] for d in self.dependencies if d[1] == step.name],
            key=lambda port: port.name,
        )

    def get_input_steps(self, port: Port) -> MutableSequence[Step]:
        return sorted(
            [self.steps[d[0]] for d in self.dependencies if d[1] == port.name],
            key=lambda step: step.name,
        )

    def get_locations(self) -> MutableSequence[Location]:
        return [self.__location]

    def get_location_steps(self, location: Location) -> MutableSequence[Step]:
        return sorted(self.steps.values(), key=lambda step: step.name)

    def get_output_data(self, step: Step) -> MutableSequence[str]:
        return sorted(
            flatten_list(
                [f"({p.name},{d})" for p in self.get_output_ports(step) for d in p.data]
            )
        )

    def get_output_locations(self, port: Port) -> MutableSequence[Location]:
        return [self.__location]

    def get_output_ports(self, step: Step) -> MutableSequence[Port]:
        return sorted(
            [self.ports[d[1]] for d in self.dependencies if d[0] == step.name],
            key=lambda port: port.name,
        )

    def get_output_steps(self, port: Port) -> MutableSequence[Step]:
        return sorted(
            [self.steps[d[1]] for d in self.dependencies if d[0] == port.name],
            key=lambda step: step.name,
        )

    def get_step_locations(self, step: Step) -> MutableSequence[Location]:
        return [self.__location]


class DistributedWorkflow(Workflow):
    __slots__ = ("locations", "mapping")

    def __init__(self):
        super().__init__()
        self.locations: MutableMapping[str, Location] = {}
        self.mapping: set[tuple[str, str]] = set()

    def add_location(self, location: Location) -> None:
        self.locations[location.name] = location

    def map(self, step: Step, location: Location) -> None:
        self.mapping.add((step.name, location.name))

    def get_input_locations(self, port: Port) -> MutableSequence[Location]:
        return sorted(
            flatten_list(
                [list(self.get_step_locations(s)) for s in self.get_input_steps(port)]
            ),
            key=lambda loc: loc.name,
        )

    def get_locations(self) -> MutableSequence[Location]:
        return sorted(self.locations.values(), key=lambda loc: loc.name)

    def get_location_steps(self, location: Location) -> MutableSequence[Step]:
        return sorted(
            [self.steps[m[0]] for m in self.mapping if m[1] == location.name],
            key=lambda step: step.name,
        )

    def get_output_locations(self, port: Port) -> MutableSequence[Location]:
        return sorted(
            flatten_list(
                [list(self.get_step_locations(s)) for s in self.get_output_steps(port)]
            ),
            key=lambda loc: loc.name,
        )

    def get_step_locations(self, step: Step) -> MutableSequence[Location]:
        return sorted(
            [self.locations[m[1]] for m in self.mapping if m[0] == step.name],
            key=lambda loc: loc.name,
        )
