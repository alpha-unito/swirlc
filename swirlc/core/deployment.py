from __future__ import annotations

import os
from collections.abc import MutableMapping
from pathlib import PurePath
from typing import Any


class Deployment:
    connection_type: str | None = None

    def __init__(
        self,
        hostname: str | None = None,
        port: str | None = None,
        workdir: str | None = None,
        username: str | None = None,
        ssh_key: str | None = None,
        check_host_key: bool | None = None,
        slurm: MutableMapping[str, Any] | None = None,
    ):
        self.hostname = hostname
        self.port = port
        self.workdir = str(PurePath(workdir)) if workdir else workdir
        self.username = username
        self.ssh_key = ssh_key
        self.check_host_key = check_host_key
        self.slurm = slurm

    def get_command(self, cmd: str, location_name: str) -> str:
        return (f"cd {self.workdir} && " if self.workdir else "") + cmd

    def get_prepare_command(self) -> str:
        return f"mkdir -p {self.workdir}" if self.workdir else ""

    def get_copy_command(self, src: str, dst: str) -> str:
        return ""

    def get_fetch_command(self, src: str, dst: str) -> str:
        return ""

    def get_bind_host(self) -> str:
        return "0.0.0.0"

    def get_advertise_command(self) -> str:
        return "hostname -f"


class SshDeployment(Deployment):
    connection_type = "ssh"

    def _ssh_destination(self) -> str:
        return (
            f"{self.username}@{self.hostname}"
            if self.username and self.hostname
            else str(self.hostname)
        )

    def _ssh_options(self) -> list[str]:
        options = []
        if self.ssh_key:
            options.extend(["-i", self.ssh_key])
        if self.check_host_key is False:
            options.extend(
                ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
            )
        return options

    def _copy_destination(self, src: str, dst: str) -> str:
        filename = os.path.basename(src)
        if self.hostname and self.workdir and filename:
            return f"{self._ssh_destination()}:{self.workdir.rstrip('/')}/{filename}"
        return dst

    def _remote_path(self, path: str) -> str:
        if self.hostname and self.workdir and not os.path.isabs(path):
            return f"{self.workdir.rstrip('/')}/{path}"
        return path

    def get_command(self, cmd: str, location_name: str) -> str:
        return " ".join(
            [
                "ssh",
                *self._ssh_options(),
                self._ssh_destination(),
                f'"cd {self.workdir} && {cmd}"',
            ]
        )

    def get_prepare_command(self) -> str:
        if not self.workdir:
            return ""
        if self.hostname and self.hostname not in ("127.0.0.1", "localhost"):
            return " ".join(
                [
                    "ssh",
                    *self._ssh_options(),
                    self._ssh_destination(),
                    f'"mkdir -p {self.workdir}"',
                ]
            )
        return ""

    def get_copy_command(self, src: str, dst: str) -> str:
        return " ".join(
            ["scp", *self._ssh_options(), src, self._copy_destination(src, dst)]
        )

    def get_fetch_command(self, src: str, dst: str) -> str:
        return " ".join(
            [
                "scp",
                *self._ssh_options(),
                f"{self._ssh_destination()}:{self._remote_path(src)}",
                dst,
            ]
        )


class DockerDeployment(Deployment):
    connection_type = "docker"

    def get_command(self, cmd: str, location_name: str) -> str:
        return " ".join(
            [
                "docker",
                "exec",
                "--workdir",
                str(self.workdir),
                str(self.hostname),
                "sh",
                "-c",
                f'"{cmd}"',
            ]
        )

    def get_copy_command(self, src: str, dst: str) -> str:
        return " ".join(["docker", "cp", src, dst])

    def get_fetch_command(self, src: str, dst: str) -> str:
        source = (
            f"{self.hostname}:{self.workdir.rstrip('/')}/{src}"
            if self.hostname and self.workdir and not os.path.isabs(src)
            else src
        )
        return " ".join(["docker", "cp", source, dst])


class SlurmDeployment(SshDeployment):
    connection_type = "slurm"

    def get_command(self, cmd: str, location_name: str) -> str:
        submit = (
            "SWIRLC_RUN_ID=$SWIRLC_RUN_ID "
            f"sbatch --export=ALL,SWIRLC_RUN_ID --wait {location_name}.sbatch"
        )
        if self.hostname and self.hostname not in ("127.0.0.1", "localhost"):
            if self.workdir:
                return " ".join(
                    [
                        "ssh",
                        *self._ssh_options(),
                        self._ssh_destination(),
                        f'"cd {self.workdir} && {submit}"',
                    ]
                )
            return " ".join(
                ["ssh", *self._ssh_options(), self._ssh_destination(), f'"{submit}"']
            )
        return (f"cd {self.workdir} && " if self.workdir else "") + submit

    def get_copy_command(self, src: str, dst: str) -> str:
        if self.hostname and self.hostname not in ("127.0.0.1", "localhost"):
            return super().get_copy_command(src, dst)
        return ""

    def get_fetch_command(self, src: str, dst: str) -> str:
        if self.hostname and self.hostname not in ("127.0.0.1", "localhost"):
            return super().get_fetch_command(src, dst)
        return ""


def make_deployment(
    connection_type: str | None = None,
    hostname: str | None = None,
    port: str | None = None,
    workdir: str | None = None,
    username: str | None = None,
    ssh_key: str | None = None,
    check_host_key: bool | None = None,
    slurm: MutableMapping[str, Any] | None = None,
) -> Deployment:
    kwargs = {
        "hostname": hostname,
        "port": port,
        "workdir": workdir,
        "username": username,
        "ssh_key": ssh_key,
        "check_host_key": check_host_key,
        "slurm": slurm,
    }
    if connection_type == "ssh":
        return SshDeployment(**kwargs)
    if connection_type == "docker":
        return DockerDeployment(**kwargs)
    if connection_type == "slurm":
        return SlurmDeployment(**kwargs)
    if connection_type is None:
        return Deployment(**kwargs)
    raise NotImplementedError(f"Connection type: {connection_type} not supported")
