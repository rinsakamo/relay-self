"""Stage Q: DEV/OFFLINE single-owner L0-choice/S14-admission rehearsal.

This is NOT a second World driver, not original S49 owner installation, and not
independent authentication of the caller's S10 authority. It exercises the
original choice/ADMISSION implementations using one immutable qualified S10
successor, without issuing Actions or requesting a Minecraft runtime.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s34_native_world_cognition_ci import (
    NativeThreat,
    _native_epoch_two,
)
from adapters.mineflayer.self_world_epoch_handoff import StagePOfflineDualRead
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.learning import LearningPreferenceState
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldConditionedChoice,
    select_stage_q_dev_committed_world_choice,
)


class StageQDevBoundaryRejected(ValueError):
    """An identical owner/native source across both consumers was not proven."""


@dataclass(frozen=True, slots=True)
class StageQDevChoiceAdmission:
    """Identical retained and source; nonexecuting choice plus native S14."""

    choice: WorldConditionedChoice
    retained_revision: int
    retained_value: int
    exact_l0_s14_identity: bool
    exact_native_source_identity: bool
    s14_admission_status: str
    l0_selected_candidate: str
    s14_selected_candidate: str
    learning_grant_independently_attested: bool = False
    installed_in_original_s49: bool = False
    minecraft_action_issued: bool = False
    causal_learning_observed: bool = False


def stage_q_dev_joint_choice_admission(
    *,
    stage_p: StagePOfflineDualRead,
    previous_l0_owner: LearningPreferenceState,
    previous_s14_owner: LearningPreferenceState,
    native: NativeThreat,
    intent: IntentCommitment,
) -> StageQDevChoiceAdmission:
    """Take ONLY Stage P's one commit and next probe through original choice/S14.

    S49's legacy rev1-choice entrypoint stays intact. This DEV successor has
    to be explicitly passed; S14 reads the exact same newly committed object
    and uses its actual revision rather than the old hardcoded revision 1.
    """
    if not isinstance(stage_p, StagePOfflineDualRead):
        raise StageQDevBoundaryRejected("Stage P qualified dual-read missing")
    committed = stage_p.committed
    previous = committed.previous_state
    current = committed.new_state
    l0 = stage_p.l0_read.snapshot
    s14 = stage_p.s14_read.snapshot
    if (not isinstance(previous_l0_owner, LearningPreferenceState)
            or previous_l0_owner is not previous
            or previous_s14_owner is not previous
            or l0 is not current
            or s14 is not current
            or current is previous
            or current.last_update is not committed.record
            or previous.target_id != "risk_weight"
            or previous.revision != 1
            or previous.value != 4
            or current.revision != previous.revision + 1
            or current.value != previous.value  # Stage N HOLD, no reward
            or not stage_p.offline_only
            or stage_p.installed_in_original_s49
            or stage_p.real_world_commit_attested):
        raise StageQDevBoundaryRejected("different owner, unqualified rev2 or live promotion")
    if (not isinstance(native, NativeThreat)
            or not isinstance(native.observation, MineflayerObservation)
            or native.observation.seq != stage_p.following_native_seq
            or native.request_id != stage_p.following_request_id
            or native.observation.request_id != stage_p.following_request_id
            or native.observation.kind != "probe"
            or native.observation.provenance.source != "mineflayer"
            or not isinstance(intent, IntentCommitment)
            or intent.current is None
            or intent.current.intent_id != "escape-threat"):
        raise StageQDevBoundaryRejected("exact subsequent original native/intent missing")
    choice = select_stage_q_dev_committed_world_choice(
        native, current, commit=committed, original_owner=previous,
        expected_session_id=native.observation.session_id,
        expected_entity_id=native.entity_id,
    )
    if choice.selection is not WorldChoiceKind.MOVE_AWAY:
        raise StageQDevBoundaryRejected("no native near-threat MOVE to admit")
    values, epoch = _native_epoch_two(
        ActionSupervisor(), intent, current, current,
        expected_revision=current.revision, native=native,
    )
    s14_read = values["read"]
    plan = values["plan"]
    admission = values["admission"]
    if (epoch.cognition_requested
            or s14_read.snapshot is not current
            or s14_read.revision != choice.retained_revision
            or plan.selected is None
            or plan.selected.candidate_id != choice.selection.value
            or admission.status.value != "admitted"):
        raise StageQDevBoundaryRejected("native S14 and L0 did not accept same owner")
    return StageQDevChoiceAdmission(
        choice=choice,
        retained_revision=current.revision,
        retained_value=current.value,
        exact_l0_s14_identity=True,
        exact_native_source_identity=True,
        s14_admission_status=admission.status.value,
        l0_selected_candidate=choice.selection.value,
        s14_selected_candidate=plan.selected.candidate_id,
    )
