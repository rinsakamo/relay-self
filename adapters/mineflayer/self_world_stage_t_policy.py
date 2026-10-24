"""Stage T DEV/OFFLINE joint *original L0 host* and original S14 policy preview.

Not a new execution owner; never calls NormalSessionActionExecutor, issues a
World Action, mints an S10 grant, or proves scientific causality.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s34_native_world_cognition_ci import (
    S34EvidenceFailure,
    _native_epoch_two,
    _native_threat,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    select_world_conditioned_choice,
    verify_stage_t_dev_directional_commit,
)


class StageTDevJointRejected(ValueError):
    """No exact original L0 S17/S10 successor and S14 joint admission."""


@dataclass(frozen=True, slots=True)
class StageTDevJointPreview:
    session_id: str
    original_revision: int
    committed_revision: int
    retained_value: int
    original_l0_candidate: str
    new_l0_candidate: str
    new_s14_candidate: str
    s14_admission: str
    l0_and_s14_same_owner_identity: bool
    policy_choice_changed: bool
    new_action_request_created: bool = False
    actual_action_issued: bool = False
    issuer_independently_attested: bool = False
    scientific_on_off_sham_confirmed: bool = False
    physical_world_ran: bool = False


def preview_stage_t_joint_original_owner(
    *, host: NormalWorldL0, event: MineflayerObservation,
    probe: MineflayerObservation, intent: IntentCommitment,
) -> StageTDevJointPreview:
    """Re-run actual original host choice and existing S14; no side effects."""
    if (not isinstance(host, NormalWorldL0)
            or not isinstance(event, MineflayerObservation)
            or not isinstance(probe, MineflayerObservation)
            or not isinstance(intent, IntentCommitment)
            or intent.current_intent is None
            or intent.current_intent.intent_id != host.intent_id
            or event.session_id != host.session_id
            or probe.session_id != host.session_id
            or probe.seq <= event.seq
            or host._stage_r_dev_token is not None
            or host._stage_t_dev_commit is None
            or host._stage_t_dev_s17 is None):
        raise StageTDevJointRejected("original S49 DEV alternate-owner intent required")
    commit = host._stage_t_dev_commit
    s17 = host._stage_t_dev_s17
    state = verify_stage_t_dev_directional_commit(
        commit, commit.previous_state, s17,
    )
    if host.retained is not state:
        raise StageTDevJointRejected("original L0 and S10 successor diverged")
    before_events, before_actions = host.events, host.action_requests
    target_ids = [
        e.entity_id for e in probe.snapshot.nearby_entities
        if e.name == "zombie"
    ]
    if len(target_ids) != 1 or not isinstance(probe.request_id, str):
        raise StageTDevJointRejected("exact one correlated native zombie required")
    try:
        actual = _native_threat(
            probe, probe.request_id, expected_entity_id=target_ids[0],
        )
        l0 = host._check(event, probe)
        original = select_world_conditioned_choice(
            actual, commit.previous_state,
            expected_session_id=host.session_id,
            expected_entity_id=actual.entity_id,
        )
        values, epoch = _native_epoch_two(
            ActionSupervisor(), intent, state, state,
            expected_revision=state.revision, native=actual,
        )
    except (S34EvidenceFailure, ValueError, AssertionError) as exc:
        raise StageTDevJointRejected(
            "original native evidence or S14 admission rejected"
        ) from exc
    plan, admission, read = values["plan"], values["admission"], values["read"]
    if (epoch.cognition_requested
            or read.snapshot is not state
            or read.revision != l0.retained_revision
            or plan.selected is None
            or plan.selected.candidate_id != l0.selection.value
            or admission.status.value != "admitted"
            or l0.action_authorized
            or host.events != before_events
            or host.action_requests != before_actions):
        raise StageTDevJointRejected("original S42 alternate L0 and native S14 disagree")
    if (state.value == 3 and l0.selection is not WorldChoiceKind.WAIT
            or state.value == 5 and l0.selection is not WorldChoiceKind.MOVE_AWAY):
        raise StageTDevJointRejected("Stage T policy did not discriminate current outcome")
    return StageTDevJointPreview(
        session_id=host.session_id,
        original_revision=commit.previous_state.revision,
        committed_revision=state.revision,
        retained_value=state.value,
        original_l0_candidate=original.selection.value,
        new_l0_candidate=l0.selection.value,
        new_s14_candidate=plan.selected.candidate_id,
        s14_admission=admission.status.value,
        l0_and_s14_same_owner_identity=True,
        policy_choice_changed=original.selection is not l0.selection,
    )
