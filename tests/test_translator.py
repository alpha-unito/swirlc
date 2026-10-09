import os
import pathlib
import tempfile
from tempfile import NamedTemporaryFile

import pytest

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
    """A scatter may place one worker trace on its coordinator deployment."""
    from pathlib import Path

    import antlr4
    from ruamel.yaml import YAML

    from swirlc.antlr.SWIRLLexer import SWIRLLexer
    from swirlc.antlr.SWIRLParser import SWIRLParser
    from swirlc.main import main

    example = Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "scatter"
    translated_dir = tmp_path / "translated"
    translated_dir.mkdir()

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
    assert "exec(_s_scatter_0," in swirl_content
    assert (
        "move((task_id_0, task_payload_0) -> p_task_0, l0, {l0, l1, l2})"
        in swirl_content
    )
    assert "send(eof -> p_task_0, l0, l0)" in swirl_content
    assert "exec(_s_open_0," in swirl_content
    assert "exec(s_compute," in swirl_content
    assert "exec(_s_gather_0," in swirl_content
    assert "exec(s_post," in swirl_content
    assert swirl_content.count("// @compiler begin scatter.worker 0") == 3
    assert swirl_content.count("// @compiler end scatter.worker 0") == 3

    with open(metadata_file) as f:
        metadata = YAML(typ="safe").load(f)

    assert "[taskID]" not in metadata_file.read_text()
    assert metadata["steps"]["_s_scatter_0"]["type"] == "scatter_pairer"
    assert metadata["steps"]["_s_scatter_0"]["scatterMethod"] in (
        "dotproduct",
        "flat_crossproduct",
    )
    assert metadata["steps"]["_s_open_0"]["type"] == "scatter_open"
    assert metadata["steps"]["_s_gather_0"]["type"] == "scatter_gather"
    assert metadata["steps"]["s_compute"]["command"] == "python3"
    assert metadata["steps"]["s_post"]["command"] == "python3"
    assert metadata["scatterRegions"] == {
        "0": {
            "name": "/compute",
            "method": "flat_crossproduct",
            "scatterPorts": ["file_a", "file_b"],
        }
    }
    assert list(metadata["locations"]) == ["l0", "l1", "l2"]
    assert {
        location["deployment"]["port"] for location in metadata["locations"].values()
    } == {35080, 35081, 35082}
    assert swirl_content.count("<l0,") == 1
    assert "recv((task_id_0, task_payload_0) -> p_task_0, l0, l0)" in swirl_content

    parser = SWIRLParser(
        antlr4.CommonTokenStream(SWIRLLexer(antlr4.InputStream(swirl_content)))
    )
    parser.workflow()
    assert parser.getNumberOfSyntaxErrors() == 0


@pytest.mark.parametrize(
    ("example", "config"),
    [
        ("scatter", "streamflow.yml"),
        ("scatter", "streamflow-split.yml"),
        ("scatter-nested", "streamflow.yml"),
        ("scatter-nested-minimal", "streamflow.yml"),
        ("scatter-nested-zip", "streamflow.yml"),
    ],
)
def test_scatter_examples_emit_one_trace_per_location(tmp_path, example, config):
    """Every migrated scatter example remains valid SWIRL after translation."""
    import re

    import antlr4
    from ruamel.yaml import YAML

    from swirlc.antlr.SWIRLLexer import SWIRLLexer
    from swirlc.antlr.SWIRLParser import SWIRLParser
    from swirlc.main import main

    source = pathlib.Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / example
    outdir = tmp_path / f"{example}-{pathlib.Path(config).stem}"
    outdir.mkdir()
    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(source / config),
                "--outdir",
                str(outdir),
            ]
        )
        == 0
    )

    trace = (outdir / "workflow.swirl").read_text()
    assert re.search(
        r"// @compiler end scatter\.dispatch 0\s*\)\s*\|\s*\(\s*"
        r"// @compiler begin scatter\.gather 0",
        trace,
    )
    with open(outdir / "metadata.yml") as metadata_file:
        metadata = YAML(typ="safe").load(metadata_file)
    assert "[taskID]" not in (outdir / "metadata.yml").read_text()
    assert all(trace.count(f"<{location},") == 1 for location in metadata["locations"])

    parser = SWIRLParser(
        antlr4.CommonTokenStream(SWIRLLexer(antlr4.InputStream(trace)))
    )
    parser.workflow()
    assert parser.getNumberOfSyntaxErrors() == 0


def test_cwl_region_tree_preserves_nested_scatter_paths():
    """The recursive IR keeps subworkflow boundaries and worker bindings."""
    from pathlib import Path

    from swirlc.translator.cwl.cwl_translator import CWLTranslator, WorkflowRegion

    example = Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "scatter-nested-zip"
    translator = CWLTranslator(example / "streamflow.yml")
    root = translator.build_region_tree()

    process = next(
        invocation
        for invocation in root.invocations
        if invocation.path == "/process_all_zips"
    )
    assert process.scatter.region_id == "scatter:/process_all_zips"
    assert process.scatter.inputs == ("zip_file",)
    assert [target.deployment for target in process.deployments] == [
        "zip_worker1",
        "zip_worker2",
    ]
    assert isinstance(process.process, WorkflowRegion)
    assert process.process.inputs == {"zip_file": "/zip_files"}

    inspect = next(
        invocation
        for invocation in process.process.invocations
        if invocation.path == "/process_all_zips/inspect_step"
    )
    assert inspect.scatter.region_id == "scatter:/process_all_zips/inspect_step"
    assert inspect.scatter.inputs == ("target_file",)
    assert [target.deployment for target in inspect.deployments] == [
        "file_worker1",
        "file_worker2",
        "file_worker3",
    ]
    assert inspect.input_bindings == {
        "target_file": ("/process_all_zips/unzip_step/extracted_files",)
    }


def test_cwl_translation_builds_region_tree_once():
    """Analysis is shared by validation, lowering, naming, and metadata."""
    import io
    from pathlib import Path

    from swirlc.translator.cwl.cwl_translator import CWLTranslator

    example = Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "scatter"
    translator = CWLTranslator(example / "streamflow.yml")
    original = translator.build_region_tree
    calls = 0

    def counted_build():
        nonlocal calls
        calls += 1
        return original()

    translator.build_region_tree = counted_build
    translator.translate(io.StringIO(), io.StringIO())
    assert calls == 1


@pytest.mark.parametrize(
    "method", ["dotproduct", "flat_crossproduct", "nested_crossproduct"]
)
def test_cwl_region_tree_preserves_scatter_method(method):
    """All declared CWL scatter methods survive analysis unchanged."""
    from pathlib import Path

    from swirlc.translator.cwl.cwl_translator import CWLTranslator

    example = Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "scatter"
    translator = CWLTranslator(example / "streamflow.yml")
    translator.cwl_obj.steps[0].scatterMethod = method

    scatter = translator.build_region_tree().invocations[0].scatter
    assert scatter.method == method


def _scatter_pairs(tmp_path, method, inputs):
    """Run the generated pair helper in isolation for phase-0 input cases."""
    import json
    import logging
    import zipfile
    from collections import defaultdict
    from threading import Event

    from swirlc.compiler.default.compiler import scatter_special_helpers

    available = defaultdict(Event)
    for port in inputs:
        available[port].set()
    namespace = {
        "SCRATCH_DIR": str(tmp_path),
        "available_port_data": available,
        "json": json,
        "logger": logging.getLogger(__name__),
        "logging": logging,
        "os": os,
        "ports": dict(inputs),
        "tempfile": tempfile,
        "zipfile": zipfile,
    }
    exec(scatter_special_helpers, namespace)
    namespace["_scatter_pair"](
        "pair",
        "Pair",
        list(inputs),
        [("p_group", "file", "")],
        method,
    )
    return [
        json.loads(pathlib.Path(path).read_text())
        for path in namespace["ports"]["p_group"]
    ]


@pytest.mark.parametrize(
    ("method", "inputs", "expected"),
    [
        (
            "dotproduct",
            {"a": ["same", "same"], "b": [1, 2]},
            [["same", 1], ["same", 2]],
        ),
        (
            "flat_crossproduct",
            {"a": [1, 2], "b": ["x", "y"]},
            [[1, "x"], [1, "y"], [2, "x"], [2, "y"]],
        ),
        ("nested_crossproduct", {"a": [], "b": ["x"]}, []),
    ],
)
def test_scatter_pair_preserves_empty_and_duplicate_inputs(
    tmp_path, method, inputs, expected
):
    """Empty inputs stay empty and equal values remain distinct iterations."""
    payloads = _scatter_pairs(tmp_path, method, inputs)
    assert [
        [component["value"] for component in payload["components"]]
        for payload in payloads
    ] == expected


def test_nested_crossproduct_pair_includes_coordinates(tmp_path):
    payloads = _scatter_pairs(tmp_path, "nested_crossproduct", {"a": [1], "b": ["x"]})
    assert payloads[0]["coordinates"] == [0, 0]


def test_translate_cwl_scatter_nested_zip_acceptance(tmp_path):
    """Lock the phase-3 nested scatter trace and hint contract."""
    import re
    from pathlib import Path

    import antlr4
    from ruamel.yaml import YAML

    from swirlc.antlr.SWIRLLexer import SWIRLLexer
    from swirlc.antlr.SWIRLParser import SWIRLParser
    from swirlc.main import main

    example = Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "scatter-nested-zip"
    outdir = tmp_path / "translated"
    outdir.mkdir()
    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(example / "streamflow.yml"),
                "--outdir",
                str(outdir),
            ]
        )
        == 0
    )

    trace = (outdir / "workflow.swirl").read_text()
    with open(outdir / "metadata.yml") as metadata_file:
        metadata = YAML(typ="safe").load(metadata_file)

    # l0 is the coordinator; the two pools must not be collapsed together.
    assert len(metadata["locations"]) == 6
    assert metadata["scatterRegions"] == {
        "0": {
            "name": "/process_all_zips",
            "method": "dotproduct",
            "scatterPorts": ["zip_file"],
        },
        "1": {
            "name": "/process_all_zips/inspect_step",
            "method": "dotproduct",
            "scatterPorts": ["target_file"],
        },
    }
    assert {"_s_scatter_0", "_s_open_0", "_s_gather_0"}.issubset(metadata["steps"])
    assert {"_s_scatter_1", "_s_open_1", "_s_gather_1"}.issubset(metadata["steps"])
    for worker in ("l3", "l4", "l5"):
        assert "exec(s_inspect_step, {(p_open_data_0_1," in trace
        assert f")}}, {{{worker}}})" in trace
    assert "exec(s_inspect_step, {(p_unzip_step_extracted_files" not in trace

    directives = re.findall(
        r"^\s*// @compiler (begin|end) scatter\.(dispatch|worker|gather) (\d+)$",
        trace,
        re.M,
    )
    starts = [
        (phase, int(region)) for kind, phase, region in directives if kind == "begin"
    ]
    ends = [(phase, int(region)) for kind, phase, region in directives if kind == "end"]
    stack = []
    for kind, phase, region in directives:
        marker = (phase, int(region))
        if kind == "begin":
            stack.append(marker)
        else:
            assert stack.pop() == marker
    assert not stack
    assert {region for _, region in starts} == {0, 1}
    assert len(starts) == len(ends)
    assert sum(phase == "worker" and region == 0 for phase, region in starts) == 2
    assert sum(phase == "worker" and region == 1 for phase, region in starts) == 3

    parser = SWIRLParser(
        antlr4.CommonTokenStream(SWIRLLexer(antlr4.InputStream(trace)))
    )
    parser.workflow()
    assert parser.getNumberOfSyntaxErrors() == 0


def test_nested_scatter_uses_task_envelopes_and_scoped_eof(tmp_path):
    """Nested dispatch matches the reference task-envelope lifecycle."""
    from swirlc.main import main

    example = (
        pathlib.Path(__file__).parent.parent
        / "tests"
        / "fixtures"
        / "cwl"
        / "scatter-nested-minimal"
    )
    outdir = tmp_path / "translated"
    outdir.mkdir()

    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(example / "streamflow.yml"),
                "--outdir",
                str(outdir),
            ]
        )
        == 0
    )

    trace = (outdir / "workflow.swirl").read_text()
    assert "move((task_id_0, task_payload_0) -> p_task_0, l0, {l0, l2})" in trace
    assert "move((task_id_1, task_payload_1) -> p_task_1, l0, {l1})" in trace
    assert "move((task_id_1, task_payload_1) -> p_task_1, l2, {l1})" in trace
    assert "recv((task_id_1, task_payload_1) -> p_task_1, l0, l1)" in trace
    assert "recv((task_id_1, task_payload_1) -> p_task_1, l2, l1)" in trace
    assert "send(eof -> p_task_1, l0, l1)" in trace
    assert "send(eof -> p_task_1, l2, l1)" in trace
    assert "echo_item_id[taskID]" not in trace
    assert "echo_item_group[taskID]" not in trace
    inner_worker = trace.split("// @compiler begin scatter.worker 1", 1)[1].split(
        "// @compiler end scatter.worker 1", 1
    )[0]
    assert inner_worker.count("!(") == 2
    assert "\n  |\n  !(" in inner_worker


def test_nested_scatter_is_emitted_when_worker_pool_is_shared(tmp_path):
    """A shared pool must not collapse nested regions into local step scatter."""
    from swirlc.main import main

    example = (
        pathlib.Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "scatter-nested"
    )
    outdir = tmp_path / "translated"
    outdir.mkdir()

    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(example / "streamflow.yml"),
                "--outdir",
                str(outdir),
            ]
        )
        == 0
    )

    trace = (outdir / "workflow.swirl").read_text()
    for region in range(3):
        assert f"exec(_s_scatter_{region}," in trace
        assert f"exec(_s_open_{region}," in trace
        assert f"exec(_s_gather_{region}," in trace


def test_translate_cwl_dotproduct_rejects_unequal_lengths():
    """CWL dot-product must not silently truncate to the shorter input."""
    import io
    from pathlib import Path

    from swirlc.translator.cwl.cwl_translator import CWLTranslator

    example = Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "scatter"
    translator = CWLTranslator(example / "streamflow.yml")
    translator.cwl_obj.steps[0].scatterMethod = "dotproduct"
    translator.workflow_inputs["files_b"] = translator.workflow_inputs["files_b"][:-1]

    with pytest.raises(ValueError, match="dotproduct.*equal"):
        translator.translate(io.StringIO(), io.StringIO())


def test_translate_cwl_scatter_nested(tmp_path):
    """Nested tuple transport is represented completely in SWIRL and metadata."""
    from pathlib import Path

    import antlr4
    from ruamel.yaml import YAML

    from swirlc.antlr.SWIRLLexer import SWIRLLexer
    from swirlc.antlr.SWIRLParser import SWIRLParser
    from swirlc.main import main

    example = Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "scatter-nested"
    translated_dir = tmp_path / "translated"
    translated_dir.mkdir()

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
    assert "exec(_s_scatter_0," in swirl_content
    assert (
        "move((task_id_0, task_payload_0) -> p_task_0, l0, {l1, l2})" in swirl_content
    )
    assert "exec(_s_open_0," in swirl_content
    assert "exec(s_generate_items," in swirl_content
    assert "exec(s_compute_item," in swirl_content
    assert "exec(s_merge_items," in swirl_content
    assert "exec(s_tag_item," in swirl_content
    assert "exec(_s_gather_0," in swirl_content
    assert "exec(s_final_report," in swirl_content

    with open(metadata_file) as f:
        metadata = YAML(typ="safe").load(f)

    assert metadata["steps"]["_s_scatter_0"]["type"] == "scatter_pairer"
    assert metadata["steps"]["_s_scatter_0"]["scatterPorts"] == ["p_groups"]
    assert metadata["steps"]["_s_open_0"]["type"] == "scatter_open"
    assert "p_open_data_0_0" in metadata["steps"]["_s_open_0"]["outputs"]
    assert "p_open_data_1_0" in metadata["steps"]["_s_open_0"]["outputs"]
    assert "p_open_data_2_0" in metadata["steps"]["_s_open_0"]["outputs"]
    assert "expression" in metadata["steps"]["s_generate_items"]
    assert metadata["steps"]["_s_scatter_1"]["scatterPorts"] == [
        "p_generate_items_items"
    ]
    assert metadata["steps"]["_s_scatter_2"]["scatterPorts"] == [
        "p_open_data_1_0"
    ]
    assert metadata["steps"]["_s_gather_0"]["type"] == "scatter_gather"
    assert "p_gather_data_0_0" in metadata["steps"]["_s_gather_0"]["outputs"]
    assert "p_gather_data_1_0" in metadata["steps"]["_s_gather_0"]["outputs"]

    assert "l0" in metadata["locations"]
    assert "l1" in metadata["locations"]
    assert "l2" in metadata["locations"]

    parser = SWIRLParser(
        antlr4.CommonTokenStream(SWIRLLexer(antlr4.InputStream(swirl_content)))
    )
    parser.workflow()
    assert parser.getNumberOfSyntaxErrors() == 0


def test_cwl_file_location_is_coerced_to_an_absolute_path(tmp_path):
    from swirlc.translator.cwl.cwl_translator import _coerce_cwl_value

    assert _coerce_cwl_value(
        {"class": "File", "location": "data/input.vcf.gz"}, "file", tmp_path
    ) == str(tmp_path / "data" / "input.vcf.gz")
    assert (
        _coerce_cwl_value(
            {"class": "File", "location": "file:///data/input.vcf.gz"}, "file", tmp_path
        )
        == "/data/input.vcf.gz"
    )
    with pytest.raises(ValueError, match="Unsupported CWL file URI"):
        _coerce_cwl_value(
            {"class": "File", "location": "https://example.test/input.vcf.gz"},
            "file",
            tmp_path,
        )


def test_translate_1000genome_nested_scatters(tmp_path):
    import antlr4
    from ruamel.yaml import YAML

    from swirlc.antlr.SWIRLLexer import SWIRLLexer
    from swirlc.antlr.SWIRLParser import SWIRLParser
    from swirlc.main import main

    example = pathlib.Path(__file__).parent.parent / "tests" / "fixtures" / "cwl" / "1000genome"
    outdir = tmp_path / "1000genome"
    outdir.mkdir()
    assert (
        main(
            [
                "translate",
                "--language",
                "cwl",
                str(example / "streamflow.yml"),
                "--outdir",
                str(outdir),
            ]
        )
        == 0
    )

    trace = (outdir / "workflow.swirl").read_text()
    metadata_path = outdir / "metadata.yml"
    metadata = YAML(typ="safe").load(metadata_path)
    assert [region["name"] for region in metadata["scatterRegions"].values()] == [
        "/chromosome",
        "/chromosome/individuals",
        "/chromosome/mutation_overlap",
        "/chromosome/frequency",
    ]
    assert metadata["steps"]["_s_scatter_1"]["scatterPorts"] == [
        "p_get_intervals_counters",
        "p_get_intervals_stops",
    ]
    assert metadata["dependencies"]["individuals_counter"]["type"] == "int"
    assert metadata["dependencies"]["individuals_stop"]["type"] == "int"
    assert metadata["dependencies"]["d_overlap_files"]["type"] == "list[list[file]]"
    assert metadata["dependencies"]["d_freq_files"]["type"] == "list[list[file]]"
    assert "{'type': 'File', 'location':" not in metadata_path.read_text()
    assert "(p_individuals_output_file, individuals_output_file[task_id_0])" in trace

    parser = SWIRLParser(
        antlr4.CommonTokenStream(SWIRLLexer(antlr4.InputStream(trace)))
    )
    parser.workflow()
    assert parser.getNumberOfSyntaxErrors() == 0
