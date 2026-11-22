"""Hostile CPU-only checks for the original B/I2 cross-source fence."""
from types import SimpleNamespace

import pytest

from relay_self.i_unified_original_context_dev import (
    IUnifiedSourceHold,
    _owner,
    _same_original_source,
    prepare_i_unified_original_ingress,
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
