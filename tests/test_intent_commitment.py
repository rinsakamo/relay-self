import pytest

from relay_self.action import Provenance
from relay_self.intent import (
    DuplicateIntentIdentity,
    IntentCommitment,
    IntentEventKind,
    InvalidIntentData,
    InvalidIntentTime,
    InvalidIntentTransition,
    ReconsiderationDecision,
)


def provenance(reference: str) -> Provenance:
    return Provenance(source="test-runtime", reference=reference)


def committed() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-1",
        objective="reach the charging station",
        at_ns=10,
        provenance=provenance("commit-1"),
    )
    return owner


def test_commit_establishes_current_intent() -> None:
    owner = committed()
    current = owner.current_intent
    assert current is not None
    assert current.intent_id == "intent-1"
    assert current.objective == "reach the charging station"
    assert owner.last_at_ns == 10


def test_second_commit_cannot_replace_current_intent() -> None:
    owner = committed()
    before = owner.events
    with pytest.raises(InvalidIntentTransition, match="while intent-1 is current"):
        owner.commit(
            "intent-2",
            objective="inspect the window",
            at_ns=11,
            provenance=provenance("commit-2"),
        )
    assert owner.events is before
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "intent-1"
    assert owner.last_at_ns == 10


def test_reconsider_continue_preserves_same_current_intent() -> None:
    owner = committed()
    current = owner.reconsider(
        "intent-1",
        decision=ReconsiderationDecision.CONTINUE,
        reason="alternative is not material",
        at_ns=20,
        provenance=provenance("reconsider-continue"),
    )
    assert current is not None
    assert current.intent_id == "intent-1"
    assert owner.events[-1].kind is IntentEventKind.RECONSIDERED_CONTINUE


def test_reconsider_release_clears_current_intent() -> None:
    owner = committed()
    current = owner.reconsider(
        "intent-1",
        decision=ReconsiderationDecision.RELEASE,
        reason="precondition no longer holds",
        at_ns=20,
        provenance=provenance("reconsider-release"),
    )
    assert current is None
    assert owner.current_intent is None


@pytest.mark.parametrize(
    ("method", "kind"),
    [
        ("complete", IntentEventKind.COMPLETED),
        ("fail", IntentEventKind.FAILED),
        ("invalidate", IntentEventKind.INVALIDATED),
    ],
)
def test_terminal_release_clears_current_intent(method: str, kind: IntentEventKind) -> None:
    owner = committed()
    event = getattr(owner, method)(
        "intent-1",
        reason=f"{method}-reason",
        at_ns=20,
        provenance=provenance(method),
    )
    assert event.kind is kind
    assert owner.current_intent is None


def test_new_intent_can_commit_after_explicit_release() -> None:
    owner = committed()
    owner.reconsider(
        "intent-1",
        decision=ReconsiderationDecision.RELEASE,
        reason="material change",
        at_ns=20,
        provenance=provenance("release-1"),
    )
    current = owner.commit(
        "intent-2",
        objective="avoid the blocked corridor",
        at_ns=20,
        provenance=provenance("commit-2"),
    )
    assert current.intent_id == "intent-2"


def test_duplicate_intent_identity_cannot_be_reused() -> None:
    owner = committed()
    owner.complete(
        "intent-1",
        reason="done",
        at_ns=20,
        provenance=provenance("complete-1"),
    )
    with pytest.raises(DuplicateIntentIdentity, match="already committed"):
        owner.commit(
            "intent-1",
            objective="same identifier again",
            at_ns=21,
            provenance=provenance("commit-again"),
        )


def test_wrong_intent_cannot_be_closed() -> None:
    owner = committed()
    with pytest.raises(InvalidIntentTransition, match="is not current"):
        owner.complete(
            "intent-2",
            reason="wrong target",
            at_ns=20,
            provenance=provenance("wrong-close"),
        )
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "intent-1"


def test_transition_requires_current_intent() -> None:
    owner = IntentCommitment()
    with pytest.raises(InvalidIntentTransition, match="no current intent"):
        owner.fail(
            "intent-1",
            reason="nothing active",
            at_ns=10,
            provenance=provenance("fail-none"),
        )


def test_invalid_time_fails_without_mutation() -> None:
    owner = IntentCommitment()
    with pytest.raises(InvalidIntentTime, match="non-negative integers"):
        owner.commit(
            "intent-1",
            objective="invalid time",
            at_ns=-1,
            provenance=provenance("bad-time"),
        )
    assert owner.events == ()
    assert owner.last_at_ns is None


def test_time_cannot_move_backward() -> None:
    owner = committed()
    before = owner.events
    with pytest.raises(InvalidIntentTime, match="must be monotonic"):
        owner.invalidate(
            "intent-1",
            reason="stale event",
            at_ns=9,
            provenance=provenance("backward"),
        )
    assert owner.events is before
    assert owner.last_at_ns == 10


def test_invalid_reconsideration_decision_fails_without_mutation() -> None:
    owner = committed()
    before = owner.events
    with pytest.raises(InvalidIntentData, match="ReconsiderationDecision"):
        owner.reconsider(
            "intent-1",
            decision="continue",  # type: ignore[arg-type]
            reason="bad enum",
            at_ns=20,
            provenance=provenance("bad-decision"),
        )
    assert owner.events is before
    assert owner.last_at_ns == 10


def test_invalid_provenance_fails_without_mutation() -> None:
    owner = committed()
    before = owner.events
    with pytest.raises(InvalidIntentData, match="provenance must be Provenance"):
        owner.reconsider(
            "intent-1",
            decision=ReconsiderationDecision.CONTINUE,
            reason="bad provenance",
            at_ns=20,
            provenance=None,  # type: ignore[arg-type]
        )
    assert owner.events is before
    assert owner.last_at_ns == 10


def test_event_history_is_immutable_tuple() -> None:
    owner = committed()
    assert isinstance(owner.events, tuple)
