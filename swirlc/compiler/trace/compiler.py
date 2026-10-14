from __future__ import annotations

from typing import Optional, TextIO

from swirlc.compiler.standard.compiler import StructuredCompiler, TraceNode
from swirlc.core.entity import Data, Location, Step


class TraceTarget(StructuredCompiler):
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

    def render_location(self, location, dataset, root):
        path = __import__("pathlib").Path(self.outdir, f"{location.name}.md")
        with path.open("w") as trace:
            self.write_location_start(location, trace)
            for port, data in dataset:
                trace.write(f"input {port}: ({data.name}, {getattr(data, 'identity', 'root')}) [{data.type}] = {data.value!r}\n")
            self._render(root, trace, 0, [], set())
            self.write_location_end(location, trace)

    def _render(self, node, trace, depth, owners, bound):
        prefix = "  " * depth
        label = self._label(node)
        kind = node.kind
        args = node.args
        if kind in ("seq", "par", "choice", "repl"):
            owner = label if kind == "repl" else None
            annotation = f" owner={owner}; fresh environment; concurrent admission" if owner else ""
            if kind == "choice":
                guard = args.get("guard")
                annotation = f" guard=[{guard['port']} has data in {guard['scope']}]" if guard else " guard=atomic enabled branch"
            trace.write(f"{prefix}{label}: {kind}{annotation} {{\n")
            child_bound = set(bound)
            branch_bounds = []
            for child in node.children.values():
                branch_bound = child_bound if kind == "seq" else set(bound)
                self._render(child, trace, depth + 1, owners + ([owner] if owner else []), branch_bound)
                branch_bounds.append(branch_bound)
            join = "drain admitted instances and descendants" if owner else "join activated descendants"
            trace.write(f"{prefix}}} wait {label}: {join}\n")
            if kind == "seq":
                bound.update(child_bound)
            elif kind == "par":
                for branch_bound in branch_bounds:
                    bound.update(branch_bound)
            elif kind == "choice" and branch_bounds:
                bound.update(set.intersection(*branch_bounds))
        elif kind == "exec":
            def flow(pairs):
                return "{" + ", ".join(str(t) if t.kind == "collection" else f"({p}, {t})"
                                        for p, t in pairs) + "}"
            descriptor = self.metadata["steps"][args["tool"]]
            operation = f" operation={descriptor['operationId']} scope={descriptor['scope']}" if "operationId" in descriptor else ""
            trace.write(f"{prefix}{label}: exec {args['tool']} {flow(args['inputs'])} -> {flow(args['outputs'])} mapping={args['mapping']}{operation}\n")
            for _, term in args['outputs']:
                bound.update(getattr(term, 'variables', lambda: set())())
        elif kind in ("recv", "send", "move"):
            term = args['term']
            variables = set(getattr(term, 'variables', lambda: set())())
            detail = f" fresh={sorted(variables - bound)} exact={sorted(variables & bound)}" if kind == "recv" else ""
            trace.write(f"{prefix}{label}: {kind} {term} [{args['data_type']}] {args['src']} -> {args['dst']} : {args['port']}{detail}\n")
            if kind == "recv":
                bound.update(variables)
        elif kind == "end":
            trace.write(f"{prefix}{label}: end(): close owner={owners[-1] if owners else 'INVALID'}; stop admission and drain\n")
        else:
            trace.write(f"{prefix}{label}: zero (null process)\n")
