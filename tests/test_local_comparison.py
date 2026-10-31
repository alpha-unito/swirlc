"""Input preparation must preserve source settings and resolve nested CWL files."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "examples/1000genome/local-comparison.py"
spec = importlib.util.spec_from_file_location("local_comparison", SCRIPT)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def test_resolve_nested_inputs_without_modifying_original(tmp_path):
    (tmp_path / "input.txt").write_text("seed")
    original = {
        "files": [{"type": "File", "location": "input.txt"}],
        "record": {"file": {"class": "File", "path": "input.txt"}},
        "label": "input.txt",
        "step": 31250,
    }
    resolved = comparison.resolve_inputs(original, tmp_path)
    assert resolved["files"] == [
        {"class": "File", "location": str(tmp_path / "input.txt")}
    ]
    assert resolved["record"]["file"]["path"] == str(tmp_path / "input.txt")
    assert resolved["label"] == "input.txt"
    assert resolved["step"] == 31250
    assert original["files"] == [{"type": "File", "location": "input.txt"}]
    assert original["record"]["file"]["path"] == "input.txt"


def test_missing_input_fails_before_preparation(tmp_path):
    with pytest.raises(FileNotFoundError, match="missing.txt"):
        comparison.resolve_inputs({"class": "File", "path": "missing.txt"}, tmp_path)


def test_comparison_lock_prevents_overlapping_engines(tmp_path, monkeypatch):
    import fcntl

    monkeypatch.setattr(
        comparison, "run_engine", lambda *args: pytest.fail("run started")
    )
    with (tmp_path / "comparison.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            comparison.run(tmp_path, "streamflow")


@pytest.mark.parametrize("failure", [None, "streamflow", "cancel"])
def test_benchmark_sequence_and_failure_stop(tmp_path, monkeypatch, failure):
    import json

    calls = []

    def prepare(directory, *args):
        directory.mkdir()
        for engine in ("swirl", "streamflow"):
            (directory / engine).mkdir()

    def run(directory, engine):
        calls.append(engine)
        if failure == "cancel":
            raise KeyboardInterrupt("stopped")
        code = int(engine == failure)
        (directory / engine / "result.json").write_text(
            json.dumps(
                {
                    "status": "FAILED" if code else "COMPLETED",
                    "execution_seconds": 1.5,
                    "exit_code": code,
                }
            )
        )
        return code

    monkeypatch.setattr(comparison, "prepare", prepare)
    monkeypatch.setattr(comparison, "run", run)
    import importlib.metadata

    monkeypatch.setattr(importlib.metadata, "version", lambda name: "test-version")
    directory = tmp_path / "benchmark"
    args = (
        directory,
        10,
        2,
        tmp_path / "main.cwl",
        tmp_path / "inputs.yml",
        22222,
        28500,
    )
    if failure:
        with pytest.raises(KeyboardInterrupt if failure == "cancel" else RuntimeError):
            comparison.benchmark(*args)
    else:
        comparison.benchmark(*args)
    record = json.loads((directory / "sequence.json").read_text())
    assert record["status"] == (
        "CANCELLED" if failure == "cancel" else "FAILED" if failure else "COMPLETED"
    )
    assert calls == (
        ["swirl"]
        if failure == "cancel"
        else ["swirl", "streamflow"] if failure else ["swirl", "streamflow"] * 2
    )
    assert len((directory / "results.csv").read_text().splitlines()) == (
        1 if failure == "cancel" else 3 if failure else 5
    )
