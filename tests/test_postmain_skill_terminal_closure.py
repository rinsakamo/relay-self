"""S21 deterministic Skill closure qualification over the frozen S20 action trace."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_second_action_closure as s20
from relay_self.action import ActionState
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.skill import SkillState
from relay_self.skill_terminal_closure import (
    InvalidSkillTerminalAuthority,
    InvalidSkillTerminalEvidence,
    SkillGoalEvidence,
    SkillGoalStatus,
    SkillTerminalAuthority,
    SkillTerminalCriterion,
    SkillTerminalDisposition,
    assess_skill_terminal,
    commit_skill_terminal,
)

ROOT = Path(__file__).resolve().parents[1]


def _prepared(status=SkillGoalStatus.SATISFIED):
    data, _authorized, _issued, _world, outcome, closed2 = s20._two_completed_actions()
    skill = data["skill2"]
    criterion = SkillTerminalCriterion(
        criterion_id="s21-escape-distance",
        skill_id=skill.skill_id,
        goal_ref="escape-distance-observed",
        provenance=s20.p("skill-goal-criterion"),
    )
    evidence = SkillGoalEvidence(
        criterion_id=criterion.criterion_id,
        skill_execution_id=skill.execution_id,
        intent_id=skill.intent_id,
        action_id=closed2.action_id,
        binding_id=outcome.binding_id,
        session_id=outcome.session_id,
        goal_ref=criterion.goal_ref,
        status=status,
        observed_at_ns=41,
        provenance=s20.p("independent-goal-evaluation"),
    )
    authority = SkillTerminalAuthority(
        authority_id="s21-skill-closure-authority",
        skill_execution_id=skill.execution_id,
        criterion_id=criterion.criterion_id,
        granted=True,
        provenance=s20.p("explicit-skill-closure-authority"),
    )
    return data, closed2, outcome, criterion, evidence, authority


def _assess(data, action, outcome, criterion, evidence):
    return assess_skill_terminal(
        data["skill2"], data["supervisor"], action, outcome, criterion, evidence,
    )


def test_second_skill_success_requires_separate_goal_evidence_and_authority():
    data, action, outcome, criterion, evidence, authority = _prepared()
    original = data["skill2"]
    assessment = _assess(data, action, outcome, criterion, evidence)
    assert assessment.disposition is SkillTerminalDisposition.SUCCEEDED
    # The Action terminal did not end the Skill: two different owners.
    assert original.state is SkillState.STARTED
    assert action.state is ActionState.OUTCOME
    closed_skill = commit_skill_terminal(
        assessment, authority, at_ns=42, provenance=s20.p("skill-success-commit"),
    )
    assert closed_skill.state is SkillState.SUCCEEDED
    assert closed_skill.is_terminal and closed_skill.is_current_snapshot
    assert not original.is_current_snapshot
    assert closed_skill.events[-1].reason is not None
    assert criterion.criterion_id in closed_skill.events[-1].reason
    assert authority.authority_id in closed_skill.events[-1].reason
    assert data["supervisor"].get(action.action_id) is action
    assert data["supervisor"].get(data["closed1"].action_id) is data["closed1"]
    assert data["intent"].current_intent.intent_id == original.intent_id
    assert data["commit"].new_state.revision == 1
    assert data["commit"].new_state.value == 4
    assert data["supervisor"].open_actions == ()


def test_independent_negative_goal_evidence_may_explicitly_fail_skill():
    data, action, outcome, criterion, evidence, authority = _prepared(
        SkillGoalStatus.VIOLATED,
    )
    assessment = _assess(data, action, outcome, criterion, evidence)
    assert assessment.disposition is SkillTerminalDisposition.FAILED
    closed = commit_skill_terminal(
        assessment, authority, at_ns=42, provenance=s20.p("skill-failed"),
    )
    assert closed.state is SkillState.FAILED
    assert action.state is ActionState.OUTCOME
    assert data["intent"].current_intent.intent_id == closed.intent_id


def test_action_outcome_alone_never_implies_skill_success():
    data, action, outcome, criterion, evidence, authority = _prepared()
    assert action.state is ActionState.OUTCOME
    assert data["skill2"].state is SkillState.STARTED
    with pytest.raises(InvalidSkillTerminalEvidence):
        _assess(data, action, outcome, criterion, None)
    unknown_evidence = replace(evidence, status=SkillGoalStatus.UNDETERMINED)
    assessment = _assess(data, action, outcome, criterion, unknown_evidence)
    assert assessment.disposition is SkillTerminalDisposition.UNDETERMINED
    with pytest.raises(InvalidSkillTerminalEvidence):
        commit_skill_terminal(
            assessment, authority, at_ns=42, provenance=s20.p("must-not-close"),
        )
    assert data["skill2"].state is SkillState.STARTED


def test_unknown_action_cannot_be_promoted_by_satisfied_goal_evidence():
    data = s20._prepare_second()
    _authorized, issued = s20._issue_second(data)
    unknown = data["supervisor"].mark_unknown(
        issued.action_id, at_ns=40, provenance=s20.p("unknown-action-evidence"),
    )
    skill = data["skill2"]
    criterion = SkillTerminalCriterion(
        "s21-escape-distance", skill.skill_id, "escape-distance-observed",
        s20.p("skill-goal-criterion"),
    )
    evidence = SkillGoalEvidence(
        criterion.criterion_id, skill.execution_id, skill.intent_id,
        unknown.action_id, data["binding_result2"].binding_id, s20.SESSION2,
        criterion.goal_ref, SkillGoalStatus.SATISFIED, 41,
        s20.p("independent-goal-evaluation"),
    )
    interpretation = ActionOutcomeInterpretation(
        action_id=unknown.action_id,
        binding_id=data["binding_result2"].binding_id,
        action_ref=data["binding_result2"].action_ref,
        skill_execution_id=unknown.skill_execution_id,
        intent_id=unknown.intent_id,
        session_id=s20.SESSION2,
        source_status="failed",
        disposition=ActionOutcomeDisposition.UNKNOWN,
        reason_code="adapter_failure_consequence_unknown",
        world_provenance=unknown.events[-1].provenance,
        provenance=s20.p("unknown-interpretation"),
    )
    assessment = _assess(data, unknown, interpretation, criterion, evidence)
    assert assessment.disposition is SkillTerminalDisposition.UNDETERMINED
    assert skill.state is SkillState.STARTED


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("action_id", "wrong-action"),
        ("binding_id", "wrong-binding"),
        ("session_id", "wrong-session"),
        ("criterion_id", "wrong-criterion"),
        ("goal_ref", "wrong-goal"),
        ("intent_id", "wrong-intent"),
        ("skill_execution_id", "wrong-skill"),
        ("observed_at_ns", 39),
    ],
)
def test_mismatched_or_stale_goal_evidence_rejected(field, replacement):
    data, action, outcome, criterion, evidence, _authority = _prepared()
    with pytest.raises(InvalidSkillTerminalEvidence):
        _assess(data, action, outcome, criterion, replace(evidence, **{field: replacement}))
    assert data["skill2"].state is SkillState.STARTED


def test_cross_session_and_wrong_world_provenance_rejected():
    data, action, outcome, criterion, evidence, _authority = _prepared()
    for bad in (
        replace(outcome, session_id="other-session"),
        replace(outcome, binding_id="other-binding"),
        replace(outcome, world_provenance=s20.p("wrong-world-source")),
    ):
        with pytest.raises(InvalidSkillTerminalEvidence):
            _assess(data, action, bad, criterion, evidence)


def test_goal_evidence_must_have_separate_source_from_action_outcome():
    data, action, outcome, criterion, evidence, _authority = _prepared()
    with pytest.raises(InvalidSkillTerminalEvidence):
        _assess(
            data, action, outcome, criterion,
            replace(evidence, provenance=outcome.world_provenance),
        )


def test_missing_denied_and_wrong_scope_authority_never_mutate_skill():
    data, action, outcome, criterion, evidence, authority = _prepared()
    assessment = _assess(data, action, outcome, criterion, evidence)
    for bad in (
        None,
        replace(authority, granted=False),
        replace(authority, criterion_id="other-criterion"),
        replace(authority, skill_execution_id="other-skill"),
    ):
        with pytest.raises(InvalidSkillTerminalAuthority):
            commit_skill_terminal(
                assessment, bad, at_ns=42, provenance=s20.p("must-not-commit"),
            )
        assert data["skill2"].state is SkillState.STARTED
        assert data["skill2"].is_current_snapshot


def test_expired_timestamp_and_replayed_assessment_rejected():
    data, action, outcome, criterion, evidence, authority = _prepared()
    assessment = _assess(data, action, outcome, criterion, evidence)
    with pytest.raises(InvalidSkillTerminalEvidence):
        commit_skill_terminal(
            assessment, authority, at_ns=40, provenance=s20.p("early"),
        )
    closed = commit_skill_terminal(
        assessment, authority, at_ns=42, provenance=s20.p("valid"),
    )
    with pytest.raises(InvalidSkillTerminalEvidence):
        commit_skill_terminal(
            assessment, authority, at_ns=43, provenance=s20.p("replayed"),
        )
    with pytest.raises(InvalidSkillTerminalEvidence):
        _assess(data, action, outcome, criterion, evidence)
    assert closed.state is SkillState.SUCCEEDED
    assert closed.is_current_snapshot


def test_forged_assessment_disposition_is_rechecked_before_commit():
    data, action, outcome, criterion, evidence, authority = _prepared()
    assessment = _assess(data, action, outcome, criterion, evidence)
    with pytest.raises(InvalidSkillTerminalEvidence):
        commit_skill_terminal(
            replace(assessment, disposition=SkillTerminalDisposition.FAILED),
            authority, at_ns=42, provenance=s20.p("forgery"),
        )
    assert data["skill2"].state is SkillState.STARTED


def test_s21_receipt_preserves_no_automatic_success_or_autonomy():
    receipt = json.loads(
        (ROOT / "docs/postmain-s21-receipt.json").read_text(encoding="utf-8"),
    )
    assert receipt["base_head"] == "b8d663527d58124fba6b2d00064750dfe30a8c88"
    assert receipt["classification"] == "EXPLICIT_SECOND_SKILL_TERMINAL_EVIDENCE_GATING_QUALIFIED"
    assert receipt["action_outcome_alone_is_not_skill_success"] is True
    assert receipt["automatic_skill_closure"] is False
    assert receipt["automatic_epoch_three"] is False
    assert receipt["real_minecraft"] == "NOT_RUN"
