import pytest

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.runtime_coordination import (
    CognitionUnavailable,
    DecisionEpochResult,
    coordinate_decision_epoch,
)
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="runtime-coordinator-test", reference=reference)


def running_path(
    *,
    action_id: str = "action-1",
    deadline_ns: int = 50,
) -> tuple[IntentCommitment, SkillExecution, ActionSupervisor]:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-1",
        objective="reach safety",
        at_ns=1,
        provenance=provenance("intent"),
    )
    skill = SkillExecution.start(
        "skill-1",
        skill_id="FLEE",
        intent_commitment=commitment,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        action_id,
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=3,
        provenance=provenance("proposal"),
    ).authorize(
        at_ns=4,
        provenance=provenance("authorization"),
        authority="test-authority",
    )
    supervisor = ActionSupervisor()
    supervisor.issue(
        action,
        at_ns=5,
        deadline_ns=deadline_ns,
        provenance=provenance("issue"),
    )
    return commitment, skill, supervisor


def test_package_exports_decision_epoch_coordinator() -> None:
    assert relay_self.DecisionEpochResult is DecisionEpochResult
    assert relay_self.coordinate_decision_epoch is coordinate_decision_epoch


def test_supervision_only_epoch_services_due_action_without_cognition() -> None:
    commitment, skill, supervisor = running_path()

    result = coordinate_decision_epoch(
        supervisor,
        at_ns=50,
        provenance=provenance("epoch-50"),
    )

    assert [action.action_id for action in result.timed_out_actions] == ["action-1"]
    assert result.cognition_requested is False
    assert result.cognition_result is None
    assert result.next_action_deadline_ns is None
    assert supervisor.get("action-1").state is ActionState.TIMEOUT
    assert skill.state is SkillState.STARTED
    assert commitment.current_intent is not None
    assert commitment.current_intent.intent_id == "intent-1"


def test_owner_local_supervision_runs_before_caller_decision_work() -> None:
    _, _, supervisor = running_path()
    observed_states: list[ActionState] = []

    def deterministic_step() -> None:
        observed_states.append(supervisor.get("action-1").state)
        return None

    coordinate_decision_epoch(
        supervisor,
        at_ns=50,
        provenance=provenance("epoch-50"),
        decision_step=deterministic_step,
    )

    assert observed_states == [ActionState.TIMEOUT]


def test_resolved_deterministic_step_does_not_call_relay_engine() -> None:
    _, _, supervisor = running_path(deadline_ns=100)
    model_calls: list[object] = []

    def relay_engine(request: object) -> str:
        model_calls.append(request)
        return "unused"

    result = coordinate_decision_epoch(
        supervisor,
        at_ns=20,
        provenance=provenance("epoch-20"),
        decision_step=lambda: None,
        relay_engine=relay_engine,
    )

    assert result.timed_out_actions == ()
    assert result.cognition_requested is False
    assert result.next_action_deadline_ns == 100
    assert model_calls == []


def test_unresolved_step_invokes_supplied_relay_engine_exactly_once() -> None:
    _, _, supervisor = running_path(deadline_ns=100)
    request = {"kind": "bounded-choice", "choices": ("cave", "ridge")}
    calls: list[object] = []

    def relay_engine(received: object) -> dict[str, str]:
        calls.append(received)
        return {"choice": "ridge"}

    result = coordinate_decision_epoch(
        supervisor,
        at_ns=20,
        provenance=provenance("epoch-20"),
        decision_step=lambda: request,
        relay_engine=relay_engine,
    )

    assert calls == [request]
    assert result.cognition_requested is True
    assert result.cognition_result == {"choice": "ridge"}
    assert result.next_action_deadline_ns == 100


def test_cognition_request_without_engine_fails_instead_of_falling_back() -> None:
    _, _, supervisor = running_path(deadline_ns=100)

    with pytest.raises(CognitionUnavailable, match="RelayEngine"):
        coordinate_decision_epoch(
            supervisor,
            at_ns=20,
            provenance=provenance("epoch-20"),
            decision_step=lambda: {"need": "cognition"},
        )

    assert supervisor.get("action-1").state is ActionState.ISSUED
    assert supervisor.last_at_ns == 20


def test_supervision_consequence_is_not_rolled_back_by_later_cognition_failure() -> None:
    _, _, supervisor = running_path(deadline_ns=50)

    with pytest.raises(CognitionUnavailable):
        coordinate_decision_epoch(
            supervisor,
            at_ns=50,
            provenance=provenance("epoch-50"),
            decision_step=lambda: {"need": "cognition"},
        )

    assert supervisor.get("action-1").state is ActionState.TIMEOUT
    assert supervisor.next_deadline_ns is None


def test_coordinator_returns_existing_owner_deadline_without_owning_a_clock() -> None:
    commitment, skill, supervisor = running_path(
        action_id="action-1",
        deadline_ns=50,
    )
    second = ActionLifecycle.propose(
        "action-2",
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=6,
        provenance=provenance("proposal-2"),
    ).authorize(
        at_ns=7,
        provenance=provenance("authorization-2"),
        authority="test-authority",
    )
    supervisor.issue(
        second,
        at_ns=8,
        deadline_ns=80,
        provenance=provenance("issue-2"),
    )

    result = coordinate_decision_epoch(
        supervisor,
        at_ns=50,
        provenance=provenance("epoch-50"),
    )

    assert [action.action_id for action in result.timed_out_actions] == ["action-1"]
    assert result.next_action_deadline_ns == 80
