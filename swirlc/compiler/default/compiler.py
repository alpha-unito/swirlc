from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import Optional, TextIO

from black import WriteBack
import black
from black.mode import TargetVersion

from swirlc.compiler.standard.compiler import StandardCompiler, TraceNode
from swirlc.core.entity import Data, Location, Port, Step, Workflow
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

from pathlib import Path
from io import BytesIO
from threading import Condition, Event, Thread
from typing import Any, MutableMapping, MutableSequence
"""

global_vars = """

BUF_SIZE = 8192

condition: Condition = Condition()
connections: MutableMapping[str, MutableMapping[str, socket.socket]] = {}
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

accept_function = """def _accept(sock: socket.socket):
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

exec_function = """def _exec(step_name: str, step_display_name: str, input_port_names: MutableSequence[str], output_port_name: str, data_type: str, glob_regex: str | None, cmd: str, args: MutableSequence[tuple[str,bool]]):
    for port_name in input_port_names:
        available_port_data[port_name].wait()
    workdir = os.path.join(SCRATCH_DIR, f"exec_{step_name}_{uuid.uuid4()}")
    os.mkdir(workdir)
    for port_name in input_port_names:
        os.symlink(os.path.abspath(ports[port_name]), os.path.join(workdir, os.path.basename(ports[port_name])))
    cmd = " ".join([cmd, *(ports[elem] if is_data else elem for elem, is_data in args)])
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

recv_function = """def _recv(port: str, data_type: str, src: str) -> Any:
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
        available_port_data[port].set()
    elif data_type == "file":
        filename = connections[src][port].recv(1024).decode()
        connections[src][port].send("ack".encode("utf-8"))
        filepath = os.path.join(SCRATCH_DIR, f"rcv_{port}_{uuid.uuid4()}", filename)
        os.mkdir(os.path.dirname(filepath))
        fd = open(filepath, "wb")
        while True:
            if not (data := connections[src][port].recv(BUF_SIZE)):
                break
            fd.write(data)
        fd.close()
        ports[port] = filepath
        available_port_data[port].set()
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


class DefaultTarget(StandardCompiler):
    def __init__(self, outdir: str) -> None:
        super().__init__(outdir)
        self.location_ports: set[str] = set()

    # ======== Threading policy ========
    def exec_is_threaded(self) -> bool:
        return False

    def _open_location_trace(self, location: Location) -> TextIO:
        return open(os.path.join(self.outdir, f"{location.name}.py"), "w")

    # ======== Lifecycle overrides ========

    def begin_location(self, location: Location) -> None:
        self.location_ports = set()
        super().begin_location(location)

    def end_location(self) -> None:
        assert self.current_location is not None

        location_name = self.current_location.name
        super().end_location()

        try:
            black.format_file_in_place(
                Path(self.outdir, f"{location_name}.py"),
                fast=False,
                mode=black.Mode(line_length=88, target_versions={TargetVersion.PY38}),
                write_back=WriteBack.YES,
            )
        except ImportError:
            logger.warning(
                "`black` package not found. Install black to obtain pretty-printed output files."
            )

    def end_workflow(self) -> None:
        assert self.current_workflow is not None

        script_name = "run.sh"
        workflow = self.current_workflow
        copy_traces = " &\n".join(
            [
                loc.get_copy_command(f"{loc.name}.py", f"{loc.hostname}:{loc.workdir}")
                for loc in workflow.locations.values()
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
                    for loc in workflow.locations.values()
                ]
            )
            + " &"
        )
        with open(os.path.join(self.outdir, script_name), "w") as f:
            f.write(f"""{bash_header}

trap "echo Force termination; pkill -P $$" INT

{copy_traces}

# Start workflow execution
{commands}
wait
echo "Workflow execution terminated"
""")
        usr_permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
        grp_permissions = stat.S_IRGRP | stat.S_IXGRP
        os.chmod(
            os.path.join(self.outdir, script_name), usr_permissions | grp_permissions
        )
        super().end_workflow()

    # ======== Write methods ========

    def write_location_start(self, location: Location, trace: TextIO):
        assert self.current_workflow is not None

        trace.write(preamble)
        trace.write(f"""
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(locations["{location.name}"])
    sock.settimeout(3)
    sock.listen({len(self.current_workflow.locations) - 1})

    _thread(_accept, sock)
""")

    def write_location_end(self, location: Location, trace: TextIO):
        assert self.current_workflow is not None
        trace.write("""
    logger.info("Terminated trace")
    global stopping
    stopping = True
""")

        out_dir = (
            f'str(Path("{location.outdir}").expanduser().absolute())'
            if location.outdir
            else "os.getcwd()"
        )
        scratch_dir = (
            f'str(Path("{location.workdir}").expanduser().absolute())'
            if location.workdir
            else "os.getcwd()"
        )
        locations_str = ",\n".join(
            [
                f"\t'{name}': ('{loc.hostname}', {loc.port})"
                for name, loc in self.current_workflow.locations.items()
            ]
        )
        ports_str = ",\n".join([f"\t'{p}': Event()" for p in self.location_ports])
        trace.write(f"""
locations = {{
{locations_str}
}}
available_port_data = {{
{ports_str}
}}

OUT_DIR = {out_dir}
SCRATCH_DIR = {scratch_dir}
""")
        trace.write("""
if __name__ == '__main__':
    main()
""")

    def write_thread_start(self, node: TraceNode, indent: int, trace: TextIO):
        if node.depth == 0:
            return
        i = "    " * indent
        trace.write(f"\n{i}def {node.id}():\n")

    def write_thread_end(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        comment: Optional[str] = None,
    ):
        if node.depth == 0:
            return

        i = "    " * indent
        trace.write(f"{i}{node.handle} = _thread({node.id})\n")

    def write_wait_for(self, node: TraceNode, indent: int, trace: TextIO):
        if node.depth == 0:
            return
        i = "    " * indent
        trace.write(f"{i}_wait([{node.handle}])\n")

    def write_exec(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        assert step.arguments is not None
        assert step.processors is not None

        arguments = [
            (arg.name if isinstance(arg, Port) else arg, isinstance(arg, Port))
            for arg in step.arguments
        ]
        output_port_name = next(iter(flow[1]))[0] if flow[1] else ""
        if output_port_name:
            self.location_ports.add(output_port_name)
        i = "    " * indent
        glob_val = step.processors[output_port_name].glob if output_port_name else ""
        type_val = step.processors[output_port_name].type if output_port_name else ""

        trace.write(
            f"""\n{i}_exec("{step.name}", "{step.display_name}", {[pn for pn, _ in flow[0]]}, "{output_port_name}", "{type_val}", "{glob_val}", "{step.command}", {arguments})\n"""
        )

    def write_recv(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        port: str,
        data: str,
        data_type: str,
        src: str,
        dst: str,
    ):
        self.location_ports.add(port)
        i = "    " * indent
        trace.write(
            f"""{i}{node.handle} = _thread(_recv, "{port}", "{data_type}", "{src}")\n"""
        )

    def write_send(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        data: str,
        port: str,
        data_type: str,
        src: str,
        dst: str,
    ):
        i = "    " * indent
        trace.write(
            f"""{i}{node.handle} = _thread(_send, "{port}", "{data_type}", "{src}", "{dst}")\n"""
        )

    def write_dataset(
        self, node: TraceNode, indent: int, trace: TextIO, port: str, data: Data
    ):
        assert self.current_location is not None

        self.location_ports.add(port)
        i = "    " * indent
        trace.write(f"""{i}_init_dataset("{port}", "{data.value}")\n""")
