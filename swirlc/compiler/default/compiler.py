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
import argparse
import json
import logging
import math
import os
import shlex
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
locations: MutableMapping[str, tuple[str, int]] = {}
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

file_rendezvous_helpers = """
def _advertise_host() -> str:
    try:
        host = subprocess.check_output(
            ADVERTISE_COMMAND,
            shell=True,
            text=True,
        ).strip()
    except subprocess.SubprocessError:
        host = ""
    return host or socket.getfqdn()


def _write_address_file(port: int):
    payload = {
        "runId": RUN_ID,
        "name": LOCATION_NAME,
        "host": _advertise_host(),
        "port": port,
    }
    tmp_path = f"{ADDRESS_FILE}.tmp"
    with open(tmp_path, "w") as fd:
        json.dump(payload, fd)
        fd.write("\\n")
    os.replace(tmp_path, ADDRESS_FILE)
    if logger.isEnabledFor(logging.INFO):
        logger.info("Wrote address file %s: %s", ADDRESS_FILE, payload)


def _load_address_book():
    timeout = int(os.environ.get("SWIRLC_ADDRESS_BOOK_TIMEOUT", "600"))
    deadline = time.monotonic() + timeout
    while True:
        try:
            with open(ADDRESS_BOOK_FILE) as fd:
                payload = json.load(fd)
        except FileNotFoundError:
            payload = None
        if payload and payload.get("runId") == RUN_ID:
            locations.update(
                {
                    name: (value["host"], int(value["port"]))
                    for name, value in payload["locations"].items()
                }
            )
            if logger.isEnabledFor(logging.INFO):
                logger.info("Loaded address book %s: %s", ADDRESS_BOOK_FILE, locations)
            return
        remaining = int(deadline - time.monotonic())
        if remaining <= 0:
            raise TimeoutError(
                f"Location {LOCATION_NAME} did not receive address book "
                f"{ADDRESS_BOOK_FILE} for run {RUN_ID} after {timeout}s"
            )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Waiting for address book %s for run %s (%ss left)",
                ADDRESS_BOOK_FILE,
                RUN_ID,
                remaining,
            )
        time.sleep(1)
"""

list_helper = """def _list_inner(data_type: str) -> str | None:
    \"\"\"Return the inner type of a generic list type string, else None.

    'list[file]' -> 'file', 'list[list[string]]' -> 'list[string]', 'file' -> None.
    \"\"\"
    if data_type.startswith("list[") and data_type.endswith("]"):
        return data_type[len("list["):-1]
    return None
"""

expression_function = r"""def _js_file_object(value: Any, data_type: str) -> Any:
    inner = _list_inner(data_type)
    if inner is not None:
        return [_js_file_object(item, inner) for item in value]
    if data_type == "int":
        return int(value)
    if data_type == "bool":
        return value if isinstance(value, bool) else str(value).lower() == "true"
    if data_type == "string":
        return str(value)
    if data_type not in ("file", "directory"):
        return value
    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError(
                f"Expected one {data_type} value, received {len(value)}; scatter expansion is not supported"
            )
        value = value[0]
    path = os.fspath(value)
    basename = os.path.basename(os.path.normpath(path))
    nameroot, nameext = os.path.splitext(basename)
    return {
        "class": "File" if data_type == "file" else "Directory",
        "path": path,
        "location": path,
        "dirname": os.path.dirname(path),
        "basename": basename,
        "nameroot": nameroot,
        "nameext": nameext,
    }


def _js_get(value: Any, key: Any) -> Any:
    if key == "length" and isinstance(value, (str, list, dict)):
        return len(value)
    if isinstance(value, dict):
        return value.get(key)
    if isinstance(value, (list, tuple)):
        return value[int(key)]
    if isinstance(value, str):
        if key == "split":
            return lambda separator=None: value.split(separator)
        if key == "substring":
            def substring(start: Any, end: Any = None) -> str:
                start_index = max(0, int(start))
                end_index = len(value) if end is None else max(0, int(end))
                start_index, end_index = min(start_index, end_index), max(start_index, end_index)
                return value[start_index:end_index]
            return substring
    raise TypeError(f"Cannot read JavaScript property {key!r} from {value!r}")


def _js_parse_int(value: Any, radix: Any = 10) -> int:
    return int(str(value), int(radix))


def _coerce_expression_output(value: Any, data_type: str) -> Any:
    inner = _list_inner(data_type)
    if inner is not None:
        if not isinstance(value, list):
            raise TypeError(f"Expression result for {data_type} is not a list")
        return [_coerce_expression_output(item, inner) for item in value]
    if data_type == "int":
        return int(value)
    if data_type == "bool":
        return bool(value)
    if data_type == "string":
        return str(value)
    return value


def _expression(step_display_name: str, input_specs: MutableMapping[str, tuple[str, str]], output_specs: MutableMapping[str, tuple[str, str]], function):
    for port_name, _ in input_specs.values():
        available_port_data[port_name].wait()
    inputs = {
        name: _js_file_object(ports[port_name], data_type)
        for name, (port_name, data_type) in input_specs.items()
    }
    result = function(inputs)
    if not isinstance(result, dict):
        raise TypeError(f"ExpressionTool {step_display_name} must return an object")
    for output_name, (port_name, data_type) in output_specs.items():
        if output_name not in result:
            raise KeyError(f"ExpressionTool {step_display_name} did not return output {output_name}")
        ports[port_name] = _coerce_expression_output(result[output_name], data_type)
        available_port_data[port_name].set()
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
            if not elem:
                continue
            elem_path = os.fspath(elem)
            if not os.path.exists(elem_path):
                continue
            target_name = os.path.basename(os.path.normpath(elem_path))
            if not target_name:
                continue
            os.symlink(os.path.abspath(elem_path), os.path.join(workdir, target_name))
    def _quote_arg(value: Any) -> str:
        return shlex.quote(str(value))

    # A list argument expands to its space-joined elements on the command line.
    cmd = " ".join([cmd, *(
        (" ".join(_quote_arg(e) for e in ports[elem]) if isinstance(ports[elem], list) else _quote_arg(ports[elem])) if is_data else _quote_arg(elem)
        for elem, is_data in args
    )])
    if data_type in ("string", "int", "bool") and glob_regex:
        cmd = f"{cmd} > {shlex.quote(glob_regex)}"
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
        elif data_type in ("string", "int", "bool"):
            if glob_regex:
                res = [path for path in glob.glob(os.path.join(workdir, glob_regex))]
                if len(res) == 0:
                    raise FileNotFoundError(f"Step {step_display_name}-{step_name} did not produce a file which matches the glob regex: {glob_regex}")
                if len(res) > 1:
                    raise Exception(f"Step {step_display_name}-{step_name} produced too many files which match glob regex: {res}")
                with open(res[0]) as fd:
                    value = fd.read().strip()
            else:
                value = result.stdout.decode().strip()
            if data_type == "int":
                value = int(value)
            elif data_type == "bool":
                value = value.lower() in ("1", "true", "yes", "on")
            ports[output_port_name] = value
            if logger.isEnabledFor(logging.INFO):
                logger.info(f"Step {step_display_name}-{step_name} result {data_type}: '{ports[output_port_name]}'")
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
    def _target():
        try:
            f(*args)
        except BaseException:
            logger.exception("Thread %s failed", f.__name__)
            os._exit(1)

    thread = Thread(target=_target)
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
        file_rendezvous_helpers,
        list_helper,
        expression_function,
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

    def _write_slurm_script(self, location: Location) -> None:
        slurm = location.slurm or {}
        options = dict(slurm.get("options") or {})
        script_path = os.path.join(self.outdir, f"{location.name}.sbatch")
        command = f"python3 {location.name}.py --run-id $SWIRLC_RUN_ID"

        lines = [
            "#!/bin/bash",
            f"#SBATCH --job-name=swirl-{location.name}",
        ]
        if "output" not in options:
            lines.append(f"#SBATCH --output={location.name}.slurm.out")
        if "error" not in options:
            lines.append(f"#SBATCH --error={location.name}.slurm.err")
        for key, value in sorted(options.items()):
            if key == "file":
                continue
            option = key.replace("_", "-")
            if isinstance(value, bool):
                if value:
                    lines.append(f"#SBATCH --{option}")
            else:
                lines.append(f"#SBATCH --{option}={value}")
        lines.extend(
            [
                "",
                "set -euo pipefail",
                "echo \"SWIRL Slurm job started at $(date -Iseconds)\"",
                "echo \"Host: $(hostname -f 2>/dev/null || hostname)\"",
                "echo \"Working directory: $(pwd)\"",
                "echo \"Run id: ${SWIRLC_RUN_ID:-<unset>}\"",
                "echo \"Python: $(command -v python3)\"",
                command,
                "",
            ]
        )
        with open(script_path, "w") as f:
            f.write("\n".join(lines))

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
        for loc in workflow.locations.values():
            if loc.connection_type == "slurm":
                self._write_slurm_script(loc)

        def copy_commands(location: Location) -> list[str]:
            filenames = [f"{location.name}.py"]
            if location.connection_type == "slurm":
                filenames.append(f"{location.name}.sbatch")
            commands = []
            for filename in filenames:
                command = location.get_copy_command(
                    filename, f"{location.hostname}:{location.workdir}"
                )
                if command:
                    commands.append(command)
            return commands

        def fetch_address_command(location: Location) -> str:
            filename = f"{location.name}_address.json"
            return location.get_fetch_command(filename, filename)

        def copy_address_book_command(location: Location) -> str:
            return location.get_copy_command(
                "address_book.json", f"{location.hostname}:{location.workdir}"
            )

        prepare_commands = " &\n".join(
            [
                command
                for loc in workflow.locations.values()
                if (command := loc.get_prepare_command())
            ]
        )
        if prepare_commands:
            prepare_commands += " &\nwait"
        copy_traces = " &\n".join(
            [
                command
                for loc in workflow.locations.values()
                for command in copy_commands(loc)
            ]
        )
        if copy_traces:
            copy_traces += " &\nwait"
        fetch_addresses = "\n".join(
            [
                f"{command} >/dev/null 2>&1 || true"
                for loc in workflow.locations.values()
                if (command := fetch_address_command(loc))
            ]
        )
        copy_address_book = " &\n".join(
            [
                command
                for loc in workflow.locations.values()
                if (command := copy_address_book_command(loc))
            ]
        )
        if copy_address_book:
            copy_address_book += " &\nwait"
        address_files = " ".join(
            [f"{loc.name}_address.json" for loc in workflow.locations.values()]
        )
        location_command = "python3 {name}.py --run-id $SWIRLC_RUN_ID"
        commands = (
            " &\n".join(
                [
                    loc.get_command(location_command.format(name=loc.name))
                    for loc in workflow.locations.values()
                ]
            )
            + " &"
        )
        with open(os.path.join(self.outdir, script_name), "w") as f:
            f.write(f"""{bash_header}

SWIRLC_RUN_ID="${{SWIRLC_RUN_ID:-$(date +%s)-$$}}"
export SWIRLC_RUN_ID
ADDRESS_FILES="{address_files}"

cleanup() {{
    rm -f address_book.json address_book.json.tmp *_address.json
}}

terminate() {{
    echo Force termination
    trap - INT TERM
    pkill -P $$ 2>/dev/null || true
    cleanup
    exit 130
}}

check_workflow_processes() {{
    for pid in $WORKFLOW_PIDS; do
        if ! kill -0 "$pid" 2>/dev/null; then
            wait "$pid"
            status=$?
            if [ "$status" -ne 0 ]; then
                echo "Workflow process $pid exited before rendezvous completed with status $status"
                exit "$status"
            fi
            echo "Workflow process $pid exited before rendezvous completed"
            exit 1
        fi
    done
}}

all_addresses_ready() {{
    for file in $ADDRESS_FILES; do
        if [ ! -s "$file" ]; then
            return 1
        fi
        if ! grep -q "\\"runId\\": \\"$SWIRLC_RUN_ID\\"" "$file"; then
            return 1
        fi
    done
    return 0
}}

build_address_book() {{
    python3 -c 'import json, os, sys
run_id = sys.argv[1]
locations = {{}}
for path in sys.argv[2:]:
    with open(path) as fd:
        payload = json.load(fd)
    if payload.get("runId") != run_id:
        bad_run = payload.get("runId")
        raise SystemExit(f"stale address file {{path}} for run {{bad_run}}")
    locations[payload["name"]] = {{"host": payload["host"], "port": int(payload["port"])}}
with open("address_book.json.tmp", "w") as fd:
    json.dump({{"runId": run_id, "locations": locations}}, fd)
    fd.write("\\n")
os.replace("address_book.json.tmp", "address_book.json")
' "$SWIRLC_RUN_ID" $ADDRESS_FILES
}}

trap "terminate" INT TERM
trap "cleanup" EXIT

{prepare_commands}

{copy_traces}

# Start workflow execution. Locations will publish their address file and then
# wait until this script distributes address_book.json.
echo "SWIRL run id: $SWIRLC_RUN_ID"
{commands}
WORKFLOW_PIDS="$(jobs -p)"

deadline=$(( $(date +%s) + ${{SWIRLC_ADDRESS_GATHER_TIMEOUT:-600}} ))
while ! all_addresses_ready; do
{fetch_addresses}
    check_workflow_processes
    if [ "$(date +%s)" -ge "$deadline" ]; then
        echo "Timed out waiting for address files: $ADDRESS_FILES"
        exit 1
    fi
    sleep 1
done

build_address_book
echo "Address book ready"
{copy_address_book}

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    global RUN_ID
    RUN_ID = args.run_id

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    bind_port = LOCATION_PORT if os.environ.get("SWIRLC_USE_CONFIGURED_PORT") else 0
    sock.bind((BIND_HOST, bind_port))
    sock.settimeout(3)
    sock.listen({len(self.current_workflow.locations) - 1})

    _thread(_accept, sock)
    _write_address_file(sock.getsockname()[1])
    _load_address_book()
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
        ports_str = ",\n".join([f"\t'{p}': Event()" for p in self.location_ports])
        trace.write(f"""
available_port_data = {{
{ports_str}
}}

LOCATION_NAME = "{location.name}"
LOCATION_PORT = {location.port or 0}
BIND_HOST = "{location.get_bind_host()}"
ADVERTISE_COMMAND = {location.get_advertise_command()!r}
RUN_ID = ""
ADDRESS_FILE = f"{{LOCATION_NAME}}_address.json"
ADDRESS_BOOK_FILE = "address_book.json"
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

        i = "    " * indent
        if step.expression_python is not None:
            assert self.current_workflow is not None
            input_specs = {
                name: (port.name, step.expression_input_types[name])
                for name, port in (step.expression_inputs or {}).items()
            }
            output_specs = {}
            for output_name, port in (step.expression_outputs or {}).items():
                port_name = port.name
                self.location_ports.add(port_name)
                output_specs[output_name] = (
                    port_name,
                    step.processors[port_name].type,
                )
            function_name = f"_expression_{step.name}"
            body = "\n".join(
                f"{i}    {line}" if line else ""
                for line in step.expression_python.splitlines()
            )
            trace.write(f"\n{i}def {function_name}(inputs):\n{body}\n")
            trace.write(
                f"{i}_expression({step.display_name!r}, {input_specs!r}, {output_specs!r}, {function_name})\n"
            )
            return

        arguments = [
            (arg.name if isinstance(arg, Port) else arg, isinstance(arg, Port))
            for arg in step.arguments
        ]
        output_port_name = next(iter(flow[1]))[0] if flow[1] else ""
        if output_port_name:
            self.location_ports.add(output_port_name)
        glob_val = step.processors[output_port_name].glob if output_port_name else ""
        type_val = step.processors[output_port_name].type if output_port_name else ""

        trace.write(
            f"""\n{i}_exec({step.name!r}, {step.display_name!r}, {[pn for pn, _ in flow[0]]!r}, {output_port_name!r}, {type_val!r}, {glob_val!r}, {step.command!r}, {arguments!r})\n"""
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
