from __future__ import annotations

from collections.abc import MutableSequence

from swirlc.core.compiler import BaseCompiler
from swirlc.core.entity import Data, Location, Port, Step, Workflow


class TraceCompiler(BaseCompiler):
    def __init__(self, outdir: str) -> None:
        super().__init__(outdir)

# ======== Workflow ========
    def begin_workflow(self, workflow: Workflow) -> None:
        pass

    def end_workflow(self) -> None:
        pass

# ====== Location ========
    def begin_location(self, location: Location) -> None:
        pass
      
    def end_location(self) -> None:
        pass
      
    def begin_dataset(
        self,
        dataset: MutableSequence[tuple[str, Data]],
    ):
        pass
      
# ======== Thread =======
    def begin_paren(self) -> None:
        pass

    def end_paren(self):
        pass

# ======== Parallel ========
    def end_par(self) -> None:
        pass

    def par(self) -> None:
        pass

    def begin_par(self) -> None:
        pass

# ======== Choice ========
    def choice(self):
        pass

# ========= Sequential ========
    def seq(self):
        pass

# ======== Operation ========
    def exec(
        self,
        step: Step,
        flow: tuple[set[tuple[str, str]], set[tuple[str, str]]],
        mapping: set[str],
    ):
        pass

    def recv(self, port: str, data_type: str, src: str, dst: str):
        pass

    def send(self, data: str, port: str, data_type: str, src: str, dst: str):
        pass
