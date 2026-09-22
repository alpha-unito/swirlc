from __future__ import annotations

from typing import Optional, TextIO

from swirlc.compiler.standard.compiler import StandardCompiler, TraceNode
from swirlc.core.entity import Data, Location, Step


class TraceTarget(StandardCompiler):
    def __init__(self, outdir: str, tmpdir: str | None = None) -> None:
        super().__init__(outdir, tmpdir)


    @staticmethod
    def _label(node: TraceNode) -> str:
        return node.id.replace("thread_", "t")

    def write_thread_start(self, node: TraceNode, indent: int, trace: TextIO):
        trace.write(f"{'  ' * indent}{self._label(node)} {{\n")

    def write_wait_for(self, node: TraceNode, indent: int, trace: TextIO):
        trace.write(f"{'  ' * indent}wait {self._label(node)}\n")

    def write_thread_end(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        comment: Optional[str] = None,
    ):
        comment_str = f" {comment}" if comment else ""
        trace.write(f"{'  ' * indent}}} // {self._label(node)}{comment_str}\n")

    def write_exec(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        trace.write(f"{'  ' * indent}{self._label(node)}: exec {step.name}\n")

    def write_recv(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        port: str,
        data: str,
        data_type: str,
        src: str,
        dst: str,
    ):
        trace.write(
            f"{'  ' * indent}{self._label(node)}: recv {data} [{data_type}] {src} -> {dst} : {port}\n"
        )

    def write_send(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        data: str,
        port: str,
        data_type: str,
        src: str,
        dst: str,
    ):
        trace.write(
            f"{'  ' * indent}{self._label(node)}: send {data} [{data_type}] {src} -> {dst} : {port}\n"
        )

    def write_move(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        data: str,
        port: str,
        data_type: str,
        src: str,
        dst: str,
    ):
        trace.write(
            f"{'  ' * indent}{self._label(node)}: move {data} [{data_type}] {src} -> {dst} : {port}\n"
        )

    def write_choice_start(self, node: TraceNode, indent: int, trace: TextIO, guard: str = "True"):
        trace.write(f"{'  ' * indent}{self._label(node)}: choice {{\n")

    def write_choice_alt(self, node: TraceNode, indent: int, trace: TextIO):
        trace.write(f"{'  ' * indent}}} otherwise {{\n")

    def write_choice_end(self, node: TraceNode, indent: int, trace: TextIO):
        trace.write(f"{'  ' * indent}}} // choice\n")

    def write_repl_start(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
    ):
        trace.write(f"{'  ' * indent}{self._label(node)}: repeat {{\n")


    def write_repl_end(self, node: TraceNode, indent: int, trace: TextIO):
        trace.write(f"{'  ' * indent}}} // repeat\n")

    def write_zero(self, node: TraceNode, indent: int, trace: TextIO):
        trace.write(f"{'  ' * indent}{self._label(node)}: stop\n")

    def write_dataset(
        self, node: TraceNode, indent: int, trace: TextIO, port: str, data: Data
    ):
        trace.write(
            f"{'  ' * indent}input {port}: {data.name} [{data.type}] = {data.value}\n"
        )

    def write_location_start(self, location: Location, trace: TextIO):
        trace.write(f"# {location.name}\n\n```text\n")

    def write_location_end(self, location: Location, trace: TextIO):
        trace.write("```\n")
