"""Hostile CPU-only checks for the original B/I2 cross-source fence."""
from types import SimpleNamespace

import pytest

from relay_self.i_unified_original_context_dev import (
    IUnifiedSourceHold,
    _owner,
    _same_original_source,
    prepare_i_unified_original_ingress,
    read_i_unified_b_current,
    verify_i_unified_original_ingress,
)


def source(**changes):
    data = {
        "self_id": "A", "native_session_id": "native-a",
        "native_probe_seq": 5, "native_probe_ref": "probe-a",
        "paper_session_id": "paper-a", "paper_log_sha256": "a" * 64,
        "resident_epoch": 2,
    }
    data.update(changes)
    return SimpleNamespace(**data)


def handoff(**changes):
    data = {
        "self_id": "A", "native_session_id": "native-a",
        "native_seq": 5, "native_request_id": "probe-a",
        "paper_session_id": "paper-a", "paper_log_sha256": "a" * 64,
        "resident_epoch": 2,
    }
    data.update(changes)
    return SimpleNamespace(**data)


def test_identical_original_qualified_source_is_necessary_not_permission():
    assert _same_original_source(source(), handoff(), "A")
    for altered in (
        {"self_id": "B"}, {"native_session_id": "native-b"},
        {"paper_session_id": "paper-b"}, {"paper_log_sha256": "b" * 64},
        {"resident_epoch": 3},
    ):
        assert not _same_original_source(source(), handoff(**altered), "A")
    # B source is the initial login probe; I2 can be a later correlated SENSE.
    assert _same_original_source(source(), handoff(native_seq=8, native_request_id="later"), "A")
    assert not _same_original_source(source(), handoff(), "B")


def test_original_owner_must_be_same_object_not_second_owner():
    a = object()
    b = object()
    resident = SimpleNamespace(owners={"A": a, "B": b})
    bridge = SimpleNamespace(cognitive_work=resident, owners={"A": a, "B": b})
    assert _owner(bridge, "A") is a
    bridge.owners["A"] = object()
    with pytest.raises(IUnifiedSourceHold):
        _owner(bridge, "A")
    bridge.owners["A"] = a
    with pytest.raises(IUnifiedSourceHold):
        _owner(bridge, "X")


def test_missing_qualified_source_never_produces_cognitive_or_physical_grant():
    for bridge in (None, SimpleNamespace(owners={}, cognitive_work=None)):
        with pytest.raises(IUnifiedSourceHold):
            prepare_i_unified_original_ingress(
                bridge=bridge, boot=None, world=None, links=(), self_id="A",
            )
    with pytest.raises(IUnifiedSourceHold):
        verify_i_unified_original_ingress(
            receipt=object(), bridge=None, boot=None, world=None, links=(),
        )



def test_original_b_current_unified_readonly_positive_then_paper_drift(tmp_path, monkeypatch):
    """Live owner and R0 typed CURRENT may be read; no I2/physical grant."""
    from relay_self.r0_cognitive_context_dev import context_is_live
    from test_bd1b_owner_present_dev import _configured

    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    receipt = read_i_unified_b_current(
        bridge=bridge, boot=boot, world=world, links=links, self_id="A",
    )
    assert receipt.original_owner is bridge.owners["A"]
    assert receipt.original_owner is bridge.cognitive_work.owners["A"]
    assert receipt.context.current.scope.self_id == "A"
    assert receipt.physical_authorized is False
    assert receipt.memory_adopted is False
    assert context_is_live(
        receipt.context, bridge=bridge, boot=boot, world=world, links=links,
    )
    bridge.paper._session_id = "foreign-paper-session"
    assert not context_is_live(
        receipt.context, bridge=bridge, boot=boot, world=world, links=links,
    )
    with pytest.raises(IUnifiedSourceHold):
        read_i_unified_b_current(
            bridge=bridge, boot=boot, world=world, links=links, self_id="A",
        )
