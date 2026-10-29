import socket
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from unittest.mock import MagicMock

import pytest

from swirlc.compiler.default import runtime as runtime_module
from swirlc.compiler.default.runtime import Runtime, _frame, _unframe
from tests.test_scoped_runtime import ROOT, envelope, term


@pytest.fixture
def runtime_factory():
    runtimes, listeners = [], []

    def create(start=False):
        listener = socket.socket()
        listeners.append(listener)
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        runtime = Runtime({'steps': {}, 'dependencies': {}}, 'local',
                          {'local': listener.getsockname(), 'remote': listener.getsockname()},
                          listener, lambda conn, kind, value: _frame(conn, value),
                          lambda conn, kind: _unframe(conn), lambda name, inputs: inputs)
        runtimes.append(runtime)
        if start:
            runtime.start()
        return runtime

    yield create
    for runtime in runtimes:
        runtime.close()
    for listener in listeners:
        listener.close()


def offer():
    return {'kind': 'offer', 'src': 'local', 'port': 'p', 'id': (),
            'type': 'int', 'control': None}


def test_unrelated_port_waiters_are_not_woken_and_failure_wakes_everyone(runtime_factory):
    runtime = runtime_factory()
    pattern = envelope(term('variable', 'value'), ROOT)
    waiting = {port: threading.Event() for port in ('p', 'q')}
    retried_q = threading.Event()
    original = runtime.try_receive
    calls = {'p': 0, 'q': 0}
    def receive(env, port, term, src):
        calls[port] += 1
        if port == 'q' and calls[port] > 1:
            retried_q.set()
        result = original(env, port, term, src)
        waiting[port].set()
        return result
    runtime.try_receive = receive
    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(runtime.recv, {}, 'p', pattern, 'local')
        other = pool.submit(runtime.recv, {}, 'q', pattern, 'local')
        try:
            assert all(event.wait(2) for event in waiting.values())
            sent = pool.submit(runtime._send_header, 'local', offer(), 7)
            first.result(timeout=2)
            sent.result(timeout=2)
            assert not retried_q.wait(.05)
        finally:
            runtime.fail(RuntimeError('stop test'), broadcast=False)
        with pytest.raises(RuntimeError, match='stop test'):
            other.result(timeout=2)
    assert not runtime._waiters


def test_indexed_values_preserve_duplicates_and_move_consumption(runtime_factory):
    runtime = runtime_factory()
    runtime.values = [
        {'port': 'unrelated', 'id': (i,), 'payload': i, 'type': 'int'} for i in range(1000)
    ] + [
        {'port': 'p', 'id': (), 'payload': value, 'type': 'int'} for value in (7, 8)
    ]
    pattern = envelope(term('variable', 'value'), ROOT)
    for expected in (7, 8):
        env = {}
        assert runtime.try_move(env, 'p', pattern)
        assert env['value'] == expected
    assert not runtime.try_send({}, 'p', pattern)
    assert len(runtime.values) == 1000
    runtime.values.clear()
    assert not runtime.values.by_port and not runtime.values.by_key


def test_transfer_limit_defaults_to_sixty_four(runtime_factory, monkeypatch):
    monkeypatch.delenv('SWIRLC_TRANSFER_LIMIT', raising=False)
    assert runtime_factory().transfer_limit == 64


@pytest.mark.parametrize('value', ['0', '-1', 'many', '1.5'])
def test_transfer_limit_rejects_invalid_settings(runtime_factory, monkeypatch, value):
    monkeypatch.setenv('SWIRLC_TRANSFER_LIMIT', value)
    with pytest.raises(ValueError, match='SWIRLC_TRANSFER_LIMIT'):
        runtime_factory()


@pytest.mark.parametrize('limit', [2, 8])
def test_payload_cap_precedes_connection_and_bypasses_controls(runtime_factory, monkeypatch, limit):
    monkeypatch.setenv('SWIRLC_TRANSFER_LIMIT', str(limit))
    runtime = runtime_factory()
    gate, full = threading.Event(), threading.Event()
    lock = threading.Lock()
    active = peak = 0

    def send_payload(conn, kind, value):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            if active == limit:
                full.set()
        try:
            assert gate.wait(5)
        finally:
            with lock:
                active -= 1

    def connection(*args):
        conn = MagicMock()
        conn.__enter__.return_value = conn
        return conn

    sockets = MagicMock(side_effect=connection)
    monkeypatch.setattr(runtime_module.socket, 'socket', sockets)
    monkeypatch.setattr(runtime_module, '_frame', lambda conn, value: None)
    monkeypatch.setattr(runtime_module, '_unframe', lambda conn: {'ok': True})
    monkeypatch.setattr(runtime, '_send_payload', send_payload)
    with ThreadPoolExecutor(max_workers=32) as pool:
        pending = [pool.submit(runtime._send_header, 'remote', offer(), 7) for _ in range(24)]
        try:
            assert full.wait(2)
            assert sockets.call_count == limit
            for header in [{'kind': 'error', 'message': 'failure'}, {'kind': 'done'},
                           {'kind': 'shape'}, dict(offer(), control='eof')]:
                pool.submit(runtime._send_header, 'remote', header).result(timeout=1)
            local = pool.submit(runtime._send_header, 'local', offer(), 9)
            with runtime.condition:
                assert runtime.condition.wait_for(lambda: bool(runtime.offers), timeout=2)
            env = {}
            assert runtime.try_receive(env, 'p', envelope(term('variable', 'value'), ROOT), 'local')
            local.result(timeout=1)
            assert env['value'] == 9
            assert sockets.call_count == limit + 4
        finally:
            gate.set()
        for future in pending:
            future.result(timeout=2)
    assert peak == limit
    assert runtime._active_transfers == 0


def test_slots_release_before_consumer_acknowledgement(runtime_factory, monkeypatch):
    monkeypatch.setenv('SWIRLC_TRANSFER_LIMIT', '1')
    runtime = runtime_factory(start=True)
    runtime.timeout = .1
    pattern = envelope(term('variable', 'value'), ROOT)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(runtime.send, {'value': value}, 'p', pattern, 'int', 'local', 'remote')
                   for value in (7, 8)]
        try:
            with runtime.condition:
                assert runtime.condition.wait_for(
                    lambda: len(runtime.offers) == 2 and runtime._active_transfers == 0, timeout=2)
            assert runtime._active_transfers == 0
            assert not any(future.done() for future in pending)
            received = []
            for _ in pending:
                env = {}
                assert runtime.try_receive(env, 'p', pattern, 'local')
                received.append(env['value'])
            for future in pending:
                future.result(timeout=2)
            assert sorted(received) == [7, 8]
        finally:
            runtime.fail(RuntimeError('test finished'), broadcast=False)


@pytest.mark.parametrize('stopping', [False, True])
def test_queued_senders_wake_without_opening_socket(runtime_factory, monkeypatch, stopping):
    runtime = runtime_factory()
    runtime.timeout = .01
    runtime._active_transfers = runtime.transfer_limit
    sockets = MagicMock(side_effect=AssertionError('queued sender opened a socket'))
    monkeypatch.setattr(runtime_module.socket, 'socket', sockets)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(runtime._send_header, 'remote', offer(), 7)
        try:
            with pytest.raises(TimeoutError):
                pending.result(timeout=.05)
        finally:
            if stopping:
                runtime.close()
            else:
                runtime.fail(RuntimeError('failed sibling'), broadcast=False)
        with pytest.raises(RuntimeError, match='runtime closed' if stopping else 'failed sibling'):
            pending.result(timeout=1)
    sockets.assert_not_called()


@pytest.mark.parametrize('stage', ['socket', 'connect', 'payload'])
def test_transport_errors_release_slots(runtime_factory, monkeypatch, stage):
    runtime = runtime_factory()
    conn = MagicMock()
    conn.__enter__.return_value = conn
    sockets = MagicMock(return_value=conn)
    if stage == 'socket':
        sockets.side_effect = OSError('transport failed')
    elif stage == 'connect':
        conn.connect.side_effect = OSError('transport failed')
    else:
        monkeypatch.setattr(runtime, '_send_payload', MagicMock(side_effect=OSError('transport failed')))
    monkeypatch.setattr(runtime_module.socket, 'socket', sockets)
    monkeypatch.setattr(runtime_module, '_frame', lambda conn, value: None)
    for _ in range(16):
        with pytest.raises(OSError, match='transport failed'):
            runtime._send_header('remote', offer(), 7)
        assert runtime._active_transfers == 0
