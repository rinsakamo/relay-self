"""B same-session Native refresh across original A reJOIN and normal Present poll.

These tests reuse the original Bridge/Owner/decoder and owned synthetic Paper
process. No real World, GPU or Physical Action is exercised.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from relay_self.b_np1b_continuing_b_composite_dev import ContinuingCompositeHold
from relay_self.b_np1b_fresh_native_update_dev import (
    FreshNativeHold,
    read_continuing_b_native_revision,
    update_fresh_native,
)
from relay_self.b_np1b_normal_present_poll_dev import NormalPresentPollHold
from relay_self.b_np1b_owner_bound_rejoin_dev import OwnerBoundRejoinHold
from relay_self.b_np1b_rejoin_composite_source_dev import (
    RejoinCompositeHold,
    build_rejoined_composite_source,
)
from test_b_np1b_normal_present_poll_dev import current_fixture as current_fixture
from test_b_np1b_normal_present_poll_dev import pair as pair
from test_b_np1b_normal_present_poll_dev import rejoined as rejoined
from test_b_np1b_normal_present_poll_dev import rejoined_present as rejoined_present


def bind(pair):
    f, initial, _, history, _, _, _ = pair
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=initial, historical_composite=history,
    )
    return f, initial, history


def advance(pair):
    f, initial = pair[0], pair[1]
    return asyncio.run(update_fresh_native(
        bridge=f.bridge, self_id="B", initial_receipt=initial[1],
    ))


def test_current_original_b_receipt_tracks_multiple_same_session_updates(pair):
    f, initial, old_history = bind(pair)
    prev = f.bridge.poll_normal_present_cpu()
    old_b = prev.b_present.source.composite_receipt
    old_a = prev.a_present.source.composite_receipt
    old_native = read_continuing_b_native_revision(
        bridge=f.bridge, initial_receipt=initial[1],
    )
    assert old_native.native_revision == initial[1].native_revision
    assert old_native.native_request_id == initial[1].native_request_id
    assert old_native.native_sequence == initial[1].native_sequence

    b_session = f.bridge.sessions["B"]
    b_scope = f.cognitive.current_scope("B")
    original_b_login = f.bridge.last_login_evidence["B"]
    original_b_probe = f.bridge.last_login_observations["B"]
    original_a_probe = f.owners["A"].current_worldbody_observation
    original_a_scope = f.cognitive.current_scope("A")
    previous_native = old_native

    for index in (1, 2):
        newest = advance(pair)
        assert newest.native_sequence == initial[1].native_sequence + index
        assert newest.native_session_id == initial[1].native_session_id
        assert newest.native_revision != previous_native.native_revision
        assert newest.native_request_id != previous_native.native_request_id
        assert newest == read_continuing_b_native_revision(
            bridge=f.bridge, initial_receipt=initial[1],
        )

        result = f.bridge.poll_normal_present_cpu()
        assert result == f.bridge.poll_normal_present_cpu()
        b = result.b_present.source.composite_receipt
        a = result.a_present.source.composite_receipt
        assert b.native_revision == newest.native_revision
        assert b.native_request_id == newest.native_request_id
        assert b.native_sequence == newest.native_sequence
        assert b.native_source_ref == newest.native_source_ref
        assert b.native_world_time == newest.native_world_time
        assert b.native_session_id == original_b_probe.session_id
        assert b.paper_revision == old_b.paper_revision
        assert b.paper_log_sha256 == old_b.paper_log_sha256
        assert a.native_revision == old_a.native_revision
        assert a.native_session_id == old_a.native_session_id
        assert a.b_continuity_revision != prev.a_present.source.composite_receipt.b_continuity_revision
        assert b.b_continuity_revision == a.b_continuity_revision
        assert b.a_rejoin_composite_ref != old_b.a_rejoin_composite_ref
        assert a.composite_revision != prev.a_present.source.composite_receipt.composite_revision
        assert b.composite_revision != prev.b_present.source.composite_receipt.composite_revision
        assert result.source_pair_revision != prev.source_pair_revision
        assert result.a_inquiry is not None and result.b_inquiry is not None
        for sid, projection in (("A", result.a_present), ("B", result.b_present)):
            assert projection.present.three_self.scope.self_id == sid
            assert projection.exploration_need is not None
            assert projection.present.three_self.source_revision_refs[-1] == (
                "composite:rejoin:" + projection.source.composite_receipt.composite_revision
            )
        assert f.bridge.sessions["B"] is b_session
        assert f.cognitive.current_scope("B") == b_scope
        assert f.bridge.last_login_evidence["B"] is original_b_login
        assert f.bridge.last_login_observations["B"] is original_b_probe
        assert f.owners["A"].current_worldbody_observation is original_a_probe
        assert f.cognitive.current_scope("A") == original_a_scope
        assert old_history.native_session_id == pair[4]
        assert initial[1].native_revision == old_native.native_revision
        prev, previous_native = result, newest


@pytest.mark.parametrize("fault", [
    "adopted_revision", "adopted_probe", "copied_probe", "bound_initial",
    "pending", "decoder", "last_login", "last_login_probe", "tick",
    "native_session", "world_epoch", "resident_epoch", "owner", "b_logout",
    "paper_log", "paper_pid",
])
def test_current_original_b_rejects_tampered_fresh_adoption(pair, monkeypatch, fault):
    f, initial, history = bind(pair)
    assert advance(pair)
    assert f.bridge.poll_normal_present_cpu().source_pair_revision
    bridge = f.bridge
    b = f.owners["B"]
    record = bridge._fresh_native_current["B"]
    probe, revision = record

    if fault == "adopted_revision":
        bridge._fresh_native_current["B"] = (probe, replace(revision, native_revision="fake"))
    elif fault == "adopted_probe":
        bridge._fresh_native_current["B"] = (replace(probe, seq=probe.seq), revision)
    elif fault == "copied_probe":
        b.current_worldbody_observation = replace(probe, seq=probe.seq)
    elif fault == "bound_initial":
        bridge._fresh_native_initial["B"] = replace(
            initial[1], native_request_id="foreign",
        )
    elif fault == "pending":
        bridge._fresh_native_pending["B"] = object()
    elif fault == "decoder":
        bridge.sessions["B"]._decoder._next_seq += 1
    elif fault == "last_login":
        bridge.last_login_evidence["B"] = replace(
            bridge.last_login_evidence["B"], observation_ref="foreign",
        )
    elif fault == "last_login_probe":
        bridge.last_login_observations["B"] = replace(
            bridge.last_login_observations["B"], request_id="foreign",
        )
    elif fault == "tick":
        b.last_observed_tick += 1
    elif fault == "native_session":
        bridge.sessions["B"]._started = replace(
            bridge.sessions["B"].started, session_id="foreign",
        )
    elif fault == "world_epoch":
        f.cognitive._states["B"].world_epoch += 1
    elif fault == "resident_epoch":
        f.cognitive._states["B"].epoch += 1
    elif fault == "owner":
        bridge.owners["B"] = bridge.owners["A"]
    elif fault == "b_logout":
        asyncio.run(bridge.logout("B"))
    elif fault == "paper_log":
        f.paper._log_path.write_text(f.paper._log_path.read_text() + "unverified\n")
    else:
        process = f.paper._assert_owned
        monkeypatch.setattr(
            f.paper, "_assert_owned",
            lambda: type("ChangedPaper", (), {"pid": process().pid + 1})(),
        )

    if fault == "paper_pid":
        # The A verifier independently requires the original owned Paper PID.
        with pytest.raises((RejoinCompositeHold, RuntimeError)):
            build_rejoined_composite_source(
                bridge=bridge, initial_receipts=initial, historical_composite=history,
            )
    elif fault != "paper_log":
        # B Native provenance is independently validated without Paper bytes.
        with pytest.raises((FreshNativeHold, RuntimeError, ValueError)):
            read_continuing_b_native_revision(
                bridge=bridge, initial_receipt=initial[1],
            )
    # A alone may recognize the old Paper ACK despite a later log append;
    # the paired B source MUST reject a log without a latest terminal ACK.
    with pytest.raises((NormalPresentPollHold, RuntimeError, ValueError)):
        bridge.poll_normal_present_cpu()


def test_b_native_update_cannot_publish_during_original_paper_qualification(pair, monkeypatch):
    f, initial, _, historical, *_ = pair
    paper = f.paper
    original = paper.read_owned_log
    changed = [False]

    def update_during_paper(session):
        if not changed[0]:
            changed[0] = True
            advance(pair)
        return original(session)

    monkeypatch.setattr(paper, "read_owned_log", update_during_paper)
    with pytest.raises((OwnerBoundRejoinHold, RejoinCompositeHold, ContinuingCompositeHold)):
        build_rejoined_composite_source(
            bridge=f.bridge, initial_receipts=initial,
            historical_composite=historical,
        )
    assert changed == [True]


def test_invalid_detached_b_source_is_not_promoted(pair):
    f, initial, _, historical, *_ = pair
    original = read_continuing_b_native_revision(
        bridge=f.bridge, initial_receipt=initial[1],
    )
    with pytest.raises(FreshNativeHold):
        read_continuing_b_native_revision(
            bridge=f.bridge,
            initial_receipt=replace(initial[1], native_request_id="spoof"),
        )
    newest = advance(pair)
    with pytest.raises(FreshNativeHold):
        read_continuing_b_native_revision(
            bridge=f.bridge,
            initial_receipt=replace(initial[1], native_revision=newest.native_revision),
        )
    assert newest.native_revision != original.native_revision
    assert f.bridge.last_login_observations["B"].request_id == original.native_request_id
    assert build_rejoined_composite_source(
        bridge=f.bridge, initial_receipts=initial,
        historical_composite=historical,
    ).b_continuity_revision
