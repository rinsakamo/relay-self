"""Stage27f DEV: original L0 Outcome -> CPU TargetAssessment -> bounded L1 review.

Read-only cognitive request: never turns condition_observed into Goal/Skill success,
never edits Intent/Skill or issues an Action. A later Self-owned transition is
a separate task, after real model source and fresh WorldBody revalidation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from experiments.cognitive_physical_place_move_issue_dev import Stage27PlaceMoveReceipt

from relay_self.action import ActionState
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.initial_skill_ir import SkillCursor
from relay_self.p0d_stage26_gemma_l1_dev import PreparedStage26L1
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.p0d_stage27c_l0_place_proposal_dev import Stage27L0PlaceProposal
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    DecisionStatus,
    ProviderDecision,
)
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillInvocation
from relay_self.target_contract import (
    TargetAssessment,
    TargetBodyObservation,
    TargetConditionStatus,
    TargetKind,
    evaluate_target,
)


class Stage27EvaluationRefusal(RuntimeError):
    """Original Self outcome or current read-only L1 evaluation is unqualified."""


@dataclass(frozen=True, slots=True)
class Stage27EvaluationFrame:
    self_id: str
    native_session_id: str
    world_epoch: int
    intent_id: str
    skill_execution_id: str
    action_id: str
    invocation_ref: str
    preset_ref: str
    target_contract_ref: str
    source_probe_seq: int
    source_probe_request_id: str
    wal_digest: str
    wal_status: str
    target_assessment: TargetAssessment
    request: BoundedChoiceRequest
    completion_review_offered: bool
    owner_mutated: bool = False
    skill_succeeded: bool = False
    goal_succeeded: bool = False
    issued_physical_action: bool = False


@dataclass(frozen=True, slots=True)
class Stage27EvaluationChoice:
    self_id: str
    request_id: str
    action_id: str
    selected_number: str | None
    recommendation: str
    resolved: bool
    model_source_attested: bool = False
    owner_mutated: bool = False
    skill_succeeded: bool = False
    goal_succeeded: bool = False
    issued_physical_action: bool = False


def prepare_stage27f_outcome_evaluation(
    prepared: PreparedStage26L1,
    handoff: Stage27OwnedMoveIntent,
    l0: Stage27L0PlaceProposal,
    physical_result: Stage27PlaceMoveReceipt,
    *,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    world_epoch: int,
) -> Stage27EvaluationFrame:
    """Use ONLY current original issuer/WAL/native source; do not ask an LLM yet."""
    if (
        not isinstance(prepared, PreparedStage26L1)
        or not isinstance(handoff, Stage27OwnedMoveIntent)
        or not isinstance(l0, Stage27L0PlaceProposal)
        or not isinstance(physical_result, Stage27PlaceMoveReceipt)
        or not isinstance(owner, CheckpointedCognitiveOwner)
        or not isinstance(physical, PhysicalIssueAdmission)
        or type(world_epoch) is not int
        or owner is not prepared.original_owner
        or owner.self_id != prepared.self_id
        or handoff.self_id != prepared.self_id
        or l0.self_id != prepared.self_id
        or handoff.native_session_id != prepared.native_session
        or l0.native_session_id != prepared.native_session
        or physical_result.native_session_id != prepared.native_session
        or handoff.world_epoch != prepared.world_epoch
        or l0.world_epoch != world_epoch
        or world_epoch != prepared.world_epoch
        or owner.native_session_id != prepared.native_session
        or owner.fresh_native_observation_required
        or not physical.resident_mode
        or physical.closed
        or physical.active_action_ids
        or physical.current_native_sessions.get(owner.self_id) != prepared.native_session
        or physical.resident_states.get(owner.self_id) != "ONLINE"
        or handoff.intent_id != l0.intent_id
        or owner.intent.current_intent is None
        or handoff.intent_id != owner.intent.current_intent.intent_id
    ):
        raise Stage27EvaluationRefusal("original Self/Intent/native epoch unavailable")

    original_options = prepared.round.frame.options
    if len(original_options) != 1:
        raise Stage27EvaluationRefusal("not exactly one selected Invocation")
    invocation = original_options[0].invocation
    if not isinstance(invocation, SkillInvocation) or invocation.target.contract is None:
        raise Stage27EvaluationRefusal("original typed Invocation/Target missing")
    contract = invocation.target.contract
    skill = owner.skills.get(handoff.skill_execution_id)
    action = owner.supervisor.get(l0.action_id)
    cursor: SkillCursor | None = l0.interpreter._current
    if (
        contract.kind is not TargetKind.PLACE
        or contract.scope != invocation.scope
        or contract.contract_ref != l0.target_contract_ref
        or contract.contract_ref != physical_result.target_contract_ref
        or contract.contract_ref != prepared.original_target.arrival_contract.contract_ref
        or invocation.goal_id != "EXPLORE_WORLD"
        or invocation.skill_id != "MOVE"
        or invocation.invocation_ref != handoff.invocation_ref
        or invocation.invocation_ref != l0.original_invocation_ref
        or invocation.invocation_ref != physical_result.original_invocation_ref
        or invocation.parameter_preset_ref != handoff.preset_ref
        or invocation.parameter_preset_ref != l0.original_preset_ref
        or invocation.parameter_preset_ref != physical_result.original_preset_ref
        or handoff.skill_execution_id != l0.skill_execution_id
        or l0.action_id != physical_result.action_id
        or not skill
        or skill.state is not SkillState.STARTED
        or not skill.is_current_snapshot
        or skill.intent_id != handoff.intent_id
        or skill.skill_id != invocation.skill_id
        or action.state is not ActionState.OUTCOME
        or not action.is_current_snapshot
        or action.skill_execution_id != skill.execution_id
        or action.intent_id != handoff.intent_id
        or owner.intent.current_intent is None
        or owner.intent.current_intent.objective != invocation.goal_id
        or owner.intent.pending_reconsideration is not None
        or physical_result.l0_step_status != "YIELD_EVALUATION"
        or physical_result.skill_success_attested
        or physical_result.l0_goal_succeeded
        or physical_result.paper_causal_attribution
        or not physical_result.native_effect_issued
        or cursor is None
        or cursor.pending_action_id is not None
        or cursor.blocked
        or cursor.index != len(l0.ir.steps)
        or cursor.intent_id != handoff.intent_id
        or cursor.execution_id != handoff.skill_execution_id
        or cursor.invocation_ref != invocation.invocation_ref
    ):
        raise Stage27EvaluationRefusal("original L0/Action/Skill/Target lineage invalid")

    settled = physical_result.settled_probe
    first = physical_result.first_stable_probe
    stop = physical_result.initial_stop_probe
    if (
        settled.kind != "probe"
        or settled.session_id != prepared.native_session
        or settled.seq <= first.seq
        or first.seq <= stop.seq
        or not settled.request_id
        or not first.request_id
        or not stop.request_id
        or len({settled.request_id, first.request_id, stop.request_id}) != 3
        or settled.snapshot.time is None
        or settled.snapshot.health <= 0
        or settled.provenance.source != "mineflayer"
        or settled.provenance.reference != f"{settled.session_id}:{settled.seq}"
    ):
        raise Stage27EvaluationRefusal("original post-STOP source unavailable")
    wal = PhysicalActionJournal.restore(owner.files.physical_wal_file, self_id=owner.self_id)
    wal.require_clear()
    if len(wal.records) != 1:
        raise Stage27EvaluationRefusal("single original terminal WAL row missing")
    row = wal.records[0]
    if (
        row["capability"] != "MOVE_PLACE"
        or row["status"] != physical_result.journal_status
        or row["status"] not in {
            "NATIVE_PLACE_MOVE_SETTLED",
            "NATIVE_PLACE_MOVE_NO_PROGRESS",
            "NATIVE_PLACE_MOVE_OVERSHOOT",
        }
        or row["action_id"] != l0.action_id
        or row["intent_id"] != handoff.intent_id
        or row["skill_execution_id"] != handoff.skill_execution_id
        or row["session_id"] != prepared.native_session
        or row["invocation_ref"] != invocation.invocation_ref
        or row["preset_ref"] != invocation.parameter_preset_ref
        or row["target_contract_ref"] != contract.contract_ref
        or row["source_ref"] != f"{prepared.native_session}:{row['probe_seq']}"
        or row["after_seq"] != settled.seq
        or wal.digest != physical_result.journal_sha256
    ):
        raise Stage27EvaluationRefusal("original Action/WAL consequence altered")
    if (
        row["budget_distance_m"] is not None
        and row["displacement_m"] is not None
        and row["status"] == "NATIVE_PLACE_MOVE_SETTLED"
        and row["displacement_m"] > row["budget_distance_m"]
    ):
        raise Stage27EvaluationRefusal("bounded-settled WAL contradicts recorded budget")
    assessment = evaluate_target(
        contract,
        TargetBodyObservation(
            scope=invocation.scope, seq=settled.seq,
            provenance=settled.provenance, position=settled.snapshot.position,
        ),
    )
    # An Action outcome is not Goal success. Only safe, observed geometry
    # may OFFER a completion-review option to L1, never perform completion.
    completion_review = (
        row["status"] == "NATIVE_PLACE_MOVE_SETTLED"
        and assessment.status is TargetConditionStatus.CONDITION_OBSERVED
    )
    choices = [
        BoundedChoice("1", "CONTINUE_INTENT: request new cognition/WorldBody observation; no physical Action"),
    ]
    if completion_review:
        choices.append(BoundedChoice(
            "2", "REVIEW_COMPLETION: consider original Goal/Skill outcome; this choice never commits success",
        ))
    choices.extend((
        BoundedChoice("3", "ESCALATE_L2: ask for further deliberation; no physical authority"),
        BoundedChoice("4", "DEFER: suspend decision pending further observation"),
    ))
    if row["status"] == "NATIVE_PLACE_MOVE_OVERSHOOT":
        # An overshoot violation must not be turned into another motor attempt.
        choices = choices[-2:]
    anchor = contract.anchor
    assert anchor is not None
    pos = settled.snapshot.position
    horizontal_distance = math.hypot(anchor.x - pos.x, anchor.z - pos.z)
    request = BoundedChoiceRequest(
        request_id=f"stage27f-eval-{owner.self_id}-{prepared.native_session}-{settled.seq}",
        instruction=(
            "Evaluate the ORIGINAL selected Intent after one physical Action. "
            "Select one existing numbered recommendation only. Position reaching "
            "an envelope is an OBSERVATION, not Goal or Skill success. "
            "Do not invent a new target, permission, motor command, or budget. "
            "No selected number automatically mutates Self. Return only the number."
        ),
        intent_id=handoff.intent_id,
        focus="POST_ACTION_GOAL_SKILL_EVALUATION",
        choices=tuple(choices),
        context=(CognitionDatum.from_value(
            "original_physical_outcome_and_target_assessment",
            {
                "self_id": owner.self_id,
                "world_session_id": prepared.native_session,
                "world_epoch": world_epoch,
                "action_id": l0.action_id,
                "skill_execution_id": handoff.skill_execution_id,
                "invocation_ref": invocation.invocation_ref,
                "preset_ref": invocation.parameter_preset_ref,
                "target_contract_ref": contract.contract_ref,
                "wal_digest": wal.digest,
                "wal_status": row["status"],
                "native_settled_seq": settled.seq,
                "native_settled_probe": settled.request_id,
                "native_xyz": [pos.x, pos.y, pos.z],
                "target_xyz": [anchor.x, anchor.y, anchor.z],
                "target_envelope_horizontal_m": [
                    contract.condition.min_horizontal_m,
                    contract.condition.max_horizontal_m,
                ],
                "remaining_horizontal_distance_m": horizontal_distance,
                "target_assessment": assessment.status.value,
                "target_condition_observed": assessment.condition_observed,
                "distance_budget_m": row["budget_distance_m"],
                "action_displacement_m": row["displacement_m"],
                "goal_success_attested": False,
                "skill_success_attested": False,
                "next_physical_action_authorized": False,
            },
            settled.provenance,
        ),),
        think_allowed=False,
    )
    return Stage27EvaluationFrame(
        owner.self_id, prepared.native_session, world_epoch,
        handoff.intent_id, handoff.skill_execution_id, l0.action_id,
        invocation.invocation_ref, invocation.parameter_preset_ref or "",
        contract.contract_ref, settled.seq, settled.request_id,
        wal.digest, row["status"], assessment, request, completion_review,
    )


def resolve_stage27f_evaluation_choice(
    frame: Stage27EvaluationFrame, provider_result: ProviderDecision,
) -> Stage27EvaluationChoice:
    """Offline bounded choice decoding only; unauthenticated input cannot mutate Self.

    Use the original resident GPU lane and a post-model fresh-probe fence
    before any model choice can become an accepted Self evaluation.
    """
    if not isinstance(frame, Stage27EvaluationFrame) or not isinstance(
        provider_result, ProviderDecision
    ):
        raise Stage27EvaluationRefusal("typed original evaluation/model result required")
    offered = {x.choice_id for x in frame.request.choices}
    if provider_result.status is DecisionStatus.UNRESOLVED:
        return Stage27EvaluationChoice(
            frame.self_id, frame.request.request_id, frame.action_id,
            None, "RECONSIDER_UNRESOLVED", False,
        )
    if provider_result.choice_id not in offered:
        raise Stage27EvaluationRefusal("L1 selected an unavailable evaluation candidate")
    chosen = {
        "1": "CONTINUE_INTENT",
        "2": "REVIEW_COMPLETION",
        "3": "ESCALATE_L2",
        "4": "DEFER",
    }[provider_result.choice_id]
    return Stage27EvaluationChoice(
        frame.self_id, frame.request.request_id, frame.action_id,
        provider_result.choice_id, chosen, True,
    )
