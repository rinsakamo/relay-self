"""S43 bounded reverse observational contrast with exact source chronology.

This is a pure evidence/choice gate, NOT an Action authorization capability.
A far-source WAIT never creates an Action, and a later near MOVE_AWAY still
requires genuine fresh S35 native cognition and separate S39 Action grants.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldChoiceRejected,
    WorldConditionedChoice,
    verify_world_contrast,
)


class ReversedWorldChoiceRejected(ValueError):
    """Reject stale, reordered, aliased, or unsolicited Action evidence."""


@dataclass(frozen=True, slots=True)
class ReversedChoiceReceipt:
    session_id: str
    far_entity_id: int
    far_event_seq: int
    far_probe_seq: int
    near_entity_id: int
    near_event_seq: int
    near_probe_seq: int
    first_choice: str
    second_choice: str
    prior_unknown_action: str
    prior_unknown_terminal: str
    same_retained_revision: int
    same_retained_value: int
    criterion_id: str
    far_action_issued: bool
    historic_unknown_reclassified: bool


def verify_far_then_near(
    far: WorldConditionedChoice,
    near: WorldConditionedChoice,
    *,
    far_event_seq: int,
    near_event_seq: int,
    supervisor: ActionSupervisor,
    prior_unknown: ActionLifecycle,
) -> ReversedChoiceReceipt:
    """Adjudicate order, current exact owner and frozen World comparison.

    This is called BEFORE any newly proposed near Action. Far observation is
    explicit and must have caused zero newly open Action. Historical UNKNOWN
    cannot be rewritten even when a later probe establishes changed geometry.
    """
    if (
        not isinstance(far, WorldConditionedChoice)
        or not isinstance(near, WorldConditionedChoice)
        or type(far_event_seq) is not int
        or type(near_event_seq) is not int
        or not isinstance(supervisor, ActionSupervisor)
        or not isinstance(prior_unknown, ActionLifecycle)
        or prior_unknown.state is not ActionState.UNKNOWN
        or supervisor.get(prior_unknown.action_id) is not prior_unknown
        or supervisor.open_actions != ()
        or not 0 <= far_event_seq < far.probe_seq < near_event_seq < near.probe_seq
        or far.selection is not WorldChoiceKind.WAIT
        or near.selection is not WorldChoiceKind.MOVE_AWAY
        or far.action_authorized
        or near.action_authorized
    ):
        raise ReversedWorldChoiceRejected(
            "exact far event/probe must precede independently admitted near event/probe"
        )
    try:
        verify_world_contrast(near, far)
    except WorldChoiceRejected as exc:
        raise ReversedWorldChoiceRejected("fixed-policy paired World contrast invalid") from exc
    return ReversedChoiceReceipt(
        session_id=near.session_id,
        far_entity_id=far.entity_id,
        far_event_seq=far_event_seq,
        far_probe_seq=far.probe_seq,
        near_entity_id=near.entity_id,
        near_event_seq=near_event_seq,
        near_probe_seq=near.probe_seq,
        first_choice=far.selection.value,
        second_choice=near.selection.value,
        prior_unknown_action=prior_unknown.action_id,
        prior_unknown_terminal=prior_unknown.state.value,
        same_retained_revision=near.retained_revision,
        same_retained_value=near.retained_value,
        criterion_id=near.criterion_id,
        far_action_issued=False,
        historic_unknown_reclassified=False,
    )
