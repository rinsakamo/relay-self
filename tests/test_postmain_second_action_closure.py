"""S20 deterministic explicit two-transaction qualification.

S19 tests supply the frozen original first Action and the qualified second
cognitive route. S20 continues the SAME caller-owned second invocation from
its fresh admission through S14-S16, without another cognitive epoch.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    InvalidMineflayerExecutionData,
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from relay_self.action import ActionLifecycle, ActionState, InvalidTransition
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    InvalidActionOutcomeData,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import DuplicateSupervisedAction
from relay_self.execution_admission import (
    AdmissionDecisionStatus,
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
)
from relay_self.execution_binding import (
    ExecutionBinding,
    InvalidExecutionBindingData,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.provenance import Provenance
from relay_self.second_epoch_action import (
    InvalidSecondEpochConsequence,
    InvalidSecondEpochLineage,
    require_fresh_second_consequence,
    validate_second_epoch_lineage,
)
from relay_self.skill import InvalidSkillTransition, SkillState

SESSION2 = "s20-session-2"
ACTION2 = "action-move-backward-2"
BINDING2 = "binding-move-away-2"
SKILL2 = "skill-exec-escape-2"
FIRST_SESSION = "s18-session"
ROOT = Path(__file__).resolve().parents[1]


def p(reference: str) -> Provenance:
    return Provenance(source="s20-two-transaction-qualification", reference=reference)


class SecondSession(s19.FakeSession):
    """S15 adapter protocol test double, independently scoped to Action 2."""

    def __init__(self, messages: tuple[object, ...]):
        super().__init__(messages)
        self.started = replace(self.started, session_id=SESSION2)
        self.sent: list[tuple[str, str]] = []

    async def send_set_control(self, action_id: str, *, control: str, state: bool):
        assert action_id == ACTION2
        assert control == "back" and state is True
        self.sent.append(("set_control", action_id))

    async def send_clear_controls(self, action_id: str):
        assert action_id == f"{ACTION2}-s15-clear"
        self.sent.append(("clear_controls", action_id))


def _prepare_second():
    supervisor, commit, intent, closed1, feedback, first_epoch = s19._epoch_one()
    assert first_epoch.cognition_requested is False
    assert closed1 is supervisor.get(closed1.action_id)
    assert closed1.state is ActionState.OUTCOME
    assert commit.new_state.revision == 1

    values, second_epoch = s19._epoch_two(
        supervisor, intent, commit.new_state, commit.new_state,
        expected_revision=1,
    )
    assert second_epoch.cognition_requested is False
    assert values["plan"].selected is not None
    assert values["plan"].selected.candidate_id == "MOVE_AWAY"
    assert values["admission"].status is AdmissionDecisionStatus.ADMITTED

    binding = ExecutionBinding(
        binding_id=BINDING2,
        candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id=SKILL2,
        skill_ref="escape-movement",
        action_id=ACTION2,
        action_ref="MOVE_BACKWARD",
        provenance=p("caller-action2-binding"),
    )
    lineage = validate_second_epoch_lineage(
        supervisor, closed1, feedback, commit.new_state,
        values["prediction_input"], values["plan"], binding,
        provenance=p("explicit-second-action-lineage"),
    )
    assert lineage.second_action_id == ACTION2
    assert lineage.committed_revision == commit.new_state.revision
    assert lineage.first_feedback_id == commit.record.feedback_id

    # Still no Action 2 proposal, commitment, authorization or issue.
    admission_guard = values["policies"][-2]
    assert admission_guard == ExecutionAdmissionCriterion(
        criterion_id="s19-fresh-admission",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=("WAIT", "MOVE_AWAY"),
    )
    bound = resolve_execution_binding(
        values["admission"], values["control"], values["route"],
        intent, admission_guard, binding,
        provenance=p("explicit-second-binding-resolution"),
    )
    # The Action/Skill owner transition records a reference to governed
    # ancestry; this reference does not authorize or issue the new Action.
    action_provenance = p(
        f"{lineage.first_feedback_id}|rev:{lineage.committed_revision}|"
        f"{lineage.second_binding_id}|{lineage.second_action_id}"
    )
    skill2, proposed2, binding_result2 = start_and_propose_bound_execution(
        bound, intent, at_ns=31, provenance=action_provenance,
    )
    assert proposed2.events[0].provenance == action_provenance
    assert skill2.state is SkillState.STARTED
    assert proposed2.state is ActionState.PROPOSED
    return {
        "supervisor": supervisor, "commit": commit, "intent": intent,
        "closed1": closed1, "feedback": feedback, "values": values,
        "second_epoch": second_epoch, "lineage": lineage, "binding": binding,
        "bound": bound, "skill2": skill2, "proposed2": proposed2,
        "binding_result2": binding_result2,
    }


def _issue_second(data):
    authorized = data["proposed2"].authorize(
        at_ns=32, provenance=p("action2-explicit-authorization"),
        authority="s20-explicit-Action2-authority",
    )
    issued = data["supervisor"].issue(
        authorized, at_ns=33, deadline_ns=100,
        provenance=p("action2-issue"),
    )
    assert issued.state is ActionState.ISSUED
    assert data["supervisor"].get(ACTION2) is issued
    return authorized, issued


def _world_second(data, issued):
    command = build_mineflayer_command(issued, data["binding_result2"])
    messages = (
        replace(s19.observation(1, 0.0), session_id=SESSION2),
        replace(s19.effect(2, ACTION2, "set_control"), session_id=SESSION2),
        replace(
            s19.effect(3, command.cleanup_action_id, "clear_controls"),
            session_id=SESSION2,
        ),
        replace(s19.observation(4, 0.20), session_id=SESSION2),
    )
    session = SecondSession(messages)
    consequence = asyncio.run(
        execute_mineflayer_command(
            session, command, provenance=p("world2-observed-consequence"),
        )
    )
    assert session.sent == [
        ("set_control", ACTION2),
        ("clear_controls", command.cleanup_action_id),
    ]
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    assert consequence.session_id == SESSION2
    assert consequence.movement_distance >= 0.05
    return consequence


def _close_second(data, issued, consequence, *, at_ns=40):
    checked = require_fresh_second_consequence(
        data["supervisor"], issued, data["binding_result2"], consequence,
        expected_session_id=SESSION2, first_session_id=FIRST_SESSION, at_ns=at_ns,
    )
    interpretation = interpret_world_consequence(
        issued, data["binding_result2"], checked,
        provenance=p("second-action-outcome-interpretation"),
    )
    closed = record_interpreted_action_outcome(
        data["supervisor"], interpretation, at_ns=at_ns,
    )
    return interpretation, closed


def _two_completed_actions():
    data = _prepare_second()
    authorized, issued = _issue_second(data)
    consequence = _world_second(data, issued)
    interpretation, closed2 = _close_second(data, issued, consequence)
    return data, authorized, issued, consequence, interpretation, closed2


def test_two_distinct_terminal_action_transactions_with_exact_retained_lineage():
    data, authorized, issued, consequence, interpretation, closed2 = (
        _two_completed_actions()
    )
    first = data["closed1"]
    commit = data["commit"]
    feedback = data["feedback"]
    lineage = data["lineage"]
    supervisor = data["supervisor"]
    assert first.action_id != closed2.action_id
    assert first.skill_execution_id != closed2.skill_execution_id
    assert first.state is ActionState.OUTCOME and first.is_current_snapshot
    assert closed2.state is ActionState.OUTCOME and closed2.is_current_snapshot
    assert supervisor.get(first.action_id) is first
    assert supervisor.get(ACTION2) is closed2
    assert authorized.events[-1].authority == "s20-explicit-Action2-authority"
    assert issued.events[-1].deadline_ns == 100
    assert data["binding_result2"].binding_id == BINDING2
    assert consequence.action_id == ACTION2
    assert consequence.binding_id == BINDING2
    assert consequence.session_id != FIRST_SESSION
    assert interpretation.session_id == SESSION2
    assert interpretation.disposition is ActionOutcomeDisposition.OUTCOME
    assert interpretation.reason_code == "observed_execution"
    assert interpretation.world_provenance == consequence.provenance
    assert feedback.feedback.feedback_id == commit.record.feedback_id
    assert lineage.first_action_id == first.action_id
    assert lineage.first_feedback_id == commit.record.feedback_id
    assert lineage.learning_authority_id == commit.record.authority_id
    assert lineage.committed_revision == commit.new_state.revision == 1
    assert lineage.second_action_id == closed2.action_id
    assert lineage.second_binding_id == BINDING2
    assert commit.record.update_provenance in (
        data["values"]["plan"].selected.source_provenance
    )
    assert data["intent"].current_intent.intent_id == first.intent_id
    assert commit.new_state.last_update is commit.record
    assert supervisor.next_deadline_ns is None
    assert supervisor.open_actions == ()
    # STOP, no Epoch 3 due work and no second LRN owner transition.
    assert supervisor.advance(at_ns=50, provenance=p("no-auto-epoch-three")) == ()
    assert commit.new_state.revision == 1
    assert data["skill2"].state is SkillState.STARTED

    record = json.loads(
        (ROOT / "docs/postmain-s20-cross-epoch.json").read_text(encoding="utf-8")
    )
    assert record["first"]["action_id"] == first.action_id
    assert record["first"]["feedback_id"] == commit.record.feedback_id
    assert record["learning"]["authority_id"] == commit.record.authority_id
    assert record["second"]["action_id"] == closed2.action_id
    assert record["second"]["binding_id"] == BINDING2
    assert record["second"]["world_session"] == consequence.session_id
    assert record["second"]["outcome"] == interpretation.disposition.name
    assert record["second"]["world_provenance"] == {
        "source": consequence.provenance.source,
        "reference": consequence.provenance.reference,
    }


def test_second_epoch_lineage_rejects_reused_or_wrong_binding_action_and_skill():
    d = _prepare_second()
    for updates in (
        {"action_id": d["closed1"].action_id},
        {"skill_execution_id": d["closed1"].skill_execution_id},
        {"binding_id": d["feedback"].binding_id},
        {"candidate_ref": "WAIT"},
        {"required_intent_id": "another-intent"},
    ):
        with pytest.raises(InvalidSecondEpochLineage):
            validate_second_epoch_lineage(
                d["supervisor"], d["closed1"], d["feedback"],
                d["commit"].new_state, d["values"]["prediction_input"],
                d["values"]["plan"], replace(d["binding"], **updates),
                provenance=p("bad-lineage"),
            )


def test_wrong_retained_revision_and_missing_feedback_provenance_reject():
    d = _prepare_second()
    wrong_prediction = replace(
        d["values"]["prediction_input"], source_refs=("no-commit",),
    )
    with pytest.raises(InvalidSecondEpochLineage):
        validate_second_epoch_lineage(
            d["supervisor"], d["closed1"], d["feedback"],
            d["commit"].new_state, wrong_prediction,
            d["values"]["plan"], d["binding"], provenance=p("wrong-source"),
        )
    old = d["commit"].previous_state
    with pytest.raises(InvalidSecondEpochLineage):
        validate_second_epoch_lineage(
            d["supervisor"], d["closed1"], d["feedback"],
            old, d["values"]["prediction_input"],
            d["values"]["plan"], d["binding"], provenance=p("old-owner"),
        )
    assert d["commit"].new_state.revision == 1


def test_execution_binding_wrong_admission_and_ref_fail_before_action():
    d = _prepare_second()
    with pytest.raises(InvalidExecutionBindingData):
        resolve_execution_binding(
            d["values"]["admission"], d["values"]["control"],
            d["values"]["route"], d["intent"], d["values"]["policies"][-2],
            replace(d["binding"], action_ref="MOVE_FORWARD", candidate_ref="WAIT"),
            provenance=p("wrong-binding"),
        )


def test_missing_invalid_authorization_and_duplicate_issue_are_rejected():
    d = _prepare_second()
    with pytest.raises(InvalidTransition):
        d["supervisor"].issue(
            d["proposed2"], at_ns=33, deadline_ns=100, provenance=p("unauthed"),
        )
    with pytest.raises(ValueError):
        d["proposed2"].authorize(
            at_ns=32, provenance=p("invalid-authority"), authority="",
        )
    authorized, issued = _issue_second(d)
    with pytest.raises(DuplicateSupervisedAction):
        d["supervisor"].issue(
            authorized, at_ns=34, deadline_ns=100, provenance=p("duplicate"),
        )
    with pytest.raises(InvalidTransition):
        authorized.issue(
            at_ns=34, deadline_ns=100, provenance=p("stale-action"),
        )
    assert d["supervisor"].get(ACTION2) is issued


def test_stale_skill_and_action_snapshots_cannot_drive_new_proposals_or_issue():
    d = _prepare_second()
    succeeded = d["skill2"].succeed(
        reason="test-skill-terminal", at_ns=32, provenance=p("skill-terminal"),
    )
    assert succeeded.state is SkillState.SUCCEEDED
    with pytest.raises(InvalidTransition):
        ActionLifecycle.propose(
            "third-action", skill_execution=d["skill2"],
            intent_commitment=d["intent"], at_ns=33, provenance=p("stale-skill"),
        )
    with pytest.raises(InvalidSkillTransition):
        d["skill2"].cancel(
            reason="stale", at_ns=34, provenance=p("stale-skill-transition"),
        )
    assert d["proposed2"].state is ActionState.PROPOSED


def test_cross_session_wrong_action_binding_and_malformed_world_result_fail_closed():
    d = _prepare_second()
    _, issued = _issue_second(d)
    c = _world_second(d, issued)
    for corrupted in (
        replace(c, action_id="action-move-backward-1"),
        replace(c, binding_id="binding-move-away-1"),
        replace(c, session_id=FIRST_SESSION),
    ):
        with pytest.raises(InvalidSecondEpochConsequence):
            require_fresh_second_consequence(
                d["supervisor"], issued, d["binding_result2"], corrupted,
                expected_session_id=SESSION2, first_session_id=FIRST_SESSION,
                at_ns=40,
            )
    with pytest.raises(InvalidMineflayerExecutionData):
        replace(c, movement_distance=None)
    with pytest.raises(InvalidSecondEpochConsequence):
        require_fresh_second_consequence(
            d["supervisor"], issued, d["binding_result2"], {"not": "WorldConsequence"},
            expected_session_id=SESSION2, first_session_id=FIRST_SESSION,
            at_ns=40,
        )
    # Internal receipt session misbinding remains rejected by frozen S16.
    internally_mismatched = replace(
        c, before_observation=replace(c.before_observation, session_id=FIRST_SESSION),
    )
    with pytest.raises(InvalidActionOutcomeData):
        interpret_world_consequence(
            issued, d["binding_result2"], internally_mismatched,
            provenance=p("wrong-evidence-session"),
        )


def test_late_consequence_and_duplicate_terminal_closure_reject_without_mutation():
    d = _prepare_second()
    _, issued = _issue_second(d)
    c = _world_second(d, issued)
    with pytest.raises(InvalidSecondEpochConsequence):
        _close_second(d, issued, c, at_ns=100)
    with pytest.raises(InvalidSecondEpochConsequence):
        _close_second(d, issued, c, at_ns=101)
    assert d["supervisor"].get(ACTION2) is issued
    interpreted, closed = _close_second(d, issued, c, at_ns=40)
    assert closed.state is ActionState.OUTCOME
    with pytest.raises(InvalidSecondEpochConsequence):
        _close_second(d, issued, c, at_ns=41)
    with pytest.raises(InvalidTransition):
        record_interpreted_action_outcome(
            d["supervisor"], interpreted, at_ns=41,
        )
    assert d["supervisor"].get(d["closed1"].action_id) is d["closed1"]


def test_no_learning_or_autonomous_third_epoch_after_action_two():
    d, _, _, _, _, closed2 = _two_completed_actions()
    assert closed2.state is ActionState.OUTCOME
    assert d["commit"].new_state.last_update is d["commit"].record
    assert d["commit"].new_state.revision == 1
    assert d["supervisor"].advance(
        at_ns=90, provenance=p("explicit-supervision-only"),
    ) == ()
    assert d["supervisor"].next_deadline_ns is None


def test_s20_receipt_and_static_guard():
    receipt = json.loads(
        (ROOT / "docs/postmain-s20-receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["base_head"] == "8ea0365f48b5e58bdbca503a120ea8bf5818e2ec"
    assert receipt["classification"] == (
        "EXPLICIT_TWO_EPOCH_SECOND_ACTION_OUTCOME_CLOSURE_QUALIFIED"
    )
    assert receipt["action_ids"] == [
        "action-move-backward-1", ACTION2,
    ]
    assert receipt["provider_model_calls"] == 0
    assert receipt["autonomous_reentry"] is False
    assert receipt["live_minecraft"] == "NOT_RUN"
    source = (ROOT / "src/relay_self/second_epoch_action.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "threading.Thread", "asyncio.create_task", "eval(", "exec(",
        "importlib", "global ", "commit_learning_update(",
        "authorize(", "issue(", "coordinate_decision_epoch(",
    ):
        assert forbidden not in source
