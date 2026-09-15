import pytest

from relay_self.action import (
    ActionLifecycle,
    ActionState,
    InvalidTransition,
    Provenance,
)
from relay_self.action_supervision import (
    ActionSupervisor,
    DuplicateSupervisedAction,
    InvalidSupervisionData,
    InvalidSupervisorTime,
    UnknownSupervisedAction,
)


def provenance(reference: str) -> Provenance:
    return Provenance(source="test-runtime", reference=reference)


def authorized_action(action_id: str = "action-1", *, at_ns: int = 20) -> ActionLifecycle:
    return ActionLifecycle.propose(
        action_id,
        at_ns=10,
        provenance=provenance(f"proposal-{action_id}"),
    ).authorize(
        at_ns=at_ns,
        provenance=provenance(f"authorization-{action_id}"),
        authority="test-policy",
    )


def issue(
    supervisor: ActionSupervisor,
    action_id: str = "action-1",
    *,
    at_ns: int = 30,
    deadline_ns: int = 50,
) -> ActionLifecycle:
    return supervisor.issue(
        authorized_action(action_id, at_ns=at_ns - 10),
        at_ns=at_ns,
        deadline_ns=deadline_ns,
        provenance=provenance(f"issue-{action_id}"),
    )


def test_supervised_issue_is_retained_atomically() -> None:
    supervisor = ActionSupervisor()

    issued = issue(supervisor)

    assert issued.state is ActionState.ISSUED
    assert supervisor.get("action-1") is issued
    assert supervisor.open_actions == (issued,)
    assert supervisor.last_at_ns == 30


def test_advance_before_deadline_keeps_action_open() -> None:
    supervisor = ActionSupervisor()
    issued = issue(supervisor)

    closed = supervisor.advance(at_ns=49, provenance=provenance("epoch-49"))

    assert closed == ()
    assert supervisor.get("action-1") is issued
    assert supervisor.open_actions == (issued,)
    assert supervisor.last_at_ns == 49


def test_advance_at_deadline_times_out_due_action() -> None:
    supervisor = ActionSupervisor()
    issue(supervisor)

    (closed,) = supervisor.advance(at_ns=50, provenance=provenance("epoch-50"))

    assert closed.state is ActionState.TIMEOUT
    assert closed.events[-1].at_ns == 50
    assert closed.events[-1].provenance.reference == "epoch-50"
    assert supervisor.get("action-1") is closed
    assert supervisor.open_actions == ()


def test_advance_times_out_only_due_actions() -> None:
    supervisor = ActionSupervisor()
    issue(supervisor, "action-1", at_ns=30, deadline_ns=50)
    second = issue(supervisor, "action-2", at_ns=40, deadline_ns=80)

    closed = supervisor.advance(at_ns=60, provenance=provenance("epoch-60"))

    assert [lifecycle.action_id for lifecycle in closed] == ["action-1"]
    assert supervisor.get("action-1").state is ActionState.TIMEOUT
    assert supervisor.get("action-2") is second
    assert supervisor.open_actions == (second,)


def test_outcome_processed_before_epoch_wins_terminal_order() -> None:
    supervisor = ActionSupervisor()
    issue(supervisor)

    outcome = supervisor.record_outcome(
        "action-1",
        at_ns=50,
        provenance=provenance("outcome-1"),
    )
    closed = supervisor.advance(at_ns=50, provenance=provenance("epoch-50"))

    assert outcome.state is ActionState.OUTCOME
    assert closed == ()
    assert supervisor.get("action-1") is outcome


def test_timeout_processed_before_outcome_is_terminal() -> None:
    supervisor = ActionSupervisor()
    issue(supervisor)
    supervisor.advance(at_ns=50, provenance=provenance("epoch-50"))

    with pytest.raises(InvalidTransition, match="timeout to outcome"):
        supervisor.record_outcome(
            "action-1",
            at_ns=50,
            provenance=provenance("late-outcome"),
        )

    assert supervisor.get("action-1").state is ActionState.TIMEOUT
    assert supervisor.last_at_ns == 50


def test_unknown_closure_uses_lifecycle_transition() -> None:
    supervisor = ActionSupervisor()
    issue(supervisor)

    closed = supervisor.mark_unknown(
        "action-1",
        at_ns=40,
        provenance=provenance("unknown-1"),
    )

    assert closed.state is ActionState.UNKNOWN
    assert supervisor.open_actions == ()


def test_supervisor_rejects_backward_processing_time() -> None:
    supervisor = ActionSupervisor()
    issue(supervisor)
    supervisor.advance(at_ns=45, provenance=provenance("epoch-45"))

    with pytest.raises(InvalidSupervisorTime, match="must be monotonic"):
        supervisor.mark_unknown(
            "action-1",
            at_ns=44,
            provenance=provenance("unknown-backward"),
        )

    assert supervisor.get("action-1").state is ActionState.ISSUED
    assert supervisor.last_at_ns == 45


def test_supervisor_rejects_invalid_time_even_when_no_action_is_due() -> None:
    supervisor = ActionSupervisor()

    with pytest.raises(InvalidSupervisorTime, match="non-negative integers"):
        supervisor.advance(at_ns=-1, provenance=provenance("bad-epoch"))

    assert supervisor.last_at_ns is None


def test_duplicate_action_identity_is_rejected_without_replacement() -> None:
    supervisor = ActionSupervisor()
    first = issue(supervisor)

    with pytest.raises(DuplicateSupervisedAction, match="already supervised"):
        supervisor.issue(
            authorized_action("action-1", at_ns=30),
            at_ns=40,
            deadline_ns=60,
            provenance=provenance("duplicate-issue"),
        )

    assert supervisor.get("action-1") is first
    assert supervisor.last_at_ns == 30


def test_unknown_action_identity_is_rejected() -> None:
    supervisor = ActionSupervisor()

    with pytest.raises(UnknownSupervisedAction, match="unknown supervised action"):
        supervisor.record_outcome(
            "missing",
            at_ns=10,
            provenance=provenance("missing-outcome"),
        )

    assert supervisor.last_at_ns is None


def test_advance_rejects_invalid_provenance_even_when_nothing_is_due() -> None:
    supervisor = ActionSupervisor()

    with pytest.raises(InvalidSupervisionData, match="provenance must be Provenance"):
        supervisor.advance(
            at_ns=10,
            provenance=None,  # type: ignore[arg-type]
        )

    assert supervisor.last_at_ns is None


def test_failed_multi_action_advance_does_not_partially_commit() -> None:
    supervisor = ActionSupervisor()
    first = issue(supervisor, "action-1", at_ns=30, deadline_ns=50)
    second = issue(supervisor, "action-2", at_ns=40, deadline_ns=50)

    with pytest.raises(InvalidSupervisionData, match="provenance must be Provenance"):
        supervisor.advance(
            at_ns=50,
            provenance=None,  # type: ignore[arg-type]
        )

    assert supervisor.get("action-1") is first
    assert supervisor.get("action-2") is second
    assert supervisor.last_at_ns == 40


def test_supervised_issue_requires_lifecycle_object() -> None:
    supervisor = ActionSupervisor()

    with pytest.raises(InvalidSupervisionData, match="requires an ActionLifecycle"):
        supervisor.issue(
            None,  # type: ignore[arg-type]
            at_ns=20,
            deadline_ns=30,
            provenance=provenance("issue-1"),
        )

    assert supervisor.last_at_ns is None


def test_supervised_issue_delegates_authorization_legality() -> None:
    supervisor = ActionSupervisor()
    proposed = ActionLifecycle.propose(
        "action-1",
        at_ns=10,
        provenance=provenance("proposal-1"),
    )

    with pytest.raises(InvalidTransition, match="proposed to issued"):
        supervisor.issue(
            proposed,
            at_ns=20,
            deadline_ns=30,
            provenance=provenance("issue-1"),
        )

    with pytest.raises(UnknownSupervisedAction):
        supervisor.get("action-1")
    assert supervisor.last_at_ns is None
