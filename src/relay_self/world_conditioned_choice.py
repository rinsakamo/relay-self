"""S42 fixed, World-geometry-conditioned WAIT versus MOVE_AWAY selection.

Bounded source-dependent decision experiment, *not* a new learned policy.
Exact real native probe, retained revision, intent and candidate scores are
traceable. The frozen S35 automatic near-threat event threshold is unchanged.
A far threat needs a separate explicit read; WAIT never issues an Action.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.s34_native_world_cognition_ci import (
    MAX_GOAL_DISTANCE_M,
    NativeThreat,
    _native_threat,
)
from relay_self.learning import LearningPreferenceState
from relay_self.planning import (
    PlanCandidate,
    PlanFeature,
    PlanSelectionStatus,
    PlanningCriterion,
    PlanningDirection,
    select_plan,
)
from relay_self.provenance import Provenance


class WorldChoiceRejected(ValueError):
    """Missing actual native source or immutable decision criteria."""


class WorldChoiceKind(str, Enum):
    WAIT = "WAIT"
    MOVE_AWAY = "MOVE_AWAY"


@dataclass(frozen=True, slots=True)
class WorldConditionedChoice:
    session_id: str
    entity_id: int
    probe_seq: int
    request_id: str
    distance_m: float
    retained_target_id: str
    retained_revision: int
    retained_value: int
    threshold_m: float
    criterion_id: str
    wait_score: int
    move_score: int
    selection: WorldChoiceKind
    action_authorized: bool
    provenance: Provenance


def select_world_conditioned_choice(
    native: NativeThreat,
    retained: LearningPreferenceState,
    *,
    expected_session_id: str,
    expected_entity_id: int,
) -> WorldConditionedChoice:
    """One frozen projection of real distance onto original finite PLAN.

    WORLD distance is the only varying comparison input: close WAIT cost
    is 2*risk_weight; far WAIT cost is 0; MOVE cost always 7.
    This is a deliberately fixed *caller* scoring policy, not an inferred
    general cognitive law. S35 doesn't automatically schedule distant probes.
    """
    if (
        not isinstance(native, NativeThreat)
        or not isinstance(retained, LearningPreferenceState)
        or type(expected_entity_id) is not int
        or expected_entity_id < 0
        or not isinstance(expected_session_id, str)
        or not expected_session_id
        or native.entity_id != expected_entity_id
        or native.observation.session_id != expected_session_id
        or native.observation.request_id != native.request_id
        or native.observation.provenance.source != "mineflayer"
        or native.observation.kind != "probe"
        or native.distance_m <= 0
        or native.distance_m > 16
        or retained.target_id != "risk_weight"
        or retained.revision != 1
        or retained.value != 4
    ):
        raise WorldChoiceRejected("exact live probe and frozen governed rev1 required")
    # Validate complete registry, exact request and real positional geometry
    # again through the existing S34 evidence validator.
    checked = _native_threat(
        native.observation, native.request_id,
        expected_entity_id=expected_entity_id,
    )
    if checked != native:
        raise WorldChoiceRejected("source-native distance or target mismatch")

    wait_score = (
        2 * retained.value if native.distance_m < MAX_GOAL_DISTANCE_M else 0
    )
    move_score = 7
    criterion = PlanningCriterion(
        "s42-fixed-native-distance-comparison", "comparison_score",
        PlanningDirection.MINIMIZE,
    )
    # Source attestation is attached to BOTH candidates, not a mere label
    # pasted on the selected output.
    source_ref = (
        f"native-session:{expected_session_id}",
        f"native-event-entity:{expected_entity_id}",
        f"native-probe:{native.request_id}:{native.observation.seq}",
        f"retained:risk_weight:revision:{retained.revision}",
    )
    candidates = (
        PlanCandidate(
            "WAIT", (PlanFeature("comparison_score", wait_score),),
            native.observation.provenance, source_refs=source_ref,
            source_provenance=(native.observation.provenance,),
        ),
        PlanCandidate(
            "MOVE_AWAY", (PlanFeature("comparison_score", move_score),),
            native.observation.provenance, source_refs=source_ref,
            source_provenance=(native.observation.provenance,),
            action_ref="MOVE_BACKWARD",
        ),
    )
    choice = select_plan(candidates, criterion)
    if choice.status is not PlanSelectionStatus.SELECTED or choice.selected is None:
        raise WorldChoiceRejected("ambiguous or incomparable World-conditioned plan")
    selection = WorldChoiceKind(choice.selected.candidate_id)
    if (
        (native.distance_m < MAX_GOAL_DISTANCE_M)
        != (selection is WorldChoiceKind.MOVE_AWAY)
    ):
        raise WorldChoiceRejected("World geometry did not determine required route")
    return WorldConditionedChoice(
        session_id=expected_session_id,
        entity_id=expected_entity_id,
        probe_seq=native.observation.seq,
        request_id=native.request_id,
        distance_m=native.distance_m,
        retained_target_id=retained.target_id,
        retained_revision=retained.revision,
        retained_value=retained.value,
        threshold_m=MAX_GOAL_DISTANCE_M,
        criterion_id=criterion.criterion_id,
        wait_score=wait_score,
        move_score=move_score,
        selection=selection,
        action_authorized=False,  # no PLAN itself authorizes Action
        provenance=native.observation.provenance,
    )


def verify_world_contrast(
    near: WorldConditionedChoice,
    far: WorldConditionedChoice,
) -> None:
    """Adjudicate paired same-session probes holding retained and policy fixed."""
    if (
        not isinstance(near, WorldConditionedChoice)
        or not isinstance(far, WorldConditionedChoice)
        or near.session_id != far.session_id
        or near.entity_id == far.entity_id
        or near.probe_seq == far.probe_seq
        or near.request_id == far.request_id
        or near.provenance == far.provenance
        or near.retained_target_id != far.retained_target_id
        or near.retained_revision != far.retained_revision
        or near.retained_value != far.retained_value
        or near.threshold_m != far.threshold_m
        or near.criterion_id != far.criterion_id
        or near.move_score != far.move_score
        or near.distance_m >= near.threshold_m
        or far.distance_m < far.threshold_m
        or near.selection is not WorldChoiceKind.MOVE_AWAY
        or far.selection is not WorldChoiceKind.WAIT
        or near.action_authorized
        or far.action_authorized
    ):
        raise WorldChoiceRejected("pair not one fixed-policy native World contrast")
