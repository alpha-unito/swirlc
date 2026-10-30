from types import SimpleNamespace

from swirlc.compiler.default.compiler import _PythonEmitter


def test_deep_parallel_trace_compiles_and_preserves_all_branches():
    def node(kind, children=None):
        return SimpleNamespace(kind=kind, args={}, children=children or {})

    root = node('zero')
    for _ in range(150):
        root = node('par', {'left': root, 'right': node('zero')})
    source = _PythonEmitter().generate(root)
    namespace = {}
    exec(compile(source, '<deep trace>', 'exec'), namespace)

    class Runtime:
        calls = 0

        def parallel(self, env, owner, *branches):
            self.calls += 1
            for branch in branches:
                branch(env.copy(), owner)

    runtime = Runtime()
    namespace['workflow'](runtime, {})
    assert runtime.calls == 150
