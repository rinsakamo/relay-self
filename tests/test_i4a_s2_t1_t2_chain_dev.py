"""I4a: historical T1 → S1 cancelled → S2 settled → independent C T2.

All observations/HTTP/physical effects are synthetic DEV only.
"""
import pytest

from relay_self.c_lane_l1_evaluation_engine_dev import execute_evaluation
from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold
from relay_self.c_lane_stage27hi_multi_action_review_dev import (
    prepare_stage27hi_multi_review,
)
from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    finish_and_anchor_live_stage27_run,
    qualify_live_s2_readiness,
)
from relay_self.i_lane_i4a_s1_source_capture_dev import (
    audit_s1_prefix_after_s2,
    freeze_original_s1_wal,
)
from relay_self.i_lane_i4a_s2_c_five_axis_dev import (
    execute_i4a_s2_c_five_axis,
    prepare_i4a_s2_c_review,
)
from relay_self.i_lane_i4a_s2_first_move_proposal_dev import (
    propose_s2_first_original_place_move,
)
from relay_self.i_lane_i4a_s2_first_native_move_dev import (
    issue_s2_first_original_place_move_synthetic_dev,
)
from relay_self.i_lane_i4a_s2_owner_handoff_dev import (
    begin_live_s2_owner_handoff,
    finish_live_s2_l1,
    prepare_live_s2_l1,
    submit_live_s2_l1,
)
from relay_self.i_lane_i4a_s2_run_boundary_dev import (
    attest_i4a_s2_empty_run_boundary,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from relay_self.skill import SkillState
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi
from test_i4a_s2_first_native_move_dev import _prepare_native
from test_i4a_s2_first_physical_reservation_dev import _prepare
from test_i4a_s2_owner_handoff_dev import P, _adopt, _obs_new, _return


def test_t1_historical_after_s1_cancel_t2_five_axes_independent(tmp_path):
    async def scenario(f, lane, server):
        loop, step, first, receipts, _ = await _run_multi(f, lane, server)
        owner = loop.owner
        peer = f.owners[f.names[1]]
        old_s1_wal = owner.files.physical_wal_file.read_bytes()
        last_s1 = receipts[-1].settled_probe
        _adopt(owner, last_s1)
        common = dict(
            physical=f.physical, lane=lane, bridge=f.bridge,
            first_action_probe=first, last_settled_probe=last_s1,
        )
        frame_t1 = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        server.choice_id = "2"
        t1 = await execute_evaluation(
            frame_t1, loop, task_id="i4a-t1-s1-original",
            **common,
        )
        assert t1.readout.complete
        assert len(t1.receipts) == 5
        assert t1.readout.action_ids == tuple(r.action_id for r in receipts)
        assert owner.files.physical_wal_file.read_bytes() == old_s1_wal
        assert owner.retained.memories == ()

        # Explicit original Owner lifecycle, never a C1 automatic verdict.
        anchor = finish_and_anchor_live_stage27_run(
            loop, lane=lane, outcome=SkillState.CANCELLED,
            reason="explicit synthetic non-success S1 terminal",
            at_ns=100000, provenance=P,
        )
        archive_dir = tmp_path / "s1-original-evidence"
        archive_dir.mkdir()
        s1_capture = freeze_original_s1_wal(
            owner, physical=f.physical, lane=lane,
            anchor=anchor, evidence_dir=archive_dir,
        )
        peer_before = (
            peer.retained, peer.intent.events, dict(peer.skills),
            peer.files.physical_wal_file.read_bytes(),
        )
        next_first = _obs_new(last_s1, 1, "i4a-t1t2-s2-first")
        _adopt(owner, next_first)
        readiness = qualify_live_s2_readiness(
            owner, physical=f.physical, lane=lane,
            anchor=anchor, first_probe=next_first,
        )
        prepared = prepare_live_s2_l1(
            owner, physical=f.physical, lane=lane,
            readiness=readiness, first_probe=next_first,
        )
        server.choice_id = "1"
        ticket_s2 = submit_live_s2_l1(prepared)
        post_s2 = _obs_new(next_first, 1, "i4a-t1t2-s2-post-l1")
        witness_s2 = await finish_live_s2_l1(
            prepared, ticket=ticket_s2,
            post_model_probe=lambda: _return(post_s2),
        )
        _adopt(owner, post_s2)
        handoff_s2 = begin_live_s2_owner_handoff(
            witness_s2, at_ns=200000, provenance=P,
        )
        boundary = attest_i4a_s2_empty_run_boundary(witness_s2, handoff_s2)
        candidate = propose_s2_first_original_place_move(
            boundary, witness_s2, physical=f.physical, lane=lane,
            native=post_s2,
            capability=PhysicalCapability(
                "MOVE", 1, "locomotion", "DESTINATION", True,
            ),
            at_ns=200010, provenance=P,
        )
        scripted, args = _prepare(f, lane, candidate, witness_s2)
        _prepare_native(f, candidate, scripted)
        receipt_s2 = await issue_s2_first_original_place_move_synthetic_dev(
            scripted, candidate, **args,
        )
        _adopt(owner, receipt_s2.settled_probe)
        source_s2 = prepare_i4a_s2_c_review(
            candidate, receipt_s2,
            physical=f.physical, lane=lane, bridge=f.bridge,
        )
        server.choice_id = "2"
        t2 = await execute_i4a_s2_c_five_axis(
            source_s2, task_id="i4a-t2-after-historical-t1",
        )
        assert t2.readout.complete
        assert len(t2.receipts) == 5
        assert t2.readout.action_ids == (candidate.action_id,)
        assert t2.readout.skill_execution_id == boundary.new_skill_id
        assert t2.readout.skill_execution_id != t1.readout.skill_execution_id
        assert t2.readout.wal_sha256 != t1.readout.wal_sha256
        assert set(t1.readout.action_ids).isdisjoint(t2.readout.action_ids)
        t1_ids = {r.ticket.request_id for r in t1.receipts}
        t2_ids = {r.ticket.request_id for r in t2.receipts}
        assert t1_ids.isdisjoint(t2_ids)
        assert all(v.startswith("i4a-t2-after-historical-t1:") for v in t2_ids)
        assert all(v.startswith("i4a-t1-s1-original:") for v in t1_ids)

        # Old T1 remains an audit record, not a CURRENT adoptable source.
        with pytest.raises(C1OwnerReviewHold):
            prepare_stage27hi_multi_review(
                loop, step, world_id=f.lifecycle.world.world_id, **common,
            )
        wal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert len(wal.records) == 4
        prefix_receipt = audit_s1_prefix_after_s2(
            s1_capture, current_wal=owner.files.physical_wal_file,
            new_action_id=candidate.action_id,
            new_skill_id=boundary.new_skill_id,
            new_intent_id=boundary.new_intent_id,
        )
        assert prefix_receipt.s2_status == "NATIVE_PLACE_MOVE_SETTLED"
        assert not prefix_receipt.restart_authenticated
        assert tuple(r["action_id"] for r in wal.records[:3]) == t1.readout.action_ids
        assert wal.records[3]["action_id"] == candidate.action_id
        assert owner.retained.memories == ()
        assert owner.skills[boundary.old_skill_id].state is SkillState.CANCELLED
        assert owner.skills[boundary.new_skill_id].state is SkillState.STARTED
        assert (peer.retained, peer.intent.events, dict(peer.skills),
                peer.files.physical_wal_file.read_bytes()) == peer_before
    _fixture(tmp_path, scenario)
