import pytest

from relay_self.action import (
    ActionEvent,
    ActionLifecycle,
    ActionState,
    InvalidActionData,
    InvalidTransition,
    Provenance,
)


def provenance(reference: str) -> Provenance:
    return Provenance(source="test-boundary", reference=reference)


def authorized_action() -> ActionLifecycle:
    return ActionLifecycle.propose(
        "action-1",
        at_ns=10,
        provenance=provenance("proposal-1"),
    ).authorize(
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
    lifecycle = ActionLifecycle.propose(
        "action-1",
        at_ns=10,
        provenance=provenance("proposal-1"),
    )

    with pytest.raises(InvalidTransition, match="proposed to issued"):
        lifecycle.issue(
            at_ns=20,
            deadline_ns=30,
            provenance=provenance("issue-1"),
        )


def test_denied_proposal_is_terminal_and_cannot_be_issued() -> None:
    lifecycle = ActionLifecycle.propose(
        "action-1",
        at_ns=10,
        provenance=provenance("proposal-1"),
    ).deny(
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
    lifecycle = ActionLifecycle.propose(
        "action-1",
        at_ns=10,
        provenance=provenance("proposal-1"),
    )

    with pytest.raises(InvalidActionData, match="authorization authority"):
        lifecycle.authorize(
            at_ns=20,
            provenance=provenance("authorization-1"),
            authority="",
        )


def test_provenance_rejects_non_string_fields_with_contract_error() -> None:
    with pytest.raises(InvalidActionData, match="provenance source"):
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
        ActionLifecycle("action-1", [event])  # type: ignore[arg-type]


def test_action_lifecycle_rejects_non_event_history_values() -> None:
    with pytest.raises(InvalidActionData, match="only ActionEvent values"):
        ActionLifecycle("action-1", ("proposed",))  # type: ignore[arg-type]
