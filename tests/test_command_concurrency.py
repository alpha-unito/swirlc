import ast
import os
import subprocess
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from swirlc.compiler.default.compiler import SCOPED_MAIN


class CommandConcurrencyTests(unittest.TestCase):
    def runner(self):
        tree = ast.parse(SCOPED_MAIN)
        nodes = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "_run_command"
                 or isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id in ("ACTIVE_RUNTIME", "COMMAND_SLOTS")
                     for target in node.targets)]
        namespace = {"BoundedSemaphore": threading.BoundedSemaphore, "subprocess": subprocess, "os": os}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "<runner>", "exec"), namespace)
        return namespace

    def test_at_most_eight_commands_and_releases_slots(self):
        self.check_concurrency("8", 8)

    def test_zero_allows_all_commands_without_waiting_for_slots(self):
        self.check_concurrency("0", 24)

    def check_concurrency(self, slots, expected_peak):
        with patch.dict(os.environ, {"SWIRLC_COMMAND_SLOTS": slots}):
            namespace = self.runner()
        gate, full = threading.Event(), threading.Event()
        lock = threading.Lock()
        active, peak, calls, errors = 0, 0, 0, []

        class Process:
            returncode = 0

            def __init__(self, *args, **kwargs):
                nonlocal active, peak, calls
                with lock:
                    active += 1
                    calls += 1
                    peak = max(peak, active)
                    if active == expected_peak:
                        full.set()

            def communicate(self, *args, **kwargs):
                nonlocal active
                gate.wait(5)
                with lock:
                    active -= 1
                return b"ok", b""

        def run():
            try:
                result = namespace["_run_command"]("unused")
                self.assertEqual(result.stdout, b"ok")
            except BaseException as exc:
                errors.append(exc)

        with patch.object(subprocess, "Popen", Process):
            workers = [threading.Thread(target=run, daemon=True) for _ in range(24)]
            try:
                for worker in workers:
                    worker.start()
                self.assertTrue(full.wait(2))
                with lock:
                    self.assertEqual(calls, expected_peak)
            finally:
                gate.set()
                for worker in workers:
                    worker.join(5)
            self.assertFalse(any(worker.is_alive() for worker in workers))
            self.assertEqual(errors, [])
            self.assertEqual(calls, 24)
            self.assertEqual(peak, expected_peak)
            self.assertEqual(active, 0)

    def test_failure_and_start_errors_release_slots(self):
        namespace = self.runner()
        with patch.object(subprocess, "Popen", side_effect=OSError("cannot start")):
            for _ in range(16):
                with self.assertRaisesRegex(OSError, "cannot start"):
                    namespace["_run_command"]("unused")
        namespace["ACTIVE_RUNTIME"] = SimpleNamespace(error=RuntimeError("failed"))
        with patch.object(subprocess, "Popen") as start:
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                namespace["_run_command"]("unused")
            start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
