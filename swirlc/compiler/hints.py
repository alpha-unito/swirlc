from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from swirlc.log_handler import logger


@dataclass(frozen=True)
class HintSpan:
    phase: str
    region: str
    start: int
    end: int


_DIRECTIVE = re.compile(
    r"^\s*//\s*@compiler\s+(begin|end)\s+scatter\.(\w+)\s+(\S+)\s*$"
)
_PHASE_STEP = {"dispatch": "_s_scatter_", "worker": "_s_open_", "gather": "_s_gather_"}


def scan_hints(source: str, metadata: dict[str, Any]) -> list[HintSpan]:
    """Read optional compiler directives; bad hints never change compilation."""
    if any(step.get("type") == "scatter_dispatch" for step in metadata.get("steps", {}).values()):
        return []  # Modern stream hints are advisory; syntax supplies all semantics.
    stack: list[tuple[str, str, int]] = []
    spans: list[HintSpan] = []
    offset = 0
    regions = metadata.get("scatterRegions", {})
    for line in source.splitlines(keepends=True):
        if "@compiler" not in line:
            offset += len(line)
            continue
        match = _DIRECTIVE.match(line)
        if not match:
            logger.warning("Ignoring malformed compiler directive: %s", line.strip())
        else:
            action, phase, region = match.groups()
            if phase not in _PHASE_STEP or not region.isdigit():
                logger.warning("Ignoring compiler directive: %s", line.strip())
            elif action == "begin":
                stack.append((phase, region, offset + len(line)))
            elif not stack or stack[-1][:2] != (phase, region):
                logger.warning("Ignoring unmatched compiler directive: %s", line.strip())
            else:
                start_phase, start_region, start = stack.pop()
                body = source[start:offset]
                if start_region not in regions or _PHASE_STEP[start_phase] + start_region not in body:
                    logger.warning("Ignoring invalid compiler hint: %s", line.strip())
                else:
                    spans.append(HintSpan(start_phase, start_region, start, offset))
        offset += len(line)
    for phase, region, _ in stack:
        logger.warning("Ignoring unmatched compiler directive: begin scatter.%s %s", phase, region)
    return spans
