"""I4a direct: scoped atomic original S1 terminal and read-only S2 admission."""
from dataclasses import replace

import pytest

from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    I4ALiveAnchorHold,
    finish_and_anchor_live_stage27_run,
    qualify_live_s2_readiness,
    verify_live_wal_history_anchor,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillState
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi

P = Provenance("i4a-synthetic", "explicit-non-success-s1-termination")


def _terminal(loop, lane):
    return finish_and_anchor_live_stage27_run(
        loop, lane=lane, outcome=SkillState.CANCELLED,
        reason="synthetic explicit reviewed cancellation", at_ns=100000,
        provenance=P,
    )


def test_atomic_original_terminal_anchors_then_current_s2_readonly(tmp_path):
    async def scenario(f, lane, server):
        loop, step, first, receipts, _ = await _run_multi(f, lane, server)
        owner = loop.owner
        peer = f.owners[f.names[1]]
        peer_before = (peer.retained, peer.intent.events, dict(peer.skills),
                       peer.files.physical_wal_file.read_bytes())
        last = receipts[-1].settled_probe
        wal_before = owner.files.physical_wal_file.read_bytes()
        anchor = _terminal(loop, lane)
        assert owner.skills[loop.handoff.skill_execution_id].state is SkillState.CANCELLED
        assert owner.intent.current_intent is None
        assert owner.files.physical_wal_file.read_bytes() == wal_before
        verify_live_wal_history_anchor(
            owner, physical=f.physical, lane=lane, anchor=anchor)
        seq = last.seq + 1
        next_probe = replace(
            last, seq=seq, request_id="i4a-s2-current",
        )
        owner.observe_world_tick(
            session_id=next_probe.session_id,
            world_tick=next_probe.snapshot.time.day * 24000
            + next_probe.snapshot.time.time_of_day,
        )
        owner.accept_rejoined_worldbody(
            next_probe, request_id=next_probe.request_id)
        ready = qualify_live_s2_readiness(
            owner, physical=f.physical, lane=lane,
            anchor=anchor, first_probe=next_probe,
        )
        assert ready.wal_sha256 == anchor.wal_sha256
        assert ready.probe_seq > last.seq
        assert ready.self_id == owner.self_id
        assert not hasattr(ready, "action_issue_authorized")
        assert (peer.retained, peer.intent.events, dict(peer.skills),
                peer.files.physical_wal_file.read_bytes()) == peer_before
    _fixture(tmp_path, scenario)


def test_competing_lease_blocks_atomic_terminal_without_mutation(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        owner = loop.owner
        state = (owner.intent.events, dict(owner.skills),
                 owner.files.physical_wal_file.read_bytes())
        with f.physical.lease(
            self_id=owner.self_id,
            native_session_id=owner.native_session_id,
            action_id="i4a-competitor", effect_family="NONE",
        ):
            with pytest.raises(I4ALiveAnchorHold, match="physical"):
                _terminal(loop, lane)
        assert (owner.intent.events, dict(owner.skills),
                owner.files.physical_wal_file.read_bytes()) == state
        assert getattr(owner, "_i4a_live_wal_anchor", None) is None
    _fixture(tmp_path, scenario)


def test_stale_and_foreign_s2_current_rejected(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, receipts, _ = await _run_multi(f, lane, server)
        owner = loop.owner
        anchor = _terminal(loop, lane)
        with pytest.raises(I4ALiveAnchorHold, match="Owner/Native"):
            qualify_live_s2_readiness(
                owner, physical=f.physical, lane=lane,
                anchor=anchor, first_probe=receipts[-1].settled_probe,
            )
        seq = receipts[-1].settled_probe.seq + 1
        new_probe = replace(
            receipts[-1].settled_probe, seq=seq,
            request_id="i4a-new-probe",
        )
        owner.observe_world_tick(
            session_id=new_probe.session_id,
            world_tick=new_probe.snapshot.time.day * 24000
            + new_probe.snapshot.time.time_of_day,
        )
        owner.accept_rejoined_worldbody(new_probe, request_id=new_probe.request_id)
        forged = replace(new_probe, request_id="forged-readonly")
        with pytest.raises(I4ALiveAnchorHold, match="Owner/Native"):
            qualify_live_s2_readiness(
                owner, physical=f.physical, lane=lane,
                anchor=anchor, first_probe=forged,
            )
    _fixture(tmp_path, scenario)
