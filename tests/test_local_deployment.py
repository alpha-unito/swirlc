import subprocess

import pytest

from swirlc.core.deployment import make_deployment


def test_local_address_does_not_require_hostname_lookup(tmp_path):
    deployment = make_deployment()
    # No hostname executable is available, as when local name resolution fails.
    host = subprocess.check_output(
        deployment.get_advertise_command(),
        shell=True,
        env={"PATH": str(tmp_path)},
        text=True,
    ).strip()
    assert host == "127.0.0.1"


@pytest.mark.parametrize("connection_type", ["ssh", "docker", "slurm"])
def test_remote_deployments_keep_network_address_discovery(connection_type):
    deployment = make_deployment(connection_type=connection_type)
    assert deployment.get_advertise_command() == "hostname -f"
