from __future__ import annotations

import contextlib
import os
import pathlib
import re
import shutil
import signal
import socket
import subprocess
import tempfile
from collections.abc import MutableSequence

from ruamel.yaml import YAML

from swirlc.main import main

_EXAMPLES_PATH = pathlib.Path(__file__).parent.parent / "examples"


@contextlib.contextmanager
def sockets_contextmanager():
    sockets: list[socket.socket] = []
    try:
        yield sockets
    finally:
        for sock in sockets:
            sock.close()


def _reserve_port(reserved_sockets: MutableSequence[socket.socket]) -> int:
    """Helper to bind a socket, keep it open, and return the port."""
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(("", 0))
    reserved_sockets.append(tcp)
    return tcp.getsockname()[1]


def _compile(trace_file: str, config_file: str, outdir: str | None = None) -> None:
    with contextlib.ExitStack() as stack:
        if outdir is None:
            outdir = stack.enter_context(tempfile.TemporaryDirectory())
        assert main(["compile", trace_file, config_file, "--outdir", outdir]) == 0


def _compile_and_run(
    example_name: str,
    trace_filename: str,
    expected_generated_files: MutableSequence[str],
    expected_stdout: str | None = None,
    expected_stderr_patterns: MutableSequence[str] | None = None,
    extra_files_to_copy: MutableSequence[str] | None = None,
    timeout: int = 15,
) -> None:
    example_dir = _EXAMPLES_PATH / example_name

    with tempfile.TemporaryDirectory() as workdir:
        config_file = os.path.join(workdir, "config.yml")

        with sockets_contextmanager() as reserved_sockets:
            _update_config_metadata(
                src_path=str(example_dir / "config.yml"),
                dst_path=config_file,
                reserved_sockets=reserved_sockets,
            )

            _compile(
                trace_file=str(example_dir / trace_filename),
                config_file=config_file,
                outdir=workdir,
            )
            for file in expected_generated_files:
                assert os.path.exists(
                    os.path.join(workdir, file)
                ), f"File '{file}' was not generated during compilation."
            if extra_files_to_copy:
                for file in extra_files_to_copy:
                    shutil.copyfile(
                        str(example_dir / file),
                        os.path.join(workdir, file),
                    )
        process = subprocess.Popen(
            ["./run.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=workdir,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"The compiled program timed out (SIGINT sent). stdout: {stdout}\nstderr: {stderr}"
            )

        assert process.returncode == 0, f"Program crashed! Stderr: {stderr}"
        if expected_stdout is not None:
            assert (
                stdout.strip() == expected_stdout
            ), f"Missing expected output. \n\nFull stdout was:\n{stdout}"
        if expected_stderr_patterns:
            for pattern in expected_stderr_patterns:
                formatted_pattern = pattern.replace("{workdir}", workdir)
                match = re.search(formatted_pattern, stderr)
                assert (
                    match
                ), f"Missing expected log: '{formatted_pattern}'\n\nFull stderr was:\n{stderr}"


def _update_config_metadata(
    src_path: str, dst_path: str, reserved_sockets: MutableSequence[socket.socket]
) -> None:
    """
    Copy the metadata from the source to a new working directory.
    In the copied metadata, an available port is assigned to each location.

    Important: The caller is responsible for iterating through `reserved_sockets`
    and closing them to free the ports once the setup is complete.
    """
    with open(src_path) as f:
        yaml = YAML(typ="safe")
        config_data = yaml.load(f)

    for _, settings in config_data["locations"].items():
        settings["port"] = _reserve_port(reserved_sockets)

    assert not os.path.exists(dst_path), f"Destination path {dst_path} already exists"

    with open(dst_path, "w") as f:
        yaml.dump(config_data, f)


def test_example1() -> None:
    _compile(
        str(_EXAMPLES_PATH / "example1" / "example1.swirl"),
        str(_EXAMPLES_PATH / "example1" / "config.yml"),
    )


def test_example2() -> None:
    _compile_and_run(
        example_name="example2",
        trace_filename="example2.swirl",
        expected_generated_files=["run.sh", "ld.py", "l1.py", "l2.py"],
        extra_files_to_copy=["world.txt"],
        expected_stdout="Workflow execution terminated",
        expected_stderr_patterns=[
            r"Step FirstStep-s1 result file: '{workdir}/.*/hello\.txt'",
            r"Step SecondStep-s2 has not an output port\. Result: 'Hello'",
            r"Step ThirdStep-s3 has not an output port\. Result: 'Hello'",
        ],
    )
