from experiments.running_skill_interrupt import (
    build_running_skill_action,
    explicitly_cancel_skill,
    request_viability_reconsideration,
)
from relay_self.action import ActionState
from relay_self.provenance import Provenance
from relay_self.skill import SkillState


def test_reconsideration_request_does_not_auto_cancel_skill_or_action() -> None:
    running = build_running_skill_action()
    skill_before = running.skill
    action_before = running.supervisor.get(running.action_id)

    request_viability_reconsideration(running)

    assert running.intent_commitment.pending_reconsideration is not None
    assert running.intent_commitment.current_intent is not None
    assert running.skill is skill_before
    assert running.skill.state is SkillState.STARTED
    assert running.supervisor.get(running.action_id) is action_before
    assert running.supervisor.get(running.action_id).state is ActionState.ISSUED


def test_explicit_skill_cancel_does_not_close_issued_action_or_intent() -> None:
    running = build_running_skill_action()
    request_viability_reconsideration(running)

    cancelled = explicitly_cancel_skill(running)

    assert cancelled.state is SkillState.CANCELLED
    assert running.intent_commitment.current_intent is not None
    assert running.intent_commitment.pending_reconsideration is not None
    assert running.supervisor.get(running.action_id).state is ActionState.ISSUED


def test_late_action_outcome_remains_recordable_after_skill_cancel() -> None:
    running = build_running_skill_action()
    request_viability_reconsideration(running)
    cancelled = explicitly_cancel_skill(running)

    outcome = running.supervisor.record_outcome(
        running.action_id,
        at_ns=8,
        provenance=Provenance(
            source="fixture.world",
            reference="action:late-outcome",
        ),
    )

    assert cancelled.state is SkillState.CANCELLED
    assert running.skill is cancelled
    assert outcome.state is ActionState.OUTCOME
    assert running.supervisor.get(running.action_id) is outcome
    assert running.intent_commitment.current_intent is not None
    assert running.intent_commitment.pending_reconsideration is not None


def test_unresolved_action_can_close_unknown_without_claiming_stop() -> None:
    running = build_running_skill_action()
    request_viability_reconsideration(running)
    cancelled = explicitly_cancel_skill(running)

    unknown = running.supervisor.mark_unknown(
        running.action_id,
        at_ns=8,
        provenance=Provenance(
            source="fixture.supervision",
            reference="action:unknown-after-interrupt",
        ),
    )

    assert cancelled.state is SkillState.CANCELLED
    assert unknown.state is ActionState.UNKNOWN
    assert running.supervisor.open_actions == ()
    assert running.intent_commitment.current_intent is not None
