import os
import tempfile
from tempfile import NamedTemporaryFile

from swirlc.core.entity import (
    Location,
    Step,
    Port,
    DistributedWorkflow,
    Workflow,
    Processor,
    Data,
)
from swirlc.core.translator import AbstractTranslator
from tests.utils.utils import get_sha1


def test_translate():
    """Test the `translate` method of the `AbstractTranslator` class."""

    class ExampleTranslator(AbstractTranslator):
        """
        Workflow model          Deployment model
              s1                    - s1 mapped on ld
              |                     - s2 mapped on l1
             p1                     - s3 mapped on l2 and l3
            /  \
           s2  s3
           |
           p2
        """

        def _translate(self) -> Workflow:
            workflow = DistributedWorkflow()

            p1 = Port("p1", "FirstPort", {"d1"})
            workflow.add_step(
                Step(
                    "s1",
                    "FirstStep",
                    "echo",
                    ["Hello"],
                    {"p1": Processor("stdout", None)},
                )
            )
            workflow.add_step(
                Step(
                    "s2",
                    "SecondStep",
                    "touch",
                    [p1],
                    {"p2": Processor("file", "Hello")},
                )
            )
            workflow.add_step(Step("s3", "ThirdStep", "echo", [p1]))

            workflow.add_output_port(workflow.steps["s1"], p1)
            workflow.add_output_port(workflow.steps["s1"], p1)
            workflow.add_input_port(workflow.steps["s2"], workflow.ports["p1"])
            workflow.add_input_port(workflow.steps["s3"], workflow.ports["p1"])
            workflow.add_output_port(
                workflow.steps["s2"], Port("p2", "SecondPort", {"d2"})
            )

            workflow.add_location(
                Location("ld", "LocationDriver", {"d": Data("d", "string", "test")})
            )
            workflow.add_location(
                Location(
                    "l1",
                    "FirstLocation",
                    {},
                    workdir=os.path.realpath(
                        os.path.join(tempfile.gettempdir(), "scratch")
                    ),
                    outdir=os.path.realpath(
                        os.path.join(tempfile.gettempdir(), "outdir")
                    ),
                )
            )
            workflow.add_location(Location("l2", "SecondLocation", {}))
            workflow.add_location(Location("l3", "ThirdLocation", {}))

            workflow.map(workflow.steps["s1"], workflow.locations["ld"])
            workflow.map(workflow.steps["s2"], workflow.locations["l1"])
            workflow.map(workflow.steps["s3"], workflow.locations["l2"])
            workflow.map(workflow.steps["s3"], workflow.locations["l3"])

            return workflow

    translator = ExampleTranslator()
    with (
        NamedTemporaryFile("w+") as workflow_fd,
        NamedTemporaryFile("w+") as metadata_fd,
    ):
        translator.translate(workflow_fd, metadata_fd)
        assert get_sha1(workflow_fd.name) == "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        assert get_sha1(metadata_fd.name) == "d5ff5195ce296fcd334b6cbb4366b0b2b3e34c88"
