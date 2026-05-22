from __future__ import annotations

from collections.abc import MutableMapping, MutableSequence
import os
from typing import Callable, Optional, TextIO

from swirlc.core.compiler import BaseCompiler
from swirlc.core.entity import Data, Location, Port, Step, Workflow

thread_counter = 0

class Thread:
  def __init__(self, depth: int = 0, parent: Optional[Thread] = None) -> None:
    self.sub_threads: MutableMapping[str, Thread] = {}
    self.depth = depth
    self.parent = parent

    global thread_counter
    self.id = f"thread_{thread_counter}"
    thread_counter += 1
    
  def write_thread_start(self, trace: TextIO):
    trace.write(f"{'  ' * self.depth}{self.id} = Thread {{\n")
    
  def write_wait_for(self, trace: TextIO):
    trace.write(f"{'  ' * self.depth}Wait: {self.id}\n")
    
  def write_thread_end(self, trace: TextIO, comment: Optional[str] = None):
    comment_str = f" {comment}" if comment else ""
    trace.write(f"{'  ' * self.depth}}} // End of {self.id}{comment_str}\n")
    
  def start_sub_thread(self, trace: TextIO) -> Thread:
    new_thread = Thread(depth=self.depth + 1, parent=self)
    self.sub_threads[new_thread.id] = new_thread
    
    return new_thread
  
  def get_last_sub_thread(self) -> Optional[Thread]:
    if not self.sub_threads:
      return None
    return list(self.sub_threads.values())[-1]
  
  def pop_sub_thread(self) -> Optional[Thread]:
    if not self.sub_threads:
      return None
    return self.sub_threads.popitem()[1]
  
  def delete_sub_thread(self, thread_id: str) -> None:
    if thread_id in self.sub_threads:
      del self.sub_threads[thread_id]

  def close_thread(self, trace: TextIO) -> None:
    # wait for all sub-threads to finish
    for _, sub_thread in self.sub_threads.items():
      sub_thread.write_wait_for(trace)
      
    self.sub_threads = {}

class TraceTarget(BaseCompiler):
    def __init__(self, outdir: str) -> None:
        super().__init__(outdir)
        
        self.current_workflow: Optional[Workflow] = None
        self.current_location: Optional[Location] = None
        self.location_traces: MutableMapping[str, TextIO] = {}
        self.current_thread: Optional[Thread] = None
        
# ======== Utils ========
    def _open_location_trace(self, location: Location) -> TextIO:
        trace = open(
            os.path.join(self.outdir, f"{location.name}.md"), "w"
        )
        return trace
      
    def _close_location_trace(self, location: Location) -> None:
        trace = self.location_traces[location.name]
        trace.close()
        
    def _get_location_trace(self, location: Location) -> TextIO:
        assert location.name in self.location_traces
        return self.location_traces[location.name]

# ======== Workflow ========
    def begin_workflow(self, workflow: Workflow) -> None:
        self.current_workflow = workflow

    def end_workflow(self) -> None:
        self.current_workflow = None

# ====== Location ========
    def begin_location(self, location: Location) -> None:
        global thread_counter
        thread_counter = 0
        
        self.current_location = location
        self.location_traces[location.name] = self._open_location_trace(location)
        
        trace = self._get_location_trace(location)
        trace.write(f"# Location: {location.name}\n\n")
        trace.write("```js\n")
        
        self.current_thread = Thread(depth=0)
        self.current_thread.write_thread_start(trace)

    def end_location(self) -> None:
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        thread = self.current_thread
        assert thread.depth == 0, "Current thread is not the main thread when ending location"
        thread.close_thread(trace)
        thread.write_thread_end(trace)
        thread.write_wait_for(trace)
        
        trace.write("```\n")
            
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
        indent = "  " * (thread.depth + 1)

        for port, data in dataset:
            trace.write(f"{indent}Dataset: {data.name} of type {data.type} on port {port} with value {data.value}\n")
            
# ======== Thread =======
    def begin_paren(self) -> None:
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        self.current_thread = self.current_thread.start_sub_thread(trace)
        self.current_thread.write_thread_start(trace)

    def end_paren(self):
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        self.current_thread.close_thread(trace)
        self.current_thread.write_thread_end(trace)
        
        assert self.current_thread.parent is not None, "Current thread has no parent to return to"
        self.current_thread = self.current_thread.parent

# ======== Parallel ========
    def end_par(self) -> None:
        pass

    def par(self) -> None:
        pass

    def begin_par(self) -> None:
        pass

# ======== Choice ========
    def begin_choice(self) -> None:
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        self.current_thread = self.current_thread.start_sub_thread(trace)
        indent = "  " * self.current_thread.depth
        trace.write(f"{indent}{self.current_thread.id} = If(condition) {{\n")
      
    def choice(self):
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        sub_thread = self.current_thread.pop_sub_thread()
        assert sub_thread is not None, "No sub-thread to end for choice"
        sub_thread.close_thread(trace)
        sub_thread.write_wait_for(trace)
        
        trace.write(f"{'  ' * self.current_thread.depth}}} else {{\n")
        
      
    def end_choice(self) -> None:
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        self.current_thread.close_thread(trace)
        self.current_thread.write_thread_end(trace, comment="(Choice)")
        self.current_thread = self.current_thread.parent

# ========= Sequential ========
    def seq(self):
        # wait on last thread
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        last_thread = self.current_thread.pop_sub_thread()
        if last_thread is not None:
            last_thread.close_thread(trace)
            last_thread.write_wait_for(trace)

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
        indent = "  " * thread.depth
        trace.write(f"{indent}{thread.id} = Exec: {step.name}\n")

    def recv(self, port: str, data_type: str, src: str, dst: str):
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        thread = self.current_thread.start_sub_thread(trace)
        indent = "  " * thread.depth
        trace.write(f"{indent}{thread.id} = Recv: {data_type} from {src} to {dst}\n")

    def send(self, data: str, port: str, data_type: str, src: str, dst: str):
        assert self.current_location is not None
        assert self.current_thread is not None
        
        trace = self._get_location_trace(self.current_location)
        
        thread = self.current_thread.start_sub_thread(trace)
        indent = "  " * thread.depth
        trace.write(f"{indent}{thread.id} = Send: {data} of type {data_type} from {src} to {dst}\n")
