"""C Lane Stage27g: an explicit original Self Skill review -> bounded C1.

The existing Stage27g bounded L1 selects a REVIEW recommendation but
MUST NOT itself terminalize Skill/Goal. This module separates:
(1) source-bound read-only review proposal,
(2) a SECOND explicit owner approval to terminalize original Skill and
    retain C1 in the original canonical Memory store.

No physical issue, automatic retry, Intent completion, learned Skill
installation, C2 acceptance or new L1 choice is performed here.
Raw HTTP SHA, existing resident GPU/source owner and fresh native Target
are rechecked, but synthetic test inputs are NOT real-world attestation.
"""
from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.c_lane_stage27_source_bridge import (
    assemble_stage27_c1_from_canonical_wal,
)
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.cognitive_learning_contract import OutcomeAssessment
from relay_self.cognitive_learning_owner_adapter import propose_existing_memory
from relay_self.p0d_stage26_gemma_l1_dev import PreparedStage26L1
from relay_self.p0d_stage27f_l1_evaluation_dev import (
    Stage27EvaluationChoice,
    Stage27EvaluationFrame,
)
from relay_self.p0d_stage27g_real_l1_evaluation_dev import Stage27gEvaluationWitness
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.relay_engine import DecisionStatus
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillInvocation
from relay_self.target_contract import (
    TargetBodyObservation,
    TargetConditionStatus,
    evaluate_target,
)


class C1OwnerReviewHold(RuntimeError):
    """Missing original Self/L1/native/physical lineage or explicit approval."""


@dataclass(frozen=True, slots=True)
class C1OriginalOwnerReviewProposal:
    self_id: str
    native_session_id: str
    world_epoch: int
    world_id: str
    skill_execution_id: str
    intent_id: str
    action_id: str
    evaluation_request_id: str
    wal_sha256: str
    original_invocation_ref: str
    model_response_sha256: str
    post_model_probe_seq: int
    outcome_candidate: str = "C1_SKILL_SUCCESS_REVIEW_ONLY"
    terminal_skill_accepted: bool = False
    memory_retained: bool = False
    goal_completed: bool = False
    action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class OriginalSelfC1Approval:
    """An EXTERNAL Self choice; construction alone authenticates nothing.

    The caller/actual cognition owner must independently determine the final
    Skill/Memory decision. Stage27g's number 2 is only permission to review,
    NOT this approval.
    """
    self_id: str
    native_session_id: str
    evaluation_request_id: str
    skill_execution_id: str
    explicit_self_decision: str
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class C1OriginalOwnerRetentionReceipt:
    self_id: str
    skill_execution_id: str
    memory_id: str
    original_wal_sha256: str
    model_response_sha256: str
    new_native_session_id: str
    recorded_original_owner_memory: bool = True
    physical_action_replayed: bool = False
    goal_succeeded: bool = False
    c2_accepted: bool = False
    actual_world_causality_attested: bool = False
    autonomous_self_approval_attested: bool = False


def _sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise C1OwnerReviewHold("original model HTTP bytes missing or symlinked")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_original_stage27g_c1_review(
    *,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    ticket: ResidentInferenceTicket,
    prepared: PreparedStage26L1,
    frame: Stage27EvaluationFrame,
    choice: Stage27EvaluationChoice,
    witness: Stage27gEvaluationWitness,
    post_model_probe: MineflayerObservation,
    world_id: str,
) -> C1OriginalOwnerReviewProposal | None:
    """Read-only gate. No success from L1 choice, Action OUTCOME or geometry."""
    if not all((
        isinstance(owner, CheckpointedCognitiveOwner),
        isinstance(physical, PhysicalIssueAdmission),
        isinstance(lane, ResidentLlamaInferenceLane),
        isinstance(ticket, ResidentInferenceTicket),
        isinstance(prepared, PreparedStage26L1),
        isinstance(frame, Stage27EvaluationFrame),
        isinstance(choice, Stage27EvaluationChoice),
        isinstance(witness, Stage27gEvaluationWitness),
        isinstance(post_model_probe, MineflayerObservation),
        type(world_id) is str and bool(world_id),
    )):
        raise C1OwnerReviewHold("typed original Stage27g owner/source evidence required")
    if (
        owner is not prepared.original_owner
        or lane.cognitive_work.owners.get(owner.self_id) is not owner
        or owner.cohort is not lane.cognitive_work
        or frame.self_id != owner.self_id
        or prepared.self_id != owner.self_id
        or owner.native_session_id != prepared.native_session
        or owner.native_session_id != frame.native_session_id
        or frame.world_epoch != prepared.world_epoch
        or lane.cognitive_work.current_scope(owner.self_id)[1:]
        != (owner.native_session_id, frame.world_epoch)
        or owner.fresh_native_observation_required
        or physical.closed or physical.active_action_ids
        or not physical.resident_mode
        or physical.resident_states.get(owner.self_id) != "ONLINE"
        or physical.current_native_sessions.get(owner.self_id)
        != owner.native_session_id
        or owner.intent.current_intent is None
        or owner.intent.current_intent.intent_id != frame.intent_id
        or owner.intent.pending_reconsideration is not None
        or frame.owner_mutated or frame.skill_succeeded
        or frame.goal_succeeded or frame.issued_physical_action
        or not frame.completion_review_offered
        or frame.wal_status != "NATIVE_PLACE_MOVE_SETTLED"
        or frame.target_assessment.status
        is not TargetConditionStatus.CONDITION_OBSERVED
        or frame.target_assessment.goal_succeeded
    ):
        raise C1OwnerReviewHold("original current Self/physical completion-review absent")
    if (
        ticket.self_id != frame.self_id
        or ticket.native_session_id != frame.native_session_id
        or ticket.world_epoch != frame.world_epoch
        or ticket.request_id != frame.request.request_id
        or ticket.work_ref
        != f"stage27g-post-action:{frame.action_id}:{frame.source_probe_seq}"
        or ticket.action_issue_authorized
        or witness.model_request_id != ticket.request_id
        or witness.model_work_ref != ticket.work_ref
        or witness.native_session_id != frame.native_session_id
        or witness.world_epoch != frame.world_epoch
        or witness.self_id != frame.self_id
        or witness.action_id != frame.action_id
        or witness.original_wal_digest != frame.wal_digest
        or witness.original_target_contract_ref != frame.target_contract_ref
        or witness.model_backend_ref != lane.backend_ref
        or witness.model_provider_kind
        != "OWNED_LLAMA_CPP_BOUNDED_PROVIDER_NOT_SCRIPTED"
        or not witness.model_source_attested
        or not witness.backend_slot_idle_after_call
        or witness.owner_mutated or witness.skill_succeeded
        or witness.goal_succeeded or witness.physical_action_issued
        or witness.initial_target_status
        != TargetConditionStatus.CONDITION_OBSERVED.value
        or witness.post_model_target_status
        != TargetConditionStatus.CONDITION_OBSERVED.value
        or witness.model_choice_number != "2"
        or witness.outcome_recommendation != "REVIEW_COMPLETION"
        or not witness.choice_resolved
        or choice.selected_number != "2"
        or choice.recommendation != "REVIEW_COMPLETION"
        or not choice.resolved or not choice.model_source_attested
        or choice.self_id != frame.self_id
        or choice.request_id != ticket.request_id
        or choice.action_id != frame.action_id
        or "2" not in {o.choice_id for o in frame.request.choices}
    ):
        raise C1OwnerReviewHold("Stage27g model choice/provenance does not admit review")
    original_result = lane.result(ticket)
    if (
        original_result is None
        or original_result.status is not DecisionStatus.RESOLVED
        or original_result.choice_id != "2"
        or witness.provider_call_facts.get("finish_reason") != "stop"
        or lane.require_world_idle().n_slots != 1
    ):
        raise C1OwnerReviewHold("original slot/model result not retrievable or idle")
    raw = lane.provider.stage26_raw_receipt(ticket.request_id)
    if (
        witness.raw_http_request_path != raw.request_path
        or witness.raw_http_response_path != raw.response_path
        or witness.raw_http_request_sha256 != raw.request_sha256
        or witness.raw_http_response_sha256 != raw.response_sha256
        or witness.raw_http_response_bytes != raw.response_bytes
        or _sha(Path(raw.request_path)) != raw.request_sha256
        or _sha(Path(raw.response_path)) != raw.response_sha256
    ):
        raise C1OwnerReviewHold("original L1 request/response bytes changed")
    if (
        post_model_probe.kind != "probe"
        or post_model_probe.session_id != frame.native_session_id
        or not post_model_probe.request_id
        or post_model_probe.request_id != witness.fresh_native_probe_request_id
        or post_model_probe.seq != witness.fresh_native_probe_seq
        or post_model_probe.seq <= frame.source_probe_seq
        or post_model_probe.provenance.source != "mineflayer"
        or post_model_probe.provenance.reference
        != f"{post_model_probe.session_id}:{post_model_probe.seq}"
        or post_model_probe.snapshot.time is None
        or post_model_probe.snapshot.health <= 0
        or owner.current_worldbody_observation != post_model_probe
    ):
        raise C1OwnerReviewHold("post-model source not freshly adopted by original Self")
    options = prepared.round.frame.options
    invocation = options[0].invocation if len(options) == 1 else None
    if (
        not isinstance(invocation, SkillInvocation)
        or invocation.target.contract is None
        or invocation.invocation_ref != frame.invocation_ref
        or invocation.parameter_preset_ref != frame.preset_ref
        or invocation.target.contract.contract_ref != frame.target_contract_ref
        or invocation.target.contract.scope != invocation.scope
        or invocation.scope.world_session_id != owner.native_session_id
        or invocation.goal_id != owner.intent.current_intent.objective
    ):
        raise C1OwnerReviewHold("original L1 bound target/Preset/Goal not current")
    assessment = evaluate_target(
        invocation.target.contract,
        TargetBodyObservation(
            scope=invocation.scope, seq=post_model_probe.seq,
            provenance=post_model_probe.provenance,
            position=post_model_probe.snapshot.position,
        ),
    )
    if assessment.status is not TargetConditionStatus.CONDITION_OBSERVED:
        raise C1OwnerReviewHold("completion-review observation expired")
    skill = owner.skills.get(frame.skill_execution_id)
    if (
        skill is None or not skill.is_current_snapshot
        or skill.state is not SkillState.STARTED
        or skill.intent_id != frame.intent_id
        or skill.skill_id != invocation.skill_id
    ):
        raise C1OwnerReviewHold("original child Skill no longer reviewable")
    action = owner.supervisor.get(frame.action_id)
    if (
        action.state is not ActionState.OUTCOME
        or not action.is_current_snapshot
        or action.skill_execution_id != skill.execution_id
        or action.intent_id != skill.intent_id
    ):
        raise C1OwnerReviewHold("original physical Action not terminal")
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=owner.self_id,
    )
    journal.require_clear()
    if (
        journal.digest != frame.wal_digest
        or len(journal.records) != 1
        or journal.records[0]["action_id"] != frame.action_id
        or journal.records[0]["skill_execution_id"] != skill.execution_id
        or journal.records[0]["session_id"] != frame.native_session_id
        or journal.records[0]["after_seq"] != frame.source_probe_seq
        or journal.records[0]["target_contract_ref"] != frame.target_contract_ref
        or journal.records[0]["invocation_ref"] != invocation.invocation_ref
        or journal.records[0]["preset_ref"] != invocation.parameter_preset_ref
        or journal.records[0]["status"] != "NATIVE_PLACE_MOVE_SETTLED"
    ):
        raise C1OwnerReviewHold("original canonical terminal WAL changed")
    return C1OriginalOwnerReviewProposal(
        self_id=owner.self_id, native_session_id=owner.native_session_id,
        world_epoch=frame.world_epoch, world_id=world_id,
        skill_execution_id=skill.execution_id, intent_id=skill.intent_id,
        action_id=action.action_id, evaluation_request_id=ticket.request_id,
        wal_sha256=journal.digest,
        original_invocation_ref=invocation.invocation_ref,
        model_response_sha256=raw.response_sha256,
        post_model_probe_seq=post_model_probe.seq,
    )


def accept_original_stage27g_c1_review(
    *,
    proposal: C1OriginalOwnerReviewProposal,
    approval: OriginalSelfC1Approval,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    ticket: ResidentInferenceTicket,
    prepared: PreparedStage26L1,
    frame: Stage27EvaluationFrame,
    choice: Stage27EvaluationChoice,
    witness: Stage27gEvaluationWitness,
    before_probe: MineflayerObservation,
    settled_probe: MineflayerObservation,
    post_model_probe: MineflayerObservation,
    world_id: str,
    at_ns: int,
) -> C1OriginalOwnerRetentionReceipt:
    """SECOND explicit Self gate. Never treat model recommendation as approval."""
    if (
        not isinstance(proposal, C1OriginalOwnerReviewProposal)
        or not isinstance(approval, OriginalSelfC1Approval)
        or approval.explicit_self_decision != "ACCEPT_SKILL_SUCCESS_AND_RETAIN_C1"
        or approval.self_id != proposal.self_id
        or approval.native_session_id != proposal.native_session_id
        or approval.evaluation_request_id != proposal.evaluation_request_id
        or approval.skill_execution_id != proposal.skill_execution_id
        or not isinstance(approval.provenance, Provenance)
        or type(at_ns) is not int or at_ns < 0
        or not isinstance(before_probe, MineflayerObservation)
        or not isinstance(settled_probe, MineflayerObservation)
    ):
        raise C1OwnerReviewHold("explicit original Self approval missing/foreign")
    # The same original owner lock encloses source revalidation, Skill
    # terminalization, Memory write and readback. Native/Paper and the
    # externally authenticated Self approval remain independent requirements.
    with owner._mutating():
        current = prepare_original_stage27g_c1_review(
            owner=owner, physical=physical, lane=lane, ticket=ticket,
            prepared=prepared, frame=frame, choice=choice, witness=witness,
            post_model_probe=post_model_probe, world_id=world_id,
        )
        if current != proposal:
            raise C1OwnerReviewHold("review proposal went stale before Self acceptance")
        if (
            before_probe.session_id != proposal.native_session_id
            or settled_probe.session_id != proposal.native_session_id
            or not before_probe.seq < settled_probe.seq < post_model_probe.seq
            or settled_probe.seq != frame.source_probe_seq
            or not before_probe.request_id or not settled_probe.request_id
            or before_probe.snapshot.time is None
            or settled_probe.snapshot.time is None
            or before_probe.snapshot.health <= 0
            or settled_probe.snapshot.health <= 0
        ):
            raise C1OwnerReviewHold("original bounded native before/settled probes absent")
        if load_persistent_cognition(owner.files.cognition_file) != owner.retained:
            raise C1OwnerReviewHold("original canonical retained Memory source unflushed")
        old = owner.skills[proposal.skill_execution_id]
        action = owner.supervisor.get(proposal.action_id)
        stamp = max(old.events[-1].at_ns, action.events[-1].at_ns)
        if at_ns <= stamp:
            raise C1OwnerReviewHold("review must occur after physical terminal Action")
        # Validate the EXACT prospective C1 with a detached Skill snapshot
        # BEFORE any original Owner mutation. This prevents malformed probes,
        # rejected Target/WAL or duplicate Memory from terminalizing the Skill.
        draft = copy.deepcopy(old).succeed(
            reason="explicit original Self terminal Skill review",
            at_ns=at_ns, provenance=approval.provenance,
        )
        invocation = prepared.round.frame.options[0].invocation
        experience = assemble_stage27_c1_from_canonical_wal(
            cognition=owner.retained, intent=owner.intent, skill=draft,
            actions=(action,), journal_path=owner.files.physical_wal_file,
            original_wal_sha256=proposal.wal_sha256,
            selected_invocation=invocation, before_probe=before_probe,
            after_probe=settled_probe,
            world_id=proposal.world_id, world_epoch=proposal.world_epoch,
            selected_provenance=approval.provenance,
        )
        if experience is None or experience.target_outcome is not OutcomeAssessment.SUCCESS:
            raise C1OwnerReviewHold("original terminal C1 source/Target not qualified")
        memory = propose_existing_memory(
            owner.retained, experience,
            integration_provenance=approval.provenance,
        )
        if memory is None:
            raise C1OwnerReviewHold("original C1 already retained; no replay")
        # Mutate the ORIGINAL Owner only after all source/preflight checks.
        # Disk failures HOLD; do not auto-retry/reissue a terminal Action.
        terminal = owner.finish_reviewed_skill(
            old.execution_id, outcome=SkillState.SUCCEEDED,
            reason="explicit original Self terminal Skill review",
            at_ns=at_ns, provenance=approval.provenance,
        )
        if terminal.events != draft.events:
            raise C1OwnerReviewHold("terminal original Skill differs from preflight")
        owner.retain_memory(memory)
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
        if (
            load_persistent_cognition(owner.files.cognition_file) != owner.retained
            or owner.skills[old.execution_id] is not terminal
            or PhysicalActionJournal.restore(
                owner.files.physical_wal_file, self_id=owner.self_id,
            ).digest != proposal.wal_sha256
        ):
            raise C1OwnerReviewHold("canonical original Self C1 persistence not verified")
        return C1OriginalOwnerRetentionReceipt(
            owner.self_id, old.execution_id, memory.memory_id,
            proposal.wal_sha256, proposal.model_response_sha256,
            owner.native_session_id,
        )
