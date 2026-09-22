from swirlc.compiler.hints import scan_hints


def test_scans_nested_valid_hints() -> None:
    source = """// @compiler begin scatter.dispatch 0
exec(_s_scatter_0,{(p,d)}->{(q,r)},l0)
// @compiler begin scatter.worker 1
exec(_s_open_1,{(p,d)}->{(q,r)},l0)
// @compiler end scatter.worker 1
// @compiler end scatter.dispatch 0
"""
    spans = scan_hints(source, {"scatterRegions": {"0": {}, "1": {}}})
    assert [(span.phase, span.region) for span in spans] == [
        ("worker", "1"),
        ("dispatch", "0"),
    ]
