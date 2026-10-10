"""Lane A E4: two correlated S29 reads -> S25 WAIT -> S26 -> S15/S16 Action4.

All World adapter frames are deterministic test doubles; 0 real Minecraft,
model or GPU. Original S18-S29 production APIs are exercised unmodified.
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import FrozenInstanceError, replace

import pytest

import test_postmain_correlated_probe as s29
import test_postmain_wait_release_action as s26
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import WorldConsequenceStatus
from experiments import epistemic_e3_s29_integration as e3
from experiments import epistemic_e4_action_closure as e4
from relay_self.action import ActionState, InvalidTransition
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    InvalidActionOutcomeData,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import DuplicateSupervisedAction, UnknownSupervisedAction
from relay_self.correlated_probe import CorrelatedProbeGrant, InvalidCorrelatedProbe
from relay_self.execution_binding import ExecutionBinding
from relay_self.explicit_probe import ExclusiveProbeCursor
from relay_self.explicit_wait import WaitAuthorityScope, WaitGateAuthority
from relay_self.provenance import Provenance
from relay_self.wait_release_action import InvalidWaitReleaseAction, WaitReleaseActionAuthority


def p(name: str) -> Provenance:
    return Provenance("e4-explicit-caller", name)


def setup_parent(price_quarters: int = 1):
    data, failed, inputs, args, kwargs = s29._subject(distance=1.8)
    first = asyncio.run(e3.continue_with_existing_owners(
        arm="CHEAP_EXACT", price_quarters=price_quarters,
        recovery_skill=inputs["recovery_skill"],
        intent=data["intent"], retained=data["commit"].new_state,
        at_ns=70, provenance=p("first-s24-epoch"), **kwargs,
    ))
    return data, failed, inputs, args, kwargs, first


def setup_second(distance: float = 0.2, *, price_quarters: int = 1):
    data, failed, inputs, args, kwargs, first = setup_parent(price_quarters)
    old = kwargs["grant"]
    if first.receipt is not None:
        first_msg = first.receipt.source_receipt.source
    else:
        first_msg = kwargs["adapter"].frames[0]
    origin = first_msg.snapshot.position
    old_entity = first_msg.snapshot.nearby_entities[0]
    new_entity = replace(
        old_entity, distance=distance,
        position=replace(old_entity.position, x=origin.x + distance),
    )
    second_msg = replace(
        first_msg, seq=6, request_id=s29.REQUEST2,
        snapshot=replace(first_msg.snapshot, nearby_entities=(new_entity,)),
    )
    kwargs["adapter"].frames = deque((second_msg,))
    second_grant = CorrelatedProbeGrant(old.authority, s29.REQUEST2)
    second_cursor = ExclusiveProbeCursor(
        session_id=args["consequence"].session_id,
        next_seq=first.receipt.next_cursor_seq if first.receipt is not None else 6,
    )
    ack = WaitGateAuthority(
        authority_id="e4-wait-ack-grant",
        scope=WaitAuthorityScope.ACKNOWLEDGE,
        intent_id=data["intent"].current_intent.intent_id,
        evidence_id=first.source_evidence_id or "unobserved",
        granted=True,
        provenance=p("independent-wait-ack"),
    )
    read_kwargs = dict(
        first=first, supervisor=data["supervisor"],
        action3=args["action"], consequence3=args["consequence"],
        recovery_skill=inputs["recovery_skill"], intent=data["intent"],
        retained=data["commit"].new_state,
        ack_authority=ack, ack_at_ns=71, expires_at_ns=110,
        ack_provenance=p("armed-wait"),
        adapter=kwargs["adapter"], cursor=second_cursor, grant=second_grant,
        observed_at_ns=80, inspected_at_ns=82,
    )
    return data, failed, inputs, args, kwargs, first, read_kwargs


def read_and_reconsider(distance: float = 0.2):
    data, failed, inputs, args, kwargs, first, read_kwargs = setup_second(distance)
    second = asyncio.run(e4.explicitly_read_after_wait(**read_kwargs))
    evidence = second.second_receipt.source_receipt.evidence
    recheck_auth = WaitGateAuthority(
        authority_id="e4-fresh-recheck-authority",
        scope=WaitAuthorityScope.REEVALUATE,
        intent_id=data["intent"].current_intent.intent_id,
        evidence_id=evidence.evidence_id, granted=True,
        provenance=p("separate-recheck-grant"),
    )
    binding = ExecutionBinding(
        binding_id=s26.BINDING4, candidate_ref="MOVE_AWAY",
        required_intent_id=data["intent"].current_intent.intent_id,
        skill_execution_id=inputs["recovery_skill"].execution_id,
        skill_ref=inputs["recovery_skill"].skill_id,
        action_id=s26.ACTION4, action_ref="MOVE_BACKWARD",
        provenance=p("distinct-action4-binding"),
    )
    release_auth = WaitReleaseActionAuthority(
        authority_id="e4-separate-release-grant",
        intent_id=data["intent"].current_intent.intent_id,
        evidence_id=evidence.evidence_id,
        action_id=s26.ACTION4, binding_id=s26.BINDING4,
        skill_execution_id=inputs["recovery_skill"].execution_id,
        granted=True, provenance=p("separate-proposal-grant"),
    )
    recheck_kwargs = dict(
        source=second, recheck_authority=recheck_auth, recheck_at_ns=90,
        recheck_provenance=p("fresh-third-s24-epoch"),
        release_authority=release_auth if distance <= 1.0 else None,
        binding=binding if distance <= 1.0 else None,
        propose_at_ns=95, proposal_provenance=p("proposal-not-authority"),
    )
    return data, failed, inputs, args, kwargs, first, second, recheck_kwargs


def test_e4_frozen_manifest_and_old_authority_is_not_modified():
    assert e4.digest() == e4.MANIFEST_SHA256
    assert e4.VERSION == "AC-A-E4-S29-S25-S26-ACTION-OUTCOME-v1"
    assert e4.MANIFEST["base_e3"] == "2609a92648ca594a9fac3d8c3c4b60a4bf991e8c"
    assert e4.MANIFEST["frozen_upstream_s29"] == "5424669a09a69eb364da559e38b9999fee7b6680"
    altered = dict(e4.MANIFEST)
    altered["world"] = "real"
    assert e4.digest(altered) != e4.MANIFEST_SHA256


def test_two_exact_correlated_source_receipts_reenter_S25_and_propose_distinct_action4():
    data, failed, inputs, args, kwargs, first, second, recheck = read_and_reconsider()
    result = e4.explicitly_reconsider_and_propose(**recheck)
    assert first.selected == "WAIT"
    assert first.receipt.probe_seq == 5
    assert second.second_receipt.probe_seq == 6
    assert second.second_receipt.request_id == s29.REQUEST2
    assert second.second_receipt.acknowledged_request_id == s29.REQUEST2
    assert kwargs["adapter"].sent_ids == [s29.REQUEST1, s29.REQUEST2]
    assert read_source_ids(result) == (s29.REQUEST1, s29.REQUEST2)
    assert second.wait_gate.trace.selected_candidate == "WAIT"
    assert result.selection == "MOVE_AWAY"
    assert result.reevaluation.result.stage_ids == first.epoch.stage_ids
    assert result.reevaluation.result.retained_revision == first.epoch.retained_revision == 1
    assert result.proposal is not None
    assert result.proposal.proposed_action.state is ActionState.PROPOSED
    assert result.proposal.binding_result.action_ref == "MOVE_BACKWARD"
    assert result.proposal.binding_result.action_id == s26.ACTION4
    assert data["supervisor"].open_actions == ()
    assert args["action"].state is ActionState.OUTCOME
    assert failed.is_terminal and inputs["recovery_skill"].is_current_snapshot
    assert data["commit"].new_state.value == 4
    assert data["commit"].new_state.revision == 1
    with pytest.raises(FrozenInstanceError):
        result.proposal = None


def read_source_ids(result):
    return (
        result.source.first.correlated_request_id,
        result.source.second_receipt.request_id,
    )


def _close_action4(data, result):
    proposal = result.proposal
    assert proposal is not None
    with pytest.raises(InvalidTransition):
        data["supervisor"].issue(
            proposal.proposed_action, at_ns=97, deadline_ns=180,
            provenance=p("forbidden-unauthorized-issue"),
        )
    authorized = proposal.proposed_action.authorize(
        at_ns=96, authority="e4-independent-action4-authorization",
        provenance=p("separate-authorization"),
    )
    issued = data["supervisor"].issue(
        authorized, at_ns=97, deadline_ns=180,
        provenance=p("independently-supervised-issue"),
    )
    assert issued.state is ActionState.ISSUED
    consequence = s26._world(issued, proposal.binding_result)
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    interpretation = interpret_world_consequence(
        issued, proposal.binding_result, consequence,
        provenance=p("exact-world-interpretation"),
    )
    closed = record_interpreted_action_outcome(
        data["supervisor"], interpretation, at_ns=105,
    )
    assert closed.state is ActionState.OUTCOME
    assert consequence.action_id == issued.action_id == closed.action_id == s26.ACTION4
    assert consequence.binding_id == s26.BINDING4
    assert consequence.session_id == s26.SESSION4
    assert data["supervisor"].open_actions == ()
    return authorized, issued, consequence, interpretation, closed


def test_full_existing_s15_s16_fourth_action_world_outcome_closure():
    data, failed, inputs, args, _kwargs, _first, _second, recheck = read_and_reconsider()
    next_step = e4.explicitly_reconsider_and_propose(**recheck)
    authorized, issued, consequence, interpretation, closed = _close_action4(data, next_step)
    assert authorized.events[-1].authority == "e4-independent-action4-authorization"
    assert interpretation.reason_code == "observed_execution"
    assert issued.action_id != args["action"].action_id
    assert next_step.proposal.fresh_evidence_id != next_step.proposal.wait_evidence_id
    assert next_step.proposal.reevaluation_authority_id != next_step.proposal.release_authority_id
    for action_id in (
        data["closed1"].action_id, s26.s25.s24.s23.s20.ACTION2,
        s26.s25.s24.s23.ACTION3, s26.ACTION4,
    ):
        assert data["supervisor"].get(action_id).state is ActionState.OUTCOME
    assert data["commit"].new_state.revision == 1
    assert data["commit"].new_state.value == 4
    assert data["intent"].current_intent.intent_id == "escape-threat"
    assert inputs["recovery_skill"].is_current_snapshot
    assert failed.is_terminal
    with pytest.raises(DuplicateSupervisedAction):
        data["supervisor"].issue(
            authorized, at_ns=106, deadline_ns=180, provenance=p("duplicate"),
        )
    with pytest.raises(InvalidTransition):
        record_interpreted_action_outcome(data["supervisor"], interpretation, at_ns=107)
    assert data["supervisor"].advance(at_ns=115, provenance=p("no-automatic-next-epoch")) == ()


def test_still_far_wait_has_second_S24_cognition_but_never_action():
    data, _failed, _inputs, _args, kwargs, first, second, recheck = read_and_reconsider(1.8)
    result = e4.explicitly_reconsider_and_propose(**recheck)
    assert result.selection == "WAIT"
    assert result.proposal is None
    assert result.reevaluation.result.wait_score == 4
    assert result.reevaluation.result.move_score == 7
    assert kwargs["adapter"].sent_ids == [s29.REQUEST1, s29.REQUEST2]
    assert first.receipt.probe_seq == 5 and second.second_receipt.probe_seq == 6
    assert data["supervisor"].open_actions == ()
    with pytest.raises(UnknownSupervisedAction):
        data["supervisor"].get(s26.ACTION4)
    with pytest.raises(e4.E4Rejected, match="non-Action"):
        e4.explicitly_reconsider_and_propose(
            **{**recheck, "release_authority": _fake_release(data, second)}
        )


def _fake_release(data, second):
    return WaitReleaseActionAuthority(
        authority_id="e4-inadmissible-release",
        intent_id=data["intent"].current_intent.intent_id,
        evidence_id=second.second_receipt.source_receipt.evidence.evidence_id,
        action_id=s26.ACTION4, binding_id=s26.BINDING4,
        skill_execution_id=second.wait_gate.recovery_skill.execution_id,
        granted=True, provenance=p("fake-proposal"),
    )


def test_no_first_observation_when_expensive_never_triggers_wait_recheck_or_action():
    data, _failed, _inputs, _args, kwargs, first, read_kwargs = setup_second(price_quarters=4)
    assert first.first == "WAIT" and first.receipt is None
    assert kwargs["adapter"].sent_ids == []
    with pytest.raises(e4.E4Rejected, match="first E3 correlated WAIT"):
        asyncio.run(e4.explicitly_read_after_wait(**read_kwargs))
    assert kwargs["adapter"].sent_ids == []
    assert not read_kwargs["cursor"].consumed
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize("kind", (
    "wrong_response_id", "wrong_session", "wrong_seq", "duplicate_req",
    "denied_ack", "wrong_ack_scope", "wrong_cursor", "expired_read",
))
def test_second_correlated_preflight_or_transport_denial_never_proposes_or_issues(kind):
    data, _failed, _inputs, args, kwargs, first, read_kwargs = setup_second()
    msg = read_kwargs["adapter"].frames[0]
    if kind == "wrong_response_id":
        read_kwargs["adapter"].frames = deque((replace(msg, request_id="alien-id"),))
    elif kind == "wrong_session":
        read_kwargs["adapter"].frames = deque((replace(msg, session_id="alien-session"),))
    elif kind == "wrong_seq":
        read_kwargs["adapter"].frames = deque((replace(msg, seq=5),))
    elif kind == "duplicate_req":
        read_kwargs["grant"] = CorrelatedProbeGrant(
            read_kwargs["grant"].authority, s29.REQUEST1,
        )
    elif kind == "denied_ack":
        read_kwargs["ack_authority"] = replace(
            read_kwargs["ack_authority"], granted=False,
        )
    elif kind == "wrong_ack_scope":
        read_kwargs["ack_authority"] = replace(
            read_kwargs["ack_authority"], scope=WaitAuthorityScope.REEVALUATE,
        )
    elif kind == "wrong_cursor":
        read_kwargs["cursor"] = ExclusiveProbeCursor(
            args["consequence"].session_id, next_seq=7,
        )
    elif kind == "expired_read":
        read_kwargs["observed_at_ns"] = 111
        read_kwargs["inspected_at_ns"] = 113
    with pytest.raises((e4.E4Rejected, InvalidCorrelatedProbe, ValueError)):
        asyncio.run(e4.explicitly_read_after_wait(**read_kwargs))
    assert data["supervisor"].open_actions == ()
    assert args["action"].state is ActionState.OUTCOME
    assert data["commit"].new_state.revision == 1


@pytest.mark.parametrize("kind", (
    "denied_recheck", "wrong_recheck_evidence", "expired_recheck",
    "denied_release", "wrong_release_binding", "wrong_binding_action",
))
def test_separate_recheck_and_release_authority_fail_closed(kind):
    data, _failed, _inputs, _args, _kwargs, _first, second, recheck = read_and_reconsider()
    if kind == "denied_recheck":
        recheck["recheck_authority"] = replace(
            recheck["recheck_authority"], granted=False,
        )
    elif kind == "wrong_recheck_evidence":
        recheck["recheck_authority"] = replace(
            recheck["recheck_authority"], evidence_id="foreign",
        )
    elif kind == "expired_recheck":
        recheck["recheck_at_ns"] = 111
    elif kind == "denied_release":
        recheck["release_authority"] = replace(
            recheck["release_authority"], granted=False,
        )
    elif kind == "wrong_release_binding":
        recheck["release_authority"] = replace(
            recheck["release_authority"], binding_id="alien",
        )
    elif kind == "wrong_binding_action":
        recheck["binding"] = replace(
            recheck["binding"], action_id=s26.s25.s24.s23.ACTION3,
        )
    with pytest.raises((e4.E4Rejected, InvalidWaitReleaseAction, ValueError)):
        e4.explicitly_reconsider_and_propose(**recheck)
    assert data["supervisor"].open_actions == ()
    assert second.second_receipt.request_id == s29.REQUEST2


def test_world_unknown_never_mistaken_for_executed_terminal_outcome():
    data, _failed, _inputs, _args, _kwargs, _first, _second, recheck = read_and_reconsider()
    trace = e4.explicitly_reconsider_and_propose(**recheck)
    authorized = trace.proposal.proposed_action.authorize(
        at_ns=96, authority="e4-explicit-unknown-case",
        provenance=p("authorized"),
    )
    issued = data["supervisor"].issue(
        authorized, at_ns=97, deadline_ns=180, provenance=p("issued"),
    )
    consequence = s26._world(issued, trace.proposal.binding_result)
    unavailable = interpret_world_consequence(
        issued, trace.proposal.binding_result,
        replace(consequence, status=WorldConsequenceStatus.UNDETERMINED),
        provenance=p("undetermined-is-not-success"),
    )
    assert unavailable.disposition is ActionOutcomeDisposition.UNAVAILABLE
    with pytest.raises(InvalidActionOutcomeData, match="cannot close Action"):
        record_interpreted_action_outcome(
            data["supervisor"], unavailable, at_ns=105,
        )
    assert data["supervisor"].get(s26.ACTION4) is issued
    assert issued.state is ActionState.ISSUED
    # A genuinely FAILED/unknown adapter outcome uses the distinct UNKNOWN
    # transition, never a successful Action OUTCOME.
    unknown = interpret_world_consequence(
        issued, trace.proposal.binding_result,
        replace(
            consequence, status=WorldConsequenceStatus.FAILED,
            error="offline-synthetic-transport-failure",
        ),
        provenance=p("failure-is-not-observed-execution"),
    )
    assert unknown.disposition is ActionOutcomeDisposition.UNKNOWN
    closed = record_interpreted_action_outcome(
        data["supervisor"], unknown, at_ns=106,
    )
    assert closed.state is ActionState.UNKNOWN
    assert data["supervisor"].open_actions == ()
