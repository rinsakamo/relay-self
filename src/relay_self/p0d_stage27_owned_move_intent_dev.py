"""Stage27a: real Stage26 READY -> ORIGINAL Self Intent/Skill, no motor.

The Stage26 operator-template target is a WORLD PLACE one metre east.
The installed native MOVE issuer accepts only RELATIVE forward/back/left/right.
This handoff deliberately does not turn PLACE into an invented direction or
bypass FiniteSkillInterpreter's parameterized-issuer block. A subsequent
source-qualified WorldBody Target resolver and native issuer are required.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.checkpointed_cognitive_runtime_dev import (
    LiveCognitionCheckpointError,
)
from relay_self.cognitive_minimal_dev import Option
from relay_self.p0d_stage26_gemma_l1_dev import (
    PreparedStage26L1,
    RealGemmaChoiceWitness,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, DecisionStatus, ProviderDecision
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillInvocation


class Stage27MoveHandoffRefusal(RuntimeError):
    """A fresh original Self decision has not earned an Intent/Skill transition."""


@dataclass(frozen=True, slots=True)
class Stage27OwnedMoveIntent:
    self_id: str
    native_session_id: str
    world_epoch: int
    decision_request_id: str
    decision_number: str
    rechecked_native_seq: int
    intent_id: str
    skill_execution_id: str
    invocation_ref: str
    preset_ref: str
    target_ref: str
    target_kind: str
    outcome: str = "INTENT_STARTED_TARGET_RESOLUTION_REQUIRED"
    target_resolution_attested: bool = False
    physical_proposal_authorized: bool = False
    physical_action_issued: bool = False
    wal_modified: bool = False
    peer_owner_mutated: bool = False


def begin_stage27_owned_move_intent(
    prepared: PreparedStage26L1,
    *,
    ticket: ResidentInferenceTicket,
    witness: RealGemmaChoiceWitness,
    refreshed: MineflayerObservation,
    lane: ResidentLlamaInferenceLane,
    physical: PhysicalIssueAdmission,
    actor_self_id: str,
    at_ns: int,
    provenance: Provenance,
) -> Stage27OwnedMoveIntent:
    """Make *one* real owned Intent/Skill from an attested bounded decision.

    The target remains PLACE; no Action, ActionPort proposal, native command,
    SkillCursor or inferred MOVE direction is emitted by this entry point.
    Other Self identities are never touched.
    """
    if (
        not isinstance(prepared, PreparedStage26L1)
        or not isinstance(ticket, ResidentInferenceTicket)
        or not isinstance(witness, RealGemmaChoiceWitness)
        or not isinstance(refreshed, MineflayerObservation)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(provenance, Provenance)
        or type(at_ns) is not int or at_ns <= 0
        or type(actor_self_id) is not str
        or actor_self_id != prepared.self_id
        or actor_self_id != witness.self_id
        or actor_self_id != ticket.self_id
        or lane.cognitive_work.owners.get(actor_self_id) is not prepared.original_owner
    ):
        raise Stage27MoveHandoffRefusal("original Self/owner/clock identity missing")
    owner = prepared.original_owner
    option = prepared.round.frame.options
    if len(option) != 1 or not isinstance(option[0], Option):
        raise Stage27MoveHandoffRefusal("exactly one completed original option required")
    selected = option[0]
    invocation = selected.invocation
    if not isinstance(invocation, SkillInvocation):
        raise Stage27MoveHandoffRefusal("accepted parameterized MOVE invocation absent")
    if (
        witness.selected_number != "1"
        or witness.l1_status != "READY"
        or witness.available_numbered_choices != ("1", "2", "3")
        or witness.selection_is_action_permission
        or witness.issued_native_effect
        or witness.old_gpu_result_reused
        or witness.old_intent_resumed
        or witness.provider_kind != "REAL_LLAMA_CPP_BOUNDED_PROVIDER_NOT_SCRIPTED"
        or not witness.backend_slot_idle_after_call
        or witness.inference_request_id != ticket.request_id
        or ticket.request_id != prepared.round.request.request_id
        or ticket.mode is not CognitionMode.BOUNDED
        or ticket.native_session_id != prepared.native_session
        or ticket.world_epoch != prepared.world_epoch
        or witness.new_native_session_id != prepared.native_session
        or witness.former_native_session_id != prepared.original_native_session
        or witness.world_epoch != prepared.world_epoch
        or witness.recheck_native_seq != refreshed.seq
        or witness.recheck_probe_id != refreshed.request_id
        or witness.first_probe_id != prepared.first_probe.request_id
        or witness.first_native_seq != prepared.first_probe.seq
        or refreshed.kind != "probe"
        or not refreshed.request_id
        or refreshed.session_id != prepared.native_session
        or refreshed.seq <= prepared.first_probe.seq
        or refreshed.snapshot.health <= 0
        or refreshed.snapshot.time is None
        or refreshed.snapshot.oxygen_level == 0
        or witness.preset_ref != invocation.parameter_preset_ref
        or witness.candidate_invocation_ref != invocation.invocation_ref
        or witness.target_contract_ref
        != prepared.original_target.arrival_contract.contract_ref
        or witness.registry_revision != prepared.registry_revision
        or selected.skill_id != "MOVE"
        or selected.skill_version != 1
        or selected.target_kind != "DESTINATION"
        or invocation.target.kind != selected.target_kind
        or invocation.target.ref != selected.target_ref
        or invocation.target.contract != selected.arrival_contract
        or invocation.scope != prepared.round.frame.scope
        or not invocation.parameter_preset_ref
    ):
        raise Stage27MoveHandoffRefusal("Stage26 original READY source or PLACE target mismatch")
    try:
        scope = lane.cognitive_work.current_scope(actor_self_id)
        decision = lane.result(ticket)
        receipt = lane.provider.stage26_raw_receipt(ticket.request_id)
    except (RuntimeError, ValueError, OSError, KeyError) as exc:
        raise Stage27MoveHandoffRefusal(
            "live original model source no longer owned by this Self"
        ) from exc
    if (
        scope[1:] != (prepared.native_session, prepared.world_epoch)
        or not isinstance(decision, ProviderDecision)
        or decision.status is not DecisionStatus.RESOLVED
        or decision.choice_id != "1"
        or receipt.response_sha256 != witness.original_http_response_sha256
        or receipt.request_sha256 != witness.original_http_request_sha256
        or receipt.response_path != witness.original_http_response_path
        or receipt.request_path != witness.original_http_request_path
        or decision.call_facts.finish_reason != "stop"
        or not witness.provider_call_facts
        or owner.native_session_id != prepared.native_session
        or owner.self_id != actor_self_id
        or owner.fresh_native_observation_required
        or owner.retained != prepared.restored.retained
        or owner.pattern_registry != prepared.restored.semantic.pattern_registry
        or physical.current_native_sessions.get(actor_self_id)
        != prepared.native_session
        or physical.resident_states.get(actor_self_id) != "ONLINE"
        or not physical.resident_mode
        or owner.supervisor.open_actions
        or owner.intent.current_intent is not None
        or owner.skills
    ):
        raise Stage27MoveHandoffRefusal("original live Self or model decision changed")
    # Another Self is deliberately NOT locked or mutated here; the caller
    # selects the single actor from the fixed original cohort.
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=actor_self_id,
    )
    journal.require_clear()
    intent_id = "stage27-intent-" + ticket.request_id
    skill_id = "stage27-skill-" + ticket.request_id
    # All observable checks above run BEFORE original owner mutation.
    # The original cohort gate, not a free IntentCommitment instance, owns
    # the current mutable state. No new physical issuer is created.
    try:
        owner.commit_intent(
            intent_id, selected.goal_id, at_ns, provenance,
        )
        owner.start_skill(
            skill_id, selected.skill_id, at_ns + 1, provenance,
        )
    except LiveCognitionCheckpointError as exc:
        raise Stage27MoveHandoffRefusal(
            "original Self not eligible for Intent/Skill ownership"
        ) from exc
    skill = owner.skills[skill_id]
    if skill.state is not SkillState.STARTED:
        raise Stage27MoveHandoffRefusal("original Skill not started")
    return Stage27OwnedMoveIntent(
        actor_self_id, prepared.native_session, prepared.world_epoch,
        ticket.request_id, "1", refreshed.seq,
        intent_id, skill_id, invocation.invocation_ref,
        invocation.parameter_preset_ref,
        selected.target_ref, selected.target_kind,
    )
