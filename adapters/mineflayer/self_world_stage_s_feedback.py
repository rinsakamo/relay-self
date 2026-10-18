"""Stage S: PREDECLARED source-grounded near-threat separation feedback.

Pure, offline DEV measurement. Exact typed native S49 S16 terminal and
same zombie ID across original/before/after observations are necessary.
Positive distance change is NOT a survival reward, memory authority, or a
prediction-match signal. No action/epoch/learning owner is mutated.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.normal_action import NormalActionClosedReadback
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.learning import FeedbackDirection
from relay_self.provenance import Provenance


class StageSFeedbackRejected(ValueError):
    """Counterfeit, replayed, ambiguous or geometrically inconsistent evidence."""


class StageSSeparationClass(str, Enum):
    SEPARATION_INCREASED = "separation_increased"
    SEPARATION_DECREASED = "separation_decreased"
    NO_RESOLVED_CHANGE = "no_resolved_change"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class StageSPredeclaredSeparationRule:
    """Fixed before outcome: ±0.100 m net same-target separation change.

    A separation increase supports INCREASE of risk_weight *only* as a
    candidate local MOVE preference update; it cannot certify fitness.
    A separation decrease suggests DECREASE; unresolved small changes HOLD.
    Missing/incomplete observations ABSTAIN and never mint S17 feedback.
    """

    criterion_name: str = "stage-s-same-target-separation-v0"
    target_id: str = "risk_weight"
    delta_m: float = 0.1
    min_motion_m: float = 0.05
    source_scope: str = "mineflayer_entity_registry"

    def __post_init__(self) -> None:
        if (self.criterion_name != "stage-s-same-target-separation-v0"
                or self.target_id != "risk_weight"
                or type(self.delta_m) is not float or self.delta_m != 0.1
                or type(self.min_motion_m) is not float
                or self.min_motion_m != 0.05
                or self.source_scope != "mineflayer_entity_registry"):
            raise StageSFeedbackRejected("Stage S criterion must be fixed before evidence")


@dataclass(frozen=True, slots=True)
class StageSSeparationAssessment:
    status: StageSSeparationClass
    reason_code: str
    session_id: str
    action_id: str
    entity_id: int | None
    distance_before_m: float | None
    distance_after_m: float | None
    distance_delta_m: float | None
    direction: FeedbackDirection | None
    typed_s17: LearningFeedbackInterpretation | None
    readonly: bool = True
    s10_authority_issued: bool = False
    s10_committed: bool = False
    action_issued: bool = False
    claimed_survival_gain: bool = False


def _require_complete_registry(
    reading: MineflayerObservation, rule: StageSPredeclaredSeparationRule,
) -> None:
    coverage = reading.snapshot.nearby_entities_coverage
    if (coverage.truncated or coverage.source_scope != rule.source_scope
            or coverage.candidate_count != len(reading.snapshot.nearby_entities)
            or coverage.max_distance != 16):
        raise StageSFeedbackRejected("native registry scope or completeness lost")


def _distance_to_target(
    reading: MineflayerObservation, entity_id: int, rule: StageSPredeclaredSeparationRule,
) -> float | None:
    _require_complete_registry(reading, rule)
    snap = reading.snapshot
    coverage = snap.nearby_entities_coverage
    candidates = [e for e in snap.nearby_entities
                  if e.entity_id == entity_id and e.name == "zombie"]
    if len(candidates) > 1:
        raise StageSFeedbackRejected("duplicate target zombie identity")
    if not candidates:
        return None
    e = candidates[0]
    p, target = snap.position, e.position
    calculated = math.dist((p.x, p.y, p.z), (target.x, target.y, target.z))
    if (not math.isfinite(calculated) or calculated <= 0
            or calculated > coverage.max_distance
            or not math.isclose(calculated, e.distance, rel_tol=0, abs_tol=1e-6)):
        raise StageSFeedbackRejected("native target distance is not positional geometry")
    return calculated


def assess_stage_s_original_separation(
    witness: NormalActionClosedReadback,
    rule: StageSPredeclaredSeparationRule,
) -> StageSSeparationAssessment:
    """Apply fixed rule to original typed S49 Action and BEFORE/AFTER World.

    An outcome is not learned merely because the command executed. This
    function neither holds nor fabricates missing target observations.
    """
    if not isinstance(witness, NormalActionClosedReadback):
        raise StageSFeedbackRejected("exact original typed S49 closure required")
    if not isinstance(rule, StageSPredeclaredSeparationRule):
        raise StageSFeedbackRejected("predeclared immutable criterion required")
    terminal, outcome, world, original = (
        witness.terminal, witness.interpretation,
        witness.consequence, witness.original_probe,
    )
    sid, action = original.session_id, terminal.action_id
    if not action.startswith("s49-native-move-"):
        raise StageSFeedbackRejected("Action not bound to original S49")
    event = action.removeprefix("s49-native-move-")
    if (not event.isdecimal()
            or original.kind != "probe"
            or original.provenance.source != "mineflayer"
            or original.request_id != f"s49-actual:{sid}:event-{event}"
            or outcome.action_id != action or world.action_id != action
            or outcome.session_id != sid or world.session_id != sid
            or outcome.binding_id != world.binding_id
            or outcome.binding_id != f"s49-binding-{event}"
            or outcome.action_ref != "MOVE_BACKWARD"
            or outcome.reason_code != "observed_execution"
            or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
            or terminal.state is not ActionState.OUTCOME
            or world.status.value != "executed"
            or world.before_observation is None
            or world.after_observation is None
            or world.movement_distance is None
            or world.movement_distance < rule.min_motion_m):
        raise StageSFeedbackRejected("genuine terminal/S16 execution lineage absent")
    before, after = world.before_observation, world.after_observation
    if (before.session_id != sid or after.session_id != sid
            or not original.seq < before.seq < after.seq
            or before.provenance.source != "mineflayer"
            or after.provenance.source != "mineflayer"):
        raise StageSFeedbackRejected("foreign or noncausal native execution frames")
    _require_complete_registry(original, rule)
    _require_complete_registry(before, rule)
    _require_complete_registry(after, rule)
    old_pos, new_pos = before.snapshot.position, after.snapshot.position
    observed_motion = math.hypot(new_pos.x - old_pos.x, new_pos.z - old_pos.z)
    if not math.isclose(observed_motion, world.movement_distance, rel_tol=0, abs_tol=1e-6):
        raise StageSFeedbackRejected("claimed movement differs from native positions")
    target = [e for e in original.snapshot.nearby_entities if e.name == "zombie"]
    if len(target) != 1 or target[0].entity_id < 0:
        return StageSSeparationAssessment(
            StageSSeparationClass.UNDETERMINED,
            "original_target_missing_or_ambiguous", sid, action,
            None, None, None, None, None, None,
        )
    entity_id = target[0].entity_id
    # The initiating S49 probe and actual executor before-frame are
    # different sources. The exact original target must be visible in BOTH.
    original_distance = _distance_to_target(original, entity_id, rule)
    distance_before = _distance_to_target(before, entity_id, rule)
    distance_after = _distance_to_target(after, entity_id, rule)
    if (original_distance is None or distance_before is None
            or distance_after is None):
        return StageSSeparationAssessment(
            StageSSeparationClass.UNDETERMINED,
            "same_target_missing_from_native_before_after", sid, action,
            entity_id, distance_before, distance_after, None, None, None,
        )
    delta = distance_after - distance_before
    if delta >= rule.delta_m:
        kind, direction = StageSSeparationClass.SEPARATION_INCREASED, FeedbackDirection.INCREASE
    elif delta <= -rule.delta_m:
        kind, direction = StageSSeparationClass.SEPARATION_DECREASED, FeedbackDirection.DECREASE
    else:
        kind, direction = StageSSeparationClass.NO_RESOLVED_CHANGE, FeedbackDirection.HOLD
    # The direction mapping is frozen in StageSPredeclaredSeparationRule,
    # not chosen ad hoc by model output or a SelfWorld prediction label.
    criterion = ActionFeedbackCriterion(
        criterion_id=f"{rule.criterion_name}:{sid}:{event}:{kind.value}",
        target_id=rule.target_id,
        required_action_id=action,
        required_binding_id=outcome.binding_id,
        required_action_ref="MOVE_BACKWARD",
        required_action_state=ActionState.OUTCOME,
        required_outcome_disposition=ActionOutcomeDisposition.OUTCOME,
        required_outcome_reason="observed_execution",
        feedback_direction=direction,
        provenance=Provenance(
            "stage-s-dev-preregistered-outcome-separation", rule.criterion_name,
        ),
    )
    typed = interpret_action_outcome_as_learning_feedback(
        terminal, outcome, criterion,
        provenance=Provenance("stage-s-observed-world-only", f"{sid}:{action}"),
    )
    if (typed.status is not LearningFeedbackInterpretationStatus.PRODUCED
            or typed.feedback is None or typed.feedback.direction is not direction):
        raise StageSFeedbackRejected("S17 did not confirm same source criterion")
    return StageSSeparationAssessment(
        kind, "same_target_distance_geometry", sid, action, entity_id,
        distance_before, distance_after, delta, direction, typed,
    )
