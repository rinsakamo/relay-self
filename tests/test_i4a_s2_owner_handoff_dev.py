"""S2 current Owner / true resident bounded L1 -> Owner-only SkillRun."""
from dataclasses import replace

import pytest

from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    finish_and_anchor_live_stage27_run,
    qualify_live_s2_readiness,
)
from relay_self.i_lane_i4a_s2_owner_handoff_dev import (
    I4ANextHandoffHold,
    begin_live_s2_owner_handoff,
    finish_live_s2_l1,
    prepare_live_s2_l1,
    submit_live_s2_l1,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillState
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi

P = Provenance("i4a-s2-test", "explicit-synthetic-non-success")


def _obs_new(last, inc, request):
    seq = last.seq + inc
    return replace(
        last, seq=seq, request_id=request,
    )


def _adopt(owner, probe):
    owner.observe_world_tick(
        session_id=probe.session_id,
        world_tick=probe.snapshot.time.day * 24000
        + probe.snapshot.time.time_of_day,
    )
    owner.accept_rejoined_worldbody(probe, request_id=probe.request_id)


async def _prepared(f, lane, server):
    loop, _, _, receipts, _ = await _run_multi(f, lane, server)
    owner = loop.owner
    anchor = finish_and_anchor_live_stage27_run(
        loop, lane=lane, outcome=SkillState.CANCELLED,
        reason="explicit test cancellation", at_ns=100000,
        provenance=P,
    )
    first = _obs_new(receipts[-1].settled_probe, 1, "i4a-s2-first")
    _adopt(owner, first)
    ready = qualify_live_s2_readiness(
        owner, physical=f.physical, lane=lane, anchor=anchor,
        first_probe=first,
    )
    prep = prepare_live_s2_l1(
        owner, physical=f.physical, lane=lane,
        readiness=ready, first_probe=first,
    )
    return loop, prep, first


def test_s2_uses_fresh_resident_choice_and_same_owner_without_physical_action(tmp_path):
    async def scenario(f, lane, server):
        loop, prepared, first = await _prepared(f, lane, server)
        owner, peer = loop.owner, f.owners[f.names[1]]
        peer_before = (peer.retained, peer.intent.events,
                       dict(peer.skills), peer.files.physical_wal_file.read_bytes())
        old_wal = owner.files.physical_wal_file.read_bytes()
        old_memory = owner.retained
        server.choice_id = "1"
        ticket = submit_live_s2_l1(prepared)
        after = _obs_new(first, 1, "i4a-s2-after")
        witness = await finish_live_s2_l1(
            prepared, ticket=ticket, post_model_probe=lambda: _return(after),
        )
        _adopt(owner, after)
        handoff = begin_live_s2_owner_handoff(
            witness, at_ns=200000, provenance=P,
        )
        assert handoff.intent_id != loop.handoff.intent_id
        assert handoff.skill_execution_id != loop.handoff.skill_execution_id
        assert handoff.physical_action_issued is False
        assert owner.intent.current_intent.intent_id == handoff.intent_id
        assert owner.skills[handoff.skill_execution_id].state is SkillState.STARTED
        assert owner.skills[loop.handoff.skill_execution_id].state is SkillState.CANCELLED
        assert owner.files.physical_wal_file.read_bytes() == old_wal
        assert owner.retained == old_memory
        assert (peer.retained, peer.intent.events,
                dict(peer.skills), peer.files.physical_wal_file.read_bytes()) == peer_before
    _fixture(tmp_path, scenario)


async def _return(value):
    return value


def test_s2_stale_current_after_inference_cannot_handoff(tmp_path):
    async def scenario(f, lane, server):
        loop, prepared, first = await _prepared(f, lane, server)
        owner = loop.owner
        before = (dict(owner.skills), owner.intent.events,
                  owner.files.physical_wal_file.read_bytes())
        server.choice_id = "1"
        ticket = submit_live_s2_l1(prepared)
        after = _obs_new(first, 1, "i4a-fresh")
        witness = await finish_live_s2_l1(
            prepared, ticket=ticket, post_model_probe=lambda: _return(after),
        )
        stale = _obs_new(first, 2, "i4a-next-observation")
        _adopt(owner, stale)
        with pytest.raises(I4ANextHandoffHold, match="CURRENT"):
            begin_live_s2_owner_handoff(
                witness, at_ns=200000, provenance=P,
            )
        assert (dict(owner.skills), owner.intent.events,
                owner.files.physical_wal_file.read_bytes()) == before
    _fixture(tmp_path, scenario)


def test_s2_memory_changes_during_gpu_cannot_handoff(tmp_path):
    from relay_self.persistent_cognition import Memory

    async def scenario(f, lane, server):
        loop, prepared, first = await _prepared(f, lane, server)
        owner = loop.owner
        server.choice_id = "1"
        ticket = submit_live_s2_l1(prepared)
        after = _obs_new(first, 1, "i4a-memory-inference")
        owner.retain_memory(Memory(
            "i4a-new-memory", "learned something",
            P, P,
        ))
        with pytest.raises(I4ANextHandoffHold, match="state changed"):
            await finish_live_s2_l1(
                prepared, ticket=ticket,
                post_model_probe=lambda: _return(after),
            )
        assert owner.intent.current_intent is None
        assert set(owner.skills) == {loop.handoff.skill_execution_id}
    _fixture(tmp_path, scenario)
