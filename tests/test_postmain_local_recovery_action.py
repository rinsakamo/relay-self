"""S23 bounded deterministic local Skill recovery -> Action3 -> outcome.

Qualified trace is another caller-explicit local Action transaction, not an
autonomously scheduled cognition epoch or a new physical Skill capability.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_second_action_closure as s20
import test_postmain_skill_exit_routing as s22
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from relay_self.action import ActionState, InvalidTransition
from relay_self.action_outcome import record_interpreted_action_outcome
from relay_self.action_supervision import DuplicateSupervisedAction
from relay_self.execution_admission import (
    AdmissionDecisionStatus,
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.execution_binding import ExecutionBinding
from relay_self.provenance import Provenance
from relay_self.recovery_action import (
    InvalidRecoveryActionLineage,
    propose_explicit_recovery_action,
)
from relay_self.route_adjudication import (
    RouteCriterion,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.skill import SkillState
from relay_self.skill_exit_routing import (
    SkillExitRoute,
    assess_skill_exit,
    start_explicit_local_recovery,
)

ROOT = Path(__file__).resolve().parents[1]
ACTION3 = "action-recovery-backward-3"
BINDING3 = "binding-recovery-move-away-3"
SKILL3 = "skill-exec-escape-recovery-3"
SESSION3 = "s23-recovery-session-3"


def p(reference: str) -> Provenance:
    return Provenance(source="s23-local-recovery-test", reference=reference)


class RecoverySession(s20.s19.FakeSession):
    """Independent S15 deterministic double for the third Action session."""

    def __init__(self, messages: tuple[object, ...]):
        super().__init__(messages)
        self.started = replace(self.started, session_id=SESSION3)
        self.sent: list[tuple[str, str]] = []

    async def send_set_control(self, action_id: str, *, control: str, state: bool):
        assert action_id == ACTION3
        assert control == "back" and state is True
        self.sent.append(("set_control", action_id))

    async def send_clear_controls(self, action_id: str):
        assert action_id == f"{ACTION3}-s15-clear"
        self.sent.append(("clear_controls", action_id))


def _prepare_recovery():
    data, failed, exit_criterion, evidence, route_authority = s22._prepared()
    assert failed.state is SkillState.FAILED
    assessment = assess_skill_exit(
        failed, data["intent"], exit_criterion, evidence,
    )
    assert assessment.route is SkillExitRoute.LOCAL_RECOVERY_CANDIDATE
    recovery_skill = start_explicit_local_recovery(
        assessment, route_authority,
        execution_id=SKILL3, at_ns=45,
        provenance=p("caller-new-skill-start"),
    )
    assert recovery_skill.state is SkillState.STARTED
    assert data["intent"].pending_reconsideration is None

    # Explicit, separate S12 projection from caller-supplied existing PLAN,
    # then a new S13 policy and decision. No claim of fresh PRD cognition.
    reroute = adjudicate_routes(
        data["values"]["plan"], None,
        RouteCriterion("s23-explicit-recovery-route", allow_single_source=True),
        provenance=p("recovery-route-adjudication"),
    )
    control = control_candidate_from_route_decision(reroute)
    assert control is not None and control.candidate_ref == "MOVE_AWAY"
    criterion = ExecutionAdmissionCriterion(
        criterion_id="s23-recovery-admission",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=("MOVE_AWAY",),
    )
    admission = admit_control_candidate(
        control, reroute, data["intent"], criterion,
        provenance=p("fresh-recovery-admission"),
    )
    assert admission.status is AdmissionDecisionStatus.ADMITTED
    binding = ExecutionBinding(
        binding_id=BINDING3, candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id=SKILL3, skill_ref="alternate-escape-path",
        action_id=ACTION3, action_ref="MOVE_BACKWARD",
        provenance=p("caller-recovery-binding"),
    )
    inputs = {
        "assessment": assessment, "route_authority": route_authority,
        "recovery_skill": recovery_skill, "previous_action": data["supervisor"].get(s20.ACTION2),
        "supervisor": data["supervisor"],
        "previous_admission": data["values"]["admission"],
        "new_admission": admission, "control": control, "route": reroute,
        "criterion": criterion, "binding": binding,
    }
    return data, failed, inputs


def _propose(inputs, **overrides):
    args = {**inputs, **overrides}
    return propose_explicit_recovery_action(
        **args, at_ns=47, provenance=p("explicit-recovery-Action3-proposal"),
    )


def _issue(data, proposed):
    authorized = proposed.authorize(
        at_ns=48, provenance=p("explicit-Action3-authorization"),
        authority="s23-distinct-Action3-authority",
    )
    issued = data["supervisor"].issue(
        authorized, at_ns=49, deadline_ns=140, provenance=p("Action3-issue"),
    )
    assert issued.state is ActionState.ISSUED
    return authorized, issued


def _world(issued, binding_result):
    command = build_mineflayer_command(issued, binding_result)
    messages = (
        replace(s20.s19.observation(1, 0.0), session_id=SESSION3),
        replace(s20.s19.effect(2, ACTION3, "set_control"), session_id=SESSION3),
        replace(
            s20.s19.effect(3, command.cleanup_action_id, "clear_controls"),
            session_id=SESSION3,
        ),
        replace(s20.s19.observation(4, 0.20), session_id=SESSION3),
    )
    session = RecoverySession(messages)
    result = asyncio.run(
        execute_mineflayer_command(session, command, provenance=p("world3-consequence")),
    )
    assert session.sent == [
        ("set_control", ACTION3), ("clear_controls", command.cleanup_action_id),
    ]
    assert result.status is WorldConsequenceStatus.EXECUTED
    return result


def _completed():
    data, failed, inputs = _prepare_recovery()
    proposed, result, handoff = _propose(inputs)
    authorized, issued = _issue(data, proposed)
    consequence = _world(issued, result)
    interpretation = interpret_world_consequence(
        issued, result, consequence,
        provenance=p("Action3-consequence-interpretation"),
    )
    closed = record_interpreted_action_outcome(
        data["supervisor"], interpretation, at_ns=60,
    )
    return data, failed, inputs, proposed, authorized, issued, result, handoff, consequence, interpretation, closed


def test_explicit_local_recovery_issues_third_action_with_independent_terminal_closure():
    (
        data, failed, inputs, proposed, authorized, issued, result, handoff,
        consequence, interpretation, closed,
    ) = _completed()
    assert failed.state is SkillState.FAILED and failed.is_current_snapshot
    assert inputs["recovery_skill"].state is SkillState.STARTED
    assert inputs["recovery_skill"].is_current_snapshot
    assert proposed.action_id == ACTION3
    assert authorized.events[-1].authority == "s23-distinct-Action3-authority"
    assert issued.events[-1].deadline_ns == 140
    assert closed.state is ActionState.OUTCOME and closed.is_current_snapshot
    assert interpretation.reason_code == "observed_execution"
    assert closed.action_id not in (data["closed1"].action_id, s20.ACTION2)
    assert result.skill_execution_id == inputs["recovery_skill"].execution_id
    assert result.skill_ref == inputs["recovery_skill"].skill_id
    assert consequence.session_id == SESSION3
    assert consequence.session_id not in ("s18-session", s20.SESSION2)
    assert consequence.action_id == closed.action_id == handoff.action_id
    assert result.binding_id == handoff.binding_id == BINDING3
    assert handoff.failed_skill_execution_id == failed.execution_id
    assert handoff.recovery_skill_execution_id == SKILL3
    assert inputs["new_admission"] != inputs["previous_admission"]
    assert inputs["criterion"].criterion_id != inputs["previous_admission"].admission_criterion_id
    for action_id in (data["closed1"].action_id, s20.ACTION2, ACTION3):
        assert data["supervisor"].get(action_id).state is ActionState.OUTCOME
    assert data["supervisor"].open_actions == ()
    assert data["intent"].pending_reconsideration is None
    assert data["intent"].current_intent.intent_id == failed.intent_id
    assert data["commit"].new_state.value == 4
    assert data["commit"].new_state.revision == 1
    assert data["supervisor"].advance(at_ns=70, provenance=p("no-auto-next-epoch")) == ()
    record = json.loads(
        (ROOT / "docs/postmain-s23-recovery-trace.json").read_text(encoding="utf-8"),
    )
    assert record["third"]["action_id"] == ACTION3
    assert record["third"]["skill_execution_id"] == SKILL3
    assert record["third"]["binding_id"] == BINDING3
    assert record["third"]["world_session"] == SESSION3
    assert record["third"]["outcome"] == "OUTCOME"


def test_no_action_without_separate_explicit_proposal_and_authorization():
    data, failed, inputs = _prepare_recovery()
    assert data["supervisor"].open_actions == ()
    assert inputs["recovery_skill"].state is SkillState.STARTED
    assert failed.state is SkillState.FAILED
    proposed, result, _handoff = _propose(inputs)
    assert proposed.state is ActionState.PROPOSED
    assert inputs["recovery_skill"].is_current_snapshot
    assert data["supervisor"].open_actions == ()
    with pytest.raises(InvalidTransition):
        data["supervisor"].issue(
            proposed, at_ns=49, deadline_ns=140,
            provenance=p("issue-without-authorization"),
        )
    assert data["supervisor"].open_actions == ()
    assert result.action_id == ACTION3


@pytest.mark.parametrize(
    "field,corrupt",
    [
        ("recovery_skill", "wrong-skill-state"),
        ("route_authority", "missing-authority"),
        ("binding", "bad-action-id"),
        ("binding", "wrong-skill-id"),
        ("binding", "wrong-skill-ref"),
        ("binding", "wrong-intent"),
        ("new_admission", "same-admission"),
        ("new_admission", "reused-admission-criterion"),
        ("new_admission", "rejected-admission"),
        ("previous_action", "wrong-supervisor-lineage"),
        ("assessment", "forged-assessment"),
    ],
)
def test_recovery_handoff_rejects_mismatched_authority_or_lineage(field, corrupt):
    data, _failed, inputs = _prepare_recovery()
    b = inputs["binding"]
    a = inputs["new_admission"]
    if corrupt == "wrong-skill-state":
        changed = inputs["recovery_skill"].fail(
            reason="externally-terminal", at_ns=46, provenance=p("terminal"),
        )
        assert changed.state is SkillState.FAILED
        value = inputs["recovery_skill"]
    elif corrupt == "missing-authority":
        value = replace(inputs[field], granted=False)
    elif corrupt == "bad-action-id":
        value = replace(b, action_id=s20.ACTION2)
    elif corrupt == "wrong-skill-id":
        value = replace(b, skill_execution_id="unrelated-skill-execution")
    elif corrupt == "wrong-skill-ref":
        value = replace(b, skill_ref="unrelated-skill")
    elif corrupt == "wrong-intent":
        value = replace(b, required_intent_id="wrong-intent")
    elif corrupt == "same-admission":
        value = inputs["previous_admission"]
    elif corrupt == "reused-admission-criterion":
        value = replace(a, admission_criterion_id=inputs["previous_admission"].admission_criterion_id)
    elif corrupt == "rejected-admission":
        value = replace(a, status=type(a.status).REJECTED, reason=type(a.reason).CANDIDATE_NOT_ALLOWED)
    elif corrupt == "wrong-supervisor-lineage":
        value = data["closed1"]
    elif corrupt == "forged-assessment":
        value = replace(inputs["assessment"], route=SkillExitRoute.RECONSIDERATION_CANDIDATE)
    else:
        raise AssertionError(corrupt)
    with pytest.raises(InvalidRecoveryActionLineage):
        _propose(inputs, **{field: value})
    assert data["supervisor"].open_actions == ()
    assert data["intent"].pending_reconsideration is None


def test_recompute_s13_rejects_wrong_candidate_without_skill_or_action_mutation():
    data, _failed, inputs = _prepare_recovery()
    other_binding = replace(inputs["binding"], candidate_ref="WAIT")
    with pytest.raises(ValueError):
        _propose(inputs, binding=other_binding)
    assert data["supervisor"].open_actions == ()
    assert inputs["recovery_skill"].state is SkillState.STARTED


def test_reconsideration_or_intent_release_invalidates_recovery_action_handoff():
    for change in ("request", "release"):
        data, failed, inputs = _prepare_recovery()
        if change == "request":
            data["intent"].request_reconsideration(
                failed.intent_id, reason="material world change",
                at_ns=46, provenance=p("independent-intent-drift"),
            )
        else:
            data["intent"].invalidate(
                failed.intent_id, reason="objective no longer valid",
                at_ns=46, provenance=p("independent-intent-release"),
            )
        with pytest.raises(InvalidRecoveryActionLineage):
            _propose(inputs)
        assert data["supervisor"].open_actions == ()


def test_duplicate_issue_and_terminal_replay_fail_without_mutating_first_two_actions():
    data, failed, inputs, proposed, authorized, issued, result, _handoff, _consequence, interpretation, closed = _completed()
    with pytest.raises(DuplicateSupervisedAction):
        data["supervisor"].issue(
            authorized, at_ns=65, deadline_ns=160, provenance=p("reissue"),
        )
    with pytest.raises(InvalidTransition):
        record_interpreted_action_outcome(data["supervisor"], interpretation, at_ns=66)
    assert data["supervisor"].get(ACTION3) is closed
    assert data["supervisor"].get(s20.ACTION2).state is ActionState.OUTCOME
    assert failed.state is SkillState.FAILED


def test_cross_session_world_evidence_is_rejected():
    data, _failed, inputs = _prepare_recovery()
    proposed, result, _handoff = _propose(inputs)
    _authorized, issued = _issue(data, proposed)
    consequence = _world(issued, result)
    with pytest.raises(ValueError):
        interpret_world_consequence(
            issued, result,
            replace(consequence, session_id=s20.SESSION2),
            provenance=p("wrong-session"),
        )
    assert data["supervisor"].get(ACTION3) is issued


def test_s23_receipt_freezes_bounded_nonclaims():
    receipt = json.loads(
        (ROOT / "docs/postmain-s23-receipt.json").read_text(encoding="utf-8"),
    )
    assert receipt["base_head"] == "7b815217db5be4402a88090d04a22e61f5ea05c7"
    assert receipt["classification"] == "EXPLICIT_LOCAL_RECOVERY_ACTION_OUTCOME_CLOSURE_QUALIFIED"
    assert receipt["autonomous_epoch_reentry"] is False
    assert receipt["fresh_cognition_for_recovery"] is False
    assert receipt["distinct_primitive_action_kind"] is False
    assert receipt["global_skill_replay_protection"] is False
    assert receipt["live_minecraft"] == "NOT_RUN"
