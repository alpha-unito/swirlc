from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import MutableMapping, MutableSequence, TextIO

from black import WriteBack

from swirlc.core.compiler import BaseCompiler
from swirlc.core.entity import Location, Step, Port, Workflow, DistributedWorkflow, Data
from swirlc.log_handler import logger
from swirlc.version import VERSION

bash_header = f"""#!/bin/sh

# This file was generated automatically using SWIRL v{VERSION},
# using command swirlc {' '.join(sys.argv[1:])}
"""

python_header = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file was generated automatically using SWIRL v{VERSION},
# using command swirlc {' '.join(sys.argv[1:])}
"""

imports = """from __future__ import annotations

import glob
import logging
import os
import socket
import subprocess
import time
import uuid

from io import BytesIO
from pathlib import Path
from threading import Condition, Event, Thread
from typing import Any, MutableMapping, MutableSequence
"""

global_vars = """

BUF_SIZE = 8192

available_port_data = {}
condition: Condition = Condition()
connections: MutableMapping[str, MutableMapping[str, socket]] = {}
ports: MutableMapping[str, Any] = {}
stopping: bool = False


logger = logging.getLogger("swirlc")
defaultStreamHandler = logging.StreamHandler()
formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d %(filename)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
defaultStreamHandler.setFormatter(formatter)
logger.addHandler(defaultStreamHandler)
logger.setLevel(logging.DEBUG)
logger.propagate = False
"""

accept_function = """def _accept(sock: socket):
    while not stopping:
        try:
            conn, _ = sock.accept()
            name, port = conn.recv(1024).decode("utf-8").split()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Accepted connection for port {port} from location {name}")
            with condition:
                connections.setdefault(name, {})[port] = conn
                conn.send("ack".encode("utf-8"))
                condition.notify_all()
        except socket.timeout:
            pass
    sock.close()
"""

exec_function = """def _exec(step_name: str, step_display_name: str, input_port_names: MutableSequence[str], output_port_name: str, data_type: str, glob_regex: str | None, cmd: str, args: MutableSequence[str], args_from: MutableSequence[tuple[str, str]], workdir: str):
    # Wait all the data
    for port_name in input_port_names:
        available_port_data[port_name].wait()
    # Prepare working directory
    workdir = os.path.join(workdir, f"exec_{step_name}_{uuid.uuid4()}")
    os.mkdir(workdir)
    for port_name in input_port_names:
        os.symlink(os.path.abspath(ports[port_name]), os.path.join(workdir, os.path.basename(ports[port_name])))
    # Populate the arguments
    arguments = []
    if (len_args := len(args)) > 0:
        args = iter(args)
    if (len_args_from := len(args_from)) > 0:
        args_from = iter(args_from)
        elem = next(args_from)
        next_pos, next_port = elem
    else:
        next_pos, next_port = -1, None
    for i in range(len_args + len_args_from):
        if i == next_pos:
            arguments.append(ports[next_port])
            if i < len_args_from - 1:
                next_pos, next_port = next(args_from)
            else:
                next_pos, next_port = -1, None
        else:
            arguments.append(next(args))
    cmd = " ".join((cmd, *arguments))
    if logger.isEnabledFor(logging.INFO):
        logger.info(f"Step {step_display_name}-{step_name} executes command '{cmd}'")
    result = subprocess.run(cmd, capture_output=True, shell=True, cwd=workdir)
    if result.returncode != 0:
        raise Exception(f"Step {step_display_name}-{step_name} failed with exit status {result.returncode}: {result.stderr.decode('utf-8')}")
    if output_port_name:
        if data_type == "stdout":
            ports[output_port_name] = result.stdout
            if logger.isEnabledFor(logging.INFO):
                logger.info(f"Step {step_display_name}-{step_name} result: '{result.stdout.decode().strip()}'")
        elif data_type in ("file", "directory"):
            res = [path for path in glob.glob(os.path.join(workdir, glob_regex))]
            if len(res) == 0:
                raise FileNotFoundError(f"Step {step_display_name}-{step_name} did not produce a file or directory which match the glob regex: {glob_regex}")
            elif len(res) == 1:
                ports[output_port_name] = os.path.join(workdir, res[0])
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f"Step {step_display_name}-{step_name} result file: '{ports[output_port_name]}'")
            else:
                raise Exception(f"Step {step_display_name}-{step_name} produced too many files or directories which match glob regex: {res}")
        else:
            raise Exception(f"Unsupported data type: {data_type}")
        available_port_data[output_port_name].set()
    else:
        if logger.isEnabledFor(logging.INFO):
            logger.info(f"Step {step_display_name}-{step_name} has not an output port. Result: '{result.stdout.decode().strip()}'")
"""

init_dataset_function = """def _init_dataset(port_name: str, data: str):
    ports[port_name] = data
    available_port_data[port_name] = Event()
    available_port_data[port_name].set()
"""

send_function = """def _send(port: str, data_type: str, src: str, dst: str):
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(locations[dst])
            break
        except socket.error:
            time.sleep(1)
    sock.send(f"{src} {port}".encode("utf-8"))
    sock.recv(BUF_SIZE)
    if data_type == "stout":
        sock.send(ports[port])
    elif data_type == "file":
        sock.send(os.path.basename(ports[port]).encode("utf-8"))
        sock.recv(BUF_SIZE)
        fd = open(ports[port], "rb")
        while True:
            buf = fd.read(BUF_SIZE)
            if not buf:
                break
            sock.sendall(buf)
        fd.close()
    elif data_type == "directory":
        raise NotImplementedError(f"Recv directories not implemented yet")
    else:
        raise Exception(f"Unsupported data type: {data_type}")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Sent data for port {port} to location {dst}")
    sock.close()
"""

recv_function = """def _recv(port: str, workdir: str, data_type: str, src: str) -> Any:
    buf = BytesIO()
    with condition:
        while connections.setdefault(src, {}).get(port) is None:
            logger.debug(f"Waiting connection for port {port} from location {src}")
            condition.wait()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Received connection for port {port} from location {src}")
    if data_type == "stdout":
        while True:
            if not (data := connections[src][port].recv(BUF_SIZE)):
                break
            buf.write(data)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Received data for port {port} from location {src}")
        buf.seek(0)
        ports[port] = buf.read().decode("utf-8")
        available_port_data.setdefault(port, Event()).set()
    elif data_type == "file":
        filename = connections[src][port].recv(1024).decode()
        connections[src][port].send("ack".encode("utf-8"))
        filepath = os.path.join(workdir, f"rcv_{port}_{uuid.uuid4()}", filename)
        os.mkdir(os.path.dirname(filepath))
        fd = open(filepath, "wb")
        while True:
            if not (data := connections[src][port].recv(BUF_SIZE)):
                break
            fd.write(data)
        fd.close()
        ports[port] = filepath
        available_port_data.setdefault(port, Event()).set()
        logger.debug(f"Received file '{ports[port]}' on port {port}")
    elif data_type == "directory":
        raise NotImplementedError(f"Recv directories not implemented yet")
    else:
        raise Exception(f"Unsupported data type: {data_type}")
    connections[src][port].close()
    connections[src][port] = None
"""

thread_function = """def _thread(f, *args) -> Thread:
    thread = Thread(target=f, args=args)
    thread.start()
    return thread
"""

wait_function = """def _wait(threads: MutableSequence[Thread]):
    for t in threads:
        t.join()
"""

preamble = "\n".join(
    [
        python_header,
        imports,
        global_vars,
        accept_function,
        exec_function,
        init_dataset_function,
        send_function,
        recv_function,
        thread_function,
        wait_function,
    ]
)


class ThreadStack:
    def __init__(self):
        self.stack: MutableSequence[set[str]] = [set()]
        self.counter = 0

    def add_group(self) -> None:
        self.stack.append(set())

    def add_thread(self) -> str:
        name = f"t{self.counter}"
        self.counter += 1
        self.stack[-1].add(name)
        return name

    def delete_group(self) -> set[str]:
        return self.stack.pop()

    def get_group(self) -> set[str]:
        return self.stack[-1]


class DefaultTarget(BaseCompiler):
    def __init__(self):
        super().__init__()
        self.current_location: Location | None = None
        self.functions = []
        self.function_counter = 0
        self.parallel_step_counter = 0
        # If `parathetized` attribute is to True it means that an open bracket has been encountered
        # but not yet its corresponding closed bracket
        self.parathetized = False
        self.programs: MutableMapping[str, TextIO] = {}
        self.workflow: DistributedWorkflow | None = None
        self.thread_stacks: MutableMapping[str, ThreadStack] = {}

    def _get_indentation(self):
        return " " * 4 if self.parallel_step_counter > 0 else ""

    def _get_thread(self, location: str) -> str:
        return self.thread_stacks.setdefault(location, ThreadStack()).add_thread()

    def begin_dataset(
        self,
        dataset: MutableSequence[tuple[str, Data]],
    ):
        for port_name, data in dataset:
            self.current_location.data[data.name] = data
            self.programs[self.current_location.name].write(
                f"""
    _init_dataset("{port_name}", "{data.value}")"""
            )

    def begin_location(self, location: Location) -> None:
        self.current_location = location
        self.programs[self.current_location.name] = open(
            f"{self.current_location.name}.py", "w"
        )
        self.programs[self.current_location.name].write(preamble)
        location = self.workflow.locations[self.current_location.name]
        self.programs[self.current_location.name].write(
            f"""def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(locations["{location.name}"])
    sock.settimeout(3)
    sock.listen({len(self.workflow.locations) - 1})

    _thread(_accept, sock)
"""
        )

    def begin_par(self) -> None:
        if self.parallel_step_counter == 0 and not self.parathetized:
            self.programs[self.current_location.name].write(
                f"""
    def f{self.function_counter}():"""
            )
            self.functions.append(f"f{self.function_counter}")
            self.function_counter += 1
        self.parallel_step_counter += 1

    def begin_paren(self) -> None:
        if self.parallel_step_counter > 1:
            self.parathetized = True

    def begin_workflow(self, workflow: Workflow) -> None:
        self.workflow = workflow

    def choice(self):
        raise NotImplementedError("Choice is not implemented yet")

    def end_location(self) -> None:
        self.programs[self.current_location.name].write(
            """
    logger.info("Terminated trace")
    global stopping
    stopping = True"""
        )
        locations = ",\n".join(
            [
                f"\t'{name}': ('{location.hostname}', {location.port})"
                for name, location in self.workflow.locations.items()
            ]
        )
        self.programs[self.current_location.name].write(
            f"""
locations = {{
{locations}
}}
"""
        )
        self.programs[self.current_location.name].write(
            """
if __name__ == '__main__':
    main()
"""
        )
        self.programs[self.current_location.name].close()

        try:
            import black

            black.format_file_in_place(
                Path(f"{self.current_location.name}.py"),
                fast=False,
                mode=black.mode.Mode(
                    target_versions={black.mode.TargetVersion.PY38}, line_length=88
                ),
                write_back=WriteBack.YES,
            )
        except ImportError:
            logger.warning(
                "`black` package not found. Install black to obtain pretty-printed output files."
            )

        self.current_location = None

    def end_par(self) -> None:
        self.parallel_step_counter -= 1
        if (
            self.thread_stacks[self.current_location.name].get_group()
            and not self.parathetized
        ):
            self.programs[self.current_location.name].write(
                f"""
        _wait([{', '.join(self.thread_stacks[self.current_location.name].delete_group())}])"""
            )
            self.thread_stacks[self.current_location.name].add_group()

        if self.parallel_step_counter == 0:
            thread_stack = ThreadStack()
            while self.functions:
                fun = self.functions.pop()
                thr = thread_stack.add_thread()
                self.programs[self.current_location.name].write(
                    f"""
    {thr} = _thread({fun})"""
                )
            if thread_stack.stack:
                self.programs[self.current_location.name].write(
                    f"""
    _wait([{', '.join(thread_stack.get_group())}])"""
                )

    def end_paren(self):
        self.parathetized = False
        if self.thread_stacks[self.current_location.name].get_group():
            self.programs[self.current_location.name].write(
                f"""
    {self._get_indentation()}_wait([{', '.join(self.thread_stacks[self.current_location.name].delete_group())}])"""
            )
            self.thread_stacks[self.current_location.name].add_group()

    def end_workflow(self) -> None:
        script_name = "run.sh"
        copy_traces = " &\n".join(
            [
                loc.get_copy_command(f"{loc.name}.py", f"{loc.hostname}:{loc.workdir}")
                for loc in self.workflow.locations.values()
                if loc.get_copy_command(
                    f"{loc.name}.py", f"{loc.hostname}:{loc.workdir}"
                )
            ]
        )
        if copy_traces:
            copy_traces += " &\nwait"
        commands = (
            " &\n".join(
                [
                    loc.get_command(f"python {loc.name}.py")
                    for loc in self.workflow.locations.values()
                ]
            )
            + " &"
        )
        with open(script_name, "w") as f:
            f.write(
                f"""{bash_header}

trap "echo Force termination; pkill -P $$" INT

{copy_traces}

# Start workflow execution
{commands}
wait
echo "Workflow execution terminated"
"""
            )
        usr_permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
        grp_permissions = stat.S_IRGRP | stat.S_IXGRP
        os.chmod(script_name, usr_permissions | grp_permissions)

    def exec(
        self,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        arguments = [arg for arg in step.arguments if not isinstance(arg, Port)]
        arguments_from_port = [
            (i, arg.name)
            for i, arg in enumerate(step.arguments)
            if isinstance(arg, Port)
        ]

        outputs = flow[1]
        output_port_name = next(iter(outputs))[0] if outputs else ""
        self.programs[self.current_location.name].write(
            f"""
    {self._get_indentation()}available_port_data.setdefault("{output_port_name}", Event())
    {self._get_indentation()}input_port_names = {[port_name for port_name, _ in flow[0]]}
    {self._get_indentation()}for port_name in input_port_names:
    {self._get_indentation()}    available_port_data.setdefault(port_name, Event())
    {self._get_indentation()}_exec("{step.name}", "{step.display_name}", input_port_names, "{output_port_name}", "{step.processors[output_port_name].type if output_port_name else ""}", "{step.processors[output_port_name].glob if output_port_name else ""}", "{step.command}", {arguments}, {arguments_from_port}, str(Path("{self.current_location.workdir}").expanduser().absolute()))"""
        )

    def par(self) -> None:
        if (
            self.thread_stacks[self.current_location.name].get_group()
            and not self.parathetized
        ):
            self.programs[self.current_location.name].write(
                f"""
        _wait([{', '.join(self.thread_stacks[self.current_location.name].delete_group())}])"""
            )
            self.thread_stacks[self.current_location.name].add_group()

        if not self.parathetized:
            self.programs[self.current_location.name].write(
                f"""
    def f{self.function_counter}():"""
            )
            self.functions.append(f"f{self.function_counter}")
            self.function_counter += 1

    def recv(self, port: str, data_type: str, src: str, dst: str):
        self.programs[self.current_location.name].write(
            f"""
    {self._get_indentation()}{self._get_thread(self.current_location.name)} = _thread(_recv, "{port}", str(Path("{self.current_location.workdir}").expanduser().absolute()), "{data_type}", "{src}")"""
        )

    def send(self, data: str, port: str, data_type: str, src: str, dst: str):
        self.programs[self.current_location.name].write(
            f"""
    {self._get_indentation()}{self._get_thread(self.current_location.name)} = _thread(_send, "{port}", "{data_type}", "{src}", "{dst}")"""
        )

    def seq(self):
        if (
            self.current_location.name in self.thread_stacks.keys()
            and self.thread_stacks[self.current_location.name].get_group()
        ):
            self.programs[self.current_location.name].write(
                f"""
    {self._get_indentation()}_wait([{', '.join(self.thread_stacks[self.current_location.name].delete_group())}])"""
            )
            self.thread_stacks[self.current_location.name].add_group()
