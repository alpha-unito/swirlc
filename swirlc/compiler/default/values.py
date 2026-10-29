"""Shared structured-value helpers embedded in generated executors."""

value_helpers = r'''import os
import json
from pathlib import Path
import shutil
import tempfile
from urllib.parse import unquote, urlparse


def _value_walk(value, visit, include_secondaries=True):
    if isinstance(value, list):
        return [_value_walk(item, visit, include_secondaries) for item in value]
    if isinstance(value, dict):
        value = {key: (_value_walk(item, visit, include_secondaries)
                       if include_secondaries or key != "secondaryFiles" else item)
                 for key, item in value.items()}
        if value.get("class") in ("File", "Directory"):
            return visit(value)
    return value


def _entry_path(root, name, allow_symlink=False):
    if not isinstance(name, str) or not name or os.path.isabs(name):
        raise ValueError("Invalid staging entry name: %r" % (name,))
    path = os.path.abspath(os.path.join(root, name))
    checked = os.path.dirname(path) if allow_symlink else path
    if (os.path.commonpath([os.path.abspath(root), path]) != os.path.abspath(root)
            or os.path.commonpath([os.path.realpath(root), os.path.realpath(checked)]) != os.path.realpath(root)):
        raise ValueError("Staging entry escapes work directory: " + name)
    return path


def _file_identity(value, path):
    value = dict(value)
    value["path"] = os.path.abspath(path)
    value["location"] = Path(value["path"]).as_uri()
    value.setdefault("basename", os.path.basename(path))
    value["dirname"] = os.path.dirname(value["path"])
    value["nameroot"], value["nameext"] = os.path.splitext(value["basename"])
    if value["class"] == "File":
        value["size"] = os.path.getsize(path)
    return value


def _validate_value(value, schema):
    if schema is None:
        return value
    if isinstance(schema, list):
        for member in schema:
            try:
                return _validate_value(value, member)
            except (TypeError, ValueError):
                pass
        raise TypeError("Value does not match its declared union")
    spec = schema if isinstance(schema, dict) else {"type": schema}
    kind = spec.get("type", "Any")
    if value is None and (kind == "null" or spec.get("nullable")):
        return value
    if kind in ("Any", "any"):
        return value
    if kind == "array":
        if not isinstance(value, list):
            raise TypeError("Expected array")
        for item in value:
            _validate_value(item, spec["items"])
    elif kind == "record":
        if not isinstance(value, dict) or value.get("class") in ("File", "Directory"):
            raise TypeError("Expected record")
        fields = spec.get("fields", {})
        if isinstance(fields, list):
            fields = {field["name"].rsplit("/", 1)[-1]: field["type"] for field in fields}
        for name, field in fields.items():
            _validate_value(value.get(name), field)
    elif kind.lower() in ("file", "directory"):
        if not isinstance(value, dict) or value.get("class", "").lower() != kind.lower():
            raise TypeError("Expected " + kind)
    elif kind in ("boolean", "bool"):
        if type(value) is not bool:
            raise TypeError("Expected boolean")
    elif kind in ("int", "long"):
        if type(value) is not int:
            raise TypeError("Expected integer")
    elif kind in ("float", "double"):
        if type(value) not in (int, float):
            raise TypeError("Expected number")
    elif kind == "string":
        if not isinstance(value, str):
            raise TypeError("Expected string")
    elif kind == "null":
        raise TypeError("Expected null")
    else:
        raise ValueError("Unsupported value schema: %r" % kind)
    return value


def _prepare_value(value, schema=None, base_dir=None):
    spec = schema if isinstance(schema, dict) else {"type": schema}
    kind = spec.get("type")
    if isinstance(value, str) and kind in ("file", "File", "directory", "Directory"):
        value = {"class": kind.capitalize(), "path": value}
    if isinstance(value, list):
        value = [_prepare_value(item, spec.get("items"), base_dir) for item in value]
    elif isinstance(value, dict) and value.get("class") not in ("File", "Directory"):
        fields = spec.get("fields", {})
        value = {key: _prepare_value(item, fields.get(key) if isinstance(fields, dict) else None, base_dir)
                 for key, item in value.items()}
    elif isinstance(value, dict):
        value = dict(value)
        raw = value.get("path") or value.get("location")
        if raw and not raw.startswith("_:"):
            parsed = urlparse(raw)
            if parsed.scheme and parsed.scheme != "file":
                raise ValueError("Unsupported file location: " + raw)
            if parsed.scheme == "file" and parsed.netloc not in ("", "localhost"):
                raise ValueError("Nonlocal file location: " + raw)
            path = unquote(parsed.path) if parsed.scheme else raw
            path = os.path.abspath(os.path.join(base_dir or os.getcwd(), path))
            if not os.path.exists(path):
                raise ValueError("File reference does not exist: " + path)
            if not (os.path.isdir(path) if value["class"] == "Directory" else os.path.isfile(path)):
                raise ValueError("File reference has the wrong class: " + path)
        else:
            root = tempfile.mkdtemp(prefix="literal_", dir=SCRATCH_DIR)
            path = _entry_path(root, value.get("basename", "directory" if value["class"] == "Directory" else "file"))
            if value["class"] == "Directory":
                os.makedirs(path)
            else:
                if not isinstance(value.get("contents"), str):
                    raise ValueError("File literal requires contents")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(value["contents"])
        value = _file_identity(value, path)
        if value["class"] == "Directory":
            listing = value.get("listing")
            if listing is None:
                listing = [{"class": "Directory" if os.path.isdir(os.path.join(path, name)) else "File",
                            "path": os.path.join(path, name)} for name in sorted(os.listdir(path))]
            value["listing"] = [_prepare_value(item, base_dir=path) for item in listing]
        if "secondaryFiles" in value:
            value["secondaryFiles"] = [_prepare_value(item, base_dir=os.path.dirname(path)) for item in value["secondaryFiles"]]
    _validate_value(value, schema)
    return value


_STAGED_VALUES = {}
_STAGED_RELOCATIONS = {}
_STAGED_WRITABLE = set()


def _stage_value(value, workdir, allow_collisions=False, writable=False):
    occupied = _STAGED_VALUES.setdefault(os.path.abspath(workdir), {})
    relocated = _STAGED_RELOCATIONS.setdefault(os.path.abspath(workdir), {})
    def stage(item, root):
        if isinstance(item, list):
            return [stage(child, root) for child in item]
        if not isinstance(item, dict):
            return item
        if item.get("class") not in ("File", "Directory"):
            return {key: stage(child, root) for key, child in item.items()}
        source = os.path.abspath(item["path"])
        name = item.get("basename", os.path.basename(source))
        proposed = os.path.abspath(os.path.join(root, name))
        target = _entry_path(root, name, allow_symlink=proposed in occupied)
        original_target = target
        if allow_collisions:
            target = relocated.get((source, target), target)
        previous = occupied.get(target)
        conflict = (previous is not None and previous != source) or (os.path.lexists(target) and previous is None)
        if allow_collisions and item["class"] == "File":
            for companion in item.get("secondaryFiles", []):
                companion_path = os.path.join(os.path.dirname(target), companion["basename"])
                companion_target = _entry_path(os.path.dirname(target), companion["basename"],
                                              allow_symlink=companion_path in occupied)
                companion_source = companion["path"]
                existing = occupied.get(companion_target)
                if ((existing is not None and existing != companion_source)
                        or (os.path.lexists(companion_target) and existing is None)) and companion_source != companion_target:
                    conflict = True
        if conflict and os.path.abspath(source) != target:
            if not allow_collisions:
                raise ValueError("Conflicting staging entry: " + target)
            root = tempfile.mkdtemp(prefix="input_", dir=root)
            target = _entry_path(root, item.get("basename", os.path.basename(source)))
            relocated[(source, original_target)] = target
        # A named writable entry may upgrade an automatically staged read-only link.
        if source == target and target in occupied:
            if not os.path.islink(target) and (not writable or target in _STAGED_WRITABLE):
                return _file_identity(item, target)
            source = occupied[target]
            if os.path.islink(target) and item["class"] == "Directory":
                item = _relocate_value(item, target, source)
        previous = occupied.get(target)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        result = dict(item)
        if item["class"] == "Directory":
            listing = item.get("listing", [])
            # Literal directories can describe children outside their physical directory.
            physical = all(isinstance(child, dict)
                           and os.path.abspath(child["path"]) == os.path.join(source, child["basename"])
                           for child in listing)
            if physical and source != target:
                if writable and (previous is None or target not in _STAGED_WRITABLE):
                    if os.path.islink(target):
                        os.unlink(target)
                    shutil.copytree(source, target, dirs_exist_ok=True)
                elif not os.path.lexists(target):
                    os.symlink(source, target, target_is_directory=True)
                result["listing"] = [_relocate_value(child, source, target) for child in listing]
            else:
                os.makedirs(target, exist_ok=True)
                result["listing"] = [stage(child, target) for child in listing]
        elif source != target and (previous is None or writable and target not in _STAGED_WRITABLE):
            if writable:
                if os.path.islink(target):
                    os.unlink(target)
                shutil.copy2(source, target)
            else:
                os.symlink(source, target)
        occupied.setdefault(target, source)
        if writable:
            _STAGED_WRITABLE.add(target)
        result["secondaryFiles"] = [stage(child, os.path.dirname(target)) for child in item.get("secondaryFiles", [])]
        return _file_identity(result, target)
    return stage(value, workdir)


def _relocate_value(value, source, target):
    def relocate(item):
        path = item["path"]
        if os.path.commonpath([source, path]) == source:
            return _file_identity(item, os.path.join(target, os.path.relpath(path, source)))
        return item
    return _value_walk(value, relocate)


def _load_contents(value):
    with open(value["path"] if isinstance(value, dict) else value, "rb") as stream:
        content = stream.read(65537)
    if len(content) > 65536:
        raise ValueError("loadContents exceeds the 64 KiB limit")
    return content.decode("utf-8")


def _apply_secondary(value, declarations, evaluate):
    def apply(item):
        if item.get("class") != "File":
            return item
        result = dict(item)
        companions = list(result.get("secondaryFiles", []))
        for declaration in declarations or []:
            declaration = declaration if isinstance(declaration, dict) else {"pattern": declaration}
            pattern = declaration["pattern"]
            required = declaration.get("required", True)
            if not isinstance(required, bool):
                required = evaluate(required, result)
            if not isinstance(required, bool):
                raise TypeError("secondaryFiles required expression must return boolean")
            if isinstance(pattern, dict) or (isinstance(pattern, str) and ("$(" in pattern or "${" in pattern)):
                candidates = evaluate(pattern, result)
                candidates = candidates if isinstance(candidates, list) else [candidates]
            else:
                name = result["basename"]
                while pattern.startswith("^"):
                    name = os.path.splitext(name)[0]
                    pattern = pattern[1:]
                candidates = [name + pattern]
            for candidate in candidates:
                if candidate is None:
                    if required:
                        raise ValueError("Missing required secondary file")
                    continue
                if isinstance(candidate, str):
                    candidate = {"class": "File", "path": candidate}
                name = candidate.get("basename") or os.path.basename(candidate.get("path", candidate.get("location", "")))
                if any(companion.get("basename") == name for companion in companions):
                    continue
                try:
                    companions.append(_prepare_value(candidate, base_dir=os.path.dirname(result["path"])))
                except ValueError:
                    if required:
                        raise
        result["secondaryFiles"] = companions
        return result
    return _value_walk(value, apply, include_secondaries=False)


def _apply_value_schema(value, schema, evaluate):
    if value is None or not isinstance(schema, dict):
        return value
    if schema.get("type") == "array":
        value = [_apply_value_schema(item, schema.get("items"), evaluate) for item in value]
    elif schema.get("type") == "record":
        fields = schema.get("fields", {})
        value = {name: _apply_value_schema(item, fields.get(name), evaluate)
                 for name, item in value.items()}
    if schema.get("secondaryFiles"):
        value = _apply_secondary(value, schema["secondaryFiles"], evaluate)
    return value


def _send_structured(sock, value, data_type=None):
    def legacy(item, kind):
        if item is None:
            return None
        if kind and kind.startswith("list[") and kind.endswith("]"):
            return [legacy(child, kind[5:-1]) for child in item]
        if kind in ("file", "directory") and isinstance(item, str):
            item = _prepare_value(item, {"type": kind})
            item["_legacy_path"] = True
        return item
    value = legacy(value, data_type)
    files = []
    def describe(item):
        item = dict(item)
        if item["class"] == "File":
            item["_transfer_index"] = len(files)
            files.append(item["path"])
        return item
    payload = json.dumps(_value_walk(value, describe)).encode("utf-8")
    _send_len(sock, len(payload))
    sock.sendall(payload)
    for path in files:
        _send_len(sock, os.stat(path).st_mode & 0o777)
        _send_len(sock, os.path.getsize(path))
        with open(path, "rb") as stream:
            while chunk := stream.read(BUF_SIZE):
                sock.sendall(chunk)


def _recv_structured(sock):
    value = json.loads(_recv_exactly(sock, _recv_len(sock)))
    def receive(item):
        root = tempfile.mkdtemp(prefix="receive_", dir=SCRATCH_DIR)
        path = _entry_path(root, item.get("basename", "file"))
        if item["class"] == "Directory":
            os.makedirs(path)
            item["listing"] = _stage_value(item.get("listing", []), path)
            result = _file_identity(item, path)
            return result["path"] if result.pop("_legacy_path", False) else result
        if "_transfer_index" not in item:
            raise ValueError("Missing file payload")
        item.pop("_transfer_index")
        mode, remaining = _recv_len(sock), _recv_len(sock)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as stream:
            while remaining:
                chunk = _recv_exactly(sock, min(BUF_SIZE, remaining))
                stream.write(chunk)
                remaining -= len(chunk)
        os.chmod(path, mode & 0o777)
        item["secondaryFiles"] = _stage_value(item.get("secondaryFiles", []), root)
        result = _file_identity(item, path)
        return result["path"] if result.pop("_legacy_path", False) else result
    return _value_walk(value, receive)
'''
