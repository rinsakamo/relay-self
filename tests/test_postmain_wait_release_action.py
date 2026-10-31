"""S26: deterministic WAIT -> fresh World recheck -> Action4 outcome closure."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_explicit_wait as s25
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from relay_self.action import ActionState, InvalidTransition
from relay_self.action_outcome import record_interpreted_action_outcome
from relay_self.action_supervision import DuplicateSupervisedAction
from relay_self.execution_binding import ExecutionBinding
from relay_self.explicit_wait import WaitAuthorityScope
from relay_self.provenance import Provenance
from relay_self.skill import SkillState
from relay_self.wait_release_action import (
    InvalidWaitReleaseAction,
    WaitReleaseActionAuthority,
    propose_explicit_wait_release_action,
)

ROOT = Path(__file__).resolve().parents[1]
ACTION4 = "action-wait-release-backward-4"
BINDING4 = "binding-wait-release-4"
SESSION4 = "s26-wait-release-session-4"


def p(ref: str) -> Provenance:
    return Provenance("s26-wait-release-test", ref)


class WaitReleaseSession(s25.s24.s23.s20.s19.FakeSession):
    """Deterministic fourth Mineflayer session; no live endpoint."""

    def __init__(self, messages):
        super().__init__(messages)
        self.started = replace(self.started, session_id=SESSION4)
        self.sent: list[tuple[str, str]] = []

    async def send_set_control(self, action_id: str, *, control: str, state: bool):
        assert action_id == ACTION4 and control == "back" and state is True
        self.sent.append(("set_control", action_id))

    async def send_clear_controls(self, action_id: str):
        assert action_id == f"{ACTION4}-s15-clear"
        self.sent.append(("clear_controls", action_id))


def _prepared(*, new_clearance=20):
    data, failed, inputs, _s24_context, args = s25._prepared()
    gate = s25._ack(args)
    new_evidence = s25._new_observation(args, clearance=new_clearance)
    recheck_auth = s25._recheck_auth(new_evidence)
    reevaluation = s25._recheck(gate, new_evidence, recheck_auth)
    skill = inputs["recovery_skill"]
    binding = ExecutionBinding(
        binding_id=BINDING4,
        candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id=skill.execution_id,
        skill_ref=skill.skill_id,
        action_id=ACTION4,
        action_ref="MOVE_BACKWARD",
        provenance=p("independent-S14-Action4-mapping"),
    )
    release_auth = WaitReleaseActionAuthority(
        authority_id="s26-release-proposal-authority",
        intent_id=skill.intent_id,
        evidence_id=new_evidence.evidence_id,
        action_id=ACTION4,
        binding_id=BINDING4,
        skill_execution_id=skill.execution_id,
        granted=True,
        provenance=p("explicit-caller-proposal-grant"),
    )
    kwargs = {
        "reevaluation": reevaluation,
        "reevaluation_authority": recheck_auth,
        "release_authority": release_auth,
        "binding": binding,
    }
    return data, failed, inputs, gate, kwargs


def _propose(kwargs, **overrides):
    return propose_explicit_wait_release_action(
        **{**kwargs, **overrides}, at_ns=95,
        provenance=p("explicit-new-S26-Action4-proposal"),
    )


def _issue(data, trace):
    proposed = trace.proposed_action
    authorized = proposed.authorize(
        at_ns=96,
        provenance=p("independent-Action4-authorization"),
        authority="s26-independent-Action4-issue-authority",
    )
    issued = data["supervisor"].issue(
        authorized, at_ns=97, deadline_ns=180,
        provenance=p("supervised-distinct-Action4-ISSUE"),
    )
    return authorized, issued


def _world(issued, bound):
    command = build_mineflayer_command(issued, bound)
    messages = (
        replace(s25.s24.s23.s20.s19.observation(1, 0.0), session_id=SESSION4),
        replace(s25.s24.s23.s20.s19.effect(2, ACTION4, "set_control"), session_id=SESSION4),
        replace(
            s25.s24.s23.s20.s19.effect(3, command.cleanup_action_id, "clear_controls"),
            session_id=SESSION4,
        ),
        replace(s25.s24.s23.s20.s19.observation(4, 0.2), session_id=SESSION4),
    )
    session = WaitReleaseSession(messages)
    consequence = asyncio.run(
        execute_mineflayer_command(session, command, provenance=p("WorldConsequence4")),
    )
    assert session.sent == [
        ("set_control", ACTION4),
        ("clear_controls", command.cleanup_action_id),
    ]
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    return consequence


def _completed():
    data, failed, inputs, gate, kwargs = _prepared()
    trace = _propose(kwargs)
    authorized, issued = _issue(data, trace)
    consequence = _world(issued, trace.binding_result)
    interpretation = interpret_world_consequence(
        issued, trace.binding_result, consequence,
        provenance=p("exact-Action4-outcome-interpretation"),
    )
    closed = record_interpreted_action_outcome(
        data["supervisor"], interpretation, at_ns=105,
    )
    return data, failed, inputs, gate, kwargs, trace, authorized, issued, consequence, interpretation, closed


def test_wait_release_new_action_is_separately_authorized_and_outcome_closed():
    data, failed, inputs, gate, kwargs, trace, authorized, issued, consequence, interpretation, closed = _completed()
    assert gate.trace.selected_candidate == "WAIT"
    assert kwargs["reevaluation"].result.selected_candidate == "MOVE_AWAY"
    assert trace.selected_candidate == "MOVE_AWAY"
    assert trace.proposed_action.state is ActionState.PROPOSED
    assert trace.binding_result.action_state is ActionState.PROPOSED
    assert trace.binding_result.skill_execution_id == inputs["recovery_skill"].execution_id
    assert trace.binding_result.action_ref == "MOVE_BACKWARD"
    assert trace.fresh_evidence_id == kwargs["reevaluation"].new_evidence.evidence_id
    assert trace.wait_evidence_id != trace.fresh_evidence_id
    assert trace.release_authority_id != trace.reevaluation_authority_id
    assert trace.admission_criterion_id == "s26-explicit-release-admission"
    assert authorized.events[-1].authority == "s26-independent-Action4-issue-authority"
    assert issued.state is ActionState.ISSUED
    assert closed.state is ActionState.OUTCOME and closed.is_current_snapshot
    assert consequence.action_id == ACTION4 == closed.action_id
    assert consequence.binding_id == BINDING4
    assert consequence.session_id == SESSION4
    assert interpretation.reason_code == "observed_execution"
    for action in (data["closed1"].action_id, s25.s24.s23.s20.ACTION2, s25.s24.s23.ACTION3, ACTION4):
        assert data["supervisor"].get(action).state is ActionState.OUTCOME
    assert data["supervisor"].open_actions == ()
    assert inputs["recovery_skill"].state is SkillState.STARTED
    assert failed.state is SkillState.FAILED
    assert data["intent"].current_intent.intent_id == "escape-threat"
    assert data["intent"].pending_reconsideration is None
    assert data["commit"].new_state.revision == 1
    assert data["commit"].new_state.value == 4
    assert data["supervisor"].advance(at_ns=115, provenance=p("no-auto-epoch")) == ()
    document = json.loads((ROOT / "docs/postmain-s26-wait-release-trace.json").read_text())
    assert document["action4"]["action_id"] == ACTION4
    assert document["action4"]["outcome"] == "OUTCOME"
    assert document["action4"]["world_session"] == SESSION4


def test_proposal_is_not_authorization_or_issuance():
    data, _failed, _inputs, gate, kwargs = _prepared()
    assert gate.trace.selected_candidate == "WAIT"
    assert data["supervisor"].open_actions == ()
    trace = _propose(kwargs)
    assert trace.proposed_action.state is ActionState.PROPOSED
    assert data["supervisor"].open_actions == ()
    assert data["supervisor"].last_at_ns == 90
    with pytest.raises(InvalidTransition):
        data["supervisor"].issue(
            trace.proposed_action, at_ns=97, deadline_ns=180,
            provenance=p("unauthorized-issue"),
        )
    assert data["supervisor"].open_actions == ()


def test_recheck_still_wait_must_not_be_released_into_action():
    data, _failed, _inputs, _gate, kwargs = _prepared(new_clearance=250)
    assert kwargs["reevaluation"].result.selected_candidate == "WAIT"
    with pytest.raises(InvalidWaitReleaseAction):
        _propose(kwargs)
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize(
    "field,mutation",
    [
        ("reevaluation_authority", "missing"),
        ("reevaluation_authority", "denied"),
        ("reevaluation_authority", "wrong_scope"),
        ("reevaluation_authority", "wrong_evidence"),
        ("reevaluation_authority", "wrong_id"),
        ("release_authority", "missing"),
        ("release_authority", "denied"),
        ("release_authority", "wrong_evidence"),
        ("release_authority", "wrong_action"),
        ("release_authority", "wrong_binding"),
        ("release_authority", "wrong_skill"),
        ("release_authority", "reuse_recheck_id"),
        ("binding", "action3_replay"),
        ("binding", "wrong_candidate"),
        ("binding", "wrong_action_ref"),
        ("binding", "wrong_skill"),
        ("binding", "wrong_intent"),
        ("binding", "wrong_binding_id"),
        ("reevaluation", "forged_candidate"),
        ("reevaluation", "forged_score"),
        ("reevaluation", "forged_parent"),
        ("reevaluation", "forged_criterion"),
        ("reevaluation", "forged_source"),
    ],
)
def test_wait_release_identity_and_authority_guards(field, mutation):
    data, _failed, _inputs, _gate, kwargs = _prepared()
    value = kwargs[field]
    ev = kwargs["reevaluation"]
    if mutation == "missing":
        value = None
    elif mutation == "denied":
        value = replace(value, granted=False)
    elif mutation == "wrong_scope":
        value = replace(value, scope=WaitAuthorityScope.ACKNOWLEDGE)
    elif mutation == "wrong_evidence":
        value = replace(value, evidence_id="other-evidence")
    elif mutation == "wrong_id":
        value = replace(value, authority_id="other-id")
    elif mutation == "wrong_action":
        value = replace(value, action_id="wrong-action")
    elif mutation == "wrong_binding":
        value = replace(value, binding_id="wrong-binding")
    elif mutation == "wrong_skill":
        value = replace(value, skill_execution_id="wrong-skill")
    elif mutation == "reuse_recheck_id":
        value = replace(value, authority_id=ev.reevaluation_authority_id)
    elif mutation == "action3_replay":
        value = replace(value, action_id=s25.s24.s23.ACTION3)
    elif mutation == "wrong_candidate":
        value = replace(value, candidate_ref="WAIT")
    elif mutation == "wrong_action_ref":
        value = replace(value, action_ref="WAIT")
    elif mutation == "wrong_intent":
        value = replace(value, required_intent_id="wrong-intent")
    elif mutation == "wrong_binding_id":
        value = replace(value, binding_id="wrong-binding")
    elif mutation == "forged_candidate":
        value = replace(ev, result=replace(ev.result, selected_candidate="WAIT"))
    elif mutation == "forged_score":
        value = replace(ev, result=replace(ev.result, wait_score=100))
    elif mutation == "forged_parent":
        value = replace(ev, new_evidence=replace(ev.new_evidence, session_id="forged-session"))
    elif mutation == "forged_criterion":
        value = replace(ev, result=replace(ev.result, stage_ids=()))
    elif mutation == "forged_source":
        value = replace(ev, result=replace(ev.result, source_provenance=()))
    else:
        raise AssertionError(mutation)
    before = data["supervisor"].last_at_ns
    with pytest.raises(InvalidWaitReleaseAction):
        _propose(kwargs, **{field: value})
    assert data["supervisor"].last_at_ns == before
    assert data["supervisor"].open_actions == ()


def test_stale_intent_or_skill_blocks_wait_release():
    for scenario in ("reconsider", "release", "skill_terminal"):
        data, failed, inputs, _gate, kwargs = _prepared()
        if scenario == "reconsider":
            data["intent"].request_reconsideration(
                failed.intent_id, reason="new challenge", at_ns=92, provenance=p("reconsider"),
            )
        elif scenario == "release":
            data["intent"].invalidate(
                failed.intent_id, reason="new invalidation", at_ns=92, provenance=p("invalidate"),
            )
        else:
            inputs["recovery_skill"].fail(
                reason="separately terminal", at_ns=92, provenance=p("skill-closes"),
            )
        with pytest.raises(InvalidWaitReleaseAction):
            _propose(kwargs)
        assert data["supervisor"].open_actions == ()


def test_early_and_expired_handoff_fail_closed():
    data, _failed, _inputs, _gate, kwargs = _prepared()
    for at_ns in (80, 111):
        with pytest.raises(InvalidWaitReleaseAction):
            propose_explicit_wait_release_action(
                **kwargs, at_ns=at_ns, provenance=p("bad-time"),
            )
    assert data["supervisor"].open_actions == ()


def test_duplicate_issue_and_outcome_replay_preserve_existing_terminals():
    data, _failed, _inputs, _gate, _kwargs, trace, authorized, _issued, _consequence, interpretation, closed = _completed()
    with pytest.raises(DuplicateSupervisedAction):
        data["supervisor"].issue(
            authorized, at_ns=107, deadline_ns=200,
            provenance=p("duplicate-issued-Action4"),
        )
    with pytest.raises(InvalidTransition):
        record_interpreted_action_outcome(
            data["supervisor"], interpretation, at_ns=108,
        )
    assert data["supervisor"].get(ACTION4) is closed
    assert data["supervisor"].open_actions == ()
    assert trace.proposed_action.state is ActionState.PROPOSED


def test_mismatched_world_session_rejected_for_action4():
    data, _failed, _inputs, _gate, kwargs = _prepared()
    trace = _propose(kwargs)
    _authorized, issued = _issue(data, trace)
    consequence = _world(issued, trace.binding_result)
    with pytest.raises(ValueError):
        interpret_world_consequence(
            issued, trace.binding_result,
            replace(consequence, session_id=s25.s24.s23.SESSION3),
            provenance=p("wrong-World-session"),
        )
    assert data["supervisor"].get(ACTION4) is issued


def test_s26_receipt_frozen_limits():
    receipt = json.loads((ROOT / "docs/postmain-s26-receipt.json").read_text())
    assert receipt["base_head"] == "dce5fe3bf33ed2fd450ab5e4ccea076e628ad938"
    assert receipt["classification"] == "EXPLICIT_WAIT_RELEASE_FOURTH_ACTION_OUTCOME_CLOSURE_QUALIFIED"
    assert receipt["automatic_wait_release"] is False
    assert receipt["automatic_action_authorization"] is False
    assert receipt["global_replay_protection"] is False
    assert receipt["live_minecraft"] == "NOT_RUN"
