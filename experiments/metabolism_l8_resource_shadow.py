"""M/L8 cross-lane shadow: S retained choice + L1 proposal + B0 hint.

This is an M-owned *read-only* join. L8 computes and validates its own
experience-based proposal, S already returned the coordinator's choice, and M
already produced a B0 one-tick model annotation. This bridge rechecks the
L8 pure evidence comparison but never schedules cognition or issues Action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_s_epoch_resource import (
    PostSEpochResourceObservation,
    observe_completed_s_resource_epoch,
)

CandidateStatus = Literal[
    "MODEL_AFFORDABLE", "MODEL_INSUFFICIENT",
    "MODEL_AMBIGUOUS", "UNKNOWN", "NO_ADMISSIBLE_L1_CANDIDATE",
]


@dataclass(frozen=True, slots=True)
class SL8MResourceContrast:
    """No preference update and no inference of real physical cost."""

    s_epoch: object
    l8: object
    m_resource: PostSEpochResourceObservation
    s_choice_ref: str
    l1_shadow_ref: str | None
    l1_status: str
    original_probe_sha256: str
    l1_candidate_model_status: CandidateStatus
    s_model_tension: str
    s_choice_kept: bool = True
    action_authority: bool = False
    action_issues: int = 0
    learning_updates: int = 0
    habit_grants: int = 0
    source_scope: str = "M_L8_POST_S_EPOCH_SHADOW_NOT_NATIVE_ATTESTATION"


def contrast_l8_with_m_resource(
    l8_observation: object,
    m_observation: PostSEpochResourceObservation,
    *,
    native: object,
    retained: object,
    learning: object,
    retention_enabled: bool,
) -> SL8MResourceContrast:
    """Revalidate L8's original same-source comparison; S choice is immutable.

    The M B0 owner tick and L8's S-assigned source revision are independent
    clocks. They must NEVER be equated. The S epoch identity and original
    native probe/session/sequence/provenance are the join boundaries instead.

    The B0 one-tick generic MOVE estimate is NOT verified S49 MOVE_AWAY
    displacement cost. The result is not an instruction to pick WAIT/MOVE.
    """
    # L8 is an independent owner branch: import its typed read-only API only
    # inside this optional experimental seam, never in M standalone imports.
    from relay_self.epoch_plan import PlannedDecisionEpochResult
    from relay_self.l1_epoch_observer import (
        SEpochL1Observation,
        SEpochObservationRejected,
        observe_s_epoch_l1,
    )
    from relay_self.l1_s_choice_shadow import SChoiceContrastStatus
    from relay_self.learning_epoch import LearningEpochResult

    if (
        not isinstance(l8_observation, SEpochL1Observation)
        or not isinstance(m_observation, PostSEpochResourceObservation)
        or not isinstance(learning, LearningEpochResult)
        or type(retention_enabled) is not bool
        or l8_observation.s_epoch is not m_observation.s_epoch
        or l8_observation.action_authority
        or l8_observation.action_issues
        or l8_observation.learning_updates
        or l8_observation.habit_grants
        or m_observation.action_authority
        or m_observation.action_issues
        or m_observation.learning_updates
        or m_observation.habit_grants
        or not m_observation.s_choice_kept
        or m_observation.source_scope
        != "M_S_POST_EPOCH_B0_MODEL_ONLY_NO_ACTION_AUTHORITY"
        or l8_observation.planned_work_ids != m_observation.executed_work_ids
    ):
        raise ValueError("foreign, action-bearing or nonidentical S/L8/M epoch")

    # L8 stores the inner original S decision; planned work IDs are
    # separately retained. Replay its pure observer with the *same* planned
    # boundary rather than discarding IDs and falsely rejecting completion.
    l8_source = l8_observation.s_epoch
    if l8_observation.planned_work_ids:
        l8_source = PlannedDecisionEpochResult(
            l8_source, l8_observation.planned_work_ids, ()
        )
    try:
        rechecked = observe_s_epoch_l1(
            l8_source,
            native=native,
            retained=retained,
            learning=learning,
            retention_enabled=retention_enabled,
        )
    except (SEpochObservationRejected, ValueError) as exc:
        raise ValueError("L8 source/admission or S replay verification failed") from exc
    if rechecked != l8_observation:
        raise ValueError("counterfeit or unadmitted L8 shadow observation")

    choice = l8_observation.s_epoch.cognition_result
    b0 = m_observation.body
    if (
        not isinstance(b0.owner_tick, int)
        or isinstance(b0.owner_tick, bool)
        or b0.owner_tick < 0
        or b0.owner_sensor_ref != (
            f"{choice.session_id}:{b0.owner_tick}:{choice.probe_seq}:"
            f"{choice.request_id}"
        )
    ):
        raise ValueError("M B0 owner source/tick link malformed")
    # Re-evaluate the *pure* M post-S source/choice verification.
    # In planned mode the original L8/M executed IDs must already agree.
    m_source = m_observation.s_epoch
    if m_observation.executed_work_ids:
        m_source = PlannedDecisionEpochResult(
            m_observation.s_epoch, m_observation.executed_work_ids, ()
        )
    reread_m = observe_completed_s_resource_epoch(
        m_source, native=native, retained=retained, body=b0,
    )
    if reread_m != m_observation:
        raise ValueError("counterfeit M resource tension, S choice or owner source")
    comparison = l8_observation.comparison
    if (
        comparison.s_choice.value != m_observation.choice.value
        or choice.selection.value != comparison.s_choice.value
        or comparison.s_session_id != m_observation.body.session_id
        or comparison.probe_seq != m_observation.body.native_seq
        or comparison.probe_seq != choice.probe_seq
        or not isinstance(comparison.original_probe_sha256, str)
        or len(comparison.original_probe_sha256) != 64
        or comparison.original_probe_sha256
        not in learning.admitted_current_probe_sha256
        or not comparison.s_choice_kept
        or comparison.action_authority
        or comparison.action_issues
        or comparison.learning_updates
        or comparison.habit_grants
        or not isinstance(comparison.status, SChoiceContrastStatus)
        or comparison.candidate_differs != (
            comparison.l1_shadow_ref is not None
            and comparison.l1_shadow_ref != choice.selection.value
        )
        or m_observation.body.native_source_ref != (
            f"native-probe:{choice.session_id}:{choice.probe_seq}:"
            f"{choice.request_id}"
        )
    ):
        raise ValueError("L8/M candidate, digest, choice or source mismatch")

    if comparison.l1_shadow_ref is None:
        candidate_status: CandidateStatus = "NO_ADMISSIBLE_L1_CANDIDATE"
    else:
        # L8 accepts ONLY its finite WAIT/MOVE_AWAY proposals. This index
        # mapping is explicitly B0 generic 1-tick cost, NOT a G4/S49 gait.
        if comparison.l1_shadow_ref == "WAIT":
            index = 0
        elif comparison.l1_shadow_ref == "MOVE_AWAY":
            index = 1
        else:
            raise ValueError("L8 proposed unrecognized action reference")
        candidate_status = m_observation.body.facts[index].affordability

    return SL8MResourceContrast(
        s_epoch=l8_observation.s_epoch,
        l8=l8_observation,
        m_resource=m_observation,
        s_choice_ref=choice.selection.value,
        l1_shadow_ref=comparison.l1_shadow_ref,
        l1_status=comparison.status.value,
        original_probe_sha256=comparison.original_probe_sha256,
        l1_candidate_model_status=candidate_status,
        s_model_tension=m_observation.modeled_tension,
    )
