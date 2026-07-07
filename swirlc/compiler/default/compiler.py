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

list_helper = """def _list_inner(data_type: str) -> str | None:
    \"\"\"Return the inner type of a generic list type string, else None.

    'list[file]' -> 'file', 'list[list[string]]' -> 'list[string]', 'file' -> None.
    \"\"\"
    if data_type.startswith("list[") and data_type.endswith("]"):
        return data_type[len("list["):-1]
    return None
"""

framing_helpers = """def _send_len(sock: socket.socket, n: int):
    sock.sendall(n.to_bytes(8, "big"))


def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(BUF_SIZE, n - len(buf)))
        if not chunk:
            raise EOFError("Connection closed mid-frame")
        buf.extend(chunk)
    return bytes(buf)


def _recv_len(sock: socket.socket) -> int:
    return int.from_bytes(_recv_exactly(sock, 8), "big")


def _send_value(sock: socket.socket, data_type: str, value: Any):
    \"\"\"Serialise a (possibly nested) value onto the socket, framed by length.

    Framing is driven by the type string, which is identical on both ends, so
    nested lists (e.g. list[list[file]]) round-trip without an explicit schema.
    \"\"\"
    inner = _list_inner(data_type)
    if inner is not None:
        _send_len(sock, len(value))
        for elem in value:
            _send_value(sock, inner, elem)
    elif data_type in ("file", "directory"):
        if data_type == "directory":
            raise NotImplementedError("Sending directories is not implemented yet")
        name = os.path.basename(value).encode("utf-8")
        _send_len(sock, len(name))
        sock.sendall(name)
        _send_len(sock, os.path.getsize(value))
        with open(value, "rb") as fd:
            while buf := fd.read(BUF_SIZE):
                sock.sendall(buf)
    else:
        payload = value if isinstance(value, bytes) else str(value).encode("utf-8")
        _send_len(sock, len(payload))
        sock.sendall(payload)


def _recv_value(sock: socket.socket, data_type: str) -> Any:
    \"\"\"Inverse of _send_value: rebuild a value from the framed socket stream.\"\"\"
    inner = _list_inner(data_type)
    if inner is not None:
        return [_recv_value(sock, inner) for _ in range(_recv_len(sock))]
    elif data_type in ("file", "directory"):
        if data_type == "directory":
            raise NotImplementedError("Receiving directories is not implemented yet")
        name = _recv_exactly(sock, _recv_len(sock)).decode("utf-8")
        path = os.path.join(SCRATCH_DIR, f"rcv_{uuid.uuid4()}", name)
        os.mkdir(os.path.dirname(path))
        size = _recv_len(sock)
        with open(path, "wb") as fd:
            remaining = size
            while remaining:
                chunk = _recv_exactly(sock, min(BUF_SIZE, remaining))
                fd.write(chunk)
                remaining -= len(chunk)
        return path
    else:
        payload = _recv_exactly(sock, _recv_len(sock))
        return payload.decode("utf-8")
"""

exec_function = """def _exec(step_name: str, step_display_name: str, input_port_names: MutableSequence[str], output_port_name: str, data_type: str, glob_regex: str | None, cmd: str, args: MutableSequence[tuple[str,bool]]):
    for port_name in input_port_names:
        available_port_data[port_name].wait()
    workdir = os.path.join(SCRATCH_DIR, f"exec_{step_name}_{uuid.uuid4()}")
    os.mkdir(workdir)
    for port_name in input_port_names:
        value = ports[port_name]
        # A list input (e.g. list[file]) symlinks each element into the workdir.
        for elem in (value if isinstance(value, list) else [value]):
            os.symlink(os.path.abspath(elem), os.path.join(workdir, os.path.basename(elem)))
    # A list argument expands to its space-joined elements on the command line.
    cmd = " ".join([cmd, *(
        (" ".join(str(e) for e in ports[elem]) if isinstance(ports[elem], list) else str(ports[elem])) if is_data else elem
        for elem, is_data in args
    )])
    if logger.isEnabledFor(logging.INFO):
        logger.info(f"Step {step_display_name}-{step_name} executes command '{cmd}'")
    result = subprocess.run(cmd, capture_output=True, shell=True, cwd=workdir)
    if result.returncode != 0:
        raise Exception(f"Step {step_display_name}-{step_name} failed with exit status {result.returncode}: {result.stderr.decode('utf-8')}")
    if output_port_name:
        inner_type = _list_inner(data_type)
        if inner_type is not None:
            # Generic list output. Only a flat list of files/directories collected
            # via glob is materialised here; other/nested list outputs are TODO.
            if inner_type not in ("file", "directory"):
                raise NotImplementedError(f"Step {step_display_name}-{step_name} produces unsupported list output type: {data_type}")
            res = sorted(glob.glob(os.path.join(workdir, glob_regex)))
            ports[output_port_name] = res
            if logger.isEnabledFor(logging.INFO):
                logger.info(f"Step {step_display_name}-{step_name} result list ({len(res)}): {res}")
        elif data_type == "stdout":
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

init_dataset_function = """def _init_dataset(port_name: str, data: Any):
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
    sock.recv(BUF_SIZE)  # accept handshake ack
    _send_value(sock, data_type, ports[port])
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Sent data for port {port} to location {dst}")
    sock.close()
"""

recv_function = """def _recv(port: str, data_type: str, src: str) -> Any:
    with condition:
        while connections.setdefault(src, {}).get(port) is None:
            logger.debug(f"Waiting connection for port {port} from location {src}")
            condition.wait()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Received connection for port {port} from location {src}")
    conn = connections[src][port]
    ports[port] = _recv_value(conn, data_type)
    available_port_data[port].set()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Received data for port {port} from location {src}: {ports[port]}")
    conn.close()
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
        list_helper,
        framing_helpers,
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
        # repr() so both scalar strings and list values emit as valid Python literals.
        trace.write(f"""{i}_init_dataset("{port}", {data.value!r})\n""")
