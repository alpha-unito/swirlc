import os
import socket
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from typing import Any

from swirlc.compiler.default.runtime import Runtime, _frame, _unframe


def term(kind, name='', *items):
    return {'kind': kind, 'name': name, 'items': list(items)}


def envelope(payload, identity):
    return term('tuple', '', payload, identity)


ROOT = term('literal', 'root')


class ScopedRuntimeTests(unittest.TestCase):
    def runtime(self, metadata=None):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        runtime = Runtime(metadata or {'steps': {}, 'dependencies': {}}, 'local',
                          {'local': listener.getsockname()}, listener,
                          lambda sock, kind, value: _frame(sock, value),
                          lambda sock, kind: _unframe(sock), lambda name, inputs: inputs)
        runtime.timeout = .5
        runtime.start()
        self.addCleanup(runtime.close)
        return runtime

    def test_atomic_match_does_not_bind_on_wrong_scope(self):
        runtime = self.runtime()
        runtime.offers.append({'src': 'other', 'port': 'p', 'id': (2, 3),
                               'value': 'data', 'type': 'string', 'event': threading.Event()})
        pattern = envelope(term('variable', 'payload'), term('path', '', ROOT,
                           term('variable', 'parent'), term('variable', 'child')))
        env = {'parent': 1}
        self.assertFalse(runtime.try_receive(env, 'p', pattern, 'other'))
        self.assertEqual(env, {'parent': 1})
        self.assertEqual(len(runtime.offers), 1)

    def test_receive_acknowledges_commit_and_preserves_scalar(self):
        runtime = self.runtime()
        action = {'kind': 'send', 'src': 'local', 'dst': 'local', 'port': 'p',
                  'data_type': 'int', 'term': envelope(term('variable', 'value'), ROOT)}
        done = threading.Event()
        worker = threading.Thread(target=lambda: (runtime.send({'value': 7}, 'p', action['term'], 'int', 'local', 'local'), done.set()))
        worker.start()
        runtime._wait(lambda: bool(runtime.offers), 'test offer')
        self.assertFalse(done.is_set())
        env = {}
        runtime.recv(env, 'p', envelope(term('variable', 'received'), ROOT), 'local')
        worker.join(1)
        self.assertTrue(done.is_set())
        self.assertEqual(runtime.values[0]['payload'], 7)

    def test_control_like_payloads_are_data_and_controls_never_match_data(self):
        for value in ['begin', 'eof', ('begin', 'eof')]:
            with self.subTest(value=value):
                runtime = self.runtime()
                sent = []
                runtime._send_header = lambda dst, header, payload=None, sent=sent: sent.append((header, payload))
                runtime.send({'value': value, '_payload_types': {'value': ['string', 'string']} if isinstance(value, tuple) else {}},
                             'p', envelope(term('variable', 'value'), ROOT), 'string', 'local', 'local')
                header, payload = sent[0]
                self.assertIsNone(header['control'])
                self.assertEqual(payload, value)
                offer = dict(header, value=value, id=(), event=threading.Event())
                runtime.offers.append(offer)
                pattern = term('tuple', '', term('variable', 'a'), term('variable', 'b')) if isinstance(value, tuple) else term('variable', 'v')
                env = {}
                action = {'kind': 'recv', 'src': 'local', 'port': 'p', 'term': envelope(pattern, ROOT)}
                with runtime.condition:
                    self.assertTrue(runtime.try_receive(env, action['port'], action['term'], action['src']))
                self.assertEqual(runtime.values[-1]['payload'], value)
                runtime.offers.append(dict(header, control='eof', value='eof', id=(), event=threading.Event()))
                generic = dict(action, term=envelope(pattern, term('variable', 'scope')))
                self.assertFalse(runtime.try_receive({}, generic['port'], generic['term'], generic['src']))
                control_receive = dict(action, term=envelope(term('literal', 'eof'), ROOT))
                with runtime.condition:
                    self.assertTrue(runtime.try_receive({}, control_receive['port'], control_receive['term'], control_receive['src']))
                self.assertEqual(len(runtime.values), 1)

    def test_tuple_homogeneous_list_type_fallback_and_unknown_type_rejection(self):
        runtime = self.runtime()
        variable = term('variable', 'pair')
        self.assertEqual(runtime._payload_type(variable, {}, 'list[int]', (1, 2)), ['int', 'int'])
        self.assertEqual(runtime._payload_type(variable, {}, 'list[list[string]]', (('begin',), ('eof',))), [['string'], ['string']])
        with self.assertRaisesRegex(ValueError, 'lacks component transport types'):
            runtime._payload_type(variable, {}, 'string', ('begin', 2))

    def test_actual_socket_preserves_heterogeneous_nested_tuple_and_file(self):
        from swirlc.compiler.default.compiler import framing_helpers, list_helper
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / 'source.txt'
        source.write_text('file contents\n')
        metadata = {'steps': {}, 'dependencies': {
            'text': {'type': 'string'}, 'number': {'type': 'int'},
            'file': {'type': 'file'}, 'tail': {'type': 'string'}
        }}
        runtime = self.runtime(metadata)
        namespace = {'socket': socket, 'Any': Any, 'os': os, 'uuid': uuid,
                     'SCRATCH_DIR': temporary.name, 'BUF_SIZE': 4096}
        exec(list_helper + framing_helpers, namespace)
        runtime.send_value, runtime.recv_value = namespace['_send_value'], namespace['_recv_value']
        payload = term('tuple', '', term('literal', 'text'), term('literal', 'number'),
                       term('tuple', '', term('literal', 'file'), term('literal', 'tail')))
        action = {'kind': 'send', 'src': 'local', 'dst': 'local', 'port': 'p',
                  'data_type': 'string', 'term': envelope(payload, ROOT)}
        sender = threading.Thread(target=runtime.send, args=(
                  {'text': 'begin', 'number': 42, 'file': str(source), 'tail': 'eof'}, 'p', action['term'], 'string', 'local', 'local'))
        sender.start()
        bindings = {}
        receive = {'kind': 'recv', 'src': 'local', 'port': 'p', 'term': envelope(term('variable', 'pair'), ROOT)}
        runtime.recv(bindings, 'p', receive['term'], 'local')
        sender.join(1)
        self.assertFalse(sender.is_alive())
        received = bindings['pair']
        self.assertIsInstance(received, tuple)
        self.assertEqual(received[:2], ('begin', 42))
        self.assertIsInstance(received[1], int)
        self.assertIsInstance(received[2], tuple)
        self.assertEqual(Path(received[2][0]).read_text(), 'file contents\n')
        self.assertEqual(received[2][1], 'eof')
        self.assertEqual(bindings['_payload_types']['pair'], ['string', 'int', ['file', 'string']])
        forward = dict(action, port='q', data_type='dynamic', term=envelope(term('variable', 'pair'), ROOT))
        sender = threading.Thread(target=runtime.send, args=(bindings, 'q', forward['term'], 'dynamic', 'local', 'local'))
        sender.start()
        rebound = {}
        runtime.recv(rebound, 'q', receive['term'], 'local')
        sender.join(1)
        self.assertFalse(sender.is_alive())
        self.assertEqual(rebound['pair'][:2], ('begin', 42))
        self.assertEqual(Path(rebound['pair'][2][0]).read_text(), 'file contents\n')
        self.assertEqual(rebound['_payload_types']['pair'], ['string', 'int', ['file', 'string']])

    def test_scoped_snapshot_preserves_occurrences_and_nested_payload(self):
        runtime = self.runtime()
        runtime._store('p', (1, 0), ['same', 'same'], 'list[string]')
        runtime._store('p', (2, 0), [], 'list[string]')
        runtime._store('other', (1, 0), 'foreign', 'string')
        selected = runtime._snapshot('p', (1,))
        self.assertEqual([v['payload'] for v in selected], [['same', 'same']])

    def test_closed_stream_missing_bound_key_fails_without_blocking(self):
        runtime = self.runtime()
        runtime.closed.add(('source', 'p', ()))
        action = {'kind': 'recv', 'src': 'source', 'port': 'p',
                  'term': envelope(term('variable', 'value'), term('path', '', ROOT, term('variable', 'i')))}
        with self.assertRaisesRegex(ValueError, 'missing required key'):
            runtime.try_receive({'i': 2}, action['port'], action['term'], action['src'])

    def test_failure_wakes_blocked_receive(self):
        runtime = self.runtime()
        errors = []
        def receive():
            try:
                runtime.recv({}, 'p', envelope(term('variable', 'value'), ROOT), 'source')
            except Exception as exc:
                errors.append(exc)
        worker = threading.Thread(target=receive)
        worker.start()
        runtime.fail(ValueError('scoped task failure'))
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertRegex(str(errors[0]), 'scoped task failure')

    def test_replication_admits_concurrently_and_drains_before_join(self):
        runtime = self.runtime({'steps': {'task': {}}, 'dependencies': {}})
        both_started = threading.Event()
        second_finished = threading.Event()
        started = []
        finished = []
        lock = threading.Lock()
        def execute(name, inputs):
            with lock:
                started.append(inputs['p'])
                if len(started) == 2:
                    both_started.set()
            if not both_started.wait(.3):
                raise AssertionError('replicas were serialized')
            if inputs['p'] == 0:
                if not second_finished.wait(.3):
                    raise AssertionError('second replica did not finish independently')
            finished.append(inputs['p'])
            if inputs['p'] == 1:
                second_finished.set()
            return {}
        runtime.execute = execute
        data = envelope(term('variable', 'value'), term('path', '', ROOT, term('variable', 'i')))
        close = envelope(term('literal', 'eof'), ROOT)
        owner = runtime.new_owner()
        def selector(env):
            if runtime.try_receive(env, 'p', data, 'local'):
                return 0
            if runtime.try_receive(env, 'p', close, 'local'):
                return 1
            return None
        def task(env, owner):
            runtime.execute_step(env, 'task', [['p', data]], [])
        def produce():
            for i in range(2):
                runtime.send({'value': i, 'i': i}, 'p', data, 'int', 'local', 'local')
            runtime.send({}, 'p', close, None, 'local', 'local')
        producer = threading.Thread(target=produce)
        producer.start()
        while not owner['closed']:
            branch, candidate = runtime.admit({}, owner, selector)
            if branch == 0:
                runtime.spawn(owner, task, candidate)
            elif branch == 1:
                runtime.end(owner)
        runtime.join(owner)
        runtime.finish()
        producer.join(1)
        self.assertFalse(producer.is_alive())
        self.assertEqual(finished, [1, 0])

    def test_scoped_failure_wakes_parallel_completion_join(self):
        runtime = self.runtime({'steps': {'failure': {}}, 'dependencies': {}})
        runtime.execute = lambda name, inputs: (_ for _ in ()).throw(ValueError('failed child'))
        def blocked(env, owner):
            runtime.recv(env, 'blocked', envelope(term('variable', 'v'), ROOT), 'source')
        def failure(env, owner):
            runtime.execute_step(env, 'failure', [], [])
        with self.assertRaisesRegex(Exception, 'failed child'):
            runtime.parallel({}, None, blocked, failure)

    def test_direct_parallel_join_merges_bindings_and_types(self):
        runtime = self.runtime()
        env = {'inherited': 1}
        def left(local, owner):
            self.assertNotIn('right', local)
            local['left'] = 'a'
            runtime._bind_types(term('variable', 'left'), 'string', local)
        def right(local, owner):
            self.assertNotIn('left', local)
            local['right'] = 2
            runtime._bind_types(term('variable', 'right'), 'int', local)
        runtime.parallel(env, None, left, right)
        self.assertEqual(env['left'], 'a')
        self.assertEqual(env['right'], 2)
        self.assertEqual(env['_payload_types'], {'left': 'string', 'right': 'int'})

    def test_exhaustion_requires_finished_dispatch_and_closed_owner_stops_admission(self):
        runtime = self.runtime()
        self.assertFalse(runtime.has_data('p', ROOT, {}))
        self.assertFalse(runtime.exhausted('p', ROOT, {}))
        runtime.finite.add(('p', ()))
        self.assertTrue(runtime.exhausted('p', ROOT, {}))
        runtime._store('p', (0,), 'item', 'string')
        self.assertTrue(runtime.has_data('p', ROOT, {}))
        self.assertFalse(runtime.exhausted('p', ROOT, {}))
        owner = runtime.new_owner()
        runtime.end(owner)
        def forbidden(env):
            raise AssertionError('closed owner attempted admission')
        self.assertEqual(runtime.admit({}, owner, forbidden), (None, None))
        runtime.join(owner)

    def test_direct_executor_preserves_mapping_and_initialization(self):
        runtime = self.runtime({'steps': {'task': {}}, 'dependencies': {}})
        env = runtime.initialize([{'port': 'p', 'name': 'input', 'payload': ['a', 'a'],
                                  'type': 'list[string]', 'identity': ROOT}], {})
        self.assertEqual(env['input'], ['a', 'a'])
        self.assertEqual(runtime.values[0]['id'], ())
        runtime.execute_step(env, 'task', [], [], mapping=['local'])
        with self.assertRaisesRegex(ValueError, 'violates placement'):
            runtime.execute_step(env, 'task', [], [], mapping=['other'])

    def test_nested_cartesian_empty_shape_is_retained(self):
        metadata = {'steps': {'gather': {'type': 'scatter_gather', 'shapeFrom': ['a', 'b'],
                    'operationId': 'op', 'scatterMethod': 'nested_crossproduct',
                    'outputs': {'out': {'dataName': 'result'}}}},
                    'dependencies': {'result': {'type': 'list[list[string]]'}}}
        runtime = self.runtime(metadata)
        runtime.shapes.update({('a', ()): 2, ('b', ()): 0})
        runtime.execute_step({}, 'gather', [['p', term('collection', 'p', term('literal', 'stream'), ROOT)]],
                             [['out', envelope(term('literal', 'result'), ROOT)]])
        self.assertEqual(runtime.values[-1]['payload'], [[], []])

    def test_independent_producers_publish_dynamic_lengths_before_validation(self):
        metadata = {'steps': {}, 'dependencies': {}}
        for name, dimension, port in [('a', 'left', 'pa'), ('b', 'right', 'pb')]:
            metadata['steps'][name] = {'type': 'scatter_dispatch', 'operationId': 'op',
                'dimensions': ['left', 'right'], 'dimension': dimension, 'scatterMethod': 'dotproduct',
                'keySpace': {'dispatches': ['a', 'b']}, 'outputs': {port: {'collection': {'type': 'int'}}}}
        left, right = self.runtime(metadata), self.runtime(metadata)
        left.location, right.location = 'left', 'right'
        addresses = {'left': left.listener.getsockname(), 'right': right.listener.getsockname()}
        left.addresses = right.addresses = addresses
        errors = []
        def dispatch(runtime, name, port, items):
            try:
                runtime.execute_step({'items': items}, name, [['input', envelope(term('variable', 'items'), ROOT)]],
                                     [[port, term('collection', port, term('literal', 'stream'), ROOT)]])
            except Exception as exc:
                runtime.fail(exc)
                errors.append(exc)
        threads = [threading.Thread(target=dispatch, args=(left, 'a', 'pa', [1, 2])),
                   threading.Thread(target=dispatch, args=(right, 'b', 'pb', [3]))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(1)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(errors), 2)
        self.assertTrue(all('cardinalities differ' in str(error) for error in errors))
        self.assertEqual(left.shapes['b', ()], 1)
        self.assertEqual(right.shapes['a', ()], 2)

    def test_all_dimensions_route_same_full_key_to_same_worker(self):
        metadata = {'steps': {
            'a': {'type': 'scatter_dispatch', 'operationId': 'same-operation', 'outputs': {'pa': {}}},
            'b': {'type': 'scatter_dispatch', 'operationId': 'same-operation', 'outputs': {'pb': {}}}
        }, 'dependencies': {}}
        runtime = self.runtime(metadata)
        sent = []
        runtime._send_header = lambda dst, header, payload=None, sent=sent: sent.append((dst, header))
        for port in ['pa', 'pb']:
            for i in range(8):
                runtime._store(port, (i,), 'duplicate', 'string')
                runtime.move({}, port, envelope(term('variable', 'v'), term('path', '', ROOT, term('variable', 'i'))),
                             'string', 'local', ['w1', 'w2', 'w3'])
        routes = [{tuple(header['id']): dst for dst, header in sent if header['port'] == port} for port in ['pa', 'pb']]
        self.assertEqual(routes[0], routes[1])
        self.assertEqual(len(routes[0]), 8)

    def test_gather_rejects_missing_and_invalid_keys(self):
        metadata = {'steps': {'gather': {'type': 'scatter_gather', 'shapeFrom': ['a'],
                    'operationId': 'op', 'scatterMethod': 'dotproduct', 'outputs': {}}}, 'dependencies': {}}
        runtime = self.runtime(metadata)
        runtime.shapes['a', ()] = 1
        node = {'tool': 'gather', 'inputs': [['p', term('collection', 'p', term('literal', 'stream'), ROOT)]], 'outputs': []}
        with self.assertRaisesRegex(ValueError, 'missing gather keys'):
            runtime.execute_step({}, node['tool'], node['inputs'], node['outputs'])
        runtime._store('p', (99,), 'invalid', 'string')
        with self.assertRaisesRegex(ValueError, 'invalid gather key'):
            runtime.execute_step({}, node['tool'], node['inputs'], node['outputs'])

    def test_blocked_receive_has_bounded_deadline(self):
        runtime = self.runtime()
        runtime.timeout = .05
        start = time.monotonic()
        with self.assertRaisesRegex(TimeoutError, 'blocked receive'):
            runtime.recv({}, 'p', envelope(term('variable', 'v'), ROOT), 'missing')
        self.assertLess(time.monotonic() - start, .5)

    def test_gather_rejects_duplicate_key(self):
        metadata = {'steps': {'gather': {'type': 'scatter_gather', 'shapeFrom': ['a'],
                    'operationId': 'op', 'scatterMethod': 'dotproduct', 'outputs': {}}}, 'dependencies': {}}
        runtime = self.runtime(metadata)
        runtime.shapes['a', ()] = 1
        runtime._store('p', (0,), 'first', 'string')
        runtime._store('p', (0,), 'second', 'string')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            runtime.execute_step({}, 'gather', [['p', term('collection', 'p', term('literal', 'stream'), ROOT)]], [])


if __name__ == '__main__':
    unittest.main()
