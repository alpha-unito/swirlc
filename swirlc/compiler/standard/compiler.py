from __future__ import annotations

from collections.abc import MutableMapping, MutableSequence
import os
from typing import Optional, TextIO

from swirlc.core.compiler import BaseCompiler
from swirlc.core.entity import Data, Location, Step, Workflow


class ThreadStack:
    # static counter to generate unique thread IDs
    counter = 0

    def __init__(self, depth: int = 0, parent: Optional[ThreadStack] = None) -> None:
        self.sub_threads: MutableMapping[str, ThreadStack] = {}
        self.depth = depth
        self.parent = parent

        self.id = f"thread_{ThreadStack.counter}"
        ThreadStack.counter += 1

    def reset_counter(self):
        ThreadStack.counter = 0

    def start_sub_thread(self, trace: TextIO) -> ThreadStack:
        new_thread = ThreadStack(depth=self.depth + 1, parent=self)
        self.sub_threads[new_thread.id] = new_thread

        return new_thread

    def get_last_sub_thread(self) -> Optional[ThreadStack]:
        if not self.sub_threads:
            return None
        return list(self.sub_threads.values())[-1]

    def pop_sub_thread(self) -> Optional[ThreadStack]:
        if not self.sub_threads:
            return None
        return self.sub_threads.popitem()[1]

    def delete_sub_thread(self, thread_id: str) -> None:
        if thread_id in self.sub_threads:
            del self.sub_threads[thread_id]

    def pop_sub_threads(self) -> list[ThreadStack]:
        threads = list(self.sub_threads.values())
        self.sub_threads.clear()
        return threads


class StandardCompiler(BaseCompiler):
    def __init__(self, outdir: str) -> None:
        super().__init__(outdir)

        self.current_workflow: Optional[Workflow] = None
        self.current_location: Optional[Location] = None
        self.location_traces: MutableMapping[str, TextIO] = {}
        self.current_thread: Optional[ThreadStack] = None

    # ======== Writes =======
    def write_thread_start(self, thread: ThreadStack, indent: int, trace: TextIO):
        pass

    def write_wait_for(self, thread: ThreadStack, indent: int, trace: TextIO):
        pass

    def write_thread_end(
        self,
        thread: ThreadStack,
        indent: int,
        trace: TextIO,
        comment: Optional[str] = None,
    ):
        pass

    def write_choice_start(self, thread: ThreadStack, indent: int, trace: TextIO):
        pass

    def write_choice_else(self, thread: ThreadStack, indent: int, trace: TextIO):
        pass

    def write_choice_end(self, thread: ThreadStack, indent: int, trace: TextIO):
        pass

    def write_exec(
        self,
        thread: ThreadStack,
        indent: int,
        trace: TextIO,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        pass

    def write_recv(
        self,
        thread: ThreadStack,
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
        thread: ThreadStack,
        indent: int,
        trace: TextIO,
        data: str,
        port: str,
        data_type: str,
        src: str,
        dst: str,
    ):
        pass

    def write_dataset(
        self, thread: ThreadStack, indent: int, trace: TextIO, port: str, data: Data
    ):
        pass

    def write_location_start(self, location: Location, trace: TextIO):
        pass

    def write_location_end(self, location: Location, trace: TextIO):
        pass

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

    def _close_thread(self, thread: ThreadStack, trace: TextIO) -> None:
        # wait for all sub-threads to finish
        for sub_thread in thread.pop_sub_threads():
            self.write_wait_for(sub_thread, thread.depth + 1, trace)

    # ======== Workflow ========
    def begin_workflow(self, workflow: Workflow) -> None:
        self.current_workflow = workflow

    def end_workflow(self) -> None:
        self.current_workflow = None

    # ====== Location ========
    def begin_location(self, location: Location) -> None:
        if self.current_thread is not None:
            self.current_thread.reset_counter()  # reset thread counter for each location
        self.current_thread = ThreadStack(depth=0)

        self.current_location = location
        self.location_traces[location.name] = self._open_location_trace(location)

        trace = self._get_location_trace(location)
        self.write_location_start(location, trace)

        self.write_thread_start(self.current_thread, 0, trace)

    def end_location(self) -> None:
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)

        thread = self.current_thread
        assert (
            thread.depth == 0
        ), "Current thread is not the main thread when ending location"
        self._close_thread(thread, trace)
        self.write_thread_end(thread, thread.depth, trace)
        self.write_wait_for(thread, thread.depth, trace)
        self.write_location_end(self.current_location, trace)

        self._close_location_trace(self.current_location)
        self.current_location = None

    def begin_dataset(
        self,
        dataset: MutableSequence[tuple[str, Data]],
    ):
        assert self.current_location is not None
        assert self.current_thread is not None

        trace = self._get_location_trace(self.current_location)
        thread = self.current_thread

        for port, data in dataset:
            self.write_dataset(thread, thread.depth + 1, trace, port, data)

    # ======== Thread =======
    def begin_paren(self) -> None:
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)

        self.current_thread = self.current_thread.start_sub_thread(trace)
        self.write_thread_start(self.current_thread, self.current_thread.depth, trace)

    def end_paren(self):
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)

        self._close_thread(self.current_thread, trace)
        self.write_thread_end(self.current_thread, self.current_thread.depth, trace)

        assert (
            self.current_thread.parent is not None
        ), "Current thread has no parent to return to"
        self.current_thread = self.current_thread.parent

    # ======== Parallel ========

    # ======== Choice ========
    def begin_choice(self) -> None:
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)

        self.current_thread = self.current_thread.start_sub_thread(trace)
        self.write_choice_start(self.current_thread, self.current_thread.depth, trace)

    def choice(self):
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)

        for sub_thread in self.current_thread.pop_sub_threads():
            self._close_thread(sub_thread, trace)
            self.write_wait_for(sub_thread, sub_thread.depth, trace)

        self.write_choice_else(self.current_thread, self.current_thread.depth, trace)

    def end_choice(self) -> None:
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)

        self._close_thread(self.current_thread, trace)
        self.write_choice_end(self.current_thread, self.current_thread.depth, trace)
        self.current_thread = self.current_thread.parent

    # ========= Sequential ========
    def seq(self):
        # wait on last thread
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)

        last_thread = self.current_thread.pop_sub_thread()
        if last_thread is not None:
            self._close_thread(last_thread, trace)
            self.write_wait_for(last_thread, last_thread.depth, trace)

    # ======== Operation ========
    def exec(
        self,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)
        thread = self.current_thread.start_sub_thread(trace)

        self.write_exec(thread, thread.depth, trace, step, flow, mapping)

    def recv(self, port: str, data: str, data_type: str, src: str, dst: str):
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)
        thread = self.current_thread.start_sub_thread(trace)

        self.write_recv(thread, thread.depth, trace, port, data, data_type, src, dst)

    def send(self, data: str, port: str, data_type: str, src: str, dst: str):
        assert self.current_location is not None
        assert self.current_thread is not None
        trace = self._get_location_trace(self.current_location)
        thread = self.current_thread.start_sub_thread(trace)

        self.write_send(thread, thread.depth, trace, data, port, data_type, src, dst)
