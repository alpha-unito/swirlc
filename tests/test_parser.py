from __future__ import annotations

import pytest

from swirlc.core.parsing import parse_workflow


def test_phase5_surface() -> None:
    parse_workflow(
        "<l0,{(p,d)},!(!((exec(s,{(p,(a,b))}->{(q,r[k])},{l0,l1}) "
        ". move((a,b)->p,l0,{l0,l1})) + (recv(eof->p,l1,l0) . 0)))>"
    )


@pytest.mark.parametrize(
    "source",
    [
        "<l0,{(p,d)},!x exec(s,{(p,d)}->{(q,r)},l0)>",
        "<l0,{(p,d)},exec(s,{(p,(a,b)}->{(q,r)},l0)>",
        "<l0,{(p,d)},exec(s,{(p,d)}->{(q,r)},l0) +foo 0>",
    ],
)
def test_rejects_old_or_malformed_syntax(source: str) -> None:
    with pytest.raises(ValueError, match="Invalid SWIRL"):
        parse_workflow(source)
