"""Stage27f: original one-Action review is read-only, never Goal/Skill success."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from experiments.p0d_stage27_real_place_move_dev import (
    run_stage27_real_world,
    stage27f_real_a_motor_hook,
)
from relay_self.p0d_stage27f_l1_evaluation_dev import (
    Stage27EvaluationRefusal,
    prepare_stage27f_outcome_evaluation,
    resolve_stage27f_evaluation_choice,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.relay_engine import ProviderDecision
from relay_self.skill import SkillState
from relay_self.target_contract import TargetConditionStatus
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27c_place_move_wal_issuer_dev import (
    ScriptedPlaceNative,
    _args,
    selected_original,
)


async def _run_original(f, lane, *, mode):
    prepared, handoff, plan, l0, previous, current = await selected_original(f, lane)
    native = ScriptedPlaceNative(
        l0.native_session_id, blocked=mode == "blocked",
        overshoot=mode == "overshoot",
    )
    native.seq = current.seq
    native.tick = 1213
    native.gate = lambda session, effect, action: f.physical.require_native_effect(
        self_id=f.names[0], native_session_id=session,
        effect=effect, action_id=action,
    )
    kwargs = _args(f, prepared, handoff, plan, l0, previous, current)
    receipt = await f.physical.issue_place_move(native, **kwargs)
    return prepared, handoff, l0, receipt


def _world_fixture(tmp_path, case):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(
        tmp_path, 2, cognitive_work=True, allow_resident_move=True,
    )
    lane = _attach_and_audit(f, endpoint, tmp_path)
    try:
        return asyncio.run(case(f, lane))
    finally:
        f.stop_paper()
        http.stop()


@pytest.mark.parametrize(
    ("mode", "expected_status", "completion_offered"),
    [
        ("moved", TargetConditionStatus.CONDITION_OBSERVED, True),
        ("blocked", TargetConditionStatus.OUTSIDE, False),
        ("overshoot", TargetConditionStatus.OUTSIDE, False),
    ],
)
def test_original_outcome_target_assessment_and_l1_choices(
    tmp_path, mode, expected_status, completion_offered,
):
    async def scenario(f, lane):
        prepared, handoff, l0, receipt = await _run_original(f, lane, mode=mode)
        owner = f.owners[f.names[0]]
        peer = f.owners[f.names[1]]
        b_before = (
            tuple(peer.intent.events), tuple(peer.skills),
            PhysicalActionJournal.restore(
                peer.files.physical_wal_file, self_id=peer.self_id,
            ).digest,
        )
        intent_before = tuple(owner.intent.events)
        skills_before = dict(owner.skills)
        frame = prepare_stage27f_outcome_evaluation(
            prepared, handoff, l0, receipt, owner=owner,
            physical=f.physical, world_epoch=prepared.world_epoch,
        )
        assert frame.target_assessment.status is expected_status
        assert frame.completion_review_offered is completion_offered
        assert frame.target_assessment.goal_succeeded is False
        assert not frame.goal_succeeded
        assert not frame.skill_succeeded
        assert not frame.issued_physical_action
        assert not frame.owner_mutated
        assert owner.skills[handoff.skill_execution_id].state is SkillState.STARTED
        ids = {c.choice_id for c in frame.request.choices}
        assert ("2" in ids) is completion_offered
        if mode == "overshoot":
            assert ids == {"3", "4"}
        else:
            assert {"1", "3", "4"} <= ids
        assert tuple(owner.intent.events) == intent_before
        assert owner.skills == skills_before
        assert (
            tuple(peer.intent.events), tuple(peer.skills),
            PhysicalActionJournal.restore(
                peer.files.physical_wal_file, self_id=peer.self_id,
            ).digest,
        ) == b_before
        # A bounded decision is a mere recommendation, no mutation.
        result = resolve_stage27f_evaluation_choice(
            frame, ProviderDecision.resolved("2" if completion_offered else "3"),
        )
        assert result.recommendation == (
            "REVIEW_COMPLETION" if completion_offered else "ESCALATE_L2"
        )
        assert not result.model_source_attested
        assert not result.owner_mutated
        assert owner.skills == skills_before
        assert owner.intent.events == intent_before
        return frame

    frame = _world_fixture(tmp_path, scenario)
    if mode == "moved":
        ctx = frame.request.context[0].value_json
        assert '"target_condition_observed":true' in ctx
        assert '"goal_success_attested":false' in ctx
        assert '"skill_success_attested":false' in ctx


def test_nonoffered_or_unknown_l1_choice_cannot_complete_original_skill(tmp_path):
    async def scenario(f, lane):
        prepared, handoff, l0, receipt = await _run_original(
            f, lane, mode="blocked",
        )
        frame = prepare_stage27f_outcome_evaluation(
            prepared, handoff, l0, receipt,
            owner=f.owners[f.names[0]], physical=f.physical,
            world_epoch=prepared.world_epoch,
        )
        with pytest.raises(Stage27EvaluationRefusal, match="unavailable"):
            resolve_stage27f_evaluation_choice(frame, ProviderDecision.resolved("2"))
        unknown = resolve_stage27f_evaluation_choice(
            frame, ProviderDecision.unresolved(reason="unqualified choice"),
        )
        assert unknown.recommendation == "RECONSIDER_UNRESOLVED"
        assert not unknown.resolved
        assert not unknown.skill_succeeded
        assert not unknown.owner_mutated

    _world_fixture(tmp_path, scenario)


@pytest.mark.parametrize("fault", [
    "wrong-wal-digest", "wrong-native", "wrong-preset", "wrong-action",
    "foreign-world", "wrong-l0", "wrong-owner-epoch",
])
def test_source_or_original_lifecycle_mismatch_rejected(tmp_path, fault):
    async def scenario(f, lane):
        prepared, handoff, l0, receipt = await _run_original(f, lane, mode="moved")
        owner = f.owners[f.names[0]]
        if fault == "wrong-wal-digest":
            receipt = replace(receipt, journal_sha256="0" * 64)
        elif fault == "wrong-native":
            receipt = replace(receipt, native_session_id="native-foreign")
        elif fault == "wrong-preset":
            receipt = replace(receipt, original_preset_ref="preset-wrong")
        elif fault == "wrong-action":
            receipt = replace(receipt, action_id="action-wrong")
        elif fault == "foreign-world":
            prepared = replace(prepared, world_epoch=prepared.world_epoch + 1)
        elif fault == "wrong-l0":
            receipt = replace(receipt, l0_step_status="NOT_EXECUTED")
        elif fault == "wrong-owner-epoch":
            owner.fresh_native_observation_required = True
        before = tuple(owner.intent.events)
        with pytest.raises(Stage27EvaluationRefusal):
            prepare_stage27f_outcome_evaluation(
                prepared, handoff, l0, receipt, owner=owner,
                physical=f.physical, world_epoch=handoff.world_epoch,
            )
        assert owner.intent.events == before

    _world_fixture(tmp_path, scenario)


def test_stage27f_explicit_runner_hook_without_changing_stage27e_default(tmp_path):
    args = dict(
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
        original.return_value = Path(tmp_path / "report.json")
        got = asyncio.run(run_stage27_real_world(
            **args, stage27f_cpu_evaluation=True,
        ))
        assert got == tmp_path / "report.json"
        assert original.await_args.kwargs["_stage27_motor_hook"] is (
            stage27f_real_a_motor_hook
        )
        original.reset_mock()
        asyncio.run(run_stage27_real_world(**args))
        assert original.await_args.kwargs["_stage27_motor_hook"] is not (
            stage27f_real_a_motor_hook
        )
