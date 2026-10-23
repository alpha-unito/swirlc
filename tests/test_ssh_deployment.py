from pathlib import Path

import pytest
from ruamel.yaml import YAML

from swirlc.config.validator import SwirlValidator
from swirlc.core.deployment import SlurmDeployment, SshDeployment
from swirlc.main import main


@pytest.mark.parametrize("deployment_type", [SshDeployment, SlurmDeployment])
def test_accept_new_applies_to_all_ssh_and_scp_commands(deployment_type):
    deployment = deployment_type(
        hostname="compute", workdir="/work", check_host_key="accept-new",
    )
    commands = [
        deployment.get_prepare_command(),
        deployment.get_setup_command("./l0.launch.sh --prepare", "l0"),
        deployment.get_command("./l0.launch.sh", "l0"),
        deployment.get_copy_command("l0.py", "l0.py"),
        deployment.get_fetch_command("result.txt", "result.txt"),
    ]
    for command in commands:
        assert "-o StrictHostKeyChecking=accept-new" in command
        assert "UserKnownHostsFile=/dev/null" not in command


@pytest.mark.parametrize("version", ["v1.0", "v1.1"])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("policy", [True, False, "accept-new", "invalid"])
def test_host_key_policy_validation(version, nested, policy):
    location = {"checkHostKey": policy}
    config = {"version": version, "locations": {
        "l0": {"deployment": location} if nested else location,
    }}
    if policy == "invalid":
        with pytest.raises(Exception, match="configuration is invalid"):
            SwirlValidator().validate(config)
    else:
        assert SwirlValidator().validate(config) is config


def test_existing_host_key_options_are_preserved():
    assert SshDeployment()._ssh_options() == []
    assert SshDeployment(check_host_key=True)._ssh_options() == []
    assert SshDeployment(check_host_key=False)._ssh_options() == [
        "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
    ]


def test_accept_new_survives_translation_and_compilation(tmp_path):
    example = Path(__file__).resolve().parents[1] / "examples/cwl/basic/main.cwl"
    config = {
        "version": "v1.0",
        "workflows": {"main": {
            "type": "cwl", "config": {"file": str(example), "settings": "inputs.yml"},
            "bindings": [{"step": "/", "target": {"deployment": "remote"}}],
        }},
        "deployments": {"remote": {
            "type": "ssh", "workdir": "/work",
            "config": {"nodes": ["compute"], "checkHostKey": "accept-new"},
        }},
    }
    source = tmp_path / "streamflow.yml"
    with source.open("w") as stream:
        YAML().dump(config, stream)
    assert main(["translate", "--language", "cwl", str(source),
                 "--outdir", str(tmp_path)]) == 0
    assert main(["compile", str(tmp_path / "workflow.swirl"),
                 str(tmp_path / "metadata.yml"), "--outdir", str(tmp_path)]) == 0
    assert "-o StrictHostKeyChecking=accept-new" in (tmp_path / "run.sh").read_text()
