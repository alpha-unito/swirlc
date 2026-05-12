import pathlib


from swirlc.main import main

EXAMPLES_PATH = pathlib.Path(__file__).parent.parent / "examples"


def _compile(trace_file: str, config_file: str) -> None:
    assert main(["compile", trace_file, config_file]) == 0


def test_example1():
    _compile(
        str(EXAMPLES_PATH / "example1" / "example1.swirl"),
        str(EXAMPLES_PATH / "example1" / "config.yml"),
    )


def test_example2():
    _compile(
        str(EXAMPLES_PATH / "example2" / "example2.swirl"),
        str(EXAMPLES_PATH / "example2" / "config.yml"),
    )
