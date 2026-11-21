"""I4a characterization: settled S1 still cannot enter the existing S2 handoff."""
import asyncio
from dataclasses import replace

import pytest

from relay_self.c_lane_l1_evaluation_engine_dev import execute_evaluation
from relay_self.c_lane_stage27hi_multi_action_review_dev import prepare_stage27hi_multi_review
from relay_self.p0d_stage26_gemma_l1_dev import (
    Stage26L1Refusal,
    finish_restored_preset_l1,
    prepare_restored_preset_l1,
    submit_restored_preset_l1,
)
from relay_self.p0d_stage27_owned_move_intent_dev import (
    Stage27MoveHandoffRefusal,
    begin_stage27_owned_move_intent,
)
from relay_self.persistent_cognition import Memory
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.skill import SkillState
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi


def test_settled_evaluated_and_cancelled_run_still_blocks_next_handoff(tmp_path):
    async def scenario(f, lane, server):
        loop, step, first, receipts, _ = await _run_multi(f, lane, server)
        owner = loop.owner
        peer = f.owners[f.names[1]]
        peer_before = (peer.intent.events, dict(peer.skills), peer.retained,
                       peer.files.physical_wal_file.read_bytes())
        last = receipts[-1].settled_probe
        owner.observe_world_tick(session_id=last.session_id, world_tick=(
            last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day))
        owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common)
        result = await execute_evaluation(frame, loop, task_id="i4a-t1", **common)
        assert len(result.receipts) == 5
        wal_before = owner.files.physical_wal_file.read_bytes()
        retained = owner.retained
        provenance = Provenance("i4a-test", "explicit-synthetic-cancel")
        owner.finish_reviewed_skill(loop.handoff.skill_execution_id,
                                    outcome=SkillState.CANCELLED,
                                    reason="synthetic explicit cancellation",
                                    at_ns=100000, provenance=provenance)
        owner.complete_intent(loop.handoff.intent_id, reason="synthetic release",
                              at_ns=100001, provenance=provenance)
        assert owner.intent.current_intent is None
        assert owner.skills[loop.handoff.skill_execution_id].state is SkillState.CANCELLED
        assert owner.retained == retained
        assert owner.files.physical_wal_file.read_bytes() == wal_before
        PhysicalActionJournal.restore(owner.files.physical_wal_file,
                                      self_id=owner.self_id).require_clear()
        # A new synthetic probe and resident GPU decision do not erase S1.
        new_first = replace(last, seq=last.seq + 1, request_id="i4a-next-first")
        new_second = replace(last, seq=last.seq + 2, request_id="i4a-next-recheck")
        prepared = prepare_restored_preset_l1(
            self_id=owner.self_id, restored=loop.prepared.restored,
            first=new_first, owner=owner, lane=lane,
            definition=loop.prepared.definition)
        ticket = submit_restored_preset_l1(prepared, lane=lane)
        witness, refreshed = await finish_restored_preset_l1(
            prepared, ticket=ticket, lane=lane,
            fresh_probe=lambda: asyncio.sleep(0, result=new_second))
        with pytest.raises(Stage27MoveHandoffRefusal, match="original live Self"):
            begin_stage27_owned_move_intent(
                prepared, ticket=ticket, witness=witness, refreshed=refreshed,
                lane=lane, physical=f.physical, actor_self_id=owner.self_id,
                at_ns=100002, provenance=provenance)
        assert owner.intent.current_intent is None
        assert owner.files.physical_wal_file.read_bytes() == wal_before
        owner.retain_memory(Memory("i4a-memory", "retained audit memory",
                                   provenance, provenance))
        with pytest.raises(Stage26L1Refusal, match="recovered A/B Schema"):
            prepare_restored_preset_l1(
                self_id=owner.self_id, restored=loop.prepared.restored,
                first=new_first, owner=owner, lane=lane,
                definition=loop.prepared.definition)
        assert owner.retained.memories[-1].memory_id == "i4a-memory"
        assert (peer.intent.events, dict(peer.skills), peer.retained,
                peer.files.physical_wal_file.read_bytes()) == peer_before
    _fixture(tmp_path, scenario)


def test_recomputed_wal_checksum_is_not_historical_authentication(tmp_path):
    """A valid readback alone cannot prove the prior Owner's settled history."""
    import hashlib
    import json

    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        owner = loop.owner
        path = owner.files.physical_wal_file
        original = PhysicalActionJournal.restore(path, self_id=owner.self_id)
        assert len(original.records) == 3
        original.require_clear()
        envelope = json.loads(path.read_bytes())
        envelope["body"]["actions"][0]["action_id"] = "forged-action-id"
        canonical = json.dumps(
            envelope["body"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        envelope["sha256"] = hashlib.sha256(canonical).hexdigest()
        path.write_text(json.dumps(envelope), encoding="utf-8")
        changed = PhysicalActionJournal.restore(path, self_id=owner.self_id)
        changed.require_clear()
        assert changed.digest != original.digest
        assert changed.records[0]["action_id"] == "forged-action-id"
        assert changed.records[0]["action_id"] != original.records[0]["action_id"]

    _fixture(tmp_path, scenario)
