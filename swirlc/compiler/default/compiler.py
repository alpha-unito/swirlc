from __future__ import annotations

import base64
import hashlib
import io
import os
import stat
import sys
import zipfile
from importlib import metadata
from pathlib import Path
from typing import Optional, TextIO

import black
from black import WriteBack
from black.mode import TargetVersion
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from swirlc.compiler.standard.compiler import StandardCompiler, TraceNode
from swirlc.core.entity import Data, Location, Port, Step
from swirlc.log_handler import logger
from swirlc.version import VERSION

bash_header = f"""#!/bin/sh

# This file was generated automatically using SWIRL v{VERSION},
# using command swirlc {" ".join(sys.argv[1:])}
"""

python_header = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file was generated automatically using SWIRL v{VERSION},
# using command swirlc {" ".join(sys.argv[1:])}
"""

javascript_requirements = """\
Js2Py==0.74; python_version < "3.13"
Js2Py-3.14==0.74.2; python_version >= "3.13"
pyjsparser==2.7.1
six==1.17.0
tzlocal==5.4.4
"""


def _build_dependency_archive(root_distributions: tuple[str, ...]) -> tuple[str, str]:
    """Return a deterministic base85 archive and its SHA-256 digest."""
    files: dict[str, Path] = {}
    pending = list(root_distributions)
    seen: set[str] = set()
    environment = default_environment()
    while pending:
        requested_name = pending.pop()
        canonical_name = canonicalize_name(requested_name)
        if canonical_name in seen:
            continue
        try:
            distribution = metadata.distribution(requested_name)
        except metadata.PackageNotFoundError as exc:
            raise RuntimeError(
                f"Cannot bundle Python distribution {requested_name!r}: it is not "
                "installed in the compiler environment."
            ) from exc
        seen.add(canonical_name)

        for requirement_text in distribution.requires or ():
            requirement = Requirement(requirement_text)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            pending.append(requirement.name)

        for entry in distribution.files or ():
            relative = Path(str(entry))
            if relative.is_absolute() or ".." in relative.parts:
                continue
            source = Path(distribution.locate_file(entry))
            if source.is_file() and "__pycache__" not in relative.parts:
                if source.suffix.lower() in {".so", ".pyd", ".dylib"}:
                    raise RuntimeError(
                        f"Cannot portably bundle {requested_name!r}: {relative} is "
                        "a compiled native extension. Use deployment-time "
                        "requirements for platform-specific libraries."
                    )
                files[relative.as_posix()] = source

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(
        archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for archive_name, source in sorted(files.items()):
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())

    archive_bytes = archive_buffer.getvalue()
    payload = base64.b85encode(archive_bytes).decode("ascii")
    return payload, hashlib.sha256(archive_bytes).hexdigest()


def _embedded_dependency_bootstrap(payload: str, digest: str) -> str:
    chunks = "\n".join(
        f"    {payload[index : index + 100]!r}" for index in range(0, len(payload), 100)
    )
    return f"""
_BUNDLED_DEPENDENCIES_SHA256 = {digest!r}
_BUNDLED_DEPENDENCIES_B85 = (
{chunks}
)


def _activate_bundled_dependencies():
    archive_path = Path(__file__).resolve().with_name(
        f".swirlc-dependencies-{{_BUNDLED_DEPENDENCIES_SHA256}}.zip"
    )
    archive_bytes = base64.b85decode(_BUNDLED_DEPENDENCIES_B85)
    if (
        not archive_path.exists()
        or hashlib.sha256(archive_path.read_bytes()).hexdigest()
        != _BUNDLED_DEPENDENCIES_SHA256
    ):
        temporary_path = archive_path.with_suffix(".tmp")
        temporary_path.write_bytes(archive_bytes)
        os.replace(temporary_path, archive_path)
    sys.path.insert(0, str(archive_path))


_activate_bundled_dependencies()
"""


def _parallel_shell_block(commands: list[str]) -> str:
    """Run commands concurrently while waiting only for this block's children."""
    if not commands:
        return ""
    lines = ["(", '    auxiliary_pids=""']
    for command in commands:
        lines.extend(
            [
                f"    {command} &",
                '    auxiliary_pids="$auxiliary_pids $!"',
            ]
        )
    lines.extend(
        [
            "    auxiliary_status=0",
            "    for auxiliary_pid in $auxiliary_pids; do",
            '        wait "$auxiliary_pid" || auxiliary_status=$?',
            "    done",
            '    exit "$auxiliary_status"',
            ")",
        ]
    )
    return "\n".join(lines)


def _start_background_shell_commands(commands: list[str], pid_variable: str) -> str:
    """Start commands and record their direct child PIDs in a shell variable."""
    lines = [f'{pid_variable}=""']
    for index, command in enumerate(commands):
        lines.extend(
            [
                f"{command} &",
                (
                    f'{pid_variable}="$!"'
                    if index == 0
                    else f'{pid_variable}="${{{pid_variable}}} $!"'
                ),
            ]
        )
    return "\n".join(lines)


imports = """from __future__ import annotations

import base64
import glob
import argparse
import datetime
import hashlib
import json
import logging
import os
import shlex
import socket
import subprocess
import sys
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
connections: MutableMapping[str, MutableMapping[str, list[tuple[socket.socket, bool]]]] = {}

locations: MutableMapping[str, tuple[str, int]] = {}
ports: MutableMapping[str, Any] = {}
_eof_ports: set[tuple[str, str]] = set()
_worker_idx: MutableSequence[int] = [0]
stopping: bool = False


class SwirlLogFormatter(logging.Formatter):
    LOC_PALETTE = [
        "\\033[1;36m",  # Bold Cyan
        "\\033[1;32m",  # Bold Green
        "\\033[1;35m",  # Bold Magenta
        "\\033[1;34m",  # Bold Blue
        "\\033[1;33m",  # Bold Yellow
        "\\033[1;96m",  # Bright Cyan
        "\\033[1;92m",  # Bright Green
        "\\033[1;95m",  # Bright Magenta
    ]
    KNOWN_LOCS = {
        "l0": "\\033[1;36m",   # Cyan
        "l1": "\\033[1;32m",   # Green
        "l2": "\\033[1;34m",   # Blue
        "l3": "\\033[1;35m",   # Magenta
        "lG": "\\033[1;33m",   # Yellow
    }
    LEVEL_COLORS = {
        logging.DEBUG: "\\033[90mDEBUG\\033[0m",
        logging.INFO: "\\033[1;32mINFO \\033[0m",
        logging.WARNING: "\\033[1;33mWARN \\033[0m",
        logging.ERROR: "\\033[1;31mERROR\\033[0m",
        logging.CRITICAL: "\\033[1;41;37mCRIT \\033[0m",
    }
    DIM = "\\033[90m"
    RESET = "\\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        loc = getattr(record, "location", None) or globals().get("LOCATION_NAME") or Path(sys.argv[0]).stem
        if loc in self.KNOWN_LOCS:
            loc_color = self.KNOWN_LOCS[loc]
        else:
            loc_color = self.LOC_PALETTE[abs(hash(loc)) % len(self.LOC_PALETTE)]
            
        t = datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S") + f".{int(record.msecs):03d}"
        level_str = self.LEVEL_COLORS.get(record.levelno, f"{record.levelname:<5}")
        loc_badge = f"{loc_color}{loc:>2} │{self.RESET}"
        time_badge = f"{self.DIM}{t}{self.RESET}"
        
        if record.levelno in (logging.DEBUG, logging.ERROR, logging.CRITICAL):
            file_info = f"{self.DIM}({record.filename}:{record.lineno}){self.RESET} "
        else:
            file_info = ""
            
        header = f"{time_badge} {loc_badge} {level_str} {file_info}"
        msg = record.getMessage()
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if msg[-1:] != "\\n":
                msg += "\\n"
            msg += record.exc_text
        if record.stack_info:
            if msg[-1:] != "\\n":
                msg += "\\n"
            msg += self.formatStack(record.stack_info)
        return f"{header}{msg}"


logger = logging.getLogger("swirlc")
defaultStreamHandler = logging.StreamHandler()
defaultStreamHandler.setFormatter(SwirlLogFormatter())
logger.addHandler(defaultStreamHandler)
logger.setLevel(logging.DEBUG)
logger.propagate = False
"""



accept_function = """def _accept(sock: socket.socket):
    while not stopping:
        try:
            conn, _ = sock.accept()
            msg = conn.recv(1024).decode("utf-8").split()
            name = msg[0]
            port = msg[1]
            is_eof = len(msg) > 2 and msg[2] == "EOF"
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Accepted connection for port {port} from location {name} (EOF={is_eof})")
            with condition:
                connections.setdefault(name, {}).setdefault(port, []).append((conn, is_eof))
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


def _to_python(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    elif hasattr(value, "to_list"):
        value = value.to_list()
    if isinstance(value, dict):
        return {str(key): _to_python(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_python(item) for item in value]
    return value


def _run_javascript_expression(expression: str, inputs: MutableMapping[str, Any]) -> Any:
    try:
        import js2py
    except ImportError:
        # Js2Py-3.14 uses a distinct import name so it can coexist with the
        # original distribution while retaining the same public API.
        import js2py_ as js2py

    js2py.disable_pyimport()
    source = expression.strip()
    if source.startswith("${") and source.endswith("}"):
        body = source[2:-1]
    elif source.startswith("$(") and source.endswith(")"):
        body = f"return ({source[2:-1]});"
    else:
        raise ValueError("CWL JavaScript expression must use $(...) or ${...} syntax")
    invocation = (
        "(function(inputs) {\n"
        + body
        + "\n})("
        + json.dumps(inputs)
        + ");"
    )
    return _to_python(js2py.eval_js(invocation))


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


def _expression(step_display_name: str, expression: str, input_specs: MutableMapping[str, tuple[str, str]], output_specs: MutableMapping[str, tuple[str, str]]):
    for port_name, _ in input_specs.values():
        available_port_data[port_name].wait()
    inputs = {
        name: _js_file_object(ports[port_name], data_type)
        for name, (port_name, data_type) in input_specs.items()
    }
    result = _run_javascript_expression(expression, inputs)
    if not isinstance(result, dict):
        raise TypeError(f"ExpressionTool {step_display_name} must return an object")
    for output_name, (port_name, data_type) in output_specs.items():
        if output_name not in result:
            raise KeyError(f"ExpressionTool {step_display_name} did not return output {output_name}")
        ports[port_name] = _coerce_expression_output(result[output_name], data_type)
        if logger.isEnabledFor(logging.INFO):
            logger.info(
                "ExpressionTool %s result %s (%s): %r",
                step_display_name,
                output_name,
                data_type,
                ports[port_name],
            )
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
        os.makedirs(os.path.dirname(path), exist_ok=True)
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

exec_function = """def _exec(step_name: str, step_display_name: str, input_port_names: MutableSequence[str], output_specs: MutableSequence[tuple[str, str, str | None]], cmd: str, args: MutableSequence[tuple[str,bool]]):
    for port_name in input_port_names:
        available_port_data[port_name].wait()
    workdir = os.path.join(SCRATCH_DIR, f"exec_{step_name}_{uuid.uuid4()}")
    os.makedirs(workdir, exist_ok=True)

    for port_name in input_port_names:
        value = ports[port_name]
        # A list input (e.g. list[file]) symlinks each element into the workdir.
        for idx, elem in enumerate(value if isinstance(value, list) else [value]):
            if not elem:
                continue
            elem_path = os.fspath(elem)
            if not os.path.exists(elem_path):
                continue
            target_name = os.path.basename(os.path.normpath(elem_path))
            if not target_name:
                continue
            dest_path = os.path.join(workdir, target_name)
            if os.path.exists(dest_path):
                dest_path = os.path.join(workdir, f"{idx}_{target_name}")
            try:
                os.symlink(os.path.abspath(elem_path), dest_path)
            except FileExistsError:
                pass

    def _quote_arg(value: Any) -> str:
        return shlex.quote(str(value))

    # A list argument expands to its space-joined elements on the command line.
    cmd = " ".join([cmd, *(
        (" ".join(_quote_arg(e) for e in ports[elem]) if isinstance(ports[elem], list) else _quote_arg(ports[elem])) if is_data else _quote_arg(elem)
        for elem, is_data in args
    )])
    for out_port, d_type, g_regex in output_specs:
        if g_regex and not any(c in g_regex for c in "*?[]"):
            if d_type in ("string", "int", "bool", "file"):
                cmd = f"{cmd} > {shlex.quote(g_regex)}"

    if logger.isEnabledFor(logging.INFO):
        logger.info(f"Step {step_display_name}-{step_name} executes command '{cmd}'")
    result = subprocess.run(cmd, capture_output=True, shell=True, cwd=workdir)
    if result.returncode != 0:
        raise Exception(f"Step {step_display_name}-{step_name} failed with exit status {result.returncode}: {result.stderr.decode('utf-8')}")
    if output_specs:
        for output_port_name, data_type, glob_regex in output_specs:
            inner_type = _list_inner(data_type)
            if inner_type is not None:
                if inner_type not in ("file", "directory"):
                    raise NotImplementedError(f"Step {step_display_name}-{step_name} produces unsupported list output type: {data_type}")
                res = sorted(glob.glob(os.path.join(workdir, glob_regex or "*")))
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
                    with open(res[0]) as fd:
                        value = fd.read().strip()
                else:
                    value = result.stdout.decode().strip() or "0"
                if data_type == "int":
                    value = int(value) if value else 0
                elif data_type == "bool":
                    value = value.lower() in ("1", "true", "yes", "on")
                ports[output_port_name] = value
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f"Step {step_display_name}-{step_name} result {data_type}: '{ports[output_port_name]}'")
            elif data_type in ("file", "directory"):
                res = [path for path in glob.glob(os.path.join(workdir, glob_regex or "*"))]
                if len(res) == 0:
                    raise FileNotFoundError(f"Step {step_display_name}-{step_name} did not produce a file or directory which match the glob regex: {glob_regex}")
                elif len(res) == 1:
                    ports[output_port_name] = os.path.join(workdir, res[0])
                    if logger.isEnabledFor(logging.INFO):
                        logger.info(f"Step {step_display_name}-{step_name} result file: '{ports[output_port_name]}'")
                else:
                    ports[output_port_name] = [os.path.join(workdir, r) for r in res]
                    if logger.isEnabledFor(logging.INFO):
                        logger.info(f"Step {step_display_name}-{step_name} result files ({len(res)}): {ports[output_port_name]}")
            else:
                ports[output_port_name] = ""
            available_port_data[output_port_name].set()
    else:
        if logger.isEnabledFor(logging.INFO):
            logger.info(f"Step {step_display_name}-{step_name} has not an output port. Result: '{result.stdout.decode().strip()}'")
"""

init_dataset_function = """def _init_dataset(port_name: str, data: Any):
    ports[port_name] = data
    available_port_data[port_name].set()
"""

send_function = """def _send(data: str, port: str, data_type: str, src: str, dst: str) -> bool:
    is_eof = (data == "eof" or port == "eof" or data_type == "eof")
    if not is_eof:
        val = ports.get(port, "")
        if isinstance(val, list) and not data_type.startswith("list["):
            if len(val) == 0:
                return False
            val = val.pop(0)
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(locations[dst])
            break
        except socket.error:
            time.sleep(1)
    tag = "EOF" if is_eof else "DATA"
    sock.send(f"{src} {port} {tag}".encode("utf-8"))
    sock.recv(BUF_SIZE)  # accept handshake ack
    if not is_eof:
        _send_value(sock, data_type, val)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Sent {'EOF' if is_eof else 'data'} for port {port} to location {dst}")
    sock.close()
    return True
"""



recv_function = """def _recv(port: str, data_type: str, src: str, is_gather: bool = False) -> Any:
    if (src, port) in _eof_ports:
        return "eof"
    with condition:
        while not connections.setdefault(src, {}).get(port):
            logger.debug(f"Waiting connection for port {port} from location {src}")
            condition.wait()
        conn, is_eof = connections[src][port].pop(0)
    if is_eof:
        conn.close()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Received EOF for port {port} from location {src}")
        _eof_ports.add((src, port))
        available_port_data[port].set()
        return "eof"
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Received connection for port {port} from location {src}")
    val = _recv_value(conn, data_type)
    conn.close()
    if is_gather:
        if port not in ports or not isinstance(ports[port], list):
            ports[port] = []
        ports[port].append(val)
    else:
        ports[port] = val
    available_port_data[port].set()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Received data for port {port} from location {src}: {ports[port]}")
    return val
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
    def __init__(
        self,
        outdir: str,
        tmpdir: str | None = None,
        bundle_dependencies: bool = False,
        additional_dependencies: list[str] | None = None,
    ) -> None:
        super().__init__(outdir, tmpdir)
        self.location_ports: set[str] = set()
        self.bundle_dependencies = bundle_dependencies
        self.additional_dependencies = tuple(additional_dependencies or ())
        self._dependency_archives: dict[tuple[str, ...], tuple[str, str]] = {}


    def _dependency_roots_for_location(self, location: Location) -> tuple[str, ...]:
        assert self.current_workflow is not None
        roots = list(self.additional_dependencies)
        if any(
            step.expression is not None
            for step in self.current_workflow.get_location_steps(location)
        ):
            roots.append("Js2Py-3.14")
        return tuple(sorted(set(roots), key=canonicalize_name))

    def _dependency_archive_for_location(
        self, location: Location
    ) -> tuple[str, str] | None:
        if not self.bundle_dependencies:
            return None
        roots = self._dependency_roots_for_location(location)
        if not roots:
            return None
        if roots not in self._dependency_archives:
            self._dependency_archives[roots] = _build_dependency_archive(roots)
        return self._dependency_archives[roots]

    # ======== Threading policy ========
    def exec_is_threaded(self) -> bool:
        return False

    def _open_location_trace(self, location: Location) -> TextIO:
        return open(os.path.join(self.outdir, f"{location.name}.py"), "w")

    def _write_runtime_bundle(self, location: Location) -> None:
        assert self.current_workflow is not None

        has_expressions = any(
            step.expression is not None
            for step in self.current_workflow.get_location_steps(location)
        )
        requirements_name = f"{location.name}.requirements.txt"
        requirements_path = os.path.join(self.outdir, requirements_name)
        with open(requirements_path, "w") as f:
            if has_expressions and not self.bundle_dependencies:
                f.write(javascript_requirements)

        launcher_name = f"{location.name}.launch.sh"
        launcher_path = os.path.join(self.outdir, launcher_name)
        venv_name = f".swirlc-venv-{location.name}"
        marker_name = ".swirlc-requirements.txt"
        with open(launcher_path, "w") as f:
            f.write(
                f"""#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

PYTHON_BIN="${{SWIRLC_PYTHON:-python3}}"
VENV_DIR="${{SWIRLC_VENV_DIR:-{venv_name}}}"
REQUIREMENTS={requirements_name!r}
MARKER="$VENV_DIR/{marker_name}"

prepare_runtime() {{
    if [ ! -s "$REQUIREMENTS" ]; then
        return
    fi
    if [ ! -x "$VENV_DIR/bin/python" ]; then
        echo "Creating SWIRL runtime environment $VENV_DIR" >&2
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi
    if [ ! -f "$MARKER" ] || ! cmp -s "$REQUIREMENTS" "$MARKER"; then
        echo "Installing SWIRL runtime requirements for {location.name}" >&2
        "$VENV_DIR/bin/python" -m pip install \\
            --disable-pip-version-check \\
            --requirement "$REQUIREMENTS"
        cp "$REQUIREMENTS" "$MARKER"
    fi
}}

prepare_runtime
if [ "${{1:-}}" = "--prepare" ]; then
    exit 0
fi

if [ -s "$REQUIREMENTS" ]; then
    exec "$VENV_DIR/bin/python" {location.name}.py "$@"
fi
exec "$PYTHON_BIN" {location.name}.py "$@"
"""
            )
        usr_permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
        grp_permissions = stat.S_IRGRP | stat.S_IXGRP
        os.chmod(launcher_path, usr_permissions | grp_permissions)

    def _write_slurm_script(self, location: Location) -> None:
        slurm = location.slurm or {}
        options = dict(slurm.get("options") or {})
        script_path = os.path.join(self.outdir, f"{location.name}.sbatch")
        command = f"./{location.name}.launch.sh --run-id $SWIRLC_RUN_ID"

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
                'echo "SWIRL Slurm job started at $(date -Iseconds)"',
                'echo "Host: $(hostname -f 2>/dev/null || hostname)"',
                'echo "Working directory: $(pwd)"',
                'echo "Run id: ${SWIRLC_RUN_ID:-<unset>}"',
                'echo "Python: $(command -v python3)"',
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
            self._write_runtime_bundle(loc)
            if loc.connection_type == "slurm":
                self._write_slurm_script(loc)

        def copy_commands(location: Location) -> list[str]:
            filenames = [
                f"{location.name}.py",
                f"{location.name}.launch.sh",
                f"{location.name}.requirements.txt",
            ]
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

        prepare_commands = _parallel_shell_block(
            [
                command
                for loc in workflow.locations.values()
                if (command := loc.get_prepare_command())
            ]
        )
        copy_traces = _parallel_shell_block(
            [
                command
                for loc in workflow.locations.values()
                for command in copy_commands(loc)
            ]
        )
        setup_runtimes = _parallel_shell_block(
            [
                loc.get_setup_command(f"./{loc.name}.launch.sh --prepare")
                for loc in workflow.locations.values()
            ]
        )
        fetch_addresses = "\n".join(
            [
                f"{command} >/dev/null 2>&1 || true"
                for loc in workflow.locations.values()
                if (command := fetch_address_command(loc))
            ]
        )
        copy_address_book = _parallel_shell_block(
            [
                command
                for loc in workflow.locations.values()
                if (command := copy_address_book_command(loc))
            ]
        )
        address_files = " ".join(
            [f"{loc.name}_address.json" for loc in workflow.locations.values()]
        )
        location_command = "./{name}.launch.sh --run-id $SWIRLC_RUN_ID"
        commands = _start_background_shell_commands(
            [
                loc.get_command(location_command.format(name=loc.name))
                for loc in workflow.locations.values()
            ],
            "WORKFLOW_PIDS",
        )
        with open(os.path.join(self.outdir, script_name), "w") as f:
            f.write(f"""{bash_header}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

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
    running_pids=""
    for pid in $WORKFLOW_PIDS; do
        if kill -0 "$pid" 2>/dev/null; then
            running_pids="$running_pids $pid"
        else
            status=0
            wait "$pid" || status=$?
            if [ "$status" -ne 0 ]; then
                echo "Workflow startup process $pid failed with status $status"
                exit "$status"
            fi
        fi
    done
    WORKFLOW_PIDS="$running_pids"
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

# Create isolated Python environments and install any trace-specific runtime
# dependencies before starting locations or submitting Slurm jobs.
{setup_runtimes}

# Start workflow execution. Locations will publish their address file and then
# wait until this script distributes address_book.json.
echo "SWIRL run id: $SWIRLC_RUN_ID"
{commands}

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

# Every location has started once it has advertised an address and received the
# complete address book. The location processes continue independently.
echo "Workflow execution started"

for pid in $WORKFLOW_PIDS; do
    wait "$pid"
done

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
        if self.tmpdir:
            scratch_dir = f'str(Path("{self.tmpdir}").expanduser().absolute())'
        elif location.workdir:
            scratch_dir = f'str(Path("{location.workdir}").expanduser().absolute())'
        else:
            scratch_dir = "os.getcwd()"
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
SCRATCH_DIR = os.environ.get("SWIRLC_TMP_DIR", os.environ.get("SWIRLC_SCRATCH_DIR", {scratch_dir}))
os.makedirs(SCRATCH_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
""")

        if dependency_archive := self._dependency_archive_for_location(location):
            trace.write(_embedded_dependency_bootstrap(*dependency_archive))
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
        if step.expression is not None:
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
            trace.write(
                f"\n{i}_expression({step.display_name!r}, {step.expression!r}, {input_specs!r}, {output_specs!r})\n"
            )
            return

        arguments = [
            (arg.name if isinstance(arg, Port) else arg, isinstance(arg, Port))
            for arg in step.arguments
        ]
        output_specs = []
        for pn, _ in flow[1]:
            self.location_ports.add(pn)
            glob_val = step.processors[pn].glob if (step.processors and pn in step.processors) else ""
            type_val = step.processors[pn].type if (step.processors and pn in step.processors) else "string"
            output_specs.append((pn, type_val, glob_val))
        for pn, _ in flow[0]:
            self.location_ports.add(pn)

        trace.write(
            f"""\n{i}_exec({step.name!r}, {step.display_name!r}, {[pn for pn, _ in flow[0]]!r}, {output_specs!r}, {step.command!r}, {arguments!r})\n"""
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
        in_repl = False
        curr: TraceNode | None = node
        while curr:
            if getattr(curr, "is_repl", False):
                curr.repl_sources.add(src)
                in_repl = True
            curr = curr.parent
        is_gather = (self.current_location.name in ("lG", "l_gather"))
        trace.write(
            f"""{i}{node.handle} = _thread(_recv, "{port}", "{data_type}", "{src}", {is_gather})\n"""
        )
        if in_repl:
            trace.write(f"{i}_wait([{node.handle}])\n")
            trace.write(f"{i}if any(src == '{src}' for src, _ in _eof_ports):\n")
            trace.write(f"{i}    return\n")



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
        self.location_ports.add(port)
        i = "    " * indent
        trace.write(
            f"""{i}{node.handle} = _thread(_send, "{data}", "{port}", "{data_type}", "{src}", "{dst}")\n"""
        )

    def write_move(
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
        self.location_ports.add(port)
        i = "    " * indent
        dst_str = str(dst).strip()
        if dst_str.startswith("{") and dst_str.endswith("}"):
            workers = [x.strip() for x in dst_str.strip("{}").split(",") if x.strip()]
            trace.write(f"{i}_workers = {workers!r}\n")
            trace.write(
                f"""{i}{node.handle} = _thread(_send, "{data}", "{port}", "{data_type}", "{src}", _workers[_worker_idx[0] % len(_workers)])\n"""
                f"""{i}_wait([{node.handle}])\n"""
                f"""{i}_worker_idx[0] += 1\n"""
            )
        else:
            trace.write(
                f"""{i}{node.handle} = _thread(_send, "{data}", "{port}", "{data_type}", "{src}", "{dst}")\n"""
            )



    def write_choice_start(self, node: TraceNode, indent: int, trace: TextIO):
        if node.depth == 0:
            return
        i = "    " * indent
        trace.write(f"\n{i}def {node.id}():\n")

    def write_choice_alt(self, node: TraceNode, indent: int, trace: TextIO):
        pass

    def write_choice_end(self, node: TraceNode, indent: int, trace: TextIO):
        if node.depth == 0:
            return
        i = "    " * indent
        trace.write(f"{i}{node.handle} = _thread({node.id})\n")

    def write_repl_start(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        param: str | None = None,
        domain: str | None = None,
    ):
        if node.depth == 0:
            return
        i = "    " * indent
        trace.write(f"\n{i}def {node.id}():\n")
        trace.write(f"{i}    while True:\n")



    def write_repl_end(self, node: TraceNode, indent: int, trace: TextIO):
        if node.depth == 0:
            return
        i = "    " * indent
        if node.repl_sources:
            sources_check = f"any(src in {list(node.repl_sources)!r} for src, _ in _eof_ports)"
        else:
            sources_check = "_eof_ports"
        trace.write(
            f"{i}        if {sources_check} or (any(isinstance(ports.get(p), list) for p in ports) and all(len(ports[p]) == 0 for p in ports if isinstance(ports.get(p), list))):\n"
        )
        trace.write(f"{i}            break\n")
        trace.write(f"{i}{node.handle} = _thread({node.id})\n")





    def write_zero(self, node: TraceNode, indent: int, trace: TextIO):
        i = "    " * indent
        trace.write(f"{i}pass\n")


    def write_dataset(
        self, node: TraceNode, indent: int, trace: TextIO, port: str, data: Data
    ):
        assert self.current_location is not None

        self.location_ports.add(port)
        i = "    " * indent
        # repr() so both scalar strings and list values emit as valid Python literals.
        trace.write(f"""{i}_init_dataset("{port}", {data.value!r})\n""")

