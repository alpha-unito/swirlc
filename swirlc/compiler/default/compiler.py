from __future__ import annotations

import base64
import hashlib
import io
import os
import pprint
import shlex
import stat
import sys
import zipfile
from importlib import metadata
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from swirlc.compiler.default.values import value_helpers
from swirlc.compiler.standard.compiler import StructuredCompiler
from swirlc.core.entity import Location
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
Js2Py==0.74; python_version < "3.11"
Js2Py-3.14==0.74.2; python_version >= "3.11"
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
        temporary_path = archive_path.with_suffix(f".{{os.getpid()}}.tmp")
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
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

from pathlib import Path
from io import BytesIO
from threading import Condition, Event, RLock, Thread
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

expression_function = r"""_javascript_lock = RLock()


def _expression_value(value: Any, data_type: str) -> Any:
    if value is None:
        return None
    inner = _list_inner(data_type)
    if inner is not None:
        return [_expression_value(item, inner) for item in value]
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
    if isinstance(value, dict):
        return value
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
    if getattr(getattr(value, "_obj", None), "Class", None) == "Array":
        value = value.to_list()
    elif hasattr(value, "to_dict"):
        value = value.to_dict()
    elif hasattr(value, "to_list"):
        value = value.to_list()
    if isinstance(value, dict):
        return {str(key): _to_python(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_python(item) for item in value]
    return value


def _run_javascript_expression(source: str, bindings: MutableMapping[str, Any]) -> Any:
    try:
        import js2py
    except ImportError:
        # Python 3.14 distribution retains the same API under a separate name.
        import js2py_ as js2py
    names = list(bindings)
    if any(not re.fullmatch(r"[A-Za-z_$][\w$]*", name) for name in names):
        raise ValueError("Invalid JavaScript binding name")
    invocation = ("(function(" + ",".join(names) + ") {\n" + source
                  + "\n})(" + ",".join(json.dumps(bindings[name]) for name in names) + ");")
    # Js2Py code generation shares mutable translator state across contexts.
    with _javascript_lock:
        js2py.disable_pyimport()
        invocation = '''
if (!String.prototype.includes) String.prototype.includes = function(search, start) {
    if (search instanceof RegExp) throw new TypeError('RegExp is not a string');
    return this.indexOf(String(search), start || 0) !== -1;
};
if (!Number.isInteger) Number.isInteger = function(value) {
    return typeof value === 'number' && isFinite(value) && Math.floor(value) === value;
};
if (!Array.prototype.flat) Array.prototype.flat = function(depth) {
    depth = depth === undefined ? 1 : Math.max(0, Math.floor(Number(depth) || 0));
    var result = [];
    function append(array, remaining) {
        for (var i = 0; i < array.length; i++) if (i in array) {
            if (Array.isArray(array[i]) && remaining > 0) append(array[i], remaining - 1);
            else result.push(array[i]);
        }
    }
    append(this, depth);
    return result;
};
''' + invocation
        return _to_python(js2py.eval_js(invocation))


def _coerce_expression_output(value: Any, data_type: str) -> Any:
    if value is None:
        return value
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
    if data_type in ("file", "directory") and isinstance(value, dict):
        return value["path"]
    return value

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
    return _send_structured(sock, value.decode("utf-8") if isinstance(value, bytes) else value, data_type)


def _recv_value(sock: socket.socket, data_type: str) -> Any:
    \"\"\"Inverse of _send_value: rebuild a value from the framed socket stream.\"\"\"
    return _recv_structured(sock)

"""

exec_function = """def _flatten_args(val: Any) -> list[Any]:
    if isinstance(val, (list, tuple)):
        flat = []
        for item in val:
            flat.extend(_flatten_args(item))
        return flat
    return [val]


def _exec(step_name: str, step_display_name: str, input_port_names: MutableSequence[str], output_specs: MutableSequence[tuple[str, str, str | None]], cmd: str, args: MutableSequence[tuple[str,bool]], scatter_info: dict | None = None):
    for port_name in input_port_names:
        available_port_data[port_name].wait()

    def _quote_arg(value: Any) -> str:
        return shlex.quote(str(value))

    scatter_ports = scatter_info.get("scatter_ports", []) if scatter_info else []
    if scatter_ports:
        scatter_in_ports = [
            p for p in input_port_names
            if p in scatter_ports or any(p.endswith(f"_{s}") or p == s for s in scatter_ports)
        ]
        if not scatter_in_ports:
            scatter_in_ports = [input_port_names[0]]

        port_items = []
        for in_p in scatter_in_ports:
            val = ports[in_p]
            port_items.append(list(val) if isinstance(val, (list, tuple)) else [val])

        import itertools
        scatter_method = scatter_info.get("scatter_method", "dotproduct") or "dotproduct"
        if scatter_method == "flat_crossproduct":
            combos = list(itertools.product(*port_items)) if port_items else []
        else:
            cnt = min(len(it) for it in port_items) if port_items else 0
            combos = [tuple(port_items[p_idx][idx] for p_idx in range(len(port_items))) for idx in range(cnt)]

        base_workdir = os.path.join(SCRATCH_DIR, f"exec_{step_name}_{uuid.uuid4()}")
        os.makedirs(base_workdir, exist_ok=True)
        all_outputs = {op_name: [] for op_name, _, _ in output_specs}

        for combo_idx, combo in enumerate(combos):
            iter_workdir = os.path.join(base_workdir, f"iter_{combo_idx}")
            os.makedirs(iter_workdir, exist_ok=True)
            iter_ports = dict(ports)
            for sp, sval in zip(scatter_in_ports, combo):
                iter_ports[sp] = sval

            for port_name in input_port_names:
                value = iter_ports[port_name]
                flat_elems = _flatten_args(value)
                for idx, elem in enumerate(flat_elems):
                    if not elem or not isinstance(elem, (str, bytes, os.PathLike)):
                        continue
                    elem_path = os.fspath(elem)
                    if not os.path.exists(elem_path):
                        continue
                    target_name = os.path.basename(os.path.normpath(elem_path))
                    if not target_name:
                        continue
                    dest_name = target_name
                    dest_path = os.path.join(iter_workdir, dest_name)
                    if os.path.lexists(dest_path):
                        dest_path = os.path.join(iter_workdir, f"{idx}_{target_name}")
                    try:
                        os.symlink(os.path.abspath(elem_path), dest_path)
                    except FileExistsError:
                        pass

            cmd_parts = [cmd]
            for elem, is_data in args:
                if is_data:
                    val = iter_ports[elem]
                    if isinstance(val, (list, tuple)):
                        cmd_parts.append(" ".join(_quote_arg(v) for v in _flatten_args(val)))
                    else:
                        cmd_parts.append(_quote_arg(val))
                else:
                    cmd_parts.append(elem)
            iter_cmd = " ".join(cmd_parts)
            non_glob_outputs = [
                g_regex for _, d_type, g_regex in output_specs
                if g_regex and not any(c in g_regex for c in "*?[]") and d_type in ("string", "int", "bool", "file")
            ]
            if len(non_glob_outputs) == 1 and not (">" in iter_cmd or "|" in iter_cmd) and non_glob_outputs[0] not in iter_cmd:
                iter_cmd = f"{iter_cmd} > {shlex.quote(non_glob_outputs[0])}"

            if logger.isEnabledFor(logging.INFO):
                logger.info(f"Step {step_display_name}-{step_name}[iter {combo_idx}] executes '{iter_cmd}'")
            res_proc = _run_command(iter_cmd, cwd=iter_workdir)
            if res_proc.returncode != 0:
                raise Exception(f"Step {step_display_name}-{step_name}[iter {combo_idx}] failed with exit status {res_proc.returncode}: {res_proc.stderr.decode('utf-8')}")

            for output_port_name, data_type, glob_regex in output_specs:
                matched = [path for path in glob.glob(os.path.join(iter_workdir, glob_regex or "*"))]
                if data_type in ("file", "directory"):
                    if len(matched) == 0:
                        raise FileNotFoundError(f"Step {step_display_name}-{step_name} produced no file matching: {glob_regex}")
                    elif len(matched) == 1:
                        all_outputs[output_port_name].append(os.path.join(iter_workdir, matched[0]))
                    else:
                        all_outputs[output_port_name].append([os.path.join(iter_workdir, r) for r in matched])
                elif data_type in ("string", "int", "bool"):
                    if glob_regex and matched:
                        with open(matched[0]) as fd:
                            val_str = fd.read().strip()
                    else:
                        val_str = res_proc.stdout.decode().strip()
                    if data_type == "int":
                        val = int(val_str) if val_str else 0
                    elif data_type == "bool":
                        val = val_str.lower() in ("1", "true", "yes", "on")
                    else:
                        val = val_str
                    all_outputs[output_port_name].append(val)
                else:
                    all_outputs[output_port_name].append(matched[0] if matched else "")

        for output_port_name, _, _ in output_specs:
            ports[output_port_name] = all_outputs[output_port_name]
            available_port_data[output_port_name].set()
            if logger.isEnabledFor(logging.INFO):
                logger.info(f"Step {step_display_name}-{step_name} scattered outputs ({len(ports[output_port_name])}): {ports[output_port_name]}")
        return

    workdir = os.path.join(SCRATCH_DIR, f"exec_{step_name}_{uuid.uuid4()}")
    os.makedirs(workdir, exist_ok=True)

    for port_name in input_port_names:
        value = ports[port_name]
        flat_elems = _flatten_args(value)
        for idx, elem in enumerate(flat_elems):
            if not elem or not isinstance(elem, (str, bytes, os.PathLike)):
                continue
            elem_path = os.fspath(elem)
            if not os.path.exists(elem_path):
                continue
            target_name = os.path.basename(os.path.normpath(elem_path))
            if not target_name:
                continue
            dest_name = target_name
            dest_path = os.path.join(workdir, dest_name)
            if os.path.lexists(dest_path):
                dest_path = os.path.join(workdir, f"{idx}_{target_name}")
            try:
                os.symlink(os.path.abspath(elem_path), dest_path)
            except FileExistsError:
                pass

    cmd_parts = [cmd]
    for elem, is_data in args:
        if is_data:
            val = ports[elem]
            if isinstance(val, (list, tuple)):
                cmd_parts.append(" ".join(_quote_arg(v) for v in _flatten_args(val)))
            else:
                cmd_parts.append(_quote_arg(val))
        else:
            cmd_parts.append(elem)
    cmd = " ".join(cmd_parts)
    non_glob_outputs = [
        g_regex for _, d_type, g_regex in output_specs
        if g_regex and not any(c in g_regex for c in "*?[]") and d_type in ("string", "int", "bool", "file")
    ]
    if len(non_glob_outputs) == 1 and not (">" in cmd or "|" in cmd) and non_glob_outputs[0] not in cmd:
        cmd = f"{cmd} > {shlex.quote(non_glob_outputs[0])}"

    if logger.isEnabledFor(logging.INFO):
        logger.info(f"Step {step_display_name}-{step_name} executes command '{cmd}'")
    result = _run_command(cmd, cwd=workdir)
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

choice_helpers = """def _has_data(port: str) -> bool:
    if port not in ports:
        return False
    val = ports[port]
    if isinstance(val, (list, tuple)):
        return len(val) > 0
    return val is not None and val != ""


def _peek_is_eof(src: str, port: str) -> bool:
    if (src, port) in _eof_ports:
        return True
    with condition:
        while not connections.setdefault(src, {}).get(port):
            if stopping:
                return True
            condition.wait()
        conn, is_eof = connections[src][port][0]
        return is_eof
"""

scatter_special_helpers = """def _scatter_pair(step_name: str, step_display_name: str, input_ports: list[str], output_specs: list[tuple[str, str, str]], scatter_method: str = "dotproduct", scatter_ports: list[str] | None = None):
    for in_p in input_ports:
        available_port_data[in_p].wait()

    workdir = tempfile.mkdtemp(prefix=f"scatter_pair_{step_name}_", dir=SCRATCH_DIR)
    tuple_dir = os.path.join(workdir, "tuples")
    id_dir = os.path.join(workdir, "ids")
    os.makedirs(tuple_dir, exist_ok=True)
    os.makedirs(id_dir, exist_ok=True)

    if scatter_ports:
        scatter_in_ports = [p for p in input_ports if p in scatter_ports]
    else:
        scatter_in_ports = list(input_ports)

    port_items = []
    for in_p in scatter_in_ports:
        val = ports[in_p]
        if isinstance(val, (list, tuple)):
            items = list(val)
        elif isinstance(val, str) and (val.endswith(".zip") or zipfile.is_zipfile(val)):
            with zipfile.ZipFile(val, "r") as z:
                names = sorted([n for n in z.namelist() if not n.endswith("/")])
                extracted = []
                ext_dir = os.path.join(workdir, f"ext_{in_p}")
                os.makedirs(ext_dir, exist_ok=True)
                for n in names:
                    z.extract(n, ext_dir)
                    extracted.append(os.path.join(ext_dir, n))
                items = extracted
        elif isinstance(val, str) and os.path.isdir(val):
            items = [os.path.join(val, f) for f in sorted(os.listdir(val))]
        elif isinstance(val, str) and os.path.isfile(val):
            items = [val]
        else:
            items = [val]
        port_items.append(items)

    import itertools
    if scatter_method in ("flat_crossproduct", "nested_crossproduct"):
        coordinates = list(itertools.product(*(range(len(items)) for items in port_items))) if port_items else []
    else:
        if port_items and len({len(items) for items in port_items}) != 1:
            raise ValueError("dotproduct scatter inputs must have equal lengths")
        count = len(port_items[0]) if port_items else 0
        coordinates = [(idx,) * len(port_items) for idx in range(count)]

    combinations = [
        tuple(port_items[p_idx][coordinate] for p_idx, coordinate in enumerate(task_coordinates))
        for task_coordinates in coordinates
    ]

    id_list = []
    tuple_list = []

    for idx, (combo, task_coordinates) in enumerate(zip(combinations, coordinates)):
        id_file = os.path.join(id_dir, f"id_{idx:02d}.txt")
        with open(id_file, "w", encoding="utf-8") as f:
            f.write(f"{idx}\\n")
        id_list.append(id_file)

        components = []
        for p_name in input_ports:
            if p_name in scatter_in_ports:
                item_val = combo[scatter_in_ports.index(p_name)]
            else:
                item_val = ports[p_name]

            if isinstance(item_val, str) and os.path.isfile(item_val):
                with open(item_val, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                basename = os.path.basename(item_val)
                components.append({
                    "port": p_name,
                    "name": basename,
                    "content": content,
                    "path": item_val,
                    "value": item_val,
                })
            elif isinstance(item_val, (list, tuple)):
                components.append({
                    "port": p_name,
                    "name": p_name,
                    "value": list(item_val),
                    "content": json.dumps(item_val),
                })
            else:
                components.append({
                    "port": p_name,
                    "name": p_name,
                    "value": item_val,
                    "content": str(item_val),
                })

        tuple_payload = {
            "id": idx,
            "coordinates": list(task_coordinates),
            "components": components,
        }
        for c_idx, c in enumerate(components):
            tuple_payload[f"content_{chr(ord('a') + c_idx)}"] = c.get("content", "")
            tuple_payload[f"name_{chr(ord('a') + c_idx)}"] = c["name"]

        tuple_file = os.path.join(tuple_dir, f"tuple_{idx:02d}.json")
        with open(tuple_file, "w", encoding="utf-8") as f:
            json.dump(tuple_payload, f, indent=2)
        tuple_list.append(tuple_file)

    for out_p, d_type, g_regex in output_specs:
        if "id" in out_p.lower():
            ports[out_p] = id_list
        else:
            ports[out_p] = tuple_list
        available_port_data[out_p].set()
        if logger.isEnabledFor(logging.INFO):
            logger.info(f"Special scatter pairer {step_display_name}-{step_name} produced {len(ports[out_p])} items for {out_p}")


def _scatter_open(step_name: str, step_display_name: str, input_ports: list[str], output_specs: list[tuple[str, str, str]]):
    in_p = input_ports[0]
    available_port_data[in_p].wait()
    tuple_file = ports[in_p]

    with open(tuple_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    components = data.get("components", [])

    workdir = tempfile.mkdtemp(prefix=f"scatter_open_{step_name}_", dir=SCRATCH_DIR)
    for idx, (out_p, d_type, g_regex) in enumerate(output_specs):
        if "open_id" in out_p:
            ports[out_p] = str(data["id"])
            available_port_data[out_p].set()
            continue
        component_index = idx - sum("open_id" in spec[0] for spec in output_specs[:idx])
        comp = components[component_index] if component_index < len(components) else {}
        val = comp.get("value")
        if d_type == "file" and comp.get("path") and os.path.isfile(comp.get("path")):
            ports[out_p] = comp["path"]
        elif d_type.startswith("list[") or isinstance(val, (list, dict, int, bool)):
            ports[out_p] = val
        elif "content" in comp and comp["content"]:
            filename = g_regex or comp.get("name") or f"component_{idx}.txt"
            out_path = os.path.join(workdir, os.path.basename(filename))
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(comp["content"])
            ports[out_p] = out_path
        elif val is not None:
            ports[out_p] = val
        else:
            filename = g_regex or comp.get("name") or f"component_{idx}.txt"
            out_path = os.path.join(workdir, os.path.basename(filename))
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("")
            ports[out_p] = out_path
        available_port_data[out_p].set()
        if logger.isEnabledFor(logging.INFO):
            logger.info(f"Special scatter open {step_display_name}-{step_name} unpacked {out_p} -> {ports[out_p]}")


def _scatter_gather(step_name: str, step_display_name: str, input_ports: list[str], output_specs: list[tuple[str, str, str]]):
    def _extract_id(item: Any) -> int:
        if isinstance(item, (list, tuple)) and item:
            return _extract_id(item[0])
        s = str(item)
        m = re.search(r"Item\\s+(\\d+)", s, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.search(r"(\\d+)", os.path.basename(s) if "/" in s else s)
        if m:
            return int(m.group(1))
        if isinstance(item, str) and os.path.isfile(item):
            try:
                with open(item, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(1024)
                    m = re.search(r"Item\\s+(\\d+)", content, re.IGNORECASE)
                    if m:
                        return int(m.group(1))
                    m = re.search(r"(\\d+)", content)
                    if m:
                        return int(m.group(1))
            except Exception:
                pass
        return 999999

    for idx, (out_p, d_type, g_regex) in enumerate(output_specs):
        in_p = input_ports[idx] if idx < len(input_ports) else input_ports[0]
        available_port_data[in_p].wait()
        results = ports.get(in_p, [])
        if not isinstance(results, list):
            results = [results] if results else []

        try:
            sorted_results = sorted(results, key=_extract_id)
        except Exception:
            sorted_results = results

        ports[out_p] = sorted_results
        available_port_data[out_p].set()
        if logger.isEnabledFor(logging.INFO):
            logger.info(f"Special scatter gather {step_display_name}-{step_name} gathered {len(sorted_results)} elements to port {out_p}: {sorted_results}")
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
        logger.debug(
            f"Sent {'EOF' if is_eof else 'data'} for port {port} to location {dst}"
        )
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
        with condition:
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

command_tool_function = r'''def _resolve_bindings(specifications, bound, context=None, input_types=None):
    context = context or {}
    def resolve(spec):
        if "value" in spec:
            return spec["value"]
        if "items" in spec:
            return [resolve(item) for item in spec["items"]]
        if "object" in spec:
            return {name: resolve(value) for name, value in spec["object"].items()}
        if "port" in spec:
            value = _expression_value(bound[spec["port"]], input_types[spec["port"]]["type"])
            return value[spec["field"]] if "field" in spec else value
        if "context" in spec:
            return context[spec["context"]]
        raise ValueError("Unsupported expression binding")
    return {name: resolve(spec) for name, spec in specifications.items()}


def _evaluate_expression(expression, bindings):
    if expression.get("language") != "javascript":
        raise ValueError(f"Unsupported expression language: {expression.get('language')!r}")
    try:
        return _run_javascript_expression(expression["source"], bindings)
    except Exception as exc:
        raise ValueError(f"Invalid JavaScript expression: {exc}") from exc


def _evaluate_value(value, bindings, bound, context=None, input_types=None):
    if not isinstance(value, dict) or "language" not in value:
        return value
    variables = dict(bindings)
    variables.update(_resolve_bindings(value.get("bindings", {}), bound, context, input_types))
    return _evaluate_expression(value, variables)


def _evaluate_condition(descriptor, bound):
    bindings = _resolve_bindings(descriptor.get("bindings", {}), bound, input_types=descriptor["inputs"])
    return _evaluate_value(descriptor["expression"], bindings, bound, input_types=descriptor["inputs"])


def _execute_command(tool, descriptor, bound):
    """Execute a bound command with explicit expression and output descriptors."""
    workdir = os.path.join(SCRATCH_DIR, f"exec_{tool}_{uuid.uuid4()}")
    os.makedirs(workdir, exist_ok=True)
    bound = {port: _stage_value(value, workdir, allow_collisions=True) for port, value in bound.items()}
    bindings = _resolve_bindings(descriptor.get("bindings", {}), bound, input_types=descriptor.get("inputs", {}))
    bindings["runtime"] = {"outdir": workdir, "tmpdir": workdir}
    bindings["inputs"] = _stage_value(bindings.get("inputs", {}), workdir, allow_collisions=True)
    for entry in descriptor.get("staging", []):
        value = _evaluate_value(entry["entry"], bindings, bound, input_types=descriptor.get("inputs", {}))
        name = entry.get("name")
        if name is not None:
            name = _evaluate_value(name, bindings, bound, input_types=descriptor.get("inputs", {}))
            destination = os.path.abspath(os.path.join(workdir, name))
            if not isinstance(name, str) or not name or os.path.isabs(name) or os.path.commonpath([workdir, destination]) != workdir:
                raise ValueError("Staging entry escapes invocation directory")
            if isinstance(value, str):
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                with open(destination, "x", encoding="utf-8") as stream:
                    stream.write(value)
            elif isinstance(value, dict):
                _stage_value({**value, "basename": name}, workdir)
            else:
                raise TypeError("Named staging entry must be text or a File/Directory")
        else:
            _stage_value(_prepare_value(value), workdir)
    def scalar(value):
        if isinstance(value, dict):
            if value.get("class") in ("File", "Directory"):
                return value["path"]
            raise TypeError("Command arguments cannot contain arbitrary objects")
        return str(value)
    command = [descriptor["command"]]
    for arg in descriptor.get("arguments", []):
        if "expression" in arg:
            value = _evaluate_value(arg["expression"], bindings, bound, input_types=descriptor.get("inputs", {}))
        elif "valueFrom" in arg:
            value = bound[arg["valueFrom"]]
        else:
            value = arg["value"]
        if value is None or value is False:
            continue
        prefix = arg.get("prefix")
        if value is True:
            values = [] if prefix else ["true"]
        elif isinstance(value, list):
            values = [scalar(item) for item in value]
            if "itemSeparator" in arg:
                values = [arg["itemSeparator"].join(values)]
        else:
            values = [scalar(value)]
        if prefix is not None:
            if arg.get("separate", True):
                values.insert(0, prefix)
            elif values:
                values[0] = prefix + values[0]
            else:
                values = [prefix]
        quote = shlex.quote if arg.get("shellQuote", True) else str
        command.extend(quote(value) for value in values)
    cmd = " ".join(command)
    stdout = descriptor.get("stdout")
    if stdout is not None:
        stdout = _evaluate_value(stdout, bindings, bound, input_types=descriptor.get("inputs", {}))
        if not isinstance(stdout, str) or not stdout or os.path.isabs(stdout) or ".." in stdout.split("/"):
            raise ValueError(f"Invalid stdout destination: {stdout!r}")
        cmd += " > " + shlex.quote(stdout)
    logger.info("Step %s executes command %r", tool, cmd)
    result = _run_command(cmd, cwd=workdir)
    if result.returncode not in descriptor.get("acceptedExitCodes", [0]):
        raise RuntimeError(f"Step {tool} failed with exit status {result.returncode}: {result.stderr.decode('utf-8')}")
    outputs = {}
    bindings["runtime"]["exitCode"] = result.returncode
    context = {"exitCode": result.returncode, "runtime": bindings["runtime"]}
    json_path = os.path.join(workdir, "cwl.output.json")
    if descriptor.get("outputNames") is not None and os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as stream:
            mapping = json.load(stream)
        if not isinstance(mapping, dict):
            raise TypeError("cwl.output.json must contain an output mapping")
        for name, port in descriptor["outputNames"].items():
            spec = descriptor["runtimeOutputs"][port]
            schema = spec.get("schema")
            if name not in mapping and not (schema or {}).get("nullable"):
                raise ValueError(f"Missing required output {name} in cwl.output.json")
            outputs[port] = _prepare_value(mapping.get(name), schema, workdir)
            outputs[port] = _apply_value_schema(outputs[port], schema,
                lambda expression, item: _evaluate_value(expression, {**bindings, "self": item}, bound, {**context, "self": item}, descriptor.get("inputs", {})))
            outputs[port] = _apply_secondary(outputs[port], spec.get("secondaryFiles", []),
                lambda expression, item: _evaluate_value(expression, {**bindings, "self": item}, bound, {**context, "self": item}, descriptor.get("inputs", {})))
        return outputs
    for port, spec in descriptor["runtimeOutputs"].items():
        patterns = spec.get("glob")
        patterns = [] if patterns is None else patterns if isinstance(patterns, list) else [patterns]
        matched = []
        for pattern in patterns:
            resolved = _evaluate_value(pattern, bindings, bound, input_types=descriptor.get("inputs", {}))
            for glob_pattern in resolved if isinstance(resolved, list) else [resolved]:
                if not isinstance(glob_pattern, str):
                    raise TypeError("Command output glob must evaluate to a string or string array")
                absolute = os.path.abspath(os.path.join(workdir, glob_pattern))
                if os.path.commonpath([workdir, absolute]) != workdir:
                    raise ValueError("Command output glob escapes invocation directory")
                matched.extend(sorted(glob.glob(absolute)))
        matched = list(dict.fromkeys(matched))
        files = [_expression_value(path, "file") for path in matched]
        if spec.get("readContents"):
            for file in files:
                file["contents"] = _load_contents(file)
        if spec.get("evaluate") is not None:
            value = _evaluate_value(spec["evaluate"], bindings, bound, {**context, "matchedFiles": files}, descriptor.get("inputs", {}))
            def payload(item, data_type):
                inner = _list_inner(data_type)
                if inner is not None:
                    if not isinstance(item, list):
                        raise TypeError(f"Command output {port} expected {data_type}")
                    return [payload(child, inner) for child in item]
                if data_type == "file":
                    if isinstance(item, dict) and item.get("class") == "File":
                        return item["path"]
                    raise TypeError(f"Command output {port} expected a File object")
                expected = {"string": str, "int": int, "bool": bool}.get(data_type)
                if expected is None or type(item) is not expected:
                    raise TypeError(f"Command output {port} expected {data_type}, received {type(item).__name__}")
                return item
            outputs[port] = (_prepare_value(value, spec["schema"], workdir) if "schema" in spec
                             else payload(value, spec["type"]))
        elif _list_inner(spec["type"]) in ("file", "directory"):
            outputs[port] = matched
        elif spec["type"] in ("file", "directory"):
            if not matched and spec.get("schema", {}).get("nullable"):
                outputs[port] = None
                continue
            if len(matched) != 1:
                raise FileNotFoundError(f"Step {tool} output {port} expected one File, matched {len(matched)}")
            outputs[port] = matched[0]
        else:
            raise NotImplementedError(f"Step {tool} output {port}: {spec['type']} requires an explicit evaluator")
    for port, value in outputs.items():
        if "schema" in descriptor["runtimeOutputs"][port]:
            outputs[port] = _prepare_value(value, descriptor["runtimeOutputs"][port]["schema"], workdir)
        outputs[port] = _apply_value_schema(outputs[port], descriptor["runtimeOutputs"][port].get("schema"),
            lambda expression, item: _evaluate_value(expression, {**bindings, "self": item}, bound, {**context, "self": item}, descriptor.get("inputs", {})))
        outputs[port] = _apply_secondary(outputs[port], descriptor["runtimeOutputs"][port].get("secondaryFiles", []),
            lambda expression, item: _evaluate_value(expression, {**bindings, "self": item}, bound, {**context, "self": item}, descriptor.get("inputs", {})))
    return outputs
'''

preamble = "\n".join(
    [
        python_header,
        imports,
        global_vars,
        accept_function,
        file_rendezvous_helpers,
        list_helper,
        expression_function,
        value_helpers,
        choice_helpers,
        scatter_special_helpers,
        framing_helpers,
        exec_function,
        init_dataset_function,
        send_function,
        recv_function,
        thread_function,
        wait_function,
    ]
)


def _contains_expression(value):
    if isinstance(value, dict):
        return value.get("language") == "javascript" or any(_contains_expression(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_expression(item) for item in value)
    return False


class DefaultTarget(StructuredCompiler):
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
            (step.expression is not None or _contains_expression(step.metadata))
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

    def _write_runtime_bundle(self, location: Location) -> None:
        assert self.current_workflow is not None

        has_expressions = any(
            (step.expression is not None or _contains_expression(step.metadata))
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
        environment_exports = "".join(
            f"export {name}={shlex.quote(value)}\n"
            for name, value in location.environment.items()
        )
        with open(launcher_path, "w") as f:
            f.write(
                f"""#!/bin/sh
set -eu
{environment_exports}

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
        options = {key: slurm[key] for key in ("partition", "nodes", "ntasks", "time") if key in slurm}
        options.update(slurm.get("options") or {})
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
    cleanup_status=$?
    if [ "$cleanup_status" -ne 0 ]; then
        for pid in ${{WORKFLOW_PIDS:-}}; do
            kill "$pid" 2>/dev/null || true
        done
    fi
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

workflow_status=0
for pid in $WORKFLOW_PIDS; do
    wait "$pid" || workflow_status=$?
done
if [ "$workflow_status" -ne 0 ]; then
    exit "$workflow_status"
fi

echo "Workflow execution terminated"
""")

        usr_permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
        grp_permissions = stat.S_IRGRP | stat.S_IXGRP
        os.chmod(
            os.path.join(self.outdir, script_name), usr_permissions | grp_permissions
        )
        super().end_workflow()

    def render_location(self, location, dataset, root):
        import json
        runtime_source = Path(__file__).with_name("runtime.py").read_text()
        metadata = json.loads(json.dumps(self.metadata))
        for name, step in self.current_workflow.steps.items():
            metadata["steps"][name]["runtimeOutputs"] = {
                port: {**metadata["steps"][name]["outputs"][port], "type": processor.type, "glob": processor.glob,
                       "readContents": processor.read_contents, "evaluate": processor.evaluate}
                for port, processor in (step.processors or {}).items()
            }
        initial = [{"port": port, "payload": data.value,
                    "name": data.name, "type": data.type,
                    "identity": data.identity.to_dict()}
                   for port, data in dataset]
        scratch = self.tmpdir or location.workdir or self.outdir
        with Path(self.outdir, f"{location.name}.py").open("w") as trace:
            trace.write("\n".join([python_header, imports, global_vars, file_rendezvous_helpers,
                                   list_helper, expression_function, value_helpers, framing_helpers, exec_function, command_tool_function]))
            trace.write(runtime_source.replace("from __future__ import annotations", ""))
            trace.write(TERM_CONSTRUCTORS)
            trace.write(f"\nMETADATA = {pprint.pformat(metadata, sort_dicts=False)}\nINITIAL = {pprint.pformat(initial, sort_dicts=False)}\n")
            trace.write(f"LOCATION_NAME = {location.name!r}\nLOCATION_PORT = {location.port or 0}\nBIND_HOST = {location.get_bind_host()!r}\nADVERTISE_COMMAND = {location.get_advertise_command()!r}\n")
            trace.write(f"SCRATCH_DIR = os.environ.get('SWIRLC_TMP_DIR', {os.path.abspath(scratch)!r})\nOUT_DIR = {os.path.abspath(location.outdir or self.outdir)!r}\n")
            trace.write("ADDRESS_FILE = f'{LOCATION_NAME}_address.json'\nADDRESS_BOOK_FILE = 'address_book.json'\nRUN_ID = ''\n")
            if dependency_archive := self._dependency_archive_for_location(location):
                trace.write(_embedded_dependency_bootstrap(*dependency_archive))
            trace.write(_PythonEmitter().generate(root))
            trace.write(SCOPED_MAIN)


SCOPED_MAIN = r"""
ACTIVE_RUNTIME = None


def _run_command(command, cwd=None):
    import signal
    process = subprocess.Popen(command, shell=True, cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        while True:
            try:
                stdout, stderr = process.communicate(timeout=.1)
                return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                if ACTIVE_RUNTIME is not None and ACTIVE_RUNTIME.error is not None:
                    raise RuntimeError(f"Command cancelled after scoped failure: {ACTIVE_RUNTIME.error}")
    except BaseException:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
        raise


def _execute_bound(tool, inputs):
    import types
    descriptor = METADATA["steps"][tool]
    metadata_command = ("bindings" in descriptor or "inputs" in descriptor or "stdout" in descriptor
                        or any("expression" in arg for arg in descriptor.get("arguments", []))
                        or any("evaluate" in output or "readContents" in output
                               or isinstance(output.get("glob"), (dict, list))
                               for output in descriptor.get("outputs", {}).values()))
    inputs = {port: _prepare_value(_expression_value(value, descriptor.get("inputs", {}).get(port, {}).get("type", "value")), descriptor.get("inputs", {}).get(port, {}).get("schema"))
              for port, value in inputs.items()}
    bindings = _resolve_bindings(descriptor.get("bindings", descriptor.get("expression", {}).get("bindings", {})), inputs, input_types=descriptor.get("inputs", {}))
    original = dict(bindings.get("inputs", {}))
    selected = dict(original)
    for name, transform in descriptor.get("inputTransforms", {}).items():
        value = original.get(name)
        if transform.get("select"):
            non_null = [item for item in value if item is not None]
            mode = transform["select"]
            if mode == "all_non_null":
                value = non_null
            elif mode == "first_non_null":
                if not non_null:
                    raise ValueError("first_non_null requires a non-null source")
                value = non_null[0]
            elif mode == "the_only_non_null":
                if len(non_null) != 1:
                    raise ValueError("the_only_non_null requires exactly one non-null source")
                value = non_null[0]
            else:
                raise ValueError(f"Unsupported source selection {mode}")
        elif transform.get("merge") == "merge_flattened":
            value = [child for item in value for child in (item if isinstance(item, list) else [item])]
        if value is None and "default" in transform:
            value = transform["default"]
        selected[name] = value
    snapshot = {**bindings, "inputs": selected}
    transformed = dict(selected)
    for name, transform in descriptor.get("inputTransforms", {}).items():
        if "evaluate" in transform:
            transformed[name] = _evaluate_value(transform["evaluate"], {**snapshot, "self": selected.get(name)}, inputs,
                                                {"self": selected.get(name)}, descriptor.get("inputs", {}))
    # Replace named bindings after all sibling expressions saw the same snapshot.
    descriptor = dict(descriptor)
    descriptor["bindings"] = {**descriptor.get("bindings", {}), "inputs": {"value": transformed}}
    transformed = {name: _prepare_value(value)
                   for name, value in transformed.items()}
    descriptor["bindings"]["inputs"] = {"value": transformed}
    for name, schema in descriptor.get("inputSchemas", {}).items():
        transformed[name] = _apply_value_schema(transformed.get(name), schema,
            lambda expression, item: _evaluate_value(expression, {**bindings, "inputs": transformed, "self": item}, inputs, {"self": item}, descriptor.get("inputs", {})))
    for name, options in descriptor.get("inputOptions", {}).items():
        transformed[name] = _apply_secondary(transformed.get(name), options.get("secondaryFiles", []),
            lambda expression, item: _evaluate_value(expression, {**bindings, "inputs": transformed, "self": item}, inputs, {"self": item}, descriptor.get("inputs", {})))
        if options.get("readContents"):
            def load(value):
                if isinstance(value, list):
                    for child in value:
                        load(child)
                elif isinstance(value, dict) and value.get("class") == "File":
                    value["contents"] = _load_contents(value)
            load(transformed.get(name))
    if descriptor.get("prepare") is not None:
        return {descriptor["prepare"]["output"]: transformed}
    # Earlier metadata embeds guards here; new translations emit named choices.
    if descriptor.get("when") is not None:
        condition = _evaluate_value(descriptor["when"], {**bindings, "inputs": transformed, "self": None}, inputs,
                                    input_types=descriptor.get("inputs", {}))
        if type(condition) is not bool:
            raise TypeError("Step condition must evaluate to a boolean")
        if not condition:
            return {port: None for port in descriptor.get("outputs", {})}
    for name, schema in descriptor.get("inputSchemas", {}).items():
        _validate_value(transformed.get(name), schema)
    for name, binding in METADATA["steps"][tool].get("bindings", {}).get("inputs", {}).get("object", {}).items():
        if "port" in binding and name in transformed:
            inputs[binding["port"]] = transformed[name]
    scope_globals = dict(globals())
    local_ports = dict(inputs)
    events = {port: Event() for port in inputs}
    for event in events.values():
        event.set()
    for port in descriptor.get("outputs", {}):
        events[port] = Event()
    scope_globals.update(ports=local_ports, available_port_data=events)
    if descriptor.get("expression"):
        expression = {**descriptor["expression"], "bindings": {**descriptor["expression"].get("bindings", {}), **descriptor["bindings"]}}
        bindings = _resolve_bindings(descriptor.get("bindings", {}), inputs, input_types=descriptor.get("inputs", {}))
        result = _evaluate_value(expression, bindings, inputs, input_types=descriptor.get("inputs", {}))
        if not isinstance(result, dict):
            raise TypeError(f"Expression step {tool} must return an object")
        return {port: (_apply_value_schema(_prepare_value(result[name], descriptor["runtimeOutputs"][port]["schema"]),
                                         descriptor["runtimeOutputs"][port]["schema"],
                                         lambda expression, item: _evaluate_value(expression, {**bindings, "self": item}, inputs, {"self": item}, descriptor.get("inputs", {})))
                       if "schema" in descriptor["runtimeOutputs"][port]
                       else _coerce_expression_output(result[name], descriptor["runtimeOutputs"][port]["type"]))
                for name, port in expression["outputs"].items()}
    elif metadata_command:
        return _execute_command(tool, descriptor, inputs)
    else:
        fn = types.FunctionType(_exec.__code__, scope_globals)
        arguments = [(arg.get("value", arg.get("valueFrom")), "valueFrom" in arg)
                     for arg in descriptor.get("arguments", [])]
        outputs = [(port, spec["type"], spec.get("glob"))
                   for port, spec in descriptor["runtimeOutputs"].items()]
        fn(tool, descriptor["displayName"], list(inputs), outputs,
           descriptor.get("command", ""), arguments, None)
    return {port: local_ports[port] for port in descriptor.get("outputs", {})}


def main():
    global RUN_ID, ACTIVE_RUNTIME
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    RUN_ID = parser.parse_args().run_id
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((BIND_HOST, LOCATION_PORT))
    listener.listen()
    _write_address_file(listener.getsockname()[1])
    _load_address_book()
    runtime = Runtime(METADATA, LOCATION_NAME, locations, listener,
                      _send_value, _recv_value, _execute_bound, _evaluate_condition)
    ACTIVE_RUNTIME = runtime
    runtime.start()
    try:
        env = runtime.initialize(INITIAL, {})
        workflow(runtime, env)
        runtime.finish()
        with open(os.path.join(OUT_DIR, f"{LOCATION_NAME}.outputs.json"), "w") as fd:
            json.dump(runtime.values, fd)
    except BaseException as exc:
        runtime.fail(exc)
        raise
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
"""


TERM_CONSTRUCTORS = """
def literal(name):
    return {"kind": "literal", "name": name, "items": []}


def variable(name):
    return {"kind": "variable", "name": name, "items": []}


def tuple_term(*items):
    return {"kind": "tuple", "name": "", "items": list(items)}


def path(*components):
    return {"kind": "path", "name": "", "items": list(components)}


def collection(port, envelope):
    return {"kind": "collection", "name": port, "items": envelope["items"]}
"""


class _PythonEmitter:
    """Lower shared trace nodes into Python control flow at compilation time."""

    def __init__(self):
        self.lines = []
        self.counter = 0

    def _write(self, depth, text=""):
        self.lines.append("    " * depth + text)

    def _name(self, prefix):
        self.counter += 1
        return f"{prefix}_{self.counter}"

    def _term(self, term):
        if term.kind in ("literal", "variable"):
            return f"{term.kind}({term.name!r})"
        if term.kind in ("tuple", "path"):
            constructor = "tuple_term" if term.kind == "tuple" else "path"
            return f"{constructor}({', '.join(self._term(item) for item in term.items)})"
        if term.kind == "collection":
            return f"collection({term.name!r}, tuple_term({self._term(term.items[0])}, {self._term(term.items[1])}))"
        raise ValueError(f"Unsupported Python term {term}")

    @staticmethod
    def _sequence(nodes):
        result = []
        for node in nodes:
            if node.kind == "seq":
                result.extend(_PythonEmitter._sequence(node.children.values()))
            else:
                result.append(node)
        return result

    def _alternatives(self, nodes, conditions=()):
        nodes = self._sequence(nodes)
        if nodes and nodes[0].kind == "choice":
            choice = nodes[0]
            guard = choice.args.get("guard")
            result = []
            for index, branch in enumerate(choice.children.values()):
                predicates = conditions + (((guard, index == 0),) if guard else ())
                result.extend(self._alternatives([branch] + nodes[1:], predicates))
            return result
        return [(nodes, conditions)]

    def _try_action(self, node, guarded=False):
        args = node.args
        if node.kind == "recv":
            return f"runtime.try_receive(env, {args['port']!r}, {self._term(args['term'])}, {args['src']!r})"
        if node.kind in ("move", "send"):
            return f"runtime.try_{node.kind}(env, {args['port']!r}, {self._term(args['term'])}, {args['dst']!r})"
        if node.kind == "exec":
            inputs = ", ".join(f"({port!r}, {self._term(term)})" for port, term in args["inputs"])
            return f"runtime.try_execute(env, {args['tool']!r}, [{inputs}])"
        if node.kind in ("par", "repl") and guarded:
            return "True"
        if node.kind != "zero":
            raise ValueError(f"Choice/replication admission cannot begin with {node.kind}; begin with an action")
        return "True"

    def _selector(self, alternatives, depth):
        name = self._name("select")
        self._write(depth, f"def {name}(env):")
        has_named = any("id" in guard for _nodes, conditions in alternatives for guard, _expected in conditions)
        if has_named:
            self._write(depth + 1, "evaluated = {}")
            self._write(depth + 1, "def condition_value(name, scope):")
            self._write(depth + 2, "if name not in evaluated:")
            self._write(depth + 3, "evaluated[name] = runtime.condition_value(name, env, scope)")
            self._write(depth + 2, "return evaluated[name]")
        for index, (nodes, conditions) in enumerate(alternatives):
            predicates = []
            for guard, has_data in conditions:
                if "id" in guard:
                    scope = self._term(guard["scope"]) if guard.get("scope") is not None else "None"
                    predicates.append(f"condition_value({guard['id']!r}, {scope}) is {has_data!r}")
                else:
                    method = "has_data" if has_data else "exhausted"
                    predicates.append(f"runtime.{method}({guard['port']!r}, {self._term(guard['scope'])}, env)")
            if nodes:
                predicates.append(self._try_action(nodes[0], guarded=bool(conditions)))
            condition = " and ".join(predicates) or "True"
            self._write(depth + 1, f"if {condition}:")
            self._write(depth + 2, f"return {index}")
        self._write(depth + 1, "return None")
        return name

    @staticmethod
    def _terminal(nodes):
        if not nodes or nodes[0].kind not in ("send", "recv"):
            return False
        payload = nodes[0].args["term"].items[0]
        return payload.kind == "literal" and payload.name == "eof"

    def _continuation(self, nodes):
        # The admission receive has committed; a claimed move still sends.
        return nodes[1:] if nodes and nodes[0].kind == "recv" else nodes

    def _emit_nodes(self, nodes, depth):
        nodes = self._sequence(nodes)
        if not nodes:
            self._write(depth, "pass")
        for node in nodes:
            self._emit(node, depth)

    def _emit(self, node, depth):
        kind, args = node.kind, node.args
        if kind == "seq":
            self._emit_nodes(node.children.values(), depth)
        elif kind == "par":
            branches = []
            for branch in node.children.values():
                name = self._name("parallel_branch")
                self._write(depth, f"def {name}(env, owner):")
                self._emit(branch, depth + 1)
                branches.append(name)
            self._write(depth, f"runtime.parallel(env, owner, {', '.join(branches)})")
        elif kind == "repl":
            alternatives = self._alternatives(node.children.values())
            owner = self._name("replication_owner")
            self._write(depth, f"{owner} = runtime.new_owner()")
            selector = self._selector(alternatives, depth)
            branches = []
            for nodes, _conditions in alternatives:
                name = self._name("replica")
                self._write(depth, f"def {name}(env, owner):")
                self._emit_nodes(self._continuation(nodes), depth + 1)
                branches.append(name)
            self._write(depth, "try:")
            self._write(depth + 1, f"while not {owner}['closed']:")
            self._write(depth + 2, f"selected, replica_env = runtime.admit(env, {owner}, {selector})")
            self._write(depth + 2, "if selected is None:")
            self._write(depth + 3, "break")
            for index, ((nodes, _conditions), branch) in enumerate(zip(alternatives, branches, strict=True)):
                self._write(depth + 2, f"{'if' if index == 0 else 'elif'} selected == {index}:")
                if self._terminal(nodes):
                    self._write(depth + 3, f"runtime.close_owner({owner})")
                    self._write(depth + 3, f"runtime.join({owner})")
                    self._write(depth + 3, f"{branch}(replica_env, {owner})")
                else:
                    self._write(depth + 3, f"runtime.spawn({owner}, {branch}, replica_env)")
            self._write(depth, "finally:")
            self._write(depth + 1, f"runtime.join({owner})")
        elif kind == "choice":
            alternatives = self._alternatives([node])
            selector = self._selector(alternatives, depth)
            self._write(depth, f"selected, choice_env = runtime.admit(env, None, {selector})")
            self._write(depth, "env.update(choice_env)")
            for index, (nodes, _conditions) in enumerate(alternatives):
                self._write(depth, f"{'if' if index == 0 else 'elif'} selected == {index}:")
                self._emit_nodes(self._continuation(nodes), depth + 1)
        elif kind == "exec":
            self._write(depth, f"# exec {args['tool']}")
            self._write(depth, "runtime.execute_step(")
            self._write(depth + 1, f"env, {args['tool']!r},")
            for field in ("inputs", "outputs"):
                self._write(depth + 1, f"[  # {field}")
                for port, term in args[field]:
                    self._write(depth + 2, f"({port!r}, {self._term(term)}),")
                self._write(depth + 1, "],")
            self._write(depth + 1, f"mapping={args['mapping']!r},")
            self._write(depth, ")")
        elif kind == "recv":
            self._write(depth, f"runtime.recv(env, {args['port']!r}, {self._term(args['term'])}, {args['src']!r})")
        elif kind in ("send", "move"):
            self._write(depth, f"runtime.{kind}(env, {args['port']!r}, {self._term(args['term'])}, {args['data_type']!r}, {args['src']!r}, {args['dst']!r})")
        elif kind == "zero":
            self._write(depth, "pass  # zero")
        else:
            raise ValueError(f"Unsupported Python trace node {kind}")

    def generate(self, root):
        self._write(0, "")
        self._write(0, "def workflow(runtime, env, owner=None):")
        self._emit(root, 1)
        return "\n".join(self.lines) + "\n"
