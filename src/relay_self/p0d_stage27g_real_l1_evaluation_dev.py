"""Stage27g: post-Action original-owner L1 BOUNDED evaluation, read-only.

Actual HTTP is owned by the existing shared single-slot llama lane. The
model result is not allowed to complete Skill/Intent or authorize new motion.
A model response MUST precede a fresh native probe and owner/WAL recheck.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from typing import Awaitable, Callable

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.p0d_stage26_gemma_l1_dev import PreparedStage26L1
from relay_self.p0d_stage27f_l1_evaluation_dev import (
    Stage27EvaluationChoice,
    Stage27EvaluationFrame,
    resolve_stage27f_evaluation_choice,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.relay_engine import CognitionMode, ProviderDecision
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillInvocation
from relay_self.target_contract import (
    TargetAssessment,
    TargetBodyObservation,
    TargetConditionStatus,
    evaluate_target,
)


class Stage27gEvaluationRefusal(RuntimeError):
    """Post-Action bounded model result not attributable to current original Self."""


@dataclass(frozen=True, slots=True)
class Stage27gEvaluationWitness:
    self_id: str
    action_id: str
    model_request_id: str
    model_work_ref: str
    native_session_id: str
    world_epoch: int
    original_target_contract_ref: str
    original_wal_digest: str
    model_choice_number: str | None
    outcome_recommendation: str
    choice_resolved: bool
    initial_target_status: str
    post_model_target_status: str
    fresh_native_probe_request_id: str
    fresh_native_probe_seq: int
    model_backend_ref: str
    model_provider_kind: str
    backend_slot_idle_after_call: bool
    provider_call_facts: dict[str, object]
    raw_http_request_path: str
    raw_http_request_sha256: str
    raw_http_response_path: str
    raw_http_response_sha256: str
    raw_http_response_bytes: int
    model_source_attested: bool = True
    owner_mutated: bool = False
    skill_succeeded: bool = False
    goal_succeeded: bool = False
    physical_action_issued: bool = False


def _owner_still_eligible(
    frame: Stage27EvaluationFrame,
    prepared: PreparedStage26L1,
    *,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
) -> None:
    if (
        not isinstance(frame, Stage27EvaluationFrame)
        or not isinstance(prepared, PreparedStage26L1)
        or not isinstance(owner, CheckpointedCognitiveOwner)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or owner is not prepared.original_owner
        or lane.cognitive_work.owners.get(frame.self_id) is not owner
        or owner.self_id != frame.self_id
        or prepared.self_id != frame.self_id
        or prepared.native_session != frame.native_session_id
        or prepared.world_epoch != frame.world_epoch
        or owner.native_session_id != frame.native_session_id
        or owner.fresh_native_observation_required
        or lane.cognitive_work.current_scope(frame.self_id)[1:]
        != (frame.native_session_id, frame.world_epoch)
        or not physical.resident_mode
        or physical.closed
        or physical.active_action_ids
        or physical.current_native_sessions.get(frame.self_id) != frame.native_session_id
        or physical.resident_states.get(frame.self_id) != "ONLINE"
        or owner.intent.current_intent is None
        or owner.intent.current_intent.intent_id != frame.intent_id
        or owner.intent.pending_reconsideration is not None
        or frame.owner_mutated
        or frame.skill_succeeded
        or frame.goal_succeeded
        or frame.issued_physical_action
    ):
        raise Stage27gEvaluationRefusal("original evaluation Self/World/owner not current")
    # A Stage27f frame is a read-only source-bound claim, not a capability.
    # Recheck the exact pending candidate set and prompt source before sending
    # its contents to the actual L1 backend, rather than trusting a forged
    # completion-review option or an edited goal-success context.
    review = (
        frame.wal_status == "NATIVE_PLACE_MOVE_SETTLED"
        and frame.target_assessment.status is TargetConditionStatus.CONDITION_OBSERVED
    )
    expected_numbers = (
        ("3", "4") if frame.wal_status == "NATIVE_PLACE_MOVE_OVERSHOOT"
        else ("1", "2", "3", "4") if review else ("1", "3", "4")
    )
    if (
        frame.completion_review_offered != review
        or frame.target_assessment.contract_ref != frame.target_contract_ref
        or frame.target_assessment.goal_succeeded
        or frame.target_assessment.physical_authorized
        or frame.target_assessment.condition_observed
        != (frame.target_assessment.status is TargetConditionStatus.CONDITION_OBSERVED)
        or frame.request.request_id
        != f"stage27f-eval-{frame.self_id}-{frame.native_session_id}-{frame.source_probe_seq}"
        or frame.request.intent_id != frame.intent_id
        or frame.request.focus != "POST_ACTION_GOAL_SKILL_EVALUATION"
        or frame.request.think_allowed
        or tuple(c.choice_id for c in frame.request.choices) != expected_numbers
        or len(frame.request.context) != 1
        or frame.request.context[0].key
        != "original_physical_outcome_and_target_assessment"
        or frame.request.context[0].provenance.source != "mineflayer"
        or frame.request.context[0].provenance.reference
        != f"{frame.native_session_id}:{frame.source_probe_seq}"
    ):
        raise Stage27gEvaluationRefusal("post-Action L1 review choices/source altered")
    try:
        original_context = json.loads(frame.request.context[0].value_json)
    except (ValueError, TypeError) as exc:
        raise Stage27gEvaluationRefusal("post-Action original context invalid") from exc
    if not isinstance(original_context, dict) or any((
        original_context.get("self_id") != frame.self_id,
        original_context.get("world_session_id") != frame.native_session_id,
        original_context.get("world_epoch") != frame.world_epoch,
        original_context.get("action_id") != frame.action_id,
        original_context.get("skill_execution_id") != frame.skill_execution_id,
        original_context.get("invocation_ref") != frame.invocation_ref,
        original_context.get("preset_ref") != frame.preset_ref,
        original_context.get("target_contract_ref") != frame.target_contract_ref,
        original_context.get("wal_digest") != frame.wal_digest,
        original_context.get("wal_status") != frame.wal_status,
        original_context.get("native_settled_seq") != frame.source_probe_seq,
        original_context.get("native_settled_probe")
        != frame.source_probe_request_id,
        original_context.get("target_assessment")
        != frame.target_assessment.status.value,
        original_context.get("target_condition_observed")
        is not frame.target_assessment.condition_observed,
        original_context.get("goal_success_attested") is not False,
        original_context.get("skill_success_attested") is not False,
        original_context.get("next_physical_action_authorized") is not False,
    )):
        raise Stage27gEvaluationRefusal("original evaluation context source mismatch")
    skill = owner.skills.get(frame.skill_execution_id)
    action = owner.supervisor.get(frame.action_id)
    original_options = prepared.round.frame.options
    invocation = original_options[0].invocation if len(original_options) == 1 else None
    if (
        skill is None
        or skill.state is not SkillState.STARTED
        or not skill.is_current_snapshot
        or skill.intent_id != frame.intent_id
        or action.state is not ActionState.OUTCOME
        or not action.is_current_snapshot
        or action.skill_execution_id != frame.skill_execution_id
        or action.intent_id != frame.intent_id
        or not isinstance(invocation, SkillInvocation)
        or invocation.invocation_ref != frame.invocation_ref
        or invocation.parameter_preset_ref != frame.preset_ref
        or invocation.target.contract is None
        or invocation.target.contract.contract_ref != frame.target_contract_ref
        or invocation.target.contract.scope != prepared.round.frame.scope
    ):
        raise Stage27gEvaluationRefusal("original Intent/Skill/Action/Target lineage changed")
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=owner.self_id,
    )
    journal.require_clear()
    if (
        journal.digest != frame.wal_digest
        or len(journal.records) != 1
        or journal.records[0].get("action_id") != frame.action_id
        or journal.records[0].get("status") != frame.wal_status
    ):
        raise Stage27gEvaluationRefusal("original terminal WAL changed before L1 review")


def submit_stage27g_original_evaluation(
    frame: Stage27EvaluationFrame,
    prepared: PreparedStage26L1,
    *,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
) -> ResidentInferenceTicket:
    """Submit once on original resident GPU lane; no alternative model owner."""
    _owner_still_eligible(
        frame, prepared, owner=owner, physical=physical, lane=lane,
    )
    lane.require_world_idle()
    ticket = lane.submit(
        frame.self_id,
        work_ref=f"stage27g-post-action:{frame.action_id}:{frame.source_probe_seq}",
        request=frame.request,
        mode=CognitionMode.BOUNDED,
    )
    if (
        ticket.self_id != frame.self_id
        or ticket.request_id != frame.request.request_id
        or ticket.native_session_id != frame.native_session_id
        or ticket.world_epoch != frame.world_epoch
        or ticket.action_issue_authorized
    ):
        raise Stage27gEvaluationRefusal("original resident evaluation ticket altered")
    return ticket


async def finish_stage27g_original_evaluation(
    frame: Stage27EvaluationFrame,
    prepared: PreparedStage26L1,
    *,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    ticket: ResidentInferenceTicket,
    fresh_probe: Callable[[], Awaitable[MineflayerObservation]],
    result_timeout_s: float = 60.0,
) -> tuple[Stage27EvaluationChoice, Stage27gEvaluationWitness]:
    """Model completion/idle -> fresh native source -> strict Self/WAL recheck."""
    if (
        not isinstance(ticket, ResidentInferenceTicket)
        or not callable(fresh_probe)
        or ticket.self_id != frame.self_id
        or ticket.request_id != frame.request.request_id
        or ticket.mode is not CognitionMode.BOUNDED
        or ticket.native_session_id != frame.native_session_id
        or ticket.world_epoch != frame.world_epoch
        or ticket.backend_ref != lane.backend_ref
        or ticket.work_ref
        != f"stage27g-post-action:{frame.action_id}:{frame.source_probe_seq}"
        or ticket.action_issue_authorized
    ):
        raise Stage27gEvaluationRefusal("stale/foreign evaluation GPU request")
    _owner_still_eligible(
        frame, prepared, owner=owner, physical=physical, lane=lane,
    )
    result = await lane.await_result(ticket, timeout_s=result_timeout_s)
    if not isinstance(result, ProviderDecision) or lane.result(ticket) != result:
        raise Stage27gEvaluationRefusal("original real L1 decision unavailable")
    facts = result.call_facts
    if (
        facts.finish_reason != "stop"
        or facts.prompt_tokens is None
        or facts.completion_tokens is None
        or facts.total_tokens is None
        or facts.total_tokens != facts.prompt_tokens + facts.completion_tokens
    ):
        raise Stage27gEvaluationRefusal("original evaluation model usage not auditable")
    # Original provider independently hashes these exact on-disk HTTP bytes.
    raw = lane.provider.stage26_raw_receipt(ticket.request_id)
    # Never request the WorldBody recheck before actual model response/idle.
    fresh = await fresh_probe()
    if (
        not isinstance(fresh, MineflayerObservation)
        or fresh.kind != "probe"
        or not fresh.request_id
        or fresh.request_id == frame.source_probe_request_id
        or fresh.session_id != frame.native_session_id
        or fresh.seq <= frame.source_probe_seq
        or fresh.provenance.source != "mineflayer"
        or fresh.provenance.reference != f"{fresh.session_id}:{fresh.seq}"
        or fresh.snapshot.time is None
        or fresh.snapshot.health <= 0
    ):
        raise Stage27gEvaluationRefusal("fresh post-model original native probe unavailable")
    _owner_still_eligible(
        frame, prepared, owner=owner, physical=physical, lane=lane,
    )
    if lane.result(ticket) != result:
        raise Stage27gEvaluationRefusal("model answer lost original source identity")
    original_invocation = prepared.round.frame.options[0].invocation
    assert isinstance(original_invocation, SkillInvocation)
    contract = original_invocation.target.contract
    assert contract is not None
    fresh_assessment: TargetAssessment = evaluate_target(
        contract, TargetBodyObservation(
            scope=contract.scope, seq=fresh.seq,
            provenance=fresh.provenance, position=fresh.snapshot.position,
        ),
    )
    choice = resolve_stage27f_evaluation_choice(frame, result)
    # Observed arrival may lapse during inference; a completion-review choice
    # cannot outrun WorldBody. No CPU-side success or Intent transition.
    if (
        choice.recommendation == "REVIEW_COMPLETION"
        and fresh_assessment.status is not TargetConditionStatus.CONDITION_OBSERVED
    ):
        choice = replace(
            choice, recommendation="RECONSIDER_FRESH_WORLD_CHANGED",
            resolved=False,
        )
    choice = replace(choice, model_source_attested=True)
    return choice, Stage27gEvaluationWitness(
        frame.self_id, frame.action_id, ticket.request_id, ticket.work_ref,
        frame.native_session_id, frame.world_epoch,
        frame.target_contract_ref, frame.wal_digest,
        choice.selected_number, choice.recommendation, choice.resolved,
        frame.target_assessment.status.value, fresh_assessment.status.value,
        fresh.request_id, fresh.seq, ticket.backend_ref,
        "OWNED_LLAMA_CPP_BOUNDED_PROVIDER_NOT_SCRIPTED",
        True, asdict(result.call_facts),
        raw.request_path, raw.request_sha256, raw.response_path,
        raw.response_sha256, raw.response_bytes,
    )
