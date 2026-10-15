"""Exercise the helpers embedded in directly compiled Python tool execution."""
from __future__ import annotations

import json
import logging
import shlex
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from swirlc.compiler.default import compiler
from swirlc.compiler.default.runtime import Runtime
from tests.test_scoped_runtime import ROOT, envelope, term


def test_javascript_engine_is_serialized_across_parallel_tasks(tool_runtime, monkeypatch):
    try:
        import js2py
    except ImportError:
        import js2py_ as js2py
    original = js2py.eval_js
    active = maximum = 0
    lock = threading.Lock()
    barrier = threading.Barrier(8)
    def evaluate(source):
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        try:
            time.sleep(.005)
            return original(source)
        finally:
            with lock:
                active -= 1
    monkeypatch.setattr(js2py, "eval_js", evaluate)
    def task(index):
        barrier.wait(timeout=5)
        return tool_runtime["_run_javascript_expression"](
            "return {label: sample.nameroot + index, values: [index,index]};",
            {"sample": {"nameroot": "AFR"}, "index": index})
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(task, range(8)))
    assert results == [{"label": f"AFR{i}", "values": [i, i]} for i in range(8)]
    assert maximum == 1


@pytest.fixture
def tool_runtime(tmp_path):
    namespace = {"__name__": "tool_metadata_test", "SCRATCH_DIR": str(tmp_path),
                 "logger": logging.getLogger("tool_metadata_test")}
    exec(compiler.imports, namespace)
    exec(compiler.list_helper, namespace)
    exec(compiler.expression_function, namespace)
    exec(compiler.exec_function, namespace)
    exec(compiler.command_tool_function, namespace)
    exec(compiler.SCOPED_MAIN, namespace)
    return namespace


def expression(body, *, matched=False):
    result = {"language": "javascript", "source": body}
    if matched:
        result["bindings"] = {"self": {"context": "matchedFiles"}}
    return result


def lower(source, *, matched=False):
    # Test fixtures specify JavaScript bodies directly; runtime never parses CWL.
    if source.startswith("$(") and source.endswith(")"):
        body = "return " + source[2:-1] + ";"
    elif source.startswith("${") and source.endswith("}"):
        body = source[2:-1]
    else:
        raise ValueError(source)
    return expression(body, matched=matched)


def descriptor(arguments, *, inputs=None, input_types=None, stdout="result.txt",
               glob="result.txt", output_eval="$(self[0].contents)", data_type="string",
               command="printf"):
    arguments = [dict(argument, expression=lower(argument["expression"]))
                 if isinstance(argument.get("expression"), str) else argument
                 for argument in arguments]
    output = {"type": data_type, "glob": lower(glob) if glob.startswith("$(") else glob,
              "readContents": True, "evaluate": lower(output_eval, matched=True)}
    return {"displayName": "metadata", "command": command,
            "inputs": {port: {"type": input_types[name]} for name, port in (inputs or {}).items()},
            "bindings": {"inputs": {"object": {name: {"port": port}
                         for name, port in (inputs or {}).items()}}},
            "arguments": arguments, "stdout": lower(stdout) if stdout.startswith("$(") else stdout,
            "outputs": {"out": dict(output)}, "runtimeOutputs": {"out": dict(output)}}


def execute(namespace, step, inputs=None):
    namespace["METADATA"] = {"steps": {"tool": step}}
    return namespace["_execute_bound"]("tool", inputs or {})["out"]


def test_order_prefix_quoting_and_named_input_context(tool_runtime):
    script = "import json,sys; print(json.dumps(sys.argv[1:]))"
    step = descriptor([
        {"value": "-c", "position": -10},
        {"value": script, "position": -9},
        {"valueFrom": "p_text", "position": 2, "prefix": "--raw"},
        {"expression": "$(inputs.text)", "position": 4, "prefix": "--label=", "separate": False},
        {"value": "tail", "position": 9},
    ], inputs={"text": "p_text"}, input_types={"text": "string"},
        command=shlex.quote(sys.executable))
    assert json.loads(execute(tool_runtime, step, {"p_text": "space ' quote; literal"})) == [
        "--raw", "space ' quote; literal", "--label=space ' quote; literal", "tail",
    ]


def test_file_nameroot_transform_and_dynamic_stdout_glob(tool_runtime, tmp_path):
    source = tmp_path / "population.sample.txt"
    source.write_text("source\n")
    step = descriptor([
        {"value": "%s", "position": 0},
        {"expression": "$(inputs.population.nameroot)", "position": 1},
    ], inputs={"population": "p_population"}, input_types={"population": "file"},
        stdout="$(inputs.population.nameroot + '.result')",
        glob="$(inputs.population.nameroot + '.result')",
        output_eval="$(self[0].contents + ':' + inputs.population.nameext)")
    assert execute(tool_runtime, step, {"p_population": str(source)}) == "population.sample:.txt"


def test_output_self_is_loaded_file_objects_and_strings_are_not_trimmed(tool_runtime):
    step = descriptor([{"value": "%s"}, {"value": "  keep spaces\n\n"}],
        output_eval="$(self[0].class + ':' + self[0].basename + ':' + self[0].contents)")
    assert execute(tool_runtime, step) == "File:result.txt:  keep spaces\n\n"


def test_interpolation_parses_nested_delimiters_and_quoted_self(tool_runtime):
    step = descriptor([{"value": "%s"}, {
        "expression": "${ return 'self literal:' + inputs.text; }"}],
        inputs={"text": "p_text"}, input_types={"text": "string"},
        output_eval="$(self[0].contents)")
    assert execute(tool_runtime, step, {"p_text": "(value)"}) == "self literal:(value)"
    assert tool_runtime["_evaluate_expression"](
        expression("return 'before-' + inputs.text.replace(')', ']') + '-after';"),
        {"inputs": {"text": "(value)"}}) == "before-(value]-after"
    assert "_evaluate_cwl" not in tool_runtime
    assert "_command_tool" not in tool_runtime


def test_list_and_scalar_declared_output_types(tool_runtime):
    step = descriptor([{"value": "%s"}, {"value": "42"}], data_type="int",
                      output_eval="$(parseInt(self[0].contents))")
    assert execute(tool_runtime, step) == 42
    step["runtimeOutputs"]["out"].update(type="bool", evaluate=lower("$(self[0].contents === '42')", matched=True))
    assert execute(tool_runtime, step) is True
    step["runtimeOutputs"]["out"].update(type="list[list[string]]", evaluate=lower("$([['same','same'],[]])", matched=True))
    assert execute(tool_runtime, step) == [["same", "same"], []]


@pytest.mark.parametrize("data_type, output_eval", [
    ("string", "$(42)"), ("int", "$('42')"), ("bool", "$('false')"),
    ("int", "$(true)"), ("file", "$('result.txt')"), ("list[string]", "$([1])"),
])
def test_output_eval_rejects_wrong_declared_payload_type(tool_runtime, data_type, output_eval):
    step = descriptor([{"value": "%s"}, {"value": "value"}],
                      data_type=data_type, output_eval=output_eval)
    with pytest.raises(TypeError, match="expected"):
        execute(tool_runtime, step)


def test_explicit_stdout_does_not_follow_output_glob(tool_runtime):
    step = descriptor([{"value": "%s"}, {"value": "captured"}],
                      stdout="captured.txt", glob="*.txt")
    assert execute(tool_runtime, step) == "captured"
    assert [path.name for path in Path(tool_runtime["SCRATCH_DIR"]).glob("exec_tool_*/*.txt")] == ["captured.txt"]


def test_dynamic_glob_list_and_output_array_preserve_order_and_duplicates(tool_runtime):
    step = descriptor([{"value": "-c"}, {"value": "printf first > a.txt; printf second > b.txt"}],
                      command="/bin/sh", glob="$(inputs.patterns)", data_type="list[string]",
                      output_eval="$([self[0].contents, self[1].contents, self[0].contents])",
                      inputs={"patterns": "p_patterns"}, input_types={"patterns": "list[string]"})
    step.pop("stdout")
    assert execute(tool_runtime, step, {"p_patterns": ["b.txt", "a.txt"]}) == ["second", "first", "second"]


def test_shell_quote_false_and_item_separator(tool_runtime, monkeypatch):
    monkeypatch.setenv("SWIRLC_METADATA_LITERAL", "expanded")
    step = descriptor([{"value": "%s|%s|%s"},
                       {"value": "$SWIRLC_METADATA_LITERAL"},
                       {"value": "$SWIRLC_METADATA_LITERAL", "shellQuote": False},
                       {"valueFrom": "p_words", "itemSeparator": ","}],
                      inputs={"words": "p_words"}, input_types={"words": "list[string]"})
    assert execute(tool_runtime, step, {"p_words": ["a b", "c"]}) == "$SWIRLC_METADATA_LITERAL|expanded|a b,c"


@pytest.mark.parametrize("expression", ["$(inputs.missing.value)", "$(inputs.text +)",
                                         "$(runtime.outdir)"])
def test_unsupported_or_malformed_expressions_fail(tool_runtime, expression):
    step = descriptor([{"expression": expression}], inputs={"text": "p_text"},
                      input_types={"text": "string"})
    with pytest.raises(Exception):
        execute(tool_runtime, step, {"p_text": "value"})


def test_output_eval_failure_and_unmatched_glob_fail(tool_runtime):
    step = descriptor([{"value": "%s"}, {"value": "value"}],
                      output_eval="$(self[0].contents.nonexistent())")
    with pytest.raises(Exception):
        execute(tool_runtime, step)
    step["runtimeOutputs"]["out"]["glob"] = "missing.txt"
    step["outputs"]["out"]["glob"] = "missing.txt"
    step["runtimeOutputs"]["out"]["evaluate"] = lower("$(self[0].contents)", matched=True)
    with pytest.raises(Exception):
        execute(tool_runtime, step)


def test_processed_payload_keeps_invocation_id_and_bound_inputs(tool_runtime):
    step = descriptor([{"value": "%s"}, {"expression": "$(inputs.text)"}],
                      inputs={"text": "p_text"}, input_types={"text": "string"},
                      output_eval="$(self[0].contents.trim())")
    metadata = {"steps": {"tool": step}, "dependencies": {"out": {"type": "string"}}}
    step["outputs"]["out"]["dataName"] = "out"
    tool_runtime["METADATA"] = metadata
    runtime = Runtime(metadata, "local", {}, None, None, None, tool_runtime["_execute_bound"])
    env = {"text": "  kept  ", "i": 4}
    identity = term("path", "", ROOT, term("variable", "i"))
    runtime.execute_step(env, "tool", [["p_text", envelope(term("variable", "text"), identity)]],
                         [["out", envelope(term("variable", "result"), identity)]], mapping=["local"])
    assert env["result"] == "kept"
    assert runtime.values == [{"port": "out", "id": (4,), "payload": "kept", "type": "string"}]


def test_command_failure_wakes_parallel_work_without_waiting_for_timeout(tool_runtime):
    step = descriptor([], command="false")
    metadata = {"steps": {"tool": step}, "dependencies": {}}
    tool_runtime["METADATA"] = metadata
    runtime = Runtime(metadata, "local", {}, None, None, None, tool_runtime["_execute_bound"])
    runtime.timeout = 2
    def blocked(env, owner):
        runtime.recv(env, "missing", envelope(term("variable", "v"), ROOT), "local")
    def failure(env, owner):
        runtime.execute_step(env, "tool", [], [])
    started = time.monotonic()
    with pytest.raises(Exception, match="exit status 1"):
        runtime.parallel({}, None, blocked, failure)
    assert time.monotonic() - started < 1


def test_generic_expression_bindings_do_not_require_cwl_names(tool_runtime):
    specification = {"sample": {"port": "p_text"},
                     "configuration": {"object": {"count": {"port": "p_count"}}}}
    bindings = tool_runtime["_resolve_bindings"](specification, {"p_text": "generic", "p_count": 2},
        input_types={"p_text": {"type": "string"}, "p_count": {"type": "int"}})
    assert tool_runtime["_evaluate_expression"](
        expression("return [sample, configuration.count + 1];"), bindings) == ["generic", 3]
    with pytest.raises(ValueError, match="Unsupported expression language"):
        tool_runtime["_evaluate_expression"]({"language": "cwl", "source": "$(inputs.x)"}, {})


def test_generic_output_context_can_use_an_arbitrary_variable(tool_runtime):
    step = descriptor([{"value": "%s"}, {"value": "custom context"}])
    processor = expression("return files[0].contents;")
    processor["bindings"] = {"files": {"context": "matchedFiles"}}
    step["runtimeOutputs"]["out"]["evaluate"] = processor
    assert execute(tool_runtime, step) == "custom context"


def test_expression_local_bindings_without_tool_bindings(tool_runtime):
    step = descriptor([{"value": "%s"}])
    step.pop("bindings")
    step["inputs"] = {"p_word": {"type": "string"}}
    step["arguments"].append({"expression": {"language": "javascript", "source": "return word;",
                             "bindings": {"word": {"port": "p_word"}}}})
    assert execute(tool_runtime, step, {"p_word": "local binding"}) == "local binding"


def test_typed_inputs_stage_nested_file_lists_without_expression_bindings(tool_runtime, tmp_path):
    first, second = tmp_path / "first.txt", tmp_path / "second.txt"
    first.write_text("first\n")
    second.write_text("second\n")
    step = descriptor([
        {"value": "-c"}, {"value": "cat first.txt second.txt"},
    ], command="/bin/sh")
    step.pop("bindings")
    step["inputs"] = {"p_files": {"type": "list[list[file]]"}}
    assert execute(tool_runtime, step, {"p_files": [[str(first)], [], [str(second)]]}) == "first\nsecond\n"
