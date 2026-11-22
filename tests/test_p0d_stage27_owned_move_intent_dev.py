"""Stage27a: original restored Gemma selection becomes original A Intent/Skill.

Synthetic HTTP and native probes, never real Gemma or Minecraft effects.
The original PLACE target is not silently interpreted as RELATIVE MOVE.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from relay_self.p0d_stage26_gemma_l1_dev import (
    finish_restored_preset_l1,
    prepare_restored_preset_l1,
    submit_restored_preset_l1,
)
from relay_self.p0d_stage27_owned_move_intent_dev import (
    Stage27MoveHandoffRefusal,
    begin_stage27_owned_move_intent,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from test_p0d_real_preset_checkpoint_dev import native_probe
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit, _online_two_actor


async def _one_a_choice(f, lane):
    original = await _online_two_actor(f, lane)
    sid = f.names[0]
    native = f.bridge.sessions[sid].started.session_id
    prepared = prepare_restored_preset_l1(
        self_id=sid, restored=original[sid],
        first=native_probe(sid, 10, session=native),
        owner=f.owners[sid], lane=lane,
    )
    ticket = submit_restored_preset_l1(prepared, lane=lane)
    witness, refreshed = await finish_restored_preset_l1(
        prepared, ticket=ticket, lane=lane,
        fresh_probe=lambda: asyncio.sleep(0, result=native_probe(
            sid, 11, session=native,
        )),
    )
    return prepared, ticket, witness, refreshed


def _handoff(f, lane, prepared, ticket, witness, refreshed, **kwargs):
    args = dict(
        prepared=prepared, ticket=ticket, witness=witness,
        refreshed=refreshed, lane=lane, physical=f.physical,
        actor_self_id=f.names[0], at_ns=100,
        provenance=Provenance("original-stage27-dev", "self-A"),
    )
    args.update(kwargs)
    return begin_stage27_owned_move_intent(**args)


def test_a_real_bounded_ready_starts_only_original_a_intent_and_skill(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        prepared, ticket, witness, refreshed = await _one_a_choice(f, lane)
        before_b = (
            f.owners[f.names[1]].intent.events,
            tuple(f.owners[f.names[1]].skills.items()),
            PhysicalActionJournal.restore(
                f.owners[f.names[1]].files.physical_wal_file,
                self_id=f.names[1],
            ).digest,
        )
        result = _handoff(f, lane, prepared, ticket, witness, refreshed)
        assert result.self_id == f.names[0]
        assert result.decision_number == "1"
        assert result.target_kind == "DESTINATION"
        assert result.intent_id == f.owners[f.names[0]].intent.current_intent.intent_id
        assert result.skill_execution_id in f.owners[f.names[0]].skills
        assert result.invocation_ref == witness.candidate_invocation_ref
        assert result.preset_ref == witness.preset_ref
        assert result.outcome == "INTENT_STARTED_TARGET_RESOLUTION_REQUIRED"
        assert not result.target_resolution_attested
        assert not result.physical_proposal_authorized
        assert not result.physical_action_issued
        assert not result.wal_modified
        assert not result.peer_owner_mutated
        after_b = (
            f.owners[f.names[1]].intent.events,
            tuple(f.owners[f.names[1]].skills.items()),
            PhysicalActionJournal.restore(
                f.owners[f.names[1]].files.physical_wal_file,
                self_id=f.names[1],
            ).digest,
        )
        assert before_b == after_b
        for sid in f.names:
            assert not f.owners[sid].supervisor.open_actions
            PhysicalActionJournal.restore(
                f.owners[sid].files.physical_wal_file, self_id=sid,
            ).require_clear()
        assert len(http.calls) == 1
        with pytest.raises(Stage27MoveHandoffRefusal):
            _handoff(f, lane, prepared, ticket, witness, refreshed)
        assert len(f.owners[f.names[0]].intent.events) == 1
        for sid in f.names:
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


@pytest.mark.parametrize("choice", ["2", "3"])
def test_non_ready_never_commits_any_intent_or_skill(tmp_path, choice):
    http = _SyntheticLlamaServer()
    http.choice_id = choice
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        prepared, ticket, witness, refreshed = await _one_a_choice(f, lane)
        assert witness.l1_status in {"DEFER", "ESCALATE_L2"}
        with pytest.raises(Stage27MoveHandoffRefusal):
            _handoff(f, lane, prepared, ticket, witness, refreshed)
        assert f.owners[f.names[0]].intent.current_intent is None
        assert not f.owners[f.names[0]].skills
        for sid in f.names:
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


@pytest.mark.parametrize("fault", [
    "foreign_actor", "old_session", "foreign_request", "recheck_seq",
    "recheck_id", "preset_ref", "invocation_ref", "unsafe_permission",
    "not_idle", "replayed_old_gpu", "wrong_choice", "wrong_contract",
])
def test_source_tampering_stays_nonissuing_and_uncommitted(tmp_path, fault):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        prepared, ticket, witness, refreshed = await _one_a_choice(f, lane)
        kw = {}
        if fault == "foreign_actor":
            kw["actor_self_id"] = f.names[1]
        elif fault == "old_session":
            witness = replace(
                witness, new_native_session_id=witness.former_native_session_id,
            )
        elif fault == "foreign_request":
            witness = replace(witness, inference_request_id="foreign-request")
        elif fault == "recheck_seq":
            witness = replace(witness, recheck_native_seq=refreshed.seq + 1)
        elif fault == "recheck_id":
            witness = replace(witness, recheck_probe_id="forged-probe-id")
        elif fault == "preset_ref":
            witness = replace(witness, preset_ref="foreign-preset")
        elif fault == "invocation_ref":
            witness = replace(witness, candidate_invocation_ref="foreign-invocation")
        elif fault == "unsafe_permission":
            witness = replace(witness, selection_is_action_permission=True)
        elif fault == "not_idle":
            witness = replace(witness, backend_slot_idle_after_call=False)
        elif fault == "replayed_old_gpu":
            witness = replace(witness, old_gpu_result_reused=True)
        elif fault == "wrong_choice":
            witness = replace(witness, selected_number="3")
        elif fault == "wrong_contract":
            witness = replace(witness, target_contract_ref="foreign-contract")
        with pytest.raises(Stage27MoveHandoffRefusal):
            _handoff(f, lane, prepared, ticket, witness, refreshed, **kw)
        for sid in f.names:
            assert f.owners[sid].intent.current_intent is None
            assert not f.owners[sid].skills
            assert not f.owners[sid].supervisor.open_actions
            PhysicalActionJournal.restore(
                f.owners[sid].files.physical_wal_file, self_id=sid,
            ).require_clear()
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


def test_stage27_refuses_stale_l1_after_actual_a_logout(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        prepared, ticket, witness, refreshed = await _one_a_choice(f, lane)
        await f.bridge.logout(f.names[0])
        with pytest.raises(Stage27MoveHandoffRefusal):
            _handoff(f, lane, prepared, ticket, witness, refreshed)
        assert f.owners[f.names[0]].intent.current_intent is None
        await f.bridge.logout(f.names[1])

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()
