"""M #616: post-S-decision resource annotation, never a second chooser.

S has already returned an original WorldConditionedChoice through its owned
coordinator. This consumes that result and the independently produced B0
SelfBody readout for exactly the same native probe, without Action authority.
The B0 one-tick MOVE estimate is not an S49 trajectory or gait guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_b0_cognition import (
    B0CognitiveResourceView,
    B0TickResourceFact,
)
from relay_self.epoch_plan import PlannedDecisionEpochResult
from relay_self.learning import LearningPreferenceState
from relay_self.runtime_coordination import DecisionEpochResult
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldConditionedChoice,
    select_world_conditioned_choice,
)

Tension = Literal[
    "MOVE_MODEL_INSUFFICIENT",
    "MOVE_MODEL_AMBIGUOUS",
    "MOVE_MODEL_UNKNOWN",
    "NO_MODEL_TENSION",
]


@dataclass(frozen=True, slots=True)
class PostSEpochResourceObservation:
    """The S choice is retained even when the M model indicates tension."""

    s_epoch: DecisionEpochResult[object]
    body: B0CognitiveResourceView
    choice: WorldChoiceKind
    modeled_tension: Tension
    executed_work_ids: tuple[str, ...] = ()
    s_choice_kept: bool = True
    action_authority: bool = False
    action_issues: int = 0
    learning_updates: int = 0
    habit_grants: int = 0
    source_scope: str = "M_S_POST_EPOCH_B0_MODEL_ONLY_NO_ACTION_AUTHORITY"


def observe_completed_s_resource_epoch(
    s_epoch: DecisionEpochResult[object] | PlannedDecisionEpochResult,
    *,
    native: object,
    retained: LearningPreferenceState,
    body: B0CognitiveResourceView,
) -> PostSEpochResourceObservation:
    """Recheck S42's pure source-choice rule, *after* S coordination.

    A completed S result is required; no fresh coordinator or LLM call
    occurs. A prospective S49 Action deadline/timeout fails closed.
    The S42 MOVE_AWAY is compared to a generic B0 one-tick MOVE cost
    *only as an informational contrast*, not a gait-cost equivalence.
    S, not M, retains the original physical Action and learning owners.
    """
    ids: tuple[str, ...] = ()
    if isinstance(s_epoch, PlannedDecisionEpochResult):
        if (
            not isinstance(s_epoch.executed_work_ids, tuple)
            or not s_epoch.executed_work_ids
            or any(not isinstance(i, str) or not i for i in s_epoch.executed_work_ids)
            or len(set(s_epoch.executed_work_ids)) != len(s_epoch.executed_work_ids)
        ):
            raise ValueError("planned epoch has no actual executed cognition work")
        ids = s_epoch.executed_work_ids
        decision = s_epoch.decision
    elif isinstance(s_epoch, DecisionEpochResult):
        decision = s_epoch
    else:
        raise ValueError("typed original S epoch return required")

    if (
        not isinstance(decision, DecisionEpochResult)
        or decision.cognition_requested is not True
        or not isinstance(decision.cognition_result, WorldConditionedChoice)
        or not isinstance(decision.timed_out_actions, tuple)
        or decision.timed_out_actions
        or decision.next_action_deadline_ns is not None
    ):
        raise ValueError("S epoch incomplete, timed-out or action in-flight")
    choice = decision.cognition_result
    if (
        not isinstance(body, B0CognitiveResourceView)
        or body.source_scope != "B0_M0_OFFLINE_SIMULATION_NOT_S49_OR_WORLD_ATTESTED"
        or body.action_authority or body.action_issues
        or body.learning_updates or body.habit_grants
        or body.session_id != choice.session_id
        or body.native_seq != choice.probe_seq
        or body.native_source_ref != (
            f"native-probe:{choice.session_id}:{choice.probe_seq}:{choice.request_id}"
        )
        or not isinstance(body.facts, tuple)
        or len(body.facts) != 2
        or tuple(x.activity for x in body.facts) != ("WAIT", "MOVE")
        or any(not isinstance(x, B0TickResourceFact) for x in body.facts)
    ):
        raise ValueError("foreign, stale or action-bearing B0 SelfBody resource epoch")
    # NativeThreat is intentionally validated by S42, not reconstructed by M.
    if (
        not isinstance(retained, LearningPreferenceState)
        or getattr(native, "observation", None) is None
        or native.observation.session_id != choice.session_id
        or native.observation.seq != body.native_seq
        or native.observation.request_id != choice.request_id
        or native.observation.provenance != choice.provenance
        or choice.action_authorized
    ):
        raise ValueError("S42 source or original no-action choice not joined")
    try:
        checked = select_world_conditioned_choice(
            native, retained,
            expected_session_id=choice.session_id,
            expected_entity_id=choice.entity_id,
        )
    except ValueError as exc:
        raise ValueError("original S42 choice source validation rejected") from exc
    if checked != choice:
        raise ValueError("forged S42 choice or retained preference snapshot")
    if choice.selection is WorldChoiceKind.MOVE_AWAY:
        status = body.facts[1].affordability
        tension: Tension = {
            "MODEL_INSUFFICIENT": "MOVE_MODEL_INSUFFICIENT",
            "MODEL_AMBIGUOUS": "MOVE_MODEL_AMBIGUOUS",
            "UNKNOWN": "MOVE_MODEL_UNKNOWN",
            "MODEL_AFFORDABLE": "NO_MODEL_TENSION",
        }[status]
    else:
        tension = "NO_MODEL_TENSION"
    return PostSEpochResourceObservation(
        decision, body, choice.selection, tension, ids,
    )
