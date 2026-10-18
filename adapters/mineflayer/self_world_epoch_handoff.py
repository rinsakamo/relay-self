"""Stage P: OFFLINE owner/dual-consumer retained epoch-boundary rehearsal.

This is a pure preparation of a S10-authorized immutable snapshot for BOTH
L0 and S14. It does not install the snapshot in the frozen S49 host, issue
an Action, authenticate the caller's authority issuer, or attest a physical
World epoch. Stage P cannot be promoted until the original S49 fixed-rev1
L0 criterion and the independent S14 closure are migrated together.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action_feedback import (
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
)
from relay_self.epoch_continuation import (
    RetainedPreferenceRead,
    read_retained_preference,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningCommitResult,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateProposal,
    commit_learning_update,
)
from relay_self.provenance import Provenance


class StagePEpochRejected(ValueError):
    """No exact, properly sequenced common snapshot for the next epoch."""


@dataclass(frozen=True, slots=True)
class StagePOfflineDualRead:
    """One possible next-state, two EXACT reads; not a live owner transfer."""

    committed: LearningCommitResult
    l0_read: RetainedPreferenceRead
    s14_read: RetainedPreferenceRead
    following_native_seq: int
    following_request_id: str
    following_native_observation: MineflayerObservation
    offline_only: bool = True
    real_world_commit_attested: bool = False
    installed_in_original_s49: bool = False
    actual_next_action_changed: bool = False


def prepare_stage_p_offline_dual_read(
    *,
    previous_owner: LearningPreferenceState,
    current_l0_owner: LearningPreferenceState,
    current_s14_owner: LearningPreferenceState,
    interpretation: LearningFeedbackInterpretation,
    proposal: LearningUpdateProposal,
    authority: LearningUpdateAuthority | None,
    original_session_id: str,
    after_action_native_seq: int,
    next_probe: MineflayerObservation | None,
    provenance: Provenance,
) -> StagePOfflineDualRead:
    """Rehearse S10 commit and synchronised reads without modifying S49.

    A valid explicit S10 authority must be provided by the caller; S10's
    existing validator owns the actual transition. The positive test grant
    is expressly synthetic, not proof of a live owner-authority handoff.
    The next native source must be later than the observed physical outcome.
    """
    if (not isinstance(previous_owner, LearningPreferenceState)
            or current_l0_owner is not previous_owner
            or current_s14_owner is not previous_owner):
        raise StagePEpochRejected("previous L0 and S14 must share exact current owner")
    if (not isinstance(original_session_id, str) or not original_session_id
            or type(after_action_native_seq) is not int
            or after_action_native_seq < 0
            or not isinstance(next_probe, MineflayerObservation)
            or next_probe.session_id != original_session_id
            or next_probe.kind != "probe"
            or next_probe.provenance.source != "mineflayer"
            or next_probe.seq <= after_action_native_seq
            or not isinstance(next_probe.request_id, str)
            or not next_probe.request_id.startswith(
                f"s49-actual:{original_session_id}:event-"
            )
            or not next_probe.request_id.split("event-", 1)[-1].isdecimal()):
        raise StagePEpochRejected("newer same-session correlated native probe missing")
    # An event-number string is not a qualified later source if it refers
    # to an earlier Action or even a future event after this probe.
    following_event_seq = int(next_probe.request_id.rsplit("event-", 1)[-1])
    if not after_action_native_seq < following_event_seq < next_probe.seq:
        raise StagePEpochRejected("next native event/probe ordering not causal")
    if (not isinstance(interpretation, LearningFeedbackInterpretation)
            or interpretation.status is not LearningFeedbackInterpretationStatus.PRODUCED
            or interpretation.feedback is None
            or interpretation.feedback.direction is not FeedbackDirection.HOLD
            or not isinstance(proposal, LearningUpdateProposal)
            or proposal.feedback is not interpretation.feedback
            or proposal.target_id != previous_owner.target_id
            or interpretation.target_id != previous_owner.target_id
            or interpretation.outcome_reason != "observed_execution"
            or interpretation.action_ref != "MOVE_BACKWARD"
            or not interpretation.action_id.startswith("s49-native-move-")
            or interpretation.provenance.source != "stage-n-native-typed-closure"
            or interpretation.provenance.reference != (
                f"{original_session_id}:{interpretation.action_id}"
            )
            or interpretation.outcome_ref is None
            or not interpretation.outcome_ref.endswith(
                f":{original_session_id}:observed_execution"
            )):
        raise StagePEpochRejected("original typed S17 HOLD source/proposal mismatch")
    suffix = interpretation.action_id.removeprefix("s49-native-move-")
    if (not suffix.isdecimal()
            or interpretation.binding_id != f"s49-binding-{suffix}"
            or interpretation.criterion_provenance != Provenance(
                "stage-n-dev-predeclared", "actual-move-execution-only",
            )
            or interpretation.outcome_ref != (
                f"action-outcome:{interpretation.action_id}:"
                f"s49-binding-{suffix}:{original_session_id}:observed_execution"
            )):
        raise StagePEpochRejected("foreign S49 binding or S17 evaluation policy")
    if not isinstance(provenance, Provenance):
        raise StagePEpochRejected("audit provenance required")
    committed = commit_learning_update(
        previous_owner, proposal, authority, provenance=provenance,
    )
    next_owner = committed.new_state
    if (committed.previous_state is not previous_owner
            or committed.new_state is previous_owner
            or next_owner.revision != previous_owner.revision + 1
            or next_owner.value != previous_owner.value
            or next_owner.last_update is not committed.record):
        raise StagePEpochRejected("no exact governed HOLD next snapshot")
    # The two reads must refer to one and the SAME new committed object.
    l0 = read_retained_preference(
        next_owner, next_owner, required_target_id=previous_owner.target_id,
        expected_revision=next_owner.revision, provenance=provenance,
    )
    s14 = read_retained_preference(
        next_owner, next_owner, required_target_id=previous_owner.target_id,
        expected_revision=next_owner.revision, provenance=provenance,
    )
    if l0.snapshot is not s14.snapshot or l0.snapshot is not next_owner:
        raise StagePEpochRejected("split L0/S14 next owner")
    return StagePOfflineDualRead(
        committed=committed, l0_read=l0, s14_read=s14,
        following_native_seq=next_probe.seq,
        following_request_id=next_probe.request_id,
        following_native_observation=next_probe,
    )
