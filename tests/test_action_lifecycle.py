import pytest

from relay_self.action import (
    ActionEvent,
    ActionLifecycle,
    ActionState,
    InvalidActionData,
    InvalidTransition,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import InvalidProvenanceData, Provenance
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="test-boundary", reference=reference)


def committed_intent_owner(intent_id: str = "intent-1") -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        intent_id,
        objective="test objective",
        at_ns=1,
        provenance=provenance(f"commit-{intent_id}"),
    )
    return owner


def started_skill(
    owner: IntentCommitment,
    *,
    execution_id: str = "skill-exec-1",
) -> SkillExecution:
    return SkillExecution.start(
        execution_id,
        skill_id="test-skill",
        intent_commitment=owner,
        at_ns=2,
        provenance=provenance(f"start-{execution_id}"),
    )


def proposed_action(
    action_id: str = "action-1",
    *,
    at_ns: int = 10,
) -> ActionLifecycle:
    owner = committed_intent_owner()
    skill = started_skill(owner, execution_id=f"skill-exec-{action_id}")
    return ActionLifecycle.propose(
        action_id,
        skill_execution=skill,
        intent_commitment=owner,
        at_ns=at_ns,
        provenance=provenance(f"proposal-{action_id}"),
    )


def authorized_action() -> ActionLifecycle:
    return proposed_action().authorize(
        at_ns=20,
        provenance=provenance("authorization-1"),
        authority="test-policy",
    )


def issued_action() -> ActionLifecycle:
    return authorized_action().issue(
        at_ns=30,
        deadline_ns=50,
        provenance=provenance("issue-1"),
    )


def test_authorized_action_closes_with_outcome_and_keeps_causal_history() -> None:
    lifecycle = issued_action().record_outcome(
        at_ns=40,
        provenance=provenance("outcome-1"),
    )

    assert lifecycle.state is ActionState.OUTCOME
    assert lifecycle.is_terminal
    assert [event.state for event in lifecycle.events] == [
        ActionState.PROPOSED,
        ActionState.AUTHORIZED,
        ActionState.ISSUED,
        ActionState.OUTCOME,
    ]
    assert lifecycle.events[1].authority == "test-policy"
    assert lifecycle.events[2].deadline_ns == 50
    assert lifecycle.events[3].provenance.reference == "outcome-1"


def test_proposal_cannot_be_issued_without_authorization() -> None:
    lifecycle = proposed_action()

    with pytest.raises(InvalidTransition, match="proposed to issued"):
        lifecycle.issue(
            at_ns=20,
            deadline_ns=30,
            provenance=provenance("issue-1"),
        )


def test_denied_proposal_is_terminal_and_cannot_be_issued() -> None:
    lifecycle = proposed_action().deny(
        at_ns=20,
        provenance=provenance("denial-1"),
        authority="test-policy",
    )

    assert lifecycle.state is ActionState.DENIED
    assert lifecycle.is_terminal

    with pytest.raises(InvalidTransition, match="denied to issued"):
        lifecycle.issue(
            at_ns=30,
            deadline_ns=40,
            provenance=provenance("issue-1"),
        )


def test_issued_action_can_close_as_timeout_at_deadline() -> None:
    lifecycle = issued_action().timeout(
        at_ns=50,
        provenance=provenance("timeout-1"),
    )

    assert lifecycle.state is ActionState.TIMEOUT
    assert lifecycle.is_terminal


def test_timeout_before_deadline_is_rejected() -> None:
    with pytest.raises(InvalidTransition, match="before its deadline"):
        issued_action().timeout(
            at_ns=49,
            provenance=provenance("timeout-early"),
        )


def test_issued_action_can_close_as_unknown() -> None:
    lifecycle = issued_action().mark_unknown(
        at_ns=35,
        provenance=provenance("unknown-1"),
    )

    assert lifecycle.state is ActionState.UNKNOWN
    assert lifecycle.is_terminal


def test_terminal_state_rejects_further_transitions() -> None:
    lifecycle = issued_action().record_outcome(
        at_ns=40,
        provenance=provenance("outcome-1"),
    )

    with pytest.raises(InvalidTransition, match="outcome to unknown"):
        lifecycle.mark_unknown(
            at_ns=41,
            provenance=provenance("unknown-after-outcome"),
        )


def test_transition_time_must_be_monotonic() -> None:
    with pytest.raises(InvalidActionData, match="time must be monotonic"):
        authorized_action().issue(
            at_ns=19,
            deadline_ns=30,
            provenance=provenance("issue-backward"),
        )


def test_issue_deadline_must_be_after_issue_time() -> None:
    with pytest.raises(InvalidActionData, match="deadline must be after issue time"):
        authorized_action().issue(
            at_ns=30,
            deadline_ns=30,
            provenance=provenance("issue-no-window"),
        )


def test_authorization_requires_explicit_authority() -> None:
    lifecycle = proposed_action()

    with pytest.raises(InvalidActionData, match="authorization authority"):
        lifecycle.authorize(
            at_ns=20,
            provenance=provenance("authorization-1"),
            authority="",
        )


def test_provenance_rejects_non_string_fields_with_shared_error() -> None:
    with pytest.raises(InvalidProvenanceData, match="provenance source"):
        Provenance(source=1, reference="proposal-1")  # type: ignore[arg-type]


def test_action_event_requires_provenance_object() -> None:
    with pytest.raises(InvalidActionData, match="provenance must be Provenance"):
        ActionEvent(
            state=ActionState.PROPOSED,
            at_ns=10,
            provenance=None,  # type: ignore[arg-type]
        )


def test_action_event_requires_declared_state() -> None:
    with pytest.raises(InvalidActionData, match="state must be an ActionState"):
        ActionEvent(
            state="proposed",  # type: ignore[arg-type]
            at_ns=10,
            provenance=provenance("proposal-1"),
        )


def test_action_lifecycle_rejects_mutable_event_history() -> None:
    event = ActionEvent(
        state=ActionState.PROPOSED,
        at_ns=10,
        provenance=provenance("proposal-1"),
    )

    with pytest.raises(InvalidActionData, match="history must be an immutable tuple"):
        ActionLifecycle(
            action_id="action-1",
            skill_execution_id="skill-exec-1",
            intent_id="intent-1",
            _events=[event],  # type: ignore[arg-type]
        )


def test_action_lifecycle_rejects_non_event_history_values() -> None:
    with pytest.raises(InvalidActionData, match="only ActionEvent values"):
        ActionLifecycle(
            action_id="action-1",
            skill_execution_id="skill-exec-1",
            intent_id="intent-1",
            _events=("proposed",),  # type: ignore[arg-type]
        )


def test_action_proposal_derives_active_skill_and_current_intent_association() -> None:
    owner = committed_intent_owner()
    skill = started_skill(owner)
    intent_history = owner.events
    skill_history = skill.events

    lifecycle = ActionLifecycle.propose(
        "action-skill-1",
        skill_execution=skill,
        intent_commitment=owner,
        at_ns=3,
        provenance=provenance("proposal-skill-1"),
    )

    assert lifecycle.state is ActionState.PROPOSED
    assert lifecycle.skill_execution_id == skill.execution_id
    assert lifecycle.intent_id == "intent-1"
    assert owner.events == intent_history
    assert skill.events == skill_history


@pytest.mark.parametrize("terminal_method", ["succeed", "fail", "cancel"])
def test_terminal_skill_cannot_produce_new_action_proposal(terminal_method: str) -> None:
    owner = committed_intent_owner()
    skill = started_skill(owner)
    terminal_skill = getattr(skill, terminal_method)(
        reason="terminal",
        at_ns=3,
        provenance=provenance(f"skill-{terminal_method}"),
    )

    with pytest.raises(InvalidTransition, match="skill execution must be started"):
        ActionLifecycle.propose(
            "action-after-terminal-skill",
            skill_execution=terminal_skill,
            intent_commitment=owner,
            at_ns=4,
            provenance=provenance("proposal-after-terminal-skill"),
        )


def test_started_skill_cannot_propose_after_current_intent_closes() -> None:
    owner = committed_intent_owner()
    skill = started_skill(owner)
    owner.complete(
        "intent-1",
        reason="done",
        at_ns=3,
        provenance=provenance("intent-complete"),
    )
    skill_history = skill.events
    intent_history = owner.events

    assert skill.state is SkillState.STARTED
    with pytest.raises(InvalidTransition, match="current intent"):
        ActionLifecycle.propose(
            "action-after-intent-close",
            skill_execution=skill,
            intent_commitment=owner,
            at_ns=4,
            provenance=provenance("proposal-after-intent-close"),
        )

    assert skill.events == skill_history
    assert owner.events == intent_history


def test_stale_skill_cannot_propose_for_replacement_current_intent() -> None:
    owner = committed_intent_owner()
    stale_skill = started_skill(owner)
    owner.complete(
        "intent-1",
        reason="done",
        at_ns=3,
        provenance=provenance("intent-1-complete"),
    )
    owner.commit(
        "intent-2",
        objective="replacement objective",
        at_ns=4,
        provenance=provenance("commit-intent-2"),
    )

    with pytest.raises(InvalidTransition, match="does not match current intent"):
        ActionLifecycle.propose(
            "action-stale-skill",
            skill_execution=stale_skill,
            intent_commitment=owner,
            at_ns=5,
            provenance=provenance("proposal-stale-skill"),
        )


def test_pending_reconsideration_does_not_block_action_proposal() -> None:
    owner = committed_intent_owner()
    skill = started_skill(owner)
    owner.request_reconsideration(
        "intent-1",
        reason="new evidence",
        at_ns=3,
        provenance=provenance("reconsideration-request"),
    )

    lifecycle = ActionLifecycle.propose(
        "action-pending-reconsideration",
        skill_execution=skill,
        intent_commitment=owner,
        at_ns=4,
        provenance=provenance("proposal-pending-reconsideration"),
    )

    assert lifecycle.skill_execution_id == skill.execution_id
    assert lifecycle.intent_id == "intent-1"
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "intent-1"


def test_action_proposal_requires_real_skill_execution() -> None:
    owner = committed_intent_owner()

    with pytest.raises(InvalidActionData, match="skill execution"):
        ActionLifecycle.propose(
            "action-invalid-skill",
            skill_execution=object(),  # type: ignore[arg-type]
            intent_commitment=owner,
            at_ns=3,
            provenance=provenance("proposal-invalid-skill"),
        )


def test_action_proposal_requires_real_intent_commitment() -> None:
    owner = committed_intent_owner()
    skill = started_skill(owner)

    with pytest.raises(InvalidActionData, match="intent commitment"):
        ActionLifecycle.propose(
            "action-invalid-intent-owner",
            skill_execution=skill,
            intent_commitment=object(),  # type: ignore[arg-type]
            at_ns=3,
            provenance=provenance("proposal-invalid-intent-owner"),
        )


def test_action_supervision_preserves_skill_and_intent_association() -> None:
    owner = committed_intent_owner()
    skill = started_skill(owner)
    lifecycle = ActionLifecycle.propose(
        "action-supervised-skill",
        skill_execution=skill,
        intent_commitment=owner,
        at_ns=3,
        provenance=provenance("proposal-supervised-skill"),
    ).authorize(
        at_ns=4,
        provenance=provenance("authorization-supervised-skill"),
        authority="test-policy",
    )

    issued = ActionSupervisor().issue(
        lifecycle,
        at_ns=5,
        deadline_ns=10,
        provenance=provenance("issue-supervised-skill"),
    )

    assert issued.skill_execution_id == skill.execution_id
    assert issued.intent_id == "intent-1"
