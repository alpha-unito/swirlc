from __future__ import annotations

from typing import Optional, TextIO

from swirlc.compiler.standard.compiler import StandardCompiler, TraceNode
from swirlc.core.entity import Data, Location, Step


class TraceTarget(StandardCompiler):
    def __init__(self, outdir: str) -> None:
        super().__init__(outdir)

    # ======== Writes =======
    def write_thread_start(self, node: TraceNode, indent: int, trace: TextIO):
        trace.write(f"{'  ' * indent}{node.id} = Thread {{\n")

    def write_wait_for(self, node: TraceNode, indent: int, trace: TextIO):
        trace.write(f"{'  ' * indent}Wait: {node.id}\n")

    def write_thread_end(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        comment: Optional[str] = None,
    ):
        comment_str = f" {comment}" if comment else ""
        trace.write(f"{'  ' * indent}}} // End of {node.id}{comment_str}\n")

    def write_exec(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        trace.write(f"{'  ' * indent}{node.id} = Exec: {step.name}\n")

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
            f"{'  ' * indent}{node.id} = Recv: {data} of type {data_type} from {src} to {dst} on port {port}\n"
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
            f"{'  ' * indent}{node.id} = Send: {data} of type {data_type} from {src} to {dst} on port {port}\n"
        )

    def write_dataset(
        self, node: TraceNode, indent: int, trace: TextIO, port: str, data: Data
    ):
        trace.write(
            f"{'  ' * indent}Dataset: {data.name} of type {data.type} on port {port} with value {data.value}\n"
        )

    def write_location_start(self, location: Location, trace: TextIO):
        trace.write(f"# Location: {location.name}\n\n")
        trace.write("```js\n")

    def write_location_end(self, location: Location, trace: TextIO):
        trace.write("```\n")
