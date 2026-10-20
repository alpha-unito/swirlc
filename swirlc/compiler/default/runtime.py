"""Scoped execution of the shared compiler action tree."""
from __future__ import annotations

import hashlib
import itertools
import json
import socket
import threading
import time


def _frame(sock, value):
    data = json.dumps(value).encode()
    sock.sendall(len(data).to_bytes(8, 'big') + data)


def _exact(sock, count):
    data = bytearray()
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise EOFError('Connection closed during scoped frame')
        data.extend(part)
    return bytes(data)


def _unframe(sock):
    return json.loads(_exact(sock, int.from_bytes(_exact(sock, 8), 'big')))


def _freeze(value):
    return tuple(map(_freeze, value)) if isinstance(value, (tuple, list)) else value


class Scope(tuple):
    """Distinguish a bound complete identity from a Cartesian coordinate tuple."""


class Runtime:
    def __init__(self, metadata, location, addresses, listener, send_value, recv_value, execute, evaluate_condition=None):
        self.metadata, self.location, self.addresses = metadata, location, addresses
        self.listener, self.send_value, self.recv_value, self.execute = listener, send_value, recv_value, execute
        self.evaluate_condition = evaluate_condition
        self.condition_ports = {port for spec in metadata.get('conditions', {}).values()
                                if spec['type'] == 'expression' for port in spec['inputs']}
        self.condition = threading.Condition(threading.RLock())
        self.values = []
        self.offers = []
        self.closed = set()
        self.shapes = {}
        self.completed = set()
        self.finite = set()
        self.routing = {}
        self.error = None
        self.stopping = False
        # Bound network operations, never the time spent waiting for workflow data.
        self.timeout = float(__import__('os').environ.get('SWIRLC_RUNTIME_TIMEOUT', '60'))
        self.initial = {name: descriptor['value'] for name, descriptor in metadata.get('dependencies', {}).items() if 'value' in descriptor}

    def start(self):
        self.listener.settimeout(.2)
        threading.Thread(target=self._accept, daemon=True).start()

    def close(self):
        with self.condition:
            self.stopping = True
            self.condition.notify_all()
        self.listener.close()

    def _accept(self):
        while not self.stopping:
            try:
                conn, _ = self.listener.accept()
                threading.Thread(target=self._incoming, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                if not self.stopping:
                    self.fail(RuntimeError('Scoped listener failed'))
                return

    def _incoming(self, conn):
        try:
            header = _unframe(conn)
            if header['kind'] == 'error':
                self.fail(RuntimeError(header['message']), broadcast=False)
                _frame(conn, {'ok': True})
            elif header['kind'] == 'done':
                with self.condition:
                    self.completed.add(header['src'])
                    self.condition.notify_all()
                _frame(conn, {'ok': True})
            elif header['kind'] == 'shape':
                with self.condition:
                    self.shapes[(header['dispatch'], _freeze(header['scope']))] = header['length']
                    self.condition.notify_all()
                _frame(conn, {'ok': True})
            else:
                value = header.get('control') or self._recv_payload(conn, header['type'])
                if not header.get('control'):
                    value = self._coerce(value, header['type'])
                offer = dict(header, value=value, id=_freeze(header['id']), event=threading.Event())
                with self.condition:
                    self.offers.append(offer)
                    self.condition.notify_all()
                self._wait(lambda: offer['event'].is_set(), 'uncommitted transfer')
                _frame(conn, {'ok': True})
        except Exception as exc:
            try:
                _frame(conn, {'error': str(exc)})
            except OSError:
                pass
            self.fail(exc)
        finally:
            conn.close()

    def fail(self, error, broadcast=True):
        with self.condition:
            if self.error is not None:
                return
            self.error = error
            self.condition.notify_all()
        if broadcast:
            for dst in self.addresses:
                if dst != self.location:
                    self._notify_failure(dst, str(error))

    def _notify_failure(self, dst, message):
        try:
            self._send_header(dst, {'kind': 'error', 'message': message}, timeout=1)
        except Exception:
            pass

    def _wait(self, predicate, description):
        with self.condition:
            while True:
                if self.error:
                    raise RuntimeError(f'{description}: {self.error}') from self.error
                if self.stopping:
                    raise RuntimeError(f'{description}: runtime closed')
                if predicate():
                    return
                self.condition.wait()

    def _send_header(self, dst, header, payload=None, timeout=None):
        timeout = self.timeout if timeout is None else timeout
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            conn.settimeout(timeout)
            conn.connect(self.addresses[dst])
            _frame(conn, header)
            if payload is not None:
                self._send_payload(conn, header['type'], payload)
            # Offers are acknowledged only when workflow consumers commit them.
            if header['kind'] == 'offer':
                conn.settimeout(None)
            response = _unframe(conn)
            if 'error' in response:
                raise RuntimeError(response['error'])

    def _send_payload(self, conn, data_type, value):
        if isinstance(data_type, list):
            if not isinstance(value, tuple) or len(value) != len(data_type):
                raise ValueError('Tuple payload does not match its transport type')
            for item_type, item in zip(data_type, value, strict=True):
                self._send_payload(conn, item_type, item)
        else:
            self.send_value(conn, data_type, value)

    def _recv_payload(self, conn, data_type):
        if isinstance(data_type, list):
            return tuple(self._recv_payload(conn, item_type) for item_type in data_type)
        return self.recv_value(conn, data_type)

    def _payload_type(self, term, env, fallback, value):
        if term['kind'] == 'tuple':
            if not isinstance(value, tuple) or len(value) != len(term['items']):
                raise ValueError('Tuple payload does not match its syntax')
            if isinstance(fallback, list):
                fallbacks = fallback
            elif isinstance(fallback, str) and fallback.startswith('list['):
                fallbacks = [fallback[5:-1]] * len(value)
            else:
                fallbacks = [None] * len(value)
            return [self._payload_type(item, env, item_type, item_value) for item, item_type, item_value in zip(term['items'], fallbacks, value, strict=True)]
        bound = env.get('_payload_types', {}).get(term['name'])
        if bound is not None:
            if not isinstance(value, tuple) or isinstance(bound, list):
                return bound
            fallback = bound
        dependency = self.metadata.get('dependencies', {}).get(term['name'])
        if dependency:
            if not isinstance(value, tuple):
                return dependency['type']
            fallback = dependency['type']
        if isinstance(value, tuple):
            if isinstance(fallback, str) and fallback.startswith('list['):
                member = {'kind': 'variable', 'name': '', 'items': []}
                return [self._payload_type(member, {}, fallback[5:-1], item) for item in value]
            if not isinstance(fallback, list):
                raise ValueError(f"Tuple variable {term['name']} lacks component transport types")
            return fallback
        if fallback not in (None, 'dynamic', 'control'):
            return fallback
        if isinstance(value, bool):
            return 'bool'
        if isinstance(value, int):
            return 'int'
        if isinstance(value, float):
            return 'float'
        if isinstance(value, str):
            return 'string'
        raise ValueError(f"Payload {term['name']} lacks a supported transport type")

    def _bind_types(self, term, data_type, env):
        if term['kind'] == 'tuple':
            if not isinstance(data_type, list) or len(data_type) != len(term['items']):
                raise ValueError('Tuple pattern requires component transport types')
            for item, item_type in zip(term['items'], data_type, strict=True):
                self._bind_types(item, item_type, env)
        else:
            env['_payload_types'] = dict(env.get('_payload_types', {}), **{term['name']: data_type})

    def _identity(self, term, env):
        if term['kind'] == 'path':
            result = ()
            for item in term['items']:
                value = self._identity(item, env)
                result += value
            return result
        if term['kind'] == 'variable':
            value = env[term['name']]
            return tuple(value) if isinstance(value, Scope) else (value,)
        if term['kind'] == 'tuple':
            return (tuple(self._payload(item, env) for item in term['items']),)
        name = term['name']
        if name == 'root':
            return ()
        return (int(name) if name.isdigit() else name,)

    def _payload(self, term, env):
        kind, name = term['kind'], term['name']
        if kind == 'tuple':
            return tuple(self._payload(item, env) for item in term['items'])
        if kind == 'literal' and name in ('begin', 'eof'):
            return name
        if kind == 'variable' or name in env:
            return env[name]
        if name in self.initial:
            return self.initial[name]
        if name.isdigit():
            return int(name)
        raise ValueError(f'Unbound payload {name}')

    def _match_payload(self, term, value, env):
        if term['kind'] == 'variable':
            name = term['name']
            if name in env:
                return env[name] == value
            env[name] = value
            return True
        if term['kind'] == 'tuple':
            return isinstance(value, (tuple, list)) and len(value) == len(term['items']) and all(self._match_payload(t, v, env) for t, v in zip(term['items'], value, strict=True))
        if term['kind'] == 'literal' and term['name'] in ('begin', 'eof'):
            return value == term['name']
        name = term['name']
        if name in env:
            return env[name] == value
        env[name] = value
        return True

    def _match_id(self, term, identity, env):
        if term['kind'] == 'variable':
            name = term['name']
            if name in env:
                return self._identity(term, env) == identity
            env[name] = Scope(identity)
            return True
        if term['kind'] != 'path':
            return self._identity(term, env) == identity
        items = term['items']
        prefix = ()
        for item in items[:-1]:
            prefix += self._identity(item, env)
        if identity[:len(prefix)] != prefix or len(identity) != len(prefix) + 1:
            return False
        final = items[-1]
        if final['kind'] == 'variable' and final['name'] not in env:
            env[final['name']] = identity[-1]
            return True
        return self._identity(final, env) == identity[len(prefix):]

    def _store(self, port, identity, payload, data_type):
        self.values.append({'port': port, 'id': identity, 'payload': payload, 'type': data_type})

    def _snapshot(self, port, scope):
        return [v for v in self.values if v['port'] == port and v['id'][:-1] == scope and len(v['id']) == len(scope) + 1]

    def _bind_condition_input(self, env, port, value):
        if port in self.condition_ports:
            env['_condition_inputs'] = dict(env.get('_condition_inputs', {}), **{port: value})

    def try_receive(self, env, port, term, src):
        with self.condition:
            payload, identity = term['items']
            expected_control = payload['name'] if payload['kind'] == 'literal' and payload['name'] in ('begin', 'eof') else None
            for offer in self.offers:
                if offer['src'] != src or offer['port'] != port:
                    continue
                if offer.get('control') != expected_control:
                    continue
                candidate = dict(env)
                if self._match_payload(payload, offer['value'], candidate) and self._match_id(identity, offer['id'], candidate):
                    if expected_control is None:
                        self._bind_types(payload, offer['type'], candidate)
                        self._bind_condition_input(candidate, port, offer['value'])
                    self.offers.remove(offer)
                    env.update(candidate)
                    if offer.get('control') == 'eof':
                        self.closed.add((src, port, offer['id']))
                    elif not offer.get('control'):
                        self._store(port, offer['id'], offer['value'], offer['type'])
                    offer['event'].set()
                    self.condition.notify_all()
                    return True
            if expected_control is None:
                try:
                    wanted = self._identity(identity, env)
                except KeyError:
                    wanted = None
                if wanted is not None:
                    exhausted = (src, port, wanted[:-1]) in self.closed
                    exhausted |= any(offer['src'] == src and offer['port'] == port and offer.get('control') == 'eof' and offer['id'] == wanted[:-1] for offer in self.offers)
                    if exhausted:
                        raise ValueError(f"Closed stream {port} is missing required key {wanted}")
            return False

    def try_move(self, env, port, term, dst=None):
        with self.condition:
            payload, identity = term['items']
            workers = self._dispatch_workers(port) if dst is not None else []
            for value in self.values:
                if value['port'] != port:
                    continue
                candidate = dict(env)
                if self._match_payload(payload, value['payload'], candidate) and self._match_id(identity, value['id'], candidate):
                    selected = self.routing.get((port, value['id'])) if dst is not None else None
                    if selected is None and workers:
                        selected = self._route_worker(port, value['id'], workers)
                    if selected is not None:
                        destinations = dst if isinstance(dst, list) else [dst]
                        if selected not in destinations:
                            continue
                    self._bind_types(payload, value['type'], candidate)
                    self._bind_condition_input(candidate, port, value['payload'])
                    self.values.remove(value)
                    env.update(candidate)
                    env['_claimed'] = value
                    return True
            return False

    def recv(self, env, port, term, src):
        self._wait(lambda: self.try_receive(env, port, term, src), f'receive {port} from {src}')

    def send(self, env, port, term, data_type, src, dst):
        self._transfer(env, port, term, data_type, src, dst)

    def move(self, env, port, term, data_type, src, dst):
        if '_claimed' not in env:
            self._wait(lambda: self.try_move(env, port, term, dst), f'move {port}')
        self._transfer(env, port, term, data_type, src, dst, moving=True)

    def _transfer(self, env, port, term, data_type, src, dst, moving=False):
        if self.error:
            raise self.error
        payload_term, id_term = term['items']
        value, identity = self._payload(payload_term, env), self._identity(id_term, env)
        data_type = data_type or env.get('_claimed', {}).get('type')
        if payload_term['kind'] == 'literal' and payload_term['name'] in ('begin', 'eof'):
            control, data_type = value, 'control'
        else:
            control = None
            if data_type in (None, 'dynamic', 'control'):
                claimed = env.get('_claimed')
                data_type = claimed['type'] if claimed else env.get('_payload_types', {}).get(payload_term['name'])
                if data_type is None and payload_term['kind'] != 'tuple':
                    data_type = self._port_type(port)
        if control is None:
            data_type = self._payload_type(payload_term, env, data_type, value)
        destinations = dst if isinstance(dst, list) else [dst]
        if moving and len(destinations) > 1:
            workers = self._dispatch_workers(port) or destinations
            destinations = [self.routing.get((port, identity)) or self._route_worker(port, identity, workers)]
        for dst in destinations:
            self._send_header(dst, {'kind': 'offer', 'src': src, 'port': port, 'id': identity, 'type': data_type, 'control': control}, None if control else value)
        env.pop('_claimed', None)

    @staticmethod
    def _coerce(value, data_type):
        if isinstance(data_type, list):
            return tuple(Runtime._coerce(item, item_type) for item, item_type in zip(value, data_type, strict=True))
        if data_type.startswith('list['):
            return [Runtime._coerce(item, data_type[5:-1]) for item in value]
        if data_type == 'int':
            return int(value)
        if data_type == 'float':
            return float(value)
        if data_type == 'bool':
            return value if isinstance(value, bool) else value.lower() == 'true'
        return value

    def _port_type(self, port):
        for step in self.metadata['steps'].values():
            descriptor = step.get('outputs', {}).get(port)
            if descriptor:
                if 'binding' in descriptor:
                    return descriptor['binding']['type']
                if 'collection' in descriptor:
                    return descriptor['collection']['type']
                return self.metadata['dependencies'][descriptor['dataName']]['type']
            descriptor = step.get('collections', {}).get(port)
            if descriptor:
                return descriptor['type']
        for step in self.metadata['steps'].values():
            descriptor = step.get('inputs', {}).get(port)
            if descriptor:
                return descriptor['type']
        raise ValueError(f'No payload type for port {port}')

    def _operation_for_port(self, port):
        for step in self.metadata['steps'].values():
            if port in step.get('outputs', {}) and step.get('type') == 'scatter_dispatch':
                return step['operationId']
        return port

    def _dispatch_workers(self, port):
        for step in self.metadata['steps'].values():
            if step.get('type') == 'scatter_dispatch' and port in step.get('outputs', {}):
                for route in step.get('routes', []):
                    if route.get('producers', {}).get(step.get('dimension'), route['controller']) == self.location:
                        return route['workers']
        return []

    def _route_worker(self, port, identity, workers):
        operation = self._operation_for_port(port)
        digest = hashlib.sha256(json.dumps([operation, identity], sort_keys=True).encode()).digest()
        return workers[int.from_bytes(digest[:8], 'big') % len(workers)]

    def _shape(self, step, scope):
        names = step.get('shapeFrom') or step['keySpace']['dispatches']
        self._wait(lambda: all((name, scope) in self.shapes for name in names), 'scatter cardinalities')
        lengths = [self.shapes[name, scope] for name in names]
        if step['scatterMethod'] == 'dotproduct' and len(set(lengths)) > 1:
            raise ValueError(f"{step['operationId']}: dotproduct cardinalities differ: {lengths}")
        return lengths

    @staticmethod
    def _keys(method, lengths):
        if method == 'dotproduct':
            return [(i,) for i in range(lengths[0])]
        coordinates = list(itertools.product(*(range(length) for length in lengths)))
        return [(i,) for i in range(len(coordinates))] if method == 'flat_crossproduct' else [(c,) for c in coordinates]

    def execute_step(self, env, name, input_flow, output_flow, mapping=None):
        if self.error:
            raise self.error
        if mapping is not None and self.location not in mapping:
            raise ValueError(f'{name}: execution at {self.location} violates placement {mapping}')
        step = self.metadata['steps'][name]
        inputs = {}
        for port, term in input_flow:
            if term['kind'] == 'collection':
                scope = self._identity(term['items'][1], env)
                inputs[port] = self._snapshot(port, scope)
            else:
                inputs[port] = self._payload(term['items'][0], env)
            self._bind_condition_input(env, port, inputs[port])
        helper = step.get('type')
        if helper == 'scatter_dispatch':
            # A reusable ancestor input keeps its ID; tasks use the invocation's scope.
            scope = self._identity(output_flow[0][1]['items'][1], env)
            items = inputs[input_flow[0][0]]
            if not isinstance(items, list):
                raise ValueError(f'{name}: scatter input must be a list')
            with self.condition:
                self.shapes[name, scope] = len(items)
                self.condition.notify_all()
            for dst in self.addresses:
                if dst != self.location:
                    self._send_header(dst, {'kind': 'shape', 'dispatch': name, 'scope': scope, 'length': len(items)})
            lengths = self._shape(step, scope)
            dimension = step['dimensions'].index(step['dimension'])
            coordinates = list(itertools.product(*(range(length) for length in lengths))) if step['scatterMethod'] != 'dotproduct' else [(i,) * len(lengths) for i in range(lengths[0])]
            for port, _term in output_flow:
                output_type = step['outputs'][port]['collection']['type']
                workers = next((route['workers'] for route in step.get('routes', [])
                                if route.get('producers', {}).get(step['dimension'], route['controller']) == self.location), [])
                with self.condition:
                    for index, coordinate in enumerate(coordinates):
                        key = coordinate if step['scatterMethod'] == 'nested_crossproduct' else index
                        self._store(port, scope + (key,), items[coordinate[dimension]], output_type)
                        if workers:
                            # Shared ports can serve invocations with different reserved pools.
                            self.routing[port, scope + (key,)] = self._route_worker(port, scope + (key,), workers)
                    self.finite.add((port, scope))
                    self.condition.notify_all()
            return
        if helper == 'scatter_gather':
            first = input_flow[0][1]
            scope = self._identity(first['items'][1], env)
            unclosed = [(route['source'], route['port'], scope) for route in step.get('routes', []) if (route['source'], route['port'], scope) not in self.closed]
            if unclosed:
                raise ValueError(f'{name}: gather sources remain open: {unclosed}')
            lengths = self._shape(step, scope)
            expected = {scope + key for key in self._keys(step['scatterMethod'], lengths)}
            occurrences = [value for collection in inputs.values() for value in collection]
            by_key = {}
            for value in occurrences:
                if value['id'] not in expected or value['id'] in by_key:
                    raise ValueError(f'{name}: duplicate or invalid gather key {value["id"]}')
                by_key[value['id']] = value['payload']
            if set(by_key) != expected:
                raise ValueError(f'{name}: missing gather keys {expected - set(by_key)}')
            if step['scatterMethod'] == 'nested_crossproduct':
                def shape(prefix, depth):
                    if depth == len(lengths):
                        return by_key[scope + (prefix,)]
                    return [shape(prefix + (i,), depth + 1) for i in range(lengths[depth])]
                result = shape((), 0)
            else:
                result = [by_key[scope + key] for key in self._keys(step['scatterMethod'], lengths)]
            outputs = {port: result for port, _ in output_flow}
        else:
            outputs = self.execute(name, inputs)
        for port, term in output_flow:
            payload, identity = term['items']
            value = outputs[port]
            candidate = dict(env)
            if not self._match_payload(payload, value, candidate):
                raise ValueError(f'{name}: output payload does not match its binding pattern')
            output_type = self._payload_type(payload, candidate, self._port_type(port), value)
            self._bind_types(payload, output_type, candidate)
            self._bind_condition_input(candidate, port, value)
            env.update(candidate)
            with self.condition:
                self._store(port, self._identity(identity, env), value, output_type)
                self.condition.notify_all()

    def parallel(self, env, owner, *branches):
        if self.error:
            raise self.error
        errors = []
        results = []
        def work(child):
            try:
                local = dict(env)
                child(local, owner)
                results.append(local)
            except Exception as exc:
                errors.append(exc)
                self.fail(exc)
        threads = [threading.Thread(target=work, args=(child,)) for child in branches]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if errors:
            raise errors[0]
        changes = {}
        for local in results:
            for name, value in local.items():
                if name == '_condition_inputs':
                    original = env.get(name, {})
                    merged = changes.setdefault(name, dict(original))
                    for port, payload in value.items():
                        if port in original and original[port] == payload:
                            continue
                        if port in merged and (port not in original or merged[port] != original[port]) and merged[port] != payload:
                            raise ValueError(f'Parallel branches bind conflicting condition inputs for {port}')
                        merged[port] = payload
                    continue
                if name == '_payload_types':
                    merged = changes.setdefault(name, dict(env.get(name, {})))
                    for symbol, data_type in value.items():
                        if symbol in merged and merged[symbol] != data_type:
                            raise ValueError(f'Parallel branches bind conflicting payload types for {symbol}')
                        merged[symbol] = data_type
                    continue
                if name not in env or value != env[name]:
                    if name in changes and changes[name] != value:
                        raise ValueError(f'Parallel branches bind conflicting values for {name}')
                    changes[name] = value
        env.update(changes)

    @staticmethod
    def new_owner():
        return {'closed': False, 'threads': []}

    def spawn(self, owner, body, env):
        def instance():
            try:
                body(env, owner)
            except Exception as exc:
                self.fail(exc)
            finally:
                with self.condition:
                    self.condition.notify_all()
        thread = threading.Thread(target=instance)
        owner['threads'].append(thread)
        thread.start()

    def join(self, owner):
        for thread in owner['threads']:
            thread.join()
        if self.error:
            raise self.error

    def end(self, owner):
        if owner is None:
            raise ValueError('end() has no replication owner')
        with self.condition:
            owner['closed'] = True
            self.condition.notify_all()

    def admit(self, env, owner, selector):
        chosen = []
        def select():
            if owner is not None and owner['closed']:
                return True
            candidate = dict(env)
            selection = selector(candidate)
            if selection is not None:
                chosen.append((selection, candidate))
                return True
            return False
        self._wait(select, 'replication admission' if owner is not None else 'choice')
        return chosen[0] if chosen else (None, None)

    def condition_value(self, name, env, scope=None):
        descriptor = self.metadata['conditions'][name]
        if descriptor['type'] == 'has_data':
            with self.condition:
                if self.has_data(descriptor['port'], scope, env):
                    return True
                return False if self.exhausted(descriptor['port'], scope, env) else None
        bound = env.get('_condition_inputs', {})
        missing = set(descriptor['inputs']) - bound.keys()
        if missing:
            raise ValueError(f'Condition {name} requires already-bound inputs: {sorted(missing)}')
        if self.evaluate_condition is None:
            raise ValueError(f'Condition {name} has no expression evaluator')
        value = self.evaluate_condition(descriptor, bound)
        if type(value) is not bool:
            raise TypeError(f'Condition {name} must return a boolean, got {type(value).__name__}')
        return value

    def has_data(self, port, scope, env):
        identity = self._identity(scope, env)
        with self.condition:
            return bool(self._snapshot(port, identity))

    def exhausted(self, port, scope, env):
        identity = self._identity(scope, env)
        with self.condition:
            return (port, identity) in self.finite and not self._snapshot(port, identity)

    def initialize(self, initial, env):
        self.initial = {entry['name']: entry['payload'] for entry in initial}
        for entry in initial:
            env[entry['name']] = entry['payload']
            self._bind_condition_input(env, entry['port'], entry['payload'])
            env['_payload_types'] = dict(env.get('_payload_types', {}), **{entry['name']: entry['type']})
            identity = self._identity(entry['identity'], env)
            self._store(entry['port'], identity, entry['payload'], entry['type'])
        return env

    def finish(self):
        with self.condition:
            self.completed.add(self.location)
        for dst in self.addresses:
            if dst != self.location:
                self._send_header(dst, {'kind': 'done', 'src': self.location})
        self._wait(lambda: self.completed == set(self.addresses), 'location completion barrier')
