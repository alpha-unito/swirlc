"""Exercise the helpers embedded in directly compiled Python tool execution."""
from __future__ import annotations

import json
import logging
import shlex
import socket
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
    import quickjs
    owners, callers = [], set()
    original_compile, original_call = quickjs.Function._compile, quickjs.Function._call
    def compile_context(self, *args, **kwargs):
        owners.append(threading.get_ident())
        return original_compile(self, *args, **kwargs)
    def call(self, *args, **kwargs):
        callers.add(threading.get_ident())
        return original_call(self, *args, **kwargs)
    monkeypatch.setattr(quickjs.Function, "_compile", compile_context)
    monkeypatch.setattr(quickjs.Function, "_call", call)
    barrier = threading.Barrier(8)
    def task(index):
        barrier.wait(timeout=5)
        return tool_runtime["_run_javascript_expression"](
            "return {label: sample.nameroot + index, values: [index,index]};",
            {"sample": {"nameroot": "AFR"}, "index": index})
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(task, range(8)))
    assert results == [{"label": f"AFR{i}", "values": [i, i]} for i in range(8)]
    assert len(owners) == 1
    assert callers == set(owners)


def test_simple_references_do_not_enter_javascript(tool_runtime):
    def unexpected():
        raise AssertionError("A reference should not need QuickJS")
    tool_runtime["_get_javascript_dispatcher"] = unexpected
    evaluate = tool_runtime["_run_javascript_expression"]
    inputs = {"file": {"basename": "image.fits"}, "values": [False, None, 0]}
    for source, expected in [
        ('return (inputs.file.basename);', 'image.fits'),
        ('return inputs["values"][0];', False),
        ('return inputs.values[1];', None),
        ('return inputs.values.length;', 3),
    ]:
        assert evaluate(source, {"inputs": inputs}) == expected
    result = evaluate("return inputs;", {"inputs": inputs})
    result["file"]["basename"] = "changed"
    assert inputs["file"]["basename"] == "image.fits"


def test_cached_javascript_uses_fresh_data_and_local_scope(tool_runtime):
    evaluate = tool_runtime["_run_javascript_expression"]
    source = "var remembered = inputs.value; return [remembered, inputs.empty === null];"
    for value in [1, 2, "quote'\\\n", False]:
        assert evaluate(source, {"inputs": {"value": value, "empty": None}}) == [value, True]
    assert evaluate("return typeof remembered;", {}) == "undefined"
    assert evaluate("return inputs.value.length + 0;", {"inputs": {"value": "\U0001f600"}}) == 2


@pytest.mark.parametrize("source", [
    "leaked = 1; return null;",
    "globalThis.leaked = 1; return null;",
    "Object.prototype.leaked = 1; return null;",
    "Array.prototype.leaked = 1; return null;",
    "Object.getPrototypeOf([][Symbol.iterator]()).leaked = 1; return null;",
    "Object.getPrototypeOf(function*() {}).leaked = 1; return null;",
    "delete Array.prototype.map; return null;",
])
def test_shared_javascript_state_cannot_be_mutated(tool_runtime, source):
    import quickjs
    evaluate = tool_runtime["_run_javascript_expression"]
    with pytest.raises(quickjs.JSException):
        evaluate(source, {})
    assert evaluate("return [typeof leaked, typeof Object.prototype.leaked, [1,2].map(x => x + 1)];", {}) == [
        "undefined", "undefined", [2, 3]]


def test_javascript_can_mutate_its_own_inputs_without_changing_other_calls(tool_runtime):
    evaluate = tool_runtime["_run_javascript_expression"]
    bindings = {"inputs": {"values": [1]}}
    for _ in range(2):
        assert evaluate("inputs.values.push(2); return inputs.values;", bindings) == [1, 2]
    assert bindings == {"inputs": {"values": [1]}}


def test_reference_fast_path_falls_back_for_javascript_string_escapes(tool_runtime):
    evaluate = tool_runtime["_run_javascript_expression"]
    assert evaluate(r'return inputs["\x61"];', {"inputs": {"a": 7}}) == 7
    import quickjs
    with pytest.raises(quickjs.JSException, match="SyntaxError"):
        evaluate('return inputs[01];', {"inputs": [7, 8]})


@pytest.mark.parametrize("directory", [False, True])
@pytest.mark.parametrize("writable", [False, True])
def test_local_staging_links_readonly_and_copies_writable(tool_runtime, tmp_path, directory, writable):
    source = tmp_path / "source"
    if directory:
        source.mkdir()
        (source / "data.txt").write_text("original")
    else:
        source.write_text("original")
    value = tool_runtime["_prepare_value"]({"class": "Directory" if directory else "File", "path": str(source)})
    workdir = tmp_path / "work"
    workdir.mkdir()
    stage = tool_runtime["_stage_value"]
    staged = stage(value, str(workdir), writable=writable)
    target = Path(staged["path"])
    assert target.is_symlink() is not writable
    assert stage(value, str(workdir), writable=writable) == staged
    assert stage(staged, str(workdir), writable=writable) == staged
    if writable:
        output = target / "data.txt" if directory else target
        output.write_text("changed")
        stage(value, str(workdir), writable=True)
        assert output.read_text() == "changed"
        assert (source / "data.txt" if directory else source).read_text() == "original"


@pytest.mark.parametrize("directory", [False, True])
def test_writable_entry_upgrades_staged_link_without_modifying_source(tool_runtime, tmp_path, directory):
    source = tmp_path / "source"
    if directory:
        source.mkdir()
        (source / "data.txt").write_text("original")
    else:
        source.write_text("original")
    value = tool_runtime["_prepare_value"]({"class": "Directory" if directory else "File", "path": str(source)})
    workdir = tmp_path / "work"
    workdir.mkdir()
    stage = tool_runtime["_stage_value"]
    readonly = stage(value, str(workdir))
    writable = stage(readonly, str(workdir), writable=True)
    target = Path(writable["path"])
    assert not target.is_symlink()
    output = target / "data.txt" if directory else target
    output.write_text("changed")
    assert (source / "data.txt" if directory else source).read_text() == "original"


def test_synthetic_directory_can_contain_optional_outputs(tool_runtime, tmp_path):
    value = tool_runtime["_prepare_value"]({"class": "Directory", "basename": "data", "listing": [
        None, {"class": "File", "basename": "status.txt", "contents": "status"}]})
    staged = tool_runtime["_stage_value"](value, str(tmp_path / "work"))
    assert (Path(staged["path"]) / "status.txt").read_text() == "status"


def test_staging_rejects_unregistered_symlinks_outside_workdir(tool_runtime, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    source = tmp_path / "source.txt"
    source.write_text("source")
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "escape").symlink_to(outside, target_is_directory=True)
    value = tool_runtime["_prepare_value"]({"class": "File", "path": str(source), "basename": "escape/file.txt"})
    with pytest.raises(ValueError, match="escapes"):
        tool_runtime["_stage_value"](value, str(workdir))
    assert not (outside / "file.txt").exists()


def test_command_does_not_stage_inputs_used_only_by_step_expressions(tool_runtime, tmp_path, monkeypatch):
    source = tmp_path / "large.fits"
    source.write_text("contents must not be copied")
    step = descriptor([{"input": "name"}], command="printf", inputs={"image": "p_image"}, input_types={"image": "file"})
    step["inputSchemas"] = {"name": {"type": "string"}}
    step["inputTransforms"] = {"name": {"evaluate": expression("return inputs.image.basename;")}}
    def unexpected(*args, **kwargs):
        raise AssertionError("Expression-only files must not be staged")
    monkeypatch.setattr(tool_runtime["shutil"], "copy2", unexpected)
    monkeypatch.setattr(tool_runtime["os"], "symlink", unexpected)
    assert execute(tool_runtime, step, {"p_image": str(source)}) == "large.fits"


def test_writable_initial_workdir_entry_is_an_independent_copy(tool_runtime, tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("original")
    step = descriptor([{"value": "-c"}, {"value": "printf changed > source.txt; cat source.txt"}],
                      command="/bin/sh", inputs={"source": "p_source"}, input_types={"source": "file"})
    step["inputSchemas"] = {"source": {"type": "file"}}
    step["staging"] = [{"entry": expression("return inputs.source;"), "writable": True}]
    assert execute(tool_runtime, step, {"p_source": str(source)}) == "changed"
    assert source.read_text() == "original"


def test_container_mounts_include_readonly_symlink_sources(tool_runtime, tmp_path, monkeypatch):
    source_dir = tmp_path / "external"
    source_dir.mkdir()
    source = source_dir / "source.txt"
    source.write_text("original")
    step = descriptor([{"valueFrom": "p_source"}], command="cat",
                      inputs={"source": "p_source"}, input_types={"source": "file"})
    step["inputSchemas"] = {"source": {"type": "file"}}
    step["container"] = {"type": "docker", "image": "test-image"}
    monkeypatch.setenv("SWIRLC_CONTAINER_ENGINE", "docker")
    def run(command, cwd=None):
        assert f"{source_dir}:{source_dir}:ro" in shlex.split(command)
        assert (Path(cwd) / "source.txt").is_symlink()
        (Path(cwd) / "result.txt").write_text("original")
        return __import__('subprocess').CompletedProcess(command, 0, b'', b'')
    tool_runtime["_run_command"] = run
    assert execute(tool_runtime, step, {"p_source": str(source)}) == "original"


@pytest.fixture
def tool_runtime(tmp_path):
    namespace = {"__name__": "tool_metadata_test", "SCRATCH_DIR": str(tmp_path), "BUF_SIZE": 65536,
                 "logger": logging.getLogger("tool_metadata_test")}
    exec(compiler.imports, namespace)
    exec(compiler.list_helper, namespace)
    exec(compiler.expression_function, namespace)
    exec(compiler.value_helpers, namespace)
    exec(compiler.framing_helpers, namespace)
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
                                         "$(undeclaredRuntime.outdir)"])
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


def test_structured_values_validate_nested_fields_and_preserve_primitives(tool_runtime):
    schema = {"type": "array", "items": {"type": "record", "fields": {
        "count": {"type": "int"}, "enabled": {"type": "boolean"},
        "text": {"type": "string"}, "optional": {"type": "string", "nullable": True}}}}
    value = [{"count": 0, "enabled": False, "text": "", "optional": None}]
    assert tool_runtime["_prepare_value"](value, schema) == value
    for field, invalid in [("count", False), ("enabled", 0), ("text", None)]:
        with pytest.raises(TypeError):
            tool_runtime["_prepare_value"]([{**value[0], field: invalid}], schema)
    with pytest.raises(TypeError):
        tool_runtime["_prepare_value"]([{"enabled": False, "text": ""}], schema)


def test_literal_directory_stages_files_and_companions_without_changing_sources(tool_runtime, tmp_path):
    value = tool_runtime["_prepare_value"]({"class": "Directory", "basename": "bundle",
        "listing": [{"class": "File", "basename": "value.txt", "contents": "seed\n",
                     "secondaryFiles": [{"class": "File", "basename": "value.txt.meta",
                                         "contents": "meta\n"}]}]})
    source = Path(value["listing"][0]["path"])
    workdir = tmp_path / "invocation"
    workdir.mkdir()
    staged = tool_runtime["_stage_value"](value, str(workdir))
    assert Path(staged["path"]) == workdir / "bundle"
    assert (workdir / "bundle/value.txt").read_text() == "seed\n"
    assert (workdir / "bundle/value.txt.meta").read_text() == "meta\n"
    assert source.read_text() == "seed\n"
    assert tool_runtime["_stage_value"](value, str(workdir)) == staged


@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt", "bundle/../../escape"])
def test_staging_rejects_escaping_entries(tool_runtime, tmp_path, name):
    with pytest.raises(ValueError, match="escapes|Invalid staging"):
        tool_runtime["_entry_path"](str(tmp_path), name)


def test_staging_rejects_conflicting_entries_across_calls(tool_runtime, tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    prepare = tool_runtime["_prepare_value"]
    first = prepare({"class": "File", "basename": "same.txt", "contents": "first"})
    second = prepare({"class": "File", "basename": "same.txt", "contents": "second"})
    tool_runtime["_stage_value"](first, str(workdir))
    with pytest.raises(ValueError, match="Conflicting"):
        tool_runtime["_stage_value"](second, str(workdir))
    assert (workdir / "same.txt").read_text() == "first"


def test_secondary_patterns_expressions_and_requiredness(tool_runtime, tmp_path):
    primary = tmp_path / "sample.txt"
    primary.write_text("seed")
    (tmp_path / "sample.txt.meta").write_text("meta")
    (tmp_path / "sample.index").write_text("index")
    prepare = tool_runtime["_prepare_value"]
    value = prepare({"class": "File", "path": str(primary)})
    evaluate = lambda descriptor, own: tool_runtime["_evaluate_expression"](descriptor, {"self": own})
    result = tool_runtime["_apply_secondary"](value, [
        {"pattern": ".meta", "required": True},
        {"pattern": "^.index", "required": True},
        {"pattern": expression("return self.nameroot + '.index';"), "required": True},
        {"pattern": ".absent", "required": expression("return false;")}], evaluate)
    assert [item["basename"] for item in result["secondaryFiles"]] == ["sample.txt.meta", "sample.index"]
    # Reapplying declarations must never request sample.txt.meta.meta.
    assert tool_runtime["_apply_secondary"](result, [{"pattern": ".meta"}], evaluate) == result
    with pytest.raises(ValueError, match="does not exist"):
        tool_runtime["_apply_secondary"](value, [{"pattern": ".absent", "required": True}], evaluate)


def test_contents_loader_enforces_byte_limit(tool_runtime, tmp_path):
    path = tmp_path / "contents.txt"
    path.write_bytes(b"x" * 65536)
    assert len(tool_runtime["_load_contents"](str(path))) == 65536
    path.write_bytes(b"x" * 65537)
    with pytest.raises(ValueError, match="64 KiB"):
        tool_runtime["_load_contents"]({"path": str(path)})


def test_nested_record_transport_transfers_bytes_into_receiver_scratch(tool_runtime, tmp_path):
    sender_root, receiver_root = tmp_path / "sender", tmp_path / "receiver"
    sender_root.mkdir()
    receiver_root.mkdir()
    sender_namespace = dict(tool_runtime, SCRATCH_DIR=str(sender_root))
    receiver_namespace = dict(tool_runtime, SCRATCH_DIR=str(receiver_root))
    for namespace in (sender_namespace, receiver_namespace):
        exec(compiler.value_helpers, namespace)
        exec(compiler.framing_helpers, namespace)
    original = sender_namespace["_prepare_value"]([{"source": {"class": "File",
        "basename": "seed.txt", "contents": "seed\n", "secondaryFiles": [
            {"class": "File", "basename": "seed.txt.meta", "contents": "meta\n"}]},
        "directory": {"class": "Directory", "basename": "bundle", "listing": [
            {"class": "File", "basename": "nested.txt", "contents": "nested"}]},
        "null": None, "false": False, "zero": 0, "empty": ""}])
    sending, receiving = socket.socketpair()
    sending.settimeout(5)
    receiving.settimeout(5)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(sender_namespace["_send_structured"], sending, original)
            result = receiver_namespace["_recv_structured"](receiving)
            future.result(timeout=5)
    finally:
        sending.close()
        receiving.close()
    own = result[0]
    path = Path(own["source"]["path"])
    assert path.is_relative_to(receiver_root)
    assert path != Path(original[0]["source"]["path"])
    assert path.read_text() == "seed\n"
    assert path.with_name("seed.txt.meta").read_text() == "meta\n"
    assert Path(own["directory"]["path"]).is_relative_to(receiver_root)
    assert (Path(own["directory"]["path"]) / "nested.txt").read_text() == "nested"
    assert {key: own[key] for key in ("null", "false", "zero", "empty")} == {
        "null": None, "false": False, "zero": 0, "empty": ""}


def json_output_step(script, *, schema=None):
    spec = {"type": "string", "schema": schema or {"type": "string"}}
    return {"command": shlex.quote(sys.executable),
            "arguments": [{"value": "-c"}, {"value": script}],
            "inputs": {}, "outputNames": {"answer": "out"},
            "outputs": {"out": dict(spec)}, "runtimeOutputs": {"out": dict(spec)}}


def test_output_json_overrides_bindings_and_resolves_relative_files(tool_runtime):
    step = json_output_step("from pathlib import Path; import json; "
        "Path('report.txt').write_text('report'); "
        "Path('cwl.output.json').write_text(json.dumps({'answer': {'class':'File','location':'report.txt'}}))",
        schema={"type": "file"})
    step["runtimeOutputs"]["out"]["glob"] = "wrong-binding.txt"
    result = execute(tool_runtime, step)
    assert result["class"] == "File"
    assert Path(result["path"]).read_text() == "report"


@pytest.mark.parametrize("contents,exception,match", [
    ("{", ValueError, None),
    ("[]", TypeError, "output mapping"),
    ("{}", ValueError, "Missing required output"),
    ('{"answer": 42}', TypeError, "Expected string"),
])
def test_output_json_rejects_invalid_mapping_and_outputs(tool_runtime, contents, exception, match):
    step = json_output_step("from pathlib import Path; "
                           f"Path('cwl.output.json').write_text({contents!r})")
    with pytest.raises(exception, match=match):
        execute(tool_runtime, step)


def test_output_json_rejects_inaccessible_file_reference(tool_runtime):
    step = json_output_step("from pathlib import Path; "
        "Path('cwl.output.json').write_text('{\"answer\":{\"class\":\"File\",\"location\":\"absent.txt\"}}')",
        schema={"type": "file"})
    with pytest.raises(ValueError, match="does not exist"):
        execute(tool_runtime, step)


@pytest.mark.parametrize("status", [0, 1])
def test_accepted_status_is_available_to_output_evaluation_without_glob(tool_runtime, status):
    step = descriptor([{ "value": "-c"}, {"value": f"exit {status}"}], command="/bin/sh",
                      data_type="int", output_eval="$(runtime.exitCode)")
    step["acceptedExitCodes"] = [0, 1]
    step.pop("stdout")
    step["runtimeOutputs"]["out"].pop("glob")
    assert execute(tool_runtime, step) == status


@pytest.mark.parametrize("status,accepted", [(2, [0, 1]), (1, None)])
def test_rejected_status_cannot_be_masked_by_output_json(tool_runtime, status, accepted):
    step = json_output_step("from pathlib import Path; import sys; "
        f"Path('cwl.output.json').write_text('{{\"answer\":\"present\"}}'); sys.exit({status})")
    if accepted is not None:
        step["acceptedExitCodes"] = accepted
    with pytest.raises(RuntimeError, match=f"exit status {status}"):
        execute(tool_runtime, step)


def test_false_condition_publishes_null_without_starting_command(tool_runtime, tmp_path):
    marker = tmp_path / "must-not-exist"
    step = descriptor([{"value": "-c"}, {"value": f"touch {shlex.quote(str(marker))}"}], command="/bin/sh")
    step["when"] = expression("return false;")
    assert execute(tool_runtime, step) is None
    assert not marker.exists()
    assert not list(tmp_path.glob("exec_tool_*"))


@pytest.mark.parametrize("condition", ["return 0;", "return 'false';", "return null;"])
def test_condition_requires_boolean(tool_runtime, condition):
    step = descriptor([], command="false")
    step["when"] = expression(condition)
    with pytest.raises(TypeError, match="condition.*boolean"):
        execute(tool_runtime, step)


def selection_step(mode):
    step = descriptor([], command="true", inputs={"value": "p_value"},
        input_types={"value": "value"}, output_eval="$(JSON.stringify(inputs.value))")
    step.pop("stdout")
    step["runtimeOutputs"]["out"].pop("glob")
    step["inputTransforms"] = {"value": {"select": mode}}
    return step


@pytest.mark.parametrize("mode,values,expected", [
    ("all_non_null", [None, False, 0, "", [None, 1]], [False, 0, "", [None, 1]]),
    ("all_non_null", [None, None], []),
    ("first_non_null", [None, False, 1], False),
    ("first_non_null", [None, 0, 1], 0),
    ("first_non_null", [None, "", 1], ""),
    ("the_only_non_null", [None, 0, None], 0),
])
def test_source_selection_preserves_order_shape_and_falsey_values(tool_runtime, mode, values, expected):
    result = json.loads(execute(tool_runtime, selection_step(mode), {"p_value": values}))
    assert result == expected
    assert type(result) is type(expected)
    if isinstance(expected, list):
        assert [type(item) for item in result] == [type(item) for item in expected]


@pytest.mark.parametrize("mode,values", [
    ("first_non_null", [None, None]),
    ("the_only_non_null", [None, None]),
    ("the_only_non_null", [False, 0]),
])
def test_source_selection_rejects_wrong_non_null_count(tool_runtime, mode, values):
    with pytest.raises(ValueError, match="requires"):
        execute(tool_runtime, selection_step(mode), {"p_value": values})


def test_sibling_input_transforms_evaluate_against_original_snapshot(tool_runtime):
    step = descriptor([], command="true", inputs={"a": "p_a", "b": "p_b"},
        input_types={"a": "int", "b": "int"}, output_eval="$(JSON.stringify(inputs))")
    step.pop("stdout")
    step["runtimeOutputs"]["out"].pop("glob")
    step["inputTransforms"] = {
        "a": {"evaluate": expression("return inputs.b + 10;")},
        "b": {"evaluate": expression("return inputs.a + 20;")}}
    assert json.loads(execute(tool_runtime, step, {"p_a": 1, "p_b": 2})) == {"a": 12, "b": 21}


def test_automatic_input_staging_keeps_duplicate_basenames_and_companions(tool_runtime, tmp_path):
    prepare = tool_runtime["_prepare_value"]
    values = [prepare({"class": "File", "basename": "same.txt", "contents": label,
                      "secondaryFiles": [{"class": "File", "basename": "same.txt.meta",
                                          "contents": label + " companion"}]})
              for label in ("first", "second")]
    workdir = tmp_path / "work"
    workdir.mkdir()
    stage = tool_runtime["_stage_value"]
    result = stage(values, str(workdir), allow_collisions=True)
    assert result[0]["path"] != result[1]["path"]
    for value, expected in zip(result, ("first", "second")):
        path = Path(value["path"])
        assert path.name == "same.txt"
        assert path.read_text() == expected
        assert path.with_name("same.txt.meta").read_text() == expected + " companion"
    assert stage(values, str(workdir), allow_collisions=True) == result
    with pytest.raises(ValueError, match="Conflicting"):
        stage(values[1], str(workdir))


def test_automatic_staging_relocates_primary_when_only_companion_conflicts(tool_runtime, tmp_path):
    prepare = tool_runtime["_prepare_value"]
    values = [prepare({"class": "File", "basename": label + ".txt", "contents": label,
                      "secondaryFiles": [{"class": "File", "basename": "shared.meta",
                                          "contents": label}]}) for label in ("first", "second")]
    workdir = tmp_path / "work"
    workdir.mkdir()
    result = tool_runtime["_stage_value"](values, str(workdir), allow_collisions=True)
    for value, expected in zip(result, ("first", "second")):
        path = Path(value["path"])
        assert path.read_text() == expected
        assert path.with_name("shared.meta").read_text() == expected


def test_record_field_secondary_schema_is_applied_inside_arrays(tool_runtime, tmp_path):
    primary = tmp_path / "seed.txt"
    primary.write_text("seed")
    companion = tmp_path / "seed.txt.meta"
    companion.write_text("meta")
    value = tool_runtime["_prepare_value"]([{"source": {"class": "File", "path": str(primary)},
                                            "optional": None}])
    schema = {"type": "array", "items": {"type": "record", "fields": {
        "source": {"type": "file", "secondaryFiles": [{"pattern": ".meta", "required": True}]},
        "optional": {"type": "file", "nullable": True}}}}
    result = tool_runtime["_apply_value_schema"](value, schema, lambda *args: None)
    assert result[0]["source"]["secondaryFiles"][0]["path"] == str(companion)
    assert result[0]["optional"] is None
    missing_schema = {"type": "array", "items": {"type": "record", "fields": {
        "source": {"type": "file", "secondaryFiles": [{"pattern": ".missing", "required": True}]}}}}
    with pytest.raises(ValueError, match="does not exist"):
        tool_runtime["_apply_value_schema"](value, missing_schema, lambda *args: None)


def test_old_expression_file_outputs_keep_path_compatibility(tool_runtime, tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("source")
    assert tool_runtime["_coerce_expression_output"]({"class": "File", "path": str(source)}, "file") == str(source)
    with pytest.raises(ValueError, match="wrong class"):
        tool_runtime["_prepare_value"]({"class": "File", "path": "/dev/zero"})


def test_initial_workdir_literal_file_entries(tool_runtime):
    step = descriptor([], command="cat", output_eval="$(self[0].contents)")
    step["arguments"] = [{"value": "literal.txt"}]
    step["staging"] = [{"entry": {"class": "File", "basename": "literal.txt", "contents": "literal bytes"}}]
    assert execute(tool_runtime, step) == "literal bytes"


@pytest.mark.parametrize("value,expected", [(None, 7), (False, False), (0, 0), ("", "")])
def test_input_default_precedes_valuefrom_and_preserves_falsey_data(tool_runtime, value, expected):
    step = descriptor([], command="true", inputs={"value": "p_value"},
        input_types={"value": "value"}, output_eval="$(JSON.stringify(inputs.value))")
    step.pop("stdout")
    step["runtimeOutputs"]["out"].pop("glob")
    step["inputTransforms"] = {"value": {"default": 7, "evaluate": expression("return self;")}}
    result = json.loads(execute(tool_runtime, step, {"p_value": value}))
    assert result == expected
    assert type(result) is type(expected)


def test_preparation_publishes_transformed_inputs_before_tool_type_validation(tool_runtime):
    step = {
        "displayName": "prepare", "inputs": {"p_value": {"type": "int"}},
        "bindings": {"inputs": {"object": {"value": {"port": "p_value"}}}},
        "inputTransforms": {"value": {"evaluate": expression("return inputs.value + 1;")}},
        "inputSchemas": {"value": {"type": "string"}},
        "prepare": {"output": "prepared"},
        "outputs": {"prepared": {}}, "runtimeOutputs": {"prepared": {"type": "file", "schema": {"type": "any"}}},
    }
    tool_runtime["METADATA"] = {"steps": {"prepare": step}}
    result = tool_runtime["_execute_bound"]("prepare", {"p_value": 1})
    assert result == {"prepared": {"value": 2}}
    assert tool_runtime["_resolve_bindings"](
        {"self": {"port": "prepared", "field": "value"}}, result,
        input_types={"prepared": {"type": "file"}}) == {"self": 2}
