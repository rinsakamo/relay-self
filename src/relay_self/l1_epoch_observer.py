"""L8: read the *returned* S decision-epoch result, never run a new epoch.

Owner S remains responsible for calling its existing coordinator, observing
World/Action originals and issuing any physical Action. L only consumes the
typed completed output and compares it to an L7 next-epoch shadow candidate.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.s34_native_world_cognition_ci import NativeThreat
from relay_self.epoch_plan import PlannedDecisionEpochResult
from relay_self.l1_s_choice_shadow import (
    SChoiceContrast,
    SChoiceShadowRejected,
    compare_s_choice_with_l1,
)
from relay_self.learning import LearningPreferenceState
from relay_self.learning_epoch import LearningEpochResult
from relay_self.runtime_coordination import DecisionEpochResult
from relay_self.world_conditioned_choice import WorldConditionedChoice


class SEpochObservationRejected(ValueError):
    """S did not return an admitted, completed, quiescent decision to compare."""


@dataclass(frozen=True, slots=True)
class SEpochL1Observation:
    """Read-only contrast; does not modify the S result or issue an Action."""

    s_epoch: DecisionEpochResult[object]
    comparison: SChoiceContrast
    planned_work_ids: tuple[str, ...] = ()
    action_issues: int = 0
    learning_updates: int = 0
    habit_grants: int = 0
    action_authority: bool = False


def observe_s_epoch_l1(
    s_epoch: DecisionEpochResult[object] | PlannedDecisionEpochResult,
    *,
    native: NativeThreat,
    retained: LearningPreferenceState,
    learning: LearningEpochResult,
    retention_enabled: bool,
) -> SEpochL1Observation:
    """Observe an existing S-produced result, never schedule/evaluate it again.

    The S-owned coordinator was already invoked by its caller. Refuse missing
    cognition, deadline-bearing in-flight Action, or a timeout/UNKNOWN in this
    epoch before considering L1. Both raw and planned S coordinator results
    use the same original DecisionEpochResult and the L7 S42 replay check.

    This is not independent authentication of original Minecraft bytes:
    S/R/V must qualify inputs and Goal receipts before any live integration.
    """
    planned_ids: tuple[str, ...] = ()
    if isinstance(s_epoch, PlannedDecisionEpochResult):
        if not s_epoch.executed_work_ids:
            raise SEpochObservationRejected("planned cognition work was not executed")
        planned_ids = s_epoch.executed_work_ids
        decision = s_epoch.decision
    elif isinstance(s_epoch, DecisionEpochResult):
        decision = s_epoch
    else:
        raise SEpochObservationRejected("existing typed S coordinator result required")

    if (
        not isinstance(decision, DecisionEpochResult)
        or decision.cognition_requested is not True
        or not isinstance(decision.cognition_result, WorldConditionedChoice)
        or not isinstance(decision.timed_out_actions, tuple)
        or decision.timed_out_actions
        or decision.next_action_deadline_ns is not None
    ):
        raise SEpochObservationRejected(
            "S cognition did not finish with a quiescent World choice"
        )
    try:
        contrast = compare_s_choice_with_l1(
            native=native,
            retained=retained,
            s_choice=decision.cognition_result,
            learning=learning,
            retention_enabled=retention_enabled,
        )
    except SChoiceShadowRejected as exc:
        raise SEpochObservationRejected("S epoch/L1 source or choice mismatch") from exc
    return SEpochL1Observation(
        s_epoch=decision,
        comparison=contrast,
        planned_work_ids=planned_ids,
    )
