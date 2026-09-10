import os
import tempfile
from tempfile import NamedTemporaryFile

from swirlc.core.entity import (
    Data,
    DistributedWorkflow,
    Location,
    Port,
    Processor,
    Step,
    Workflow,
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
        assert get_sha1(metadata_fd.name) == "18e4ac9fa2ffe1abfc366d368677fee68bd93fe2"


def test_translate_cwl_scatter(tmp_path):
    """Test translating a CWL workflow with scatter to SWIRL and compiling it."""
    from pathlib import Path
    from ruamel.yaml import YAML
    from swirlc.main import main

    example = Path(__file__).parent.parent / "examples" / "cwl" / "scatter"
    translated_dir = tmp_path / "translated"
    compiled_dir = tmp_path / "compiled"
    translated_dir.mkdir()
    compiled_dir.mkdir()

    # Translate
    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(example / "streamflow.yml"),
                "--outdir",
                str(translated_dir),
            ]
        )
        == 0
    )

    swirl_file = translated_dir / "workflow.swirl"
    metadata_file = translated_dir / "metadata.yml"
    assert swirl_file.exists()
    assert metadata_file.exists()

    swirl_content = swirl_file.read_text()
    assert "exec(s_sc," in swirl_content
    assert "move(id_ID -> p_id, l0, {l1, l2, l3})" in swirl_content
    assert "move(group_ID -> p_group, l0, {l1, l2, l3})" in swirl_content
    assert "send(eof -> p_id, l0, l1)" in swirl_content
    assert "exec(s_op," in swirl_content
    assert "exec(s_work," in swirl_content
    assert "exec(s_G," in swirl_content
    assert "exec(s_post," in swirl_content

    with open(metadata_file) as f:
        metadata = YAML(typ="safe").load(f)

    assert metadata["steps"]["s_sc"]["type"] == "scatter_pairer"
    assert metadata["steps"]["s_sc"]["scatterMethod"] in ("dotproduct", "flat_crossproduct")
    assert metadata["steps"]["s_op"]["type"] == "scatter_open"
    assert metadata["steps"]["s_G"]["type"] == "scatter_gather"
    assert metadata["steps"]["s_work"]["command"] == "python3"
    assert metadata["steps"]["s_post"]["command"] == "python3"
    assert "l0" in metadata["locations"]
    assert "l1" in metadata["locations"]
    assert "l2" in metadata["locations"]
    assert "l3" in metadata["locations"]

    # Compile
    assert (
        main(
            [
                "compile",
                str(swirl_file),
                str(metadata_file),
                "--outdir",
                str(compiled_dir),
            ]
        )
        == 0
    )

    assert (compiled_dir / "l0.py").exists()
    assert (compiled_dir / "l1.py").exists()
    assert (compiled_dir / "l2.py").exists()
    assert (compiled_dir / "l3.py").exists()
    assert (compiled_dir / "run.sh").exists()


def test_translate_cwl_scatter_nested(tmp_path):
    """Test translating, compiling, and running a CWL workflow with subworkflow scatter and dynamic scatter."""
    import subprocess
    from pathlib import Path
    from ruamel.yaml import YAML
    from swirlc.main import main

    example = Path(__file__).parent.parent / "examples" / "cwl" / "scatter-nested"
    translated_dir = tmp_path / "translated"
    compiled_dir = tmp_path / "compiled"
    translated_dir.mkdir()
    compiled_dir.mkdir()

    # 1. Translate
    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(example / "streamflow.yml"),
                "--outdir",
                str(translated_dir),
            ]
        )
        == 0
    )

    swirl_file = translated_dir / "workflow.swirl"
    metadata_file = translated_dir / "metadata.yml"
    assert swirl_file.exists()
    assert metadata_file.exists()

    swirl_content = swirl_file.read_text()
    assert "exec(s_sc," in swirl_content
    assert "move(id_ID -> p_id, l0, {l1, l2})" in swirl_content
    assert "move(group_ID -> p_group, l0, {l1, l2})" in swirl_content
    assert "exec(s_op," in swirl_content
    assert "exec(s_generate_items," in swirl_content
    assert "exec(s_compute_item," in swirl_content
    assert "exec(s_merge_items," in swirl_content
    assert "exec(s_tag_item," in swirl_content
    assert "exec(s_G," in swirl_content
    assert "exec(s_final_report," in swirl_content

    with open(metadata_file) as f:
        metadata = YAML(typ="safe").load(f)

    assert metadata["steps"]["s_sc"]["type"] == "scatter_pairer"
    assert metadata["steps"]["s_sc"]["scatterPorts"] == ["p_in1"]
    assert metadata["steps"]["s_op"]["type"] == "scatter_open"
    assert "p_sub_group_file" in metadata["steps"]["s_op"]["outputs"]
    assert "p_sub_tags" in metadata["steps"]["s_op"]["outputs"]
    assert "p_sub_num_items" in metadata["steps"]["s_op"]["outputs"]
    assert "expression" in metadata["steps"]["s_generate_items"]
    assert metadata["steps"]["s_compute_item"]["scatter"] == ["p_generate_items_items"]
    assert metadata["steps"]["s_tag_item"]["scatter"] == ["p_sub_tags"]
    assert metadata["steps"]["s_G"]["type"] == "scatter_gather"
    assert "p_out_group_summary" in metadata["steps"]["s_G"]["outputs"]
    assert "p_out_tagged_results" in metadata["steps"]["s_G"]["outputs"]

    assert "l0" in metadata["locations"]
    assert "l1" in metadata["locations"]
    assert "l2" in metadata["locations"]

    # 2. Compile
    assert (
        main(
            [
                "compile",
                str(swirl_file),
                str(metadata_file),
                "--outdir",
                str(compiled_dir),
            ]
        )
        == 0
    )

    assert (compiled_dir / "l0.py").exists()
    assert (compiled_dir / "l1.py").exists()
    assert (compiled_dir / "l2.py").exists()
    assert (compiled_dir / "run.sh").exists()

    # 3. Execute compiled workflow
    proc = subprocess.run(["bash", "run.sh"], cwd=compiled_dir, capture_output=True, text=True)
    assert proc.returncode == 0, f"run.sh failed: {proc.stderr}"

    # Verify final report
    report_files = list(compiled_dir.glob("**/final_report.txt"))
    assert report_files, "final_report.txt was not generated"
    report_content = report_files[0].read_text()
    assert "=== FINAL WORKFLOW REPORT ===" in report_content
    assert "total=23" in report_content
    assert "total=43" in report_content
    assert "[ALPHA] total=23" in report_content
    assert "[BETA] total=23" in report_content
    assert "[ALPHA] total=43" in report_content
    assert "[BETA] total=43" in report_content

