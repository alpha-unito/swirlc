from __future__ import annotations

import io
import tempfile
import textwrap
import unittest
from pathlib import Path

from ruamel.yaml import YAML

from swirlc.main import main
from swirlc.translator.cwl.cwl_translator import CWLTranslator


class SlurmDeploymentTests(unittest.TestCase):
    def test_cwl_translation_keeps_slurm_deployment_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tool.cwl").write_text(textwrap.dedent("""\
                    cwlVersion: v1.2
                    class: CommandLineTool
                    baseCommand: echo
                    inputs:
                      message:
                        type: string
                        inputBinding:
                          position: 1
                    outputs:
                      out:
                        type: string
                        outputBinding:
                          glob: stdout.txt
                          loadContents: true
                    stdout: stdout.txt
                    """))
            (root / "workflow.cwl").write_text(textwrap.dedent("""\
                    cwlVersion: v1.2
                    class: Workflow
                    inputs:
                      message: string
                    outputs:
                      result:
                        type: string
                        outputSource: compute/out
                    steps:
                      compute:
                        run: tool.cwl
                        in:
                          message: message
                        out: [out]
                    """))
            (root / "job.yml").write_text("message: hello\n")
            (root / "streamflow.yml").write_text(textwrap.dedent("""\
                    version: v1.0
                    workflows:
                      master:
                        type: cwl
                        config:
                          file: workflow.cwl
                          settings: job.yml
                          docker:
                            - step: /
                              deployment:
                                type: none
                                config: {}
                        bindings:
                          - step: /
                            target:
                              deployment: local
                          - step: /compute
                            target:
                              deployment: batch
                              service: broadwell
                    deployments:
                      local:
                        type: local
                        workdir: /tmp/local
                      login:
                        type: ssh
                        config:
                          nodes: [login.example.org]
                        workdir: /remote/login
                      batch:
                        type: slurm
                        wraps: login
                        workdir: /remote/batch
                        config:
                          maxConcurrentJobs: 4
                          services:
                            broadwell:
                              partition: broadwell
                      ignored-wrapper:
                        type: docker
                        workdir: /container
                    """))

            workflow_output = io.StringIO()
            metadata_output = io.StringIO()
            CWLTranslator(root / "streamflow.yml").translate(
                workflow_output, metadata_output
            )
            metadata = YAML(typ="safe").load(metadata_output.getvalue())

            slurm_locations = [
                location
                for location in metadata["locations"].values()
                if location.get("connectionType") == "slurm"
            ]
            self.assertEqual(2, len(metadata["locations"]))
            self.assertEqual(1, len(slurm_locations))
            self.assertEqual("login.example.org", slurm_locations[0]["hostname"])
            self.assertEqual("/remote/batch", slurm_locations[0]["workdir"])
            self.assertEqual(
                {
                    "service": "broadwell",
                    "options": {"partition": "broadwell"},
                },
                slurm_locations[0]["slurm"],
            )
            self.assertNotIn(
                "docker",
                {
                    location.get("connectionType")
                    for location in metadata["locations"].values()
                },
            )
            self.assertNotIn(
                "ssh",
                {
                    location.get("connectionType")
                    for location in metadata["locations"].values()
                },
            )

    def test_compile_default_target_deploys_slurm_location_with_sbatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "workflow.swirl").write_text(
                "<l0, {(p0,d0)}, exec(s0,{(p0,d0)}->{}, {l0})>\n"
            )
            (root / "metadata.yml").write_text(textwrap.dedent("""\
                    version: v1.0
                    steps:
                      s0:
                        displayName: Echo
                        command: echo
                        arguments:
                          - valueFrom: p0
                    locations:
                      l0:
                        hostname: login.example.org
                        port: 35050
                        connectionType: slurm
                        workdir: /remote/batch
                        slurm:
                          service: broadwell
                          options:
                            partition: broadwell
                    dependencies:
                      d0:
                        type: string
                        value: hello
                    """))

            self.assertEqual(
                0,
                main(
                    [
                        "compile",
                        str(root / "workflow.swirl"),
                        str(root / "metadata.yml"),
                        "--outdir",
                        tmp,
                    ]
                ),
            )

            sbatch = (root / "l0.sbatch").read_text()
            self.assertIn("#SBATCH --job-name=swirl-l0", sbatch)
            self.assertIn("#SBATCH --partition=broadwell", sbatch)
            self.assertIn("python l0.py", sbatch)

            runner = (root / "run.sh").read_text()
            self.assertIn("scp l0.sbatch login.example.org:/remote/batch", runner)
            self.assertIn(
                'ssh login.example.org "cd /remote/batch && sbatch --wait l0.sbatch"',
                runner,
            )


if __name__ == "__main__":
    unittest.main()
