import pytest

from relay_self.action import Provenance
from relay_self.intent import IntentCommitment
from relay_self.skill import (
    SKILL_TERMINAL_STATES,
    InvalidSkillData,
    InvalidSkillTransition,
    SkillExecution,
    SkillState,
)


def provenance(reference: str) -> Provenance:
    return Provenance(source="test-runtime", reference=reference)


def started() -> SkillExecution:
    return SkillExecution.start(
        "skill-exec-1",
        skill_id="navigate-corridor",
        intent_id="intent-1",
        at_ns=10,
        provenance=provenance("skill-start"),
    )


def test_start_establishes_skill_execution_identity_and_state() -> None:
    execution = started()

    assert execution.execution_id == "skill-exec-1"
    assert execution.skill_id == "navigate-corridor"
    assert execution.intent_id == "intent-1"
    assert execution.state is SkillState.STARTED
    assert execution.is_terminal is False
    assert execution.events[0].provenance.reference == "skill-start"
    assert execution.events[0].reason is None


def test_success_is_explicit_terminal_transition() -> None:
    execution = started().succeed(
        reason="destination reached",
        at_ns=20,
        provenance=provenance("skill-success"),
    )

    assert execution.state is SkillState.SUCCEEDED
    assert execution.is_terminal is True
    assert execution.events[-1].reason == "destination reached"
    assert execution.events[-1].provenance.reference == "skill-success"
    assert len(execution.events) == 2


def test_failure_is_explicit_terminal_transition() -> None:
    execution = started().fail(
        reason="route became unavailable",
        at_ns=20,
        provenance=provenance("skill-failure"),
    )

    assert execution.state is SkillState.FAILED
    assert execution.is_terminal is True
    assert execution.events[-1].reason == "route became unavailable"
    assert execution.events[-1].provenance.reference == "skill-failure"


@pytest.mark.parametrize("terminal_state", [SkillState.SUCCEEDED, SkillState.FAILED])
def test_terminal_execution_cannot_reopen(terminal_state: SkillState) -> None:
    execution = started()
    if terminal_state is SkillState.SUCCEEDED:
        execution = execution.succeed(
            reason="done",
            at_ns=20,
            provenance=provenance("success"),
        )
    else:
        execution = execution.fail(
            reason="failed",
            at_ns=20,
            provenance=provenance("failure"),
        )

    with pytest.raises(InvalidSkillTransition, match="cannot transition"):
        execution.fail(
            reason="second terminal transition",
            at_ns=21,
            provenance=provenance("again"),
        )


def test_skill_event_time_is_monotonic() -> None:
    execution = started()

    with pytest.raises(InvalidSkillData, match="must be monotonic"):
        execution.succeed(
            reason="stale completion",
            at_ns=9,
            provenance=provenance("backward"),
        )

    assert execution.state is SkillState.STARTED
    assert len(execution.events) == 1


@pytest.mark.parametrize("at_ns", [-1, True, 1.5])
def test_start_rejects_malformed_time(at_ns: object) -> None:
    with pytest.raises(InvalidSkillData, match="non-negative integer"):
        SkillExecution.start(
            "skill-exec-1",
            skill_id="navigate-corridor",
            intent_id="intent-1",
            at_ns=at_ns,  # type: ignore[arg-type]
            provenance=provenance("bad-time"),
        )


def test_equal_time_terminal_transition_is_allowed() -> None:
    execution = SkillExecution.start(
        "skill-exec-1",
        skill_id="instant-check",
        intent_id="intent-1",
        at_ns=10,
        provenance=provenance("start"),
    ).succeed(
        reason="completed in one decision epoch",
        at_ns=10,
        provenance=provenance("success"),
    )

    assert execution.state is SkillState.SUCCEEDED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("execution_id", ""),
        ("skill_id", "   "),
        ("intent_id", ""),
    ],
)
def test_start_requires_non_empty_identity_fields(field: str, value: str) -> None:
    kwargs = {
        "execution_id": "skill-exec-1",
        "skill_id": "navigate-corridor",
        "intent_id": "intent-1",
    }
    kwargs[field] = value

    with pytest.raises(InvalidSkillData, match="non-empty string"):
        SkillExecution.start(
            kwargs["execution_id"],
            skill_id=kwargs["skill_id"],
            intent_id=kwargs["intent_id"],
            at_ns=10,
            provenance=provenance("bad-id"),
        )


def test_start_requires_valid_provenance() -> None:
    with pytest.raises(InvalidSkillData, match="provenance must be Provenance"):
        SkillExecution.start(
            "skill-exec-1",
            skill_id="navigate-corridor",
            intent_id="intent-1",
            at_ns=10,
            provenance=None,  # type: ignore[arg-type]
        )


def test_terminal_transition_requires_reason_and_provenance() -> None:
    execution = started()

    with pytest.raises(InvalidSkillData, match="terminal reason"):
        execution.fail(
            reason="",
            at_ns=20,
            provenance=provenance("empty-reason"),
        )

    with pytest.raises(InvalidSkillData, match="provenance must be Provenance"):
        execution.fail(
            reason="failed",
            at_ns=20,
            provenance=None,  # type: ignore[arg-type]
        )

    assert execution.state is SkillState.STARTED
    assert len(execution.events) == 1


def test_event_history_is_immutable_tuple() -> None:
    execution = started()

    assert isinstance(execution.events, tuple)
    assert SkillState.SUCCEEDED in SKILL_TERMINAL_STATES
    assert SkillState.FAILED in SKILL_TERMINAL_STATES


@pytest.mark.parametrize(
    ("method", "expected_state"),
    [
        ("succeed", SkillState.SUCCEEDED),
        ("fail", SkillState.FAILED),
    ],
)
def test_skill_terminal_state_does_not_automatically_mutate_current_intent(
    method: str,
    expected_state: SkillState,
) -> None:
    intent = IntentCommitment()
    intent.commit(
        "intent-1",
        objective="reach the charging station",
        at_ns=1,
        provenance=provenance("intent-commit"),
    )

    execution = SkillExecution.start(
        "skill-exec-1",
        skill_id="navigate-corridor",
        intent_id="intent-1",
        at_ns=10,
        provenance=provenance("skill-start"),
    )
    execution = getattr(execution, method)(
        reason=f"skill {method}",
        at_ns=20,
        provenance=provenance(f"skill-{method}"),
    )

    assert execution.state is expected_state
    assert intent.current_intent is not None
    assert intent.current_intent.intent_id == "intent-1"
    assert intent.pending_reconsideration is None
