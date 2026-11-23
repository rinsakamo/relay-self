"""#843 Skill evidence versus Goal satisfaction, no real native or GPU."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from experiments import run_cognitive_minimal_world as cli
from experiments.cognitive_semantic_outcome_dev import GoalEvidence, SkillEvidence
from test_cognitive_minimal_world_cli import (
    FakeAttackProcessSession,
    FakePhysicalProcessSession,
    _attack_args,
    _attack_observation,
    _inject_physical_transport,
    _physical_args,
)


class SemanticEatSession(FakePhysicalProcessSession):
    async def send_observe(self, request_id=None):
        await super().send_observe(request_id)
        if self.observation_no > 4 and self.messages:
            if self.fail_at == "stale_eval":
                return
            self.messages[-1] = replace(self.messages[-1], seq=8)


class SemanticAttackSession(FakeAttackProcessSession):
    async def send_observe(self, request_id=None):
        await super().send_observe(request_id)
        if self.observation_no > 4 and self.messages:
            if self.fail_at == "stale_eval":
                return
            if self.fail_at == "gone_after_attack":
                self.messages[-1] = replace(
                    _attack_observation(8, kind="probe", target_id=None),
                    request_id=request_id,
                )
            else:
                self.messages[-1] = replace(self.messages[-1], seq=8)


def run_eat(monkeypatch, tmp_path, *, apply=False, threshold=10, fail_at=None):
    session = SemanticEatSession(fail_at=fail_at)
    args = _physical_args(tmp_path)
    args.l0_skill_ir_dev = True
    args.semantic_eval_dev = True
    args.semantic_apply_dev = apply
    args.hunger_threshold = threshold
    session.wal_path = Path(args.physical_journal_path)
    _inject_physical_transport(monkeypatch, session)
    result = asyncio.run(cli.run(args))
    return result, session


def run_attack(monkeypatch, tmp_path, *, apply=False, fail_at=None):
    session = SemanticAttackSession(fail_at=fail_at)
    args = _attack_args(tmp_path)
    args.semantic_eval_dev = True
    args.semantic_apply_dev = apply
    session.wal_path = Path(args.physical_journal_path)
    _inject_physical_transport(monkeypatch, session)
    result = asyncio.run(cli.run(args))
    return result, session


def test_eat_assessment_readonly_does_not_mutate_skill_or_intent(
    monkeypatch, tmp_path,
):
    result, session = run_eat(monkeypatch, tmp_path)
    verdict = result["semantic_assessment"]
    assert result["status"] == "NATIVE_EAT_OUTCOME_DEV_ONLY"
    assert verdict["skill_evidence"] == SkillEvidence.SUPPORTED
    assert verdict["goal_evidence"] == GoalEvidence.SATISFIED
    assert verdict["goal_reason"] == "HUNGER_PREDICATE_NO_LONGER_TRIGGERED"
    assert result["skill_final_state"] == "started"
    assert result["intent_final_state"] == "committed"
    assert result["semantic_application"] is None
    assert result["semantic_evaluation_memory_published"] is False
    assert result["semantic_evaluation_probe"]["observation"]["seq"] == 8
    assert result["physical_journal_unresolved"] is False
    assert len([s for s in session.sent if s[0] == "consume_held"]) == 1


def test_eat_verified_goal_completion_transitions_existing_owners(
    monkeypatch, tmp_path,
):
    result, session = run_eat(monkeypatch, tmp_path, apply=True)
    assert result["semantic_application"]["skill_transition_applied"] is True
    assert result["semantic_application"]["intent_transition_applied"] is True
    assert result["skill_final_state"] == "succeeded"
    assert result["intent_final_state"] == "completed"
    assert result["action_outcome_count"] == 1
    assert len([s for s in session.sent if s[0] == "consume_held"]) == 1
    assert result["physical_journal_records"][-1]["status"] == "NATIVE_EAT_OUTCOME"


def test_eat_skill_succeeds_but_hunger_goal_remains(
    monkeypatch, tmp_path,
):
    result, _ = run_eat(monkeypatch, tmp_path, apply=True, threshold=17)
    assert result["semantic_assessment"]["skill_evidence"] == SkillEvidence.SUPPORTED
    assert result["semantic_assessment"]["goal_evidence"] == GoalEvidence.ACTIVE
    assert result["skill_final_state"] == "succeeded"
    assert result["intent_final_state"] == "committed"
    assert result["semantic_application"]["intent_transition_applied"] is False


def test_attack_hit_skill_can_succeed_without_self_defense_goal(
    monkeypatch, tmp_path,
):
    result, session = run_attack(monkeypatch, tmp_path, apply=True)
    verdict = result["semantic_assessment"]
    assert result["status"] == "NATIVE_ATTACK_HURT_OBSERVED_DEV_ONLY"
    assert verdict["skill_evidence"] == SkillEvidence.SUPPORTED
    assert verdict["goal_evidence"] == GoalEvidence.ACTIVE
    assert verdict["goal_reason"] == "ZOMBIE_THREAT_STILL_OBSERVED"
    assert result["skill_final_state"] == "succeeded"
    assert result["intent_final_state"] == "committed"
    assert result["semantic_application"]["intent_transition_applied"] is False
    assert verdict["independent_paper_damage_attested"] is False
    assert result["physical_journal_records"][-1]["status"] == "NATIVE_ATTACK_HURT_OBSERVED"
    assert len([s for s in session.sent if s[0] == "attack_entity"]) == 1


def test_attack_disappearing_zombie_is_unknown_not_safety_certificate(
    monkeypatch, tmp_path,
):
    result, _ = run_attack(
        monkeypatch, tmp_path, apply=True, fail_at="gone_after_attack",
    )
    assert result["semantic_assessment"]["goal_evidence"] == GoalEvidence.UNKNOWN
    assert result["skill_final_state"] == "succeeded"
    assert result["intent_final_state"] == "committed"
    assert result["semantic_application"]["intent_transition_applied"] is False


@pytest.mark.parametrize("kind", ["eat", "attack"])
def test_stale_evaluation_probe_never_relabels_physical_outcome(
    monkeypatch, tmp_path, kind,
):
    if kind == "eat":
        result, session = run_eat(
            monkeypatch, tmp_path, apply=True, fail_at="stale_eval",
        )
    else:
        result, session = run_attack(
            monkeypatch, tmp_path, apply=True, fail_at="stale_eval",
        )
    assert result["semantic_assessment"] is None
    assert result["semantic_application"] is None
    assert result["semantic_evaluation_error"] is not None
    assert result["skill_final_state"] == "started"
    assert result["intent_final_state"] == "committed"
    assert result["physical_journal_unresolved"] is False
    assert result["action_outcome_count"] == 1
    assert len([s for s in session.sent if s[0] in {
        "attack_entity", "consume_held",
    }]) == 1


@pytest.mark.parametrize("incorrect", [
    "without_eval", "without_l0", "without_physical",
])
def test_semantic_mode_is_explicit_before_world_launch(
    monkeypatch, tmp_path, incorrect,
):
    async def forbidden(*args, **kwargs):
        raise AssertionError("World launch is forbidden")
    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", forbidden)
    args = _attack_args(tmp_path)
    args.semantic_apply_dev = True
    args.semantic_eval_dev = True
    if incorrect == "without_eval":
        args.semantic_eval_dev = False
    elif incorrect == "without_l0":
        args.l0_skill_ir_dev = False
    else:
        args.physical_attack_dev = False
    with pytest.raises(cli.MinimalCognitionError):
        asyncio.run(cli.run(args))
    assert not Path(args.physical_journal_path).exists()
