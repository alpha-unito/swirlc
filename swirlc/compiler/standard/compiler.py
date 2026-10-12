from __future__ import annotations

import os
from collections.abc import MutableMapping, MutableSequence
from typing import Optional, TextIO

from swirlc.core.compiler import BaseCompiler
from swirlc.core.entity import Data, DistributedWorkflow, Location, Step, Workflow


class TraceNode:
    counter = 0

    def __init__(self, depth: int = 0, parent: Optional[TraceNode] = None, is_threaded: bool = True) -> None:
        self.children: MutableMapping[str, TraceNode] = {}
        self.kind = "seq"
        self.args = {}
        self.depth = depth
        self.parent = parent
        self.is_threaded = is_threaded
        self.is_repl = False
        self.has_scatter_moves = False
        self.repl_sources: set[str] = set()
        self.is_choice = False
        self.has_choice = False
        self.choice_guard = "True"
        self.choice_eof_branch: int | None = None

        self.id = f"thread_{TraceNode.counter}"
        self.handle = f"handle_{TraceNode.counter}"
        TraceNode.counter += 1

    @property
    def in_repl(self) -> bool:
        curr = self.parent
        while curr:
            if getattr(curr, "is_repl", False):
                return True
            curr = curr.parent
        return False

    def set_depth(self, depth: int):
        self.depth = depth
        for child in self.children.values():
            child.set_depth(depth + 1)

    def reset_counter(self):
        TraceNode.counter = 0

    def add_child(self, trace: TextIO, is_threaded: bool = True) -> TraceNode:
        new_node = TraceNode(depth=self.depth + 1, parent=self, is_threaded=is_threaded)
        self.children[new_node.id] = new_node
        return new_node

    def get_last_child(self) -> Optional[TraceNode]:
        if not self.children:
            return None
        return list(self.children.values())[-1]

    def pop_child(self) -> Optional[TraceNode]:
        if not self.children:
            return None
        return self.children.popitem()[1]

    def delete_child(self, node_id: str) -> None:
        if node_id in self.children:
            del self.children[node_id]

    def pop_children(self) -> list[TraceNode]:
        nodes = list(self.children.values())
        self.children.clear()
        return nodes


class StandardCompiler(BaseCompiler):
    def __init__(self, outdir: str, tmpdir: str | None = None) -> None:
        super().__init__(outdir, tmpdir)


        self.current_workflow: Optional[DistributedWorkflow] = None
        self.current_location: Optional[Location] = None
        self.location_traces: MutableMapping[str, TextIO] = {}
        self.current_node: Optional[TraceNode] = None

    # ======== Writes =======
    def write_thread_start(self, node: TraceNode, indent: int, trace: TextIO):
        pass

    def write_wait_for(self, node: TraceNode, indent: int, trace: TextIO):
        pass

    def write_thread_end(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        comment: Optional[str] = None,
    ):
        pass

    def write_exec(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        pass

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
        pass

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
        pass

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
        pass

    def write_choice_start(
        self, node: TraceNode, indent: int, trace: TextIO, guard: str = "True"
    ):
        pass

    def write_choice_alt(self, node: TraceNode, indent: int, trace: TextIO):
        pass

    def write_choice_end(self, node: TraceNode, indent: int, trace: TextIO):
        pass

    def write_repl_start(
        self,
        node: TraceNode,
        indent: int,
        trace: TextIO,
    ):
        pass


    def write_repl_end(self, node: TraceNode, indent: int, trace: TextIO):
        pass

    def write_zero(self, node: TraceNode, indent: int, trace: TextIO):
        pass

    def write_dataset(
        self, node: TraceNode, indent: int, trace: TextIO, port: str, data: Data
    ):
        pass

    def write_location_start(self, location: Location, trace: TextIO):
        pass

    def write_location_end(self, location: Location, trace: TextIO):
        pass

    # ======== Threading policy ========
    def exec_is_threaded(self) -> bool:
        return True

    def recv_is_threaded(self) -> bool:
        return True

    def send_is_threaded(self) -> bool:
        return True

    def move_is_threaded(self) -> bool:
        return True


    # ======== Utils ========
    def _open_location_trace(self, location: Location) -> TextIO:
        trace = open(os.path.join(self.outdir, f"{location.name}.md"), "w")
        return trace

    def _close_location_trace(self, location: Location) -> None:
        trace = self.location_traces[location.name]
        trace.close()

    def _get_location_trace(self, location: Location) -> TextIO:
        assert location.name in self.location_traces
        return self.location_traces[location.name]

    def _close_node(self, node: TraceNode, trace: TextIO) -> None:
        for child in node.pop_children():
            if child.is_threaded:
                self.write_wait_for(child, node.depth + 1, trace)

    # ======== Workflow ========
    def begin_workflow(self, workflow: Workflow) -> None:
        if not isinstance(workflow, DistributedWorkflow):
            raise ValueError("Workflow must be a DistributedWorkflow")
        TraceNode.counter = 0
        self.current_workflow = workflow

    def end_workflow(self) -> None:
        self.current_workflow = None

    # ====== Location ========
    def begin_location(self, location: Location) -> None:
        if self.current_node is not None:
            self.current_node.reset_counter()
        self.current_node = TraceNode(depth=0)

        self.current_location = location
        self.location_traces[location.name] = self._open_location_trace(location)

        trace = self._get_location_trace(location)
        self.write_location_start(location, trace)

        self.write_thread_start(self.current_node, 0, trace)

    def end_location(self) -> None:
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        node = self.current_node
        assert (
            node.depth == 0
        ), "Current node is not the root when ending location"
        self._close_node(node, trace)
        self.write_thread_end(node, node.depth, trace)
        self.write_wait_for(node, node.depth, trace)
        self.write_location_end(self.current_location, trace)

        self._close_location_trace(self.current_location)
        self.current_location = None

    def begin_dataset(
        self,
        dataset: MutableSequence[tuple[str, Data]],
    ):
        assert self.current_location is not None
        assert self.current_node is not None

        trace = self._get_location_trace(self.current_location)
        node = self.current_node

        for port, data in dataset:
            self.write_dataset(node, node.depth + 1, trace, port, data)

    # ======== Thread / Grouping =======
    def begin_paren(self) -> None:
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        curr: TraceNode | None = self.current_node
        in_choice_or_repl = False
        while curr:
            if (
                getattr(curr, "is_choice", False)
                or getattr(curr, "has_choice", False)
                or getattr(curr, "is_repl", False)
            ):
                in_choice_or_repl = True
                break
            curr = curr.parent

        if in_choice_or_repl:
            self.current_node = self.current_node.add_child(trace, is_threaded=False)
            self.current_node.depth = self.current_node.parent.depth
        else:
            self.current_node = self.current_node.add_child(trace)
            self.write_thread_start(self.current_node, self.current_node.depth, trace)

    def end_paren(self):
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        self._close_node(self.current_node, trace)
        if self.current_node.is_threaded:
            self.write_thread_end(self.current_node, self.current_node.depth, trace)

        assert (
            self.current_node.parent is not None
        ), "Current node has no parent to return to"
        self.current_node = self.current_node.parent

    # ======== Parallel ========

    # ========= Sequential ========
    def seq(self):
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        last_node = self.current_node.pop_child()
        if last_node is not None:
            self._close_node(last_node, trace)
            if last_node.is_threaded:
                self.write_wait_for(last_node, last_node.depth, trace)

    # ======== Operation ========
    def exec(
        self,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)
        node = self.current_node.add_child(trace, is_threaded=self.exec_is_threaded())

        self.write_exec(node, node.depth, trace, step, flow, mapping)

    def recv(self, port: str, data: str, data_type: str, src: str, dst: str):
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)
        node = self.current_node.add_child(trace, is_threaded=self.recv_is_threaded())

        self.write_recv(node, node.depth, trace, port, data, data_type, src, dst)

    def send(self, data: str, port: str, data_type: str, src: str, dst: str):
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)
        node = self.current_node.add_child(trace, is_threaded=self.send_is_threaded())

        self.write_send(node, node.depth, trace, data, port, data_type, src, dst)

    def move(self, data: str, port: str, data_type: str, src: str, dst: str):
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)
        node = self.current_node.add_child(trace, is_threaded=self.move_is_threaded())

        self.write_move(node, node.depth, trace, data, port, data_type, src, dst)

    # ======== Choice ========
    def begin_choice(self, guard: str = "True", eof_branch: int | None = None) -> None:
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        new_node = TraceNode(depth=self.current_node.depth + 1, parent=self.current_node, is_threaded=False)
        self.current_node.children[new_node.id] = new_node
        self.current_node = new_node
        self.current_node.is_choice = True
        self.current_node.choice_guard = guard
        self.current_node.choice_eof_branch = eof_branch
        curr: TraceNode | None = self.current_node
        while curr:
            curr.has_choice = True
            curr = curr.parent
        self.write_choice_start(self.current_node, self.current_node.depth, trace, guard=guard)

    def choice(self) -> None:
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        self._close_node(self.current_node, trace)
        self.write_choice_alt(self.current_node, self.current_node.depth, trace)

    def end_choice(self) -> None:
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        self._close_node(self.current_node, trace)
        self.write_choice_end(self.current_node, self.current_node.depth, trace)

        assert (
            self.current_node.parent is not None
        ), "Current node has no parent to return to"
        self.current_node = self.current_node.parent

    # ======== Replication ========
    def begin_repl(self) -> None:
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        self.current_node = self.current_node.add_child(trace)
        self.current_node.is_repl = True
        self.write_repl_start(self.current_node, self.current_node.depth, trace)
        self.current_node.depth += 1



    def end_repl(self) -> None:
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)

        self._close_node(self.current_node, trace)
        self.current_node.depth -= 1
        self.write_repl_end(self.current_node, self.current_node.depth, trace)

        assert (
            self.current_node.parent is not None
        ), "Current node has no parent to return to"
        self.current_node = self.current_node.parent


    # ======== Zero ========
    def zero(self) -> None:
        assert self.current_location is not None
        assert self.current_node is not None
        trace = self._get_location_trace(self.current_location)
        node = self.current_node.add_child(trace, is_threaded=False)
        self.write_zero(node, node.depth, trace)


class StructuredCompiler(StandardCompiler):
    """Collect the shared trace nodes before rendering either backend."""

    def begin_location(self, location):
        self.current_location = location
        self.current_node = TraceNode()
        self._root = self.current_node
        self._dataset = []

    def begin_dataset(self, dataset):
        self._dataset.extend(dataset)

    def end_location(self):
        self.render_location(self.current_location, self._dataset, self._root)
        self.current_location = None
        self.current_node = None

    def _begin(self, kind, **args):
        node = TraceNode(parent=self.current_node, depth=self.current_node.depth + 1)
        node.kind, node.args = kind, args
        self.current_node.children[node.id] = node
        self.current_node = node

    def _end(self):
        self.current_node = self.current_node.parent

    def _action(self, kind, **args):
        self._begin(kind, **args)
        self._end()

    def begin_paren(self):
        self._begin("seq")

    def end_paren(self):
        self._end()

    def begin_seq(self):
        self._begin("seq")

    def seq(self):
        pass

    def end_seq(self):
        self._end()

    def begin_par(self):
        self._begin("par")

    def par(self):
        pass

    def end_par(self):
        self._end()

    def begin_choice(self, guard=None, eof_branch=None):
        self._begin("choice", guard=guard)

    def choice(self):
        pass

    def end_choice(self):
        self._end()

    def begin_repl(self):
        self._begin("repl")

    def end_repl(self):
        self._end()

    def zero(self):
        self._action("zero")

    def end(self):
        self._action("end")

    def exec(self, step, flow, mapping):
        self._action("exec", tool=step.name, inputs=flow[0], outputs=flow[1], mapping=sorted(mapping))

    def recv(self, port, data, data_type, src, dst):
        self._action("recv", port=port, term=data, data_type=data_type, src=src, dst=dst)

    def send(self, data, port, data_type, src, dst):
        self._action("send", port=port, term=data, data_type=data_type, src=src, dst=dst)

    def move(self, data, port, data_type, src, dst):
        self._action("move", port=port, term=data, data_type=data_type, src=src, dst=dst)

    @staticmethod
    def serialize(node):
        def value(item):
            if hasattr(item, "to_dict"):
                return item.to_dict()
            if isinstance(item, (tuple, list)):
                return [value(x) for x in item]
            if isinstance(item, dict):
                return {k: value(v) for k, v in item.items()}
            return item
        return {"kind": node.kind, **value(node.args), "children": [StructuredCompiler.serialize(x) for x in node.children.values()]}
