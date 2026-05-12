from __future__ import annotations
import contextlib
import pathlib
import tempfile

from swirlc.main import main

EXAMPLES_PATH = pathlib.Path(__file__).parent.parent / "examples"


def _compile(trace_file: str, config_file: str, outdir: str | None = None) -> None:
    with contextlib.ExitStack() as stack:
        if outdir is None:
            outdir = stack.enter_context(tempfile.TemporaryDirectory())
        assert main(["compile", trace_file, config_file, "--outdir", outdir]) == 0


def test_example1() -> None:
    _compile(
        str(EXAMPLES_PATH / "example1" / "example1.swirl"),
        str(EXAMPLES_PATH / "example1" / "config.yml"),
    )


def test_example2() -> None:
    _compile(
        str(EXAMPLES_PATH / "example2" / "example2.swirl"),
        str(EXAMPLES_PATH / "example2" / "config.yml"),
    )
