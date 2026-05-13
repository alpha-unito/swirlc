# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`swirlc` is a Python compiler toolchain for **SWIRL** (Scientific Workflow Intermediate Representation Language) — a low-level IR for distributed scientific workflows. It is not intended for direct human authoring; it is a compilation target. The tool parses `.swirl` files (ANTLR4 grammar), validates a companion `config.yml` metadata file (JSON Schema), then either translates a high-level workflow format into SWIRL or compiles SWIRL into an executable bundle.

Two top-level CLI commands:
- `swirlc translate --language <lang> <dir>` — converts a high-level workflow (currently only `dax`) into `.swirl` + `metadata.yml`
- `swirlc compile <workflow.swirl> <metadata.yml>` — compiles SWIRL into an executable bundle (currently only `default` target, which generates Python + shell scripts)

## Development commands

```bash
# Install for development (activate venv first)
source venv/bin/activate
pip install -e ".[lint,test,bandit]"

# Run all tests
make test

# Run a single test file
python -m pytest tests/test_translator.py -rs

# Run a single test by name
python -m pytest tests/test_translator.py::test_translate -rs

# Run with coverage
make testcov && make coverage-report

# Lint
make flake8
make format-check

# Auto-format
make format

# Spell check (and fix)
make codespell

# Regenerate ANTLR4 parsers (requires Docker)
./scripts/generate-antlr4-parsers.sh
```

## Architecture

### Pipeline overview

```
High-level workflow (DAX, ...)
        |
  [Translator]  swirlc/translator/
        |
  Workflow IR   swirlc/core/entity.py
        |
  [AbstractTranslator.translate()]  swirlc/core/translator.py
        |
  .swirl text + metadata.yml
        |
  [ANTLR4 lexer/parser]  swirlc/antlr/  (generated, do not edit)
        |
  Parse tree
        |
  [CompileVisitor]  swirlc/core/compiler.py
        |
  [BaseCompiler subclass]  swirlc/compiler/
        |
  Executable bundle (Python scripts per location)
```

### Key modules

**`swirlc/core/entity.py`** — all domain objects: `Data`, `Location`, `Port`, `Processor`, `Step`, `Workflow`, `DistributedWorkflow`. `Workflow` models a single-location DAG; `DistributedWorkflow` extends it with multi-location mapping.

**`swirlc/core/translator.py`** — `AbstractTranslator` base class. Subclasses implement `_translate() -> Workflow` and call `translate()` which serialises the IR to `.swirl` + YAML metadata. The serialisation logic (send/recv inference, dataset pairs) lives entirely here.

**`swirlc/core/compiler.py`** — `BaseCompiler` (no-op base with hooks for every SWIRL construct) and `CompileVisitor` (ANTLR visitor that walks the parse tree and dispatches to a `BaseCompiler`). To add a new compilation target, subclass `BaseCompiler` and register it in `swirlc/compiler/__init__.py`.

**`swirlc/translator/__init__.py`** and **`swirlc/compiler/__init__.py`** — registries mapping string keys (`"dax"`, `"default"`) to classes. Add new translators/targets here.

**`swirlc/antlr/`** — generated ANTLR4 Python parser for `grammar/SWIRL.g4`. Never edit by hand; regenerate via `scripts/generate-antlr4-parsers.sh`.

**`swirlc/config/validator.py`** — validates the metadata YAML against JSON Schema (in `swirlc/config/schemas/`).

### SWIRL language structure

A SWIRL program is a `|`-parallel composition of *locations*:

```
<location_name, {(port, data), ...}, trace>
```

A *trace* is built from three predicates — `exec(step, flow, mapping)`, `send(data->port, src, dst)`, `recv(port, src, dst)` — composed with `.` (seq), `|` (par), `+` (choice).

### Metadata YAML schema (`config.yml`)

Top-level keys: `version` (always `"v1.0"`), `steps`, `locations`, `dependencies`.

- `steps.<name>`: `displayName`, `command`, `arguments` (list of `{value: ...}` or `{valueFrom: <port>}`), `outputs` (map of port → `{dataName, glob?}`)
- `locations.<name>`: `hostname`, `port`, `workdir`, `outdir`, `connectionType` (`ssh` | `docker` | absent)
- `dependencies.<name>`: `type` (`file` | `stdout` | `string`), `value?`

### Adding a new translator

1. Create `swirlc/translator/<name>_translator.py` with a class extending `AbstractTranslator` and implementing `_translate() -> Workflow`.
2. Register it in `swirlc/translator/__init__.py`: `translator_classes["<key>"] = MyTranslator`.

### Adding a new compiler target

1. Create `swirlc/compiler/<name>.py` with a class extending `BaseCompiler`, overriding the hooks you need.
2. Register it in `swirlc/compiler/__init__.py`: `targets["<key>"] = MyTarget`.

## Style / lint

- Formatter: `black` (line length 88, excludes `swirlc/antlr/`)
- Linter: `flake8` (same exclusion, `max-line-length = 88`, ignores `E203`, `E501`)
- Python 3.9+ syntax (`pyupgrade --py39-plus`)
- Security scan: `bandit`
