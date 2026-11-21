"""I4a S1 history → independent S2 native settled → C five-axis T2.

All model HTTP / Native effects are synthetic fixtures, never real World,
Gemma, C1 approval or actual Paper movement.
"""
import hashlib
import json
from dataclasses import replace

import pytest

from relay_self.c_lane_evaluation_readout_dev import EvaluationAxis
from relay_self.i_lane_i4a_s2_c_five_axis_dev import (
    I4AS2CSourceHold,
    execute_i4a_s2_c_five_axis,
    prepare_i4a_s2_c_review,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from test_c_lane_stage27hi_multi_action_review_dev import _fixture
from test_i4a_s2_first_move_proposal_dev import _first_s2, _propose
from test_i4a_s2_first_native_move_dev import (
    _prepare_native,
    issue_s2_first_original_place_move_synthetic_dev,
)
from test_i4a_s2_first_physical_reservation_dev import _prepare


async def _evaluatable(f, lane, server):
    loop, witness, boundary, observed = await _first_s2(f, lane, server)
    candidate = _propose(f, lane, witness, boundary, observed)
    native, args = _prepare(f, lane, candidate, witness)
    _prepare_native(f, candidate, native)
    receipt = await issue_s2_first_original_place_move_synthetic_dev(
        native, candidate, **args,
    )
    owner = loop.owner
    last = receipt.settled_probe
    owner.observe_world_tick(
        session_id=last.session_id,
        world_tick=last.snapshot.time.day * 24000
        + last.snapshot.time.time_of_day,
    )
    owner.accept_rejoined_worldbody(last, request_id=last.request_id)
    source = prepare_i4a_s2_c_review(
        candidate, receipt, physical=f.physical, lane=lane, bridge=f.bridge,
    )
    return loop, candidate, receipt, source


def test_s2_t2_all_five_axes_only_new_action_old_s1_retained(tmp_path):
    async def scenario(f, lane, server):
        loop, candidate, receipt, source = await _evaluatable(f, lane, server)
        owner, peer = loop.owner, f.owners[f.names[1]]
        old_peer = (
            peer.retained, peer.intent.events,
            dict(peer.skills), peer.files.physical_wal_file.read_bytes(),
        )
        old_owner = (owner.retained, owner.intent.events, dict(owner.skills))
        s2_action = candidate.action_id
        s1_ids = candidate.boundary.prefix_action_ids
        assert source.frame.action_ids == (s2_action,)
        assert not set(source.frame.action_ids).intersection(s1_ids)
        assert not source.physical_action_authorized
        assert not source.memory_adoption_authorized
        before_wal = owner.files.physical_wal_file.read_bytes()
        before_count = len(server.calls)
        server.choice_id = "2"
        executed = await execute_i4a_s2_c_five_axis(
            source, task_id="i4a-t2-current-s2-five",
        )
        assert len(server.calls) == before_count + 5
        assert executed.readout.task_id == "i4a-t2-current-s2-five"
        assert executed.readout.action_ids == (s2_action,)
        assert executed.readout.skill_execution_id == candidate.boundary.new_skill_id
        assert executed.readout.wal_sha256 == source.canonical_wal_sha256
        assert executed.readout.complete
        assert {axis.axis for axis in executed.readout.axes} == set(EvaluationAxis)
        assert len(executed.receipts) == 5
        assert len({receipt.ticket.request_id for receipt in executed.receipts}) == 5
        assert all(
            receipt.ticket.request_id.startswith("i4a-t2-current-s2-five:")
            and receipt.ticket.work_ref == receipt.task.task_ref
            and receipt.ticket.native_session_id == candidate.boundary.native_session_id
            and receipt.task.intent_ref == candidate.boundary.new_intent_id
            and not receipt.ticket.action_issue_authorized
            for receipt in executed.receipts
        )
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert len(journal.records) == 4
        assert tuple(row["action_id"] for row in journal.records[:3]) == s1_ids
        assert tuple(row["action_id"] for row in journal.records[3:]) == (s2_action,)
        assert journal.digest == executed.readout.wal_sha256
        assert not journal.unresolved
        assert owner.files.physical_wal_file.read_bytes() == before_wal
        assert (owner.retained, owner.intent.events, dict(owner.skills)) == old_owner
        assert (peer.retained, peer.intent.events, dict(peer.skills),
                peer.files.physical_wal_file.read_bytes()) == old_peer
        assert receipt.journal_status == "NATIVE_PLACE_MOVE_SETTLED"
    _fixture(tmp_path, scenario)


@pytest.mark.parametrize("fault", [
    "prefix-rechecksum", "suffix-rechecksum",
    "current-changed", "wrong-t2-id", "foreign-frame",
])
def test_s2_t2_rejects_invalid_original_source_without_llm_calls(
    tmp_path, fault,
):
    async def scenario(f, lane, server):
        loop, candidate, receipt, source = await _evaluatable(f, lane, server)
        owner = loop.owner
        task = "i4a-t2-rejection-case"
        if fault in ("prefix-rechecksum", "suffix-rechecksum"):
            path = owner.files.physical_wal_file
            envelope = json.loads(path.read_bytes())
            idx = 0 if fault == "prefix-rechecksum" else 3
            envelope["body"]["actions"][idx]["action_id"] = "forged-action"
            canonical = json.dumps(
                envelope["body"], sort_keys=True, ensure_ascii=False,
                separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")
            envelope["sha256"] = hashlib.sha256(canonical).hexdigest()
            path.write_text(json.dumps(envelope), encoding="utf-8")
        elif fault == "current-changed":
            owner.current_worldbody_observation = replace(
                receipt.settled_probe, seq=receipt.settled_probe.seq + 1,
            )
        elif fault == "wrong-t2-id":
            task = "i4a-t1-old-task"
        elif fault == "foreign-frame":
            source = replace(source, frame=replace(
                source.frame, skill_execution_id="old-run-or-foreign",
            ))
        prior = len(server.calls)
        with pytest.raises(I4AS2CSourceHold):
            await execute_i4a_s2_c_five_axis(source, task_id=task)
        assert len(server.calls) == prior
    _fixture(tmp_path, scenario)


def test_s2_t2_midflight_current_loss_preserves_receipt_and_no_adoption(
    tmp_path, monkeypatch,
):
    async def scenario(f, lane, server):
        loop, candidate, receipt, source = await _evaluatable(f, lane, server)
        owner = loop.owner
        old_owner = (owner.retained, owner.intent.events, dict(owner.skills))
        original = lane.await_result
        counter = 0

        async def invalidate(ticket, **kwargs):
            nonlocal counter
            result = await original(ticket, **kwargs)
            counter += 1
            if counter == 1:
                owner.current_worldbody_observation = replace(
                    receipt.settled_probe, seq=receipt.settled_probe.seq + 1,
                )
            return result

        monkeypatch.setattr(lane, "await_result", invalidate)
        server.choice_id = "2"
        with pytest.raises(I4AS2CSourceHold) as exc_info:
            await execute_i4a_s2_c_five_axis(
                source, task_id="i4a-t2-eviction",
            )
        audit = exc_info.value.evaluation_audit
        assert audit.status == "SOURCE_STALE"
        assert audit.task_id == "i4a-t2-eviction"
        assert len(audit.receipts) == 1
        assert len(audit.axes) == 0
        assert counter == 1
        assert (owner.retained, owner.intent.events, dict(owner.skills)) == old_owner
    _fixture(tmp_path, scenario)
