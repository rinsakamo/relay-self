"""Stage27g synthetic provider tests: original post-Action HTTP and fresh native fence."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition
from experiments.p0d_stage27_real_place_move_dev import (
    Stage27RealWorldRefusal,
    _native_post_model_probe_readback,
    run_stage27_real_world,
    stage27g_real_a_motor_hook,
)
from relay_self.p0d_stage27f_l1_evaluation_dev import (
    Stage27EvaluationRefusal,
    prepare_stage27f_outcome_evaluation,
)
from relay_self.p0d_stage27g_real_l1_evaluation_dev import (
    Stage27gEvaluationRefusal,
    finish_stage27g_original_evaluation,
    submit_stage27g_original_evaluation,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.relay_engine import BoundedChoice
from relay_self.skill import SkillState
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27f_l1_evaluation_dev import _run_original


def _run_case(tmp_path, case):
    server = _SyntheticLlamaServer()
    server.choice_id = "1"
    endpoint = server.start()
    fixture = ResidentFixture(
        tmp_path, 2, cognitive_work=True, allow_resident_move=True,
    )
    lane = _attach_and_audit(fixture, endpoint, tmp_path)
    try:
        return asyncio.run(case(fixture, lane, server))
    finally:
        fixture.stop_paper()
        server.stop()


def _new_probe(receipt, *, distant=False):
    old = receipt.settled_probe
    position = old.snapshot.position
    if distant:
        position = MineflayerPosition(position.x - 6.0, position.y, position.z)
    return replace(
        old, seq=old.seq + 1,
        request_id=f"stage27g-post-model-{old.seq + 1}",
        snapshot=replace(old.snapshot, position=position),
    )


@pytest.mark.parametrize(
    ("mode", "model_number", "expected_recommendation"),
    [
        ("moved", "2", "REVIEW_COMPLETION"),
        ("moved", "1", "CONTINUE_INTENT"),
        ("moved", "3", "ESCALATE_L2"),
        ("moved", "4", "DEFER"),
        ("blocked", "3", "ESCALATE_L2"),
        ("overshoot", "4", "DEFER"),
    ],
)
def test_actual_owned_http_choice_is_read_only_after_real_shape_action(
    tmp_path, mode, model_number, expected_recommendation,
):
    async def scenario(f, lane, server):
        pre, handoff, l0, receipt = await _run_original(f, lane, mode=mode)
        a, b = f.owners[f.names[0]], f.owners[f.names[1]]
        frame = prepare_stage27f_outcome_evaluation(
            pre, handoff, l0, receipt, owner=a,
            physical=f.physical, world_epoch=pre.world_epoch,
        )
        a_intent_before = a.intent.events
        a_skills_before = dict(a.skills)
        peer_before = (b.intent.events, tuple(b.skills),
                       PhysicalActionJournal.restore(
                           b.files.physical_wal_file, self_id=b.self_id,
                       ).digest)
        before_actions = len(a.supervisor.open_actions)
        before_calls = len(server.calls)
        server.choice_id = model_number
        ticket = submit_stage27g_original_evaluation(
            frame, pre, owner=a, physical=f.physical, lane=lane,
        )
        assert ticket.mode.value == "bounded"
        invoked = []

        async def fresh():
            # Cannot request a post-model native probe until HTTP has returned.
            assert len(server.calls) == before_calls + 1
            assert lane.require_world_idle().n_slots == 1
            invoked.append("fresh-post-model")
            return _new_probe(receipt)

        choice, witness = await finish_stage27g_original_evaluation(
            frame, pre, owner=a, physical=f.physical,
            lane=lane, ticket=ticket, fresh_probe=fresh,
        )
        assert invoked == ["fresh-post-model"]
        assert choice.model_source_attested
        assert choice.recommendation == expected_recommendation
        assert choice.resolved
        assert witness.model_choice_number == model_number
        assert witness.provider_call_facts["finish_reason"] == "stop"
        assert witness.raw_http_request_sha256
        assert witness.raw_http_response_sha256
        assert witness.raw_http_response_bytes > 0
        assert witness.fresh_native_probe_seq > frame.source_probe_seq
        assert witness.backend_slot_idle_after_call
        assert not witness.owner_mutated
        assert not witness.skill_succeeded
        assert not witness.goal_succeeded
        assert not witness.physical_action_issued
        assert a.intent.events == a_intent_before
        assert a.skills == a_skills_before
        assert a.skills[handoff.skill_execution_id].state is SkillState.STARTED
        assert len(a.supervisor.open_actions) == before_actions
        assert (b.intent.events, tuple(b.skills),
                PhysicalActionJournal.restore(
                    b.files.physical_wal_file, self_id=b.self_id,
                ).digest) == peer_before
        return True

    assert _run_case(tmp_path, scenario)


def test_fresh_world_change_downgrades_model_completion_review(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, l0, receipt = await _run_original(f, lane, mode="moved")
        a = f.owners[f.names[0]]
        frame = prepare_stage27f_outcome_evaluation(
            pre, handoff, l0, receipt, owner=a,
            physical=f.physical, world_epoch=pre.world_epoch,
        )
        server.choice_id = "2"
        ticket = submit_stage27g_original_evaluation(
            frame, pre, owner=a, physical=f.physical, lane=lane,
        )
        choice, witness = await finish_stage27g_original_evaluation(
            frame, pre, owner=a, physical=f.physical,
            lane=lane, ticket=ticket,
            fresh_probe=lambda: asyncio.sleep(0, result=_new_probe(
                receipt, distant=True,
            )),
        )
        assert witness.model_choice_number == "2"
        assert choice.recommendation == "RECONSIDER_FRESH_WORLD_CHANGED"
        assert not choice.resolved
        assert witness.post_model_target_status == "OUTSIDE"
        assert not witness.goal_succeeded
        assert a.intent.current_intent is not None

    _run_case(tmp_path, scenario)


@pytest.mark.parametrize("fault", [
    "stale", "foreign-session", "missing-request", "post-model-owner-change",
])
def test_post_model_fresh_probe_or_owner_stale_holds(tmp_path, fault):
    async def scenario(f, lane, server):
        pre, handoff, l0, receipt = await _run_original(f, lane, mode="moved")
        a = f.owners[f.names[0]]
        frame = prepare_stage27f_outcome_evaluation(
            pre, handoff, l0, receipt, owner=a,
            physical=f.physical, world_epoch=pre.world_epoch,
        )
        server.choice_id = "2"
        ticket = submit_stage27g_original_evaluation(
            frame, pre, owner=a, physical=f.physical, lane=lane,
        )
        async def fresh():
            observed = _new_probe(receipt)
            if fault == "stale":
                return receipt.settled_probe
            if fault == "foreign-session":
                return replace(observed, session_id="foreign-session")
            if fault == "missing-request":
                return replace(observed, request_id=None)
            if fault == "post-model-owner-change":
                a.fresh_native_observation_required = True
            return observed
        with pytest.raises(Stage27gEvaluationRefusal):
            await finish_stage27g_original_evaluation(
                frame, pre, owner=a, physical=f.physical,
                lane=lane, ticket=ticket, fresh_probe=fresh,
            )
        assert a.skills[handoff.skill_execution_id].state is SkillState.STARTED

    _run_case(tmp_path, scenario)


def test_original_wal_changed_before_gpu_submission_fails_closed(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, l0, receipt = await _run_original(f, lane, mode="moved")
        a = f.owners[f.names[0]]
        frame = prepare_stage27f_outcome_evaluation(
            pre, handoff, l0, receipt, owner=a,
            physical=f.physical, world_epoch=pre.world_epoch,
        )
        changed = replace(frame, wal_digest="0" * 64)
        before_calls = len(server.calls)
        with pytest.raises(Stage27gEvaluationRefusal, match="source mismatch|terminal WAL"):
            submit_stage27g_original_evaluation(
                changed, pre, owner=a, physical=f.physical, lane=lane,
            )
        assert len(server.calls) == before_calls

    _run_case(tmp_path, scenario)


def test_no_completion_candidate_when_model_selects_unoffered_number(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, l0, receipt = await _run_original(f, lane, mode="blocked")
        a = f.owners[f.names[0]]
        frame = prepare_stage27f_outcome_evaluation(
            pre, handoff, l0, receipt, owner=a,
            physical=f.physical, world_epoch=pre.world_epoch,
        )
        assert "2" not in [x.choice_id for x in frame.request.choices]
        server.choice_id = "2"
        ticket = submit_stage27g_original_evaluation(
            frame, pre, owner=a, physical=f.physical, lane=lane,
        )
        with pytest.raises(Stage27EvaluationRefusal, match="unavailable"):
            await finish_stage27g_original_evaluation(
                frame, pre, owner=a, physical=f.physical, lane=lane, ticket=ticket,
                fresh_probe=lambda: asyncio.sleep(0, result=_new_probe(receipt)),
            )
        assert a.skills[handoff.skill_execution_id].state is SkillState.STARTED

    _run_case(tmp_path, scenario)


def test_stage27g_runner_explicit_only(tmp_path):
    kwargs = dict(
        paper_jar=tmp_path / "paper.jar", paper_sha256="0" * 64,
        plugin_jar=tmp_path / "plugin.jar", plugin_sha256="0" * 64,
        scratch_parent=tmp_path, accepted_eula=True, real_world_dev_grant=True,
        gemma_l1_endpoint="http://127.0.0.1:18081/v1/chat/completions",
        gemma_l1_model="stage26-gemma",
    )
    with patch(
        "experiments.p0d_stage27_real_place_move_dev."
        "run_real_two_self_preset_checkpoint", new_callable=AsyncMock,
    ) as original:
        original.return_value = Path(tmp_path / "out.json")
        result = asyncio.run(run_stage27_real_world(
            **kwargs, stage27g_real_l1_evaluation=True,
        ))
        assert result == tmp_path / "out.json"
        assert original.await_args.kwargs["_stage27_motor_hook"] is (
            stage27g_real_a_motor_hook
        )
        original.reset_mock()
        asyncio.run(run_stage27_real_world(
            **kwargs, stage27f_cpu_evaluation=True,
        ))
        assert original.await_args.kwargs["_stage27_motor_hook"] is not (
            stage27g_real_a_motor_hook
        )


@pytest.mark.parametrize("fault", ["extra-completion", "forged-success-context"])
def test_forged_evaluation_frame_rejected_before_http(tmp_path, fault):
    async def scenario(f, lane, server):
        pre, handoff, l0, receipt = await _run_original(f, lane, mode="blocked")
        a = f.owners[f.names[0]]
        frame = prepare_stage27f_outcome_evaluation(
            pre, handoff, l0, receipt, owner=a,
            physical=f.physical, world_epoch=pre.world_epoch,
        )
        if fault == "extra-completion":
            options = frame.request.choices
            request = replace(frame.request, choices=(
                options[0],
                BoundedChoice("2", "REVIEW_COMPLETION: forged arrival"),
                *options[1:],
            ))
        else:
            datum = frame.request.context[0]
            context = json.loads(datum.value_json)
            context["goal_success_attested"] = True
            request = replace(
                frame.request, context=(replace(
                    datum, value_json=json.dumps(context),
                ),),
            )
        forged = replace(frame, request=request)
        before = len(server.calls)
        with pytest.raises(Stage27gEvaluationRefusal):
            submit_stage27g_original_evaluation(
                forged, pre, owner=a, physical=f.physical, lane=lane,
            )
        assert len(server.calls) == before
        assert a.skills[handoff.skill_execution_id].state is SkillState.STARTED

    _run_case(tmp_path, scenario)


@pytest.mark.parametrize(
    "fault", ["valid", "duplicate", "foreign", "missing", "corrupt"],
)
def test_owned_native_stdout_rechecks_post_gemma_probe(tmp_path, fault):
    native = tmp_path / "owned-original-A-native.jsonl"
    event = {
        "type": "observation", "kind": "probe",
        "session_id": "native-A-1", "seq": 56, "request_id": "post-model-56",
    }
    if fault == "missing":
        rows = [{**event, "seq": 55, "request_id": "old-55"}]
    elif fault == "foreign":
        rows = [{**event, "session_id": "native-B-1"}]
    else:
        rows = [event]
    if fault == "duplicate":
        rows.append(dict(event))
    native.write_bytes(
        b"not-json\n" if fault == "corrupt"
        else b"".join((json.dumps(row) + "\n").encode() for row in rows)
    )
    def call():
        return _native_post_model_probe_readback(
            native, session_id="native-A-1",
            probe_id="post-model-56", probe_seq=56,
            prior_settled_seq=55,
        )
    if fault == "valid":
        receipt = call()
        assert receipt["source_readback"] == "EXACT_ONCE_NATIVE_STDOUT_DEV"
        assert receipt["post_model_probe_seq"] == 56
        assert not receipt["independent_model_vs_native_wallclock_causality"]
    else:
        with pytest.raises(Stage27RealWorldRefusal):
            call()
