"""S25 bounded explicit non-Action WAIT and fresh-observation recheck."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_postfailure_cognition as s24
from relay_self.action import ActionState
from relay_self.explicit_wait import (
    InvalidWaitGate,
    WaitAuthorityScope,
    WaitGateAuthority,
    acknowledge_explicit_wait,
    reevaluate_explicit_wait,
)
from relay_self.postfailure_cognition import PostFailureWorldEvidence
from relay_self.skill import SkillState

ROOT = Path(__file__).resolve().parents[1]


def p(ref: str):
    return s24.s23.p(f"s25:{ref}")


def _prepared(clearance=180):
    data, failed, inputs, context = s24._prepared(clearance_cm=clearance)
    trace = s24._run(context)
    authorize_wait = WaitGateAuthority(
        authority_id="s25-acknowledge-authority",
        scope=WaitAuthorityScope.ACKNOWLEDGE,
        intent_id="escape-threat",
        evidence_id=context["evidence"].evidence_id,
        granted=True,
        provenance=p("explicit-acknowledge"),
    )
    args = {
        "trace": trace,
        "supervisor": data["supervisor"],
        "action3": context["action3"],
        "consequence3": context["consequence3"],
        "recovery_skill": context["recovery_skill"],
        "intent": context["intent"],
        "retained_snapshot": context["owner_snapshot"],
        "authority": authorize_wait,
    }
    return data, failed, inputs, context, args


def _ack(args, **changes):
    return acknowledge_explicit_wait(
        **{**args, **changes},
        at_ns=71, expires_at_ns=110,
        provenance=p("explicit-wait-ack"),
    )


def _new_observation(args, clearance=20, observed_at=80):
    old = args["trace"].world_evidence
    return PostFailureWorldEvidence(
        evidence_id=f"s25-fresh-clearance-{clearance}-{observed_at}",
        action_id=old.action_id,
        binding_id=old.binding_id,
        session_id=old.session_id,
        consequence_provenance=old.consequence_provenance,
        threat_clearance_cm=clearance,
        observed_at_ns=observed_at,
        provenance=p(f"independent-post-wait-world-{clearance}-{observed_at}"),
    )


def _recheck_auth(evidence):
    return WaitGateAuthority(
        authority_id="s25-reevaluation-authority",
        scope=WaitAuthorityScope.REEVALUATE,
        intent_id="escape-threat",
        evidence_id=evidence.evidence_id,
        granted=True,
        provenance=p("explicit-new-evidence-reevaluation"),
    )


def _recheck(gate, evidence, authority=None, **changes):
    return reevaluate_explicit_wait(
        gate, evidence, authority if authority is not None else _recheck_auth(evidence),
        at_ns=90, provenance=p("caller-explicit-recheck"),
        **changes,
    )


def test_explicit_wait_has_no_action_issue_and_fresh_evidence_changes_decision():
    data, failed, inputs, context, args = _prepared()
    assert args["trace"].selected_candidate == "WAIT"
    assert args["trace"].admission_status.value == "admitted"
    events_before = data["intent"].events
    actions_before = (
        data["supervisor"].get(data["closed1"].action_id),
        data["supervisor"].get(s24.s23.s20.ACTION2),
        data["supervisor"].get(s24.s23.ACTION3),
    )
    gate = _ack(args)
    assert gate.trace.selected_candidate == "WAIT"
    assert gate.armed_at_ns == 71 and gate.expires_at_ns == 110
    assert data["supervisor"].last_at_ns == 70  # acknowledgement is read-only
    assert data["supervisor"].open_actions == ()

    fresh_world = _new_observation(args, 20)
    recheck = _recheck(gate, fresh_world)
    assert recheck.result.selected_candidate == "MOVE_AWAY"
    assert (recheck.result.wait_score, recheck.result.move_score) == (8, 7)
    assert recheck.result.retained_revision == gate.trace.retained_revision == 1
    assert recheck.result.epoch.cognition_requested is False
    assert recheck.result.stage_ids == gate.trace.stage_ids
    assert fresh_world.provenance in recheck.result.source_provenance
    assert data["supervisor"].last_at_ns == 90
    assert data["supervisor"].open_actions == ()
    assert data["intent"].events == events_before
    assert data["intent"].current_intent.intent_id == "escape-threat"
    assert data["commit"].new_state.value == 4
    assert data["commit"].new_state.revision == 1
    assert failed.state is SkillState.FAILED
    assert inputs["recovery_skill"].state is SkillState.STARTED
    assert inputs["recovery_skill"].is_current_snapshot
    for before in actions_before:
        assert data["supervisor"].get(before.action_id) is before
        assert before.state is ActionState.OUTCOME
    doc = json.loads((ROOT / "docs/postmain-s25-wait-recheck.json").read_text())
    assert doc["initial"]["candidate"] == "WAIT"
    assert doc["recheck"]["candidate"] == recheck.result.selected_candidate
    assert doc["initial"]["threat_clearance_cm"] == 180
    assert doc["recheck"]["threat_clearance_cm"] == 20


def test_new_evidence_may_still_select_wait_without_automatic_repeat():
    data, _failed, _inputs, _context, args = _prepared()
    gate = _ack(args)
    evidence = _new_observation(args, clearance=250)
    update = _recheck(gate, evidence)
    assert update.result.selected_candidate == "WAIT"
    assert update.result.wait_score == 4
    assert data["supervisor"].open_actions == ()
    assert gate.armed_at_ns == 71
    assert update.result.epoch.cognition_requested is False
    # Another WAIT would need another explicit acknowledgement / authority.


def test_no_new_observation_or_explicit_recheck_means_no_transition():
    data, _failed, _inputs, _context, args = _prepared()
    gate = _ack(args)
    assert data["supervisor"].last_at_ns == 70
    assert data["supervisor"].advance(at_ns=75, provenance=p("caller-services-only-supervision")) == ()
    assert data["supervisor"].last_at_ns == 75
    assert data["supervisor"].open_actions == ()
    assert gate.trace.selected_candidate == "WAIT"
    with pytest.raises(InvalidWaitGate):
        _recheck(gate, args["trace"].world_evidence)
    assert data["supervisor"].last_at_ns == 75


def test_move_away_trace_cannot_be_acknowledged_as_wait():
    _data, _failed, _inputs, _context, args = _prepared(20)
    assert args["trace"].selected_candidate == "MOVE_AWAY"
    with pytest.raises(InvalidWaitGate):
        _ack(args)


@pytest.mark.parametrize("mutated", [
    "wrong_intent", "wrong_evidence", "wrong_scope", "denied", "missing",
    "wrong_choice", "bad_score", "bad_stage", "bad_revision", "early", "expired",
])
def test_wait_acknowledgement_fails_closed(mutated):
    data, _failed, _inputs, _context, args = _prepared()
    auth = args["authority"]
    if mutated == "wrong_intent":
        args["authority"] = replace(auth, intent_id="other-intent")
    elif mutated == "wrong_evidence":
        args["authority"] = replace(auth, evidence_id="other-evidence")
    elif mutated == "wrong_scope":
        args["authority"] = replace(auth, scope=WaitAuthorityScope.REEVALUATE)
    elif mutated == "denied":
        args["authority"] = replace(auth, granted=False)
    elif mutated == "missing":
        args["authority"] = None
    elif mutated == "wrong_choice":
        args["trace"] = replace(args["trace"], selected_candidate="MOVE_AWAY")
    elif mutated == "bad_score":
        args["trace"] = replace(args["trace"], wait_score=9)
    elif mutated == "bad_stage":
        args["trace"] = replace(args["trace"], stage_ids=())
    elif mutated == "bad_revision":
        args["retained_snapshot"] = data["commit"].previous_state
    before = data["supervisor"].last_at_ns
    with pytest.raises(InvalidWaitGate):
        if mutated == "early":
            acknowledge_explicit_wait(**args, at_ns=64, expires_at_ns=110, provenance=p("early"))
        elif mutated == "expired":
            acknowledge_explicit_wait(**args, at_ns=71, expires_at_ns=71, provenance=p("deadline"))
        else:
            _ack(args)
    assert data["supervisor"].last_at_ns == before
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize("mode", [
    "same_evidence", "same_provenance", "wrong_action", "wrong_binding",
    "wrong_session", "wrong_parent", "before_ack", "beyond_window",
    "future_observation", "expired_reeval", "missing_authority",
    "wrong_scope", "wrong_intent", "wrong_evidence", "denied_authority",
    "reuse_authority_id", "malformed_input",
])
def test_recheck_negative_guards_do_not_call_cognition(mode):
    data, _failed, _inputs, _context, args = _prepared()
    gate = _ack(args)
    evidence = _new_observation(args)
    authority = _recheck_auth(evidence)
    call_time = 90
    if mode == "same_evidence":
        evidence = args["trace"].world_evidence
    elif mode == "same_provenance":
        evidence = replace(evidence, provenance=args["trace"].world_evidence.provenance)
    elif mode == "wrong_action":
        evidence = replace(evidence, action_id="other-action")
    elif mode == "wrong_binding":
        evidence = replace(evidence, binding_id="other-binding")
    elif mode == "wrong_session":
        evidence = replace(evidence, session_id="other-session")
    elif mode == "wrong_parent":
        evidence = replace(evidence, consequence_provenance=p("wrong-world"))
    elif mode == "before_ack":
        evidence = replace(evidence, observed_at_ns=71)
    elif mode == "beyond_window":
        evidence = replace(evidence, observed_at_ns=111)
        call_time = 115
    elif mode == "future_observation":
        evidence = replace(evidence, observed_at_ns=91)
    elif mode == "expired_reeval":
        call_time = 111
    elif mode == "missing_authority":
        authority = None
    elif mode == "wrong_scope":
        authority = replace(authority, scope=WaitAuthorityScope.ACKNOWLEDGE)
    elif mode == "wrong_intent":
        authority = replace(authority, intent_id="other-intent")
    elif mode == "wrong_evidence":
        authority = replace(authority, evidence_id="other-evidence")
    elif mode == "denied_authority":
        authority = replace(authority, granted=False)
    elif mode == "reuse_authority_id":
        authority = replace(authority, authority_id=gate.acknowledgement_authority_id)
    elif mode == "malformed_input":
        evidence = "not typed"
    else:
        raise AssertionError(mode)
    before = data["supervisor"].last_at_ns
    with pytest.raises(InvalidWaitGate):
        reevaluate_explicit_wait(gate, evidence, authority, at_ns=call_time, provenance=p("denied"))
    assert data["supervisor"].last_at_ns == before
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize("drift", ["intent_request", "intent_release", "skill_terminal", "open_action"])
def test_changed_owners_reject_recheck(drift):
    data, failed, inputs, context, args = _prepared()
    gate = _ack(args)
    if drift == "intent_request":
        data["intent"].request_reconsideration(
            failed.intent_id, reason="external reconsideration", at_ns=72, provenance=p("intent-drift"),
        )
    elif drift == "intent_release":
        data["intent"].invalidate(
            failed.intent_id, reason="independent invalidation", at_ns=72,
            provenance=p("intent-release"),
        )
    elif drift == "skill_terminal":
        inputs["recovery_skill"].fail(
            reason="external terminal", at_ns=72, provenance=p("skill-terminal"),
        )
    elif drift == "open_action":
        # A separate unauthorized issuance is never created here; the existing
        # ActionSupervisor exposes no open Action in the bounded S24 subject.
        # Model drift by tampering exact current Action3 ownership via direct
        # existing-owner issue of a distinct authorized Action would require
        # a new admitted Skill; no global state mutation is introduced in S25.
        pytest.skip("requires independent Action4 admitted owner; excluded by S25 scope")
    with pytest.raises(InvalidWaitGate):
        _recheck(gate, _new_observation(args))
    assert data["supervisor"].open_actions == ()


def test_s25_receipt_scope():
    receipt = json.loads((ROOT / "docs/postmain-s25-receipt.json").read_text())
    assert receipt["base_head"] == "103dcaf887c59784baaaee761e5f4086d48e8212"
    assert receipt["classification"] == "EXPLICIT_WAIT_NONACTION_FRESH_EVIDENCE_RECHECK_QUALIFIED"
    assert receipt["automatic_epoch_reentry"] is False
    assert receipt["wait_action_issued"] is False
    assert receipt["global_wait_replay_protection"] is False
    assert receipt["real_minecraft"] == "NOT_RUN"
