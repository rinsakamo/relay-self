"""Stage27b read-only WorldBody PLACE target resolution for real L1 MOVE.

The original Stage26 selected target is immutable. An authored geometry plan
does NOT authorize LOOK, native MOVE, WAL or a physical Action. Terrain
traversability and actual heading remain UNKNOWN until source-qualified by
separate WorldBody/issuer evidence.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    mineflayer_yaw_to_target,
)
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.p0d_stage26_gemma_l1_dev import PreparedStage26L1
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillInvocation, bind_skill_invocation
from relay_self.target_contract import (
    ReferenceFrame,
    TargetBodyObservation,
    TargetConditionStatus,
    TargetKind,
    evaluate_target,
)


class Stage27PlaceResolutionRefusal(RuntimeError):
    """Native PLACE geometry is unavailable or Self ownership changed."""


@dataclass(frozen=True, slots=True)
class Stage27PlaceMotionPlan:
    self_id: str
    native_session_id: str
    world_epoch: int
    native_probe_request_id: str
    native_probe_seq: int
    inference_request_id: str
    intent_id: str
    skill_execution_id: str
    invocation_ref: str
    parameter_preset_ref: str
    target_contract_ref: str
    target_ref: str
    gap_to_arrival_envelope_m: float
    horizontal_distance_m: float
    desired_mineflayer_yaw_rad: float | None
    observation_status: str
    next_step: str
    preset_max_distance_m: float | None = None
    full_envelope_reachable_within_distance_budget: bool = False
    clearance_observed: bool = False
    facing_aligned_observed: bool = False
    action_granted: bool = False
    native_effect_issued: bool = False
    world_goal_succeeded: bool = False


def resolve_stage27_place_motion(
    prepared: PreparedStage26L1,
    handoff: Stage27OwnedMoveIntent,
    observation: MineflayerObservation,
    *,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    world_epoch: int,
) -> Stage27PlaceMotionPlan:
    """Compute desired Mineflayer yaw from a *fresh* original native position.

    This is not obstacle detection or complete pathfinding. A PLACE target
    cannot be silently substituted with the original RELATIVE MOVE issuer.
    The result must stay attached to this exact invocation and native source.
    """
    if (
        not isinstance(prepared, PreparedStage26L1)
        or not isinstance(handoff, Stage27OwnedMoveIntent)
        or not isinstance(observation, MineflayerObservation)
        or not isinstance(owner, CheckpointedCognitiveOwner)
        or not isinstance(physical, PhysicalIssueAdmission)
        or type(world_epoch) is not int or world_epoch < 0
        or owner is not prepared.original_owner
        or handoff.self_id != prepared.self_id
        or handoff.native_session_id != prepared.native_session
        or handoff.world_epoch != prepared.world_epoch
        or world_epoch != handoff.world_epoch
        or handoff.decision_request_id != prepared.round.request.request_id
        or handoff.decision_number != "1"
        or handoff.outcome != "INTENT_STARTED_TARGET_RESOLUTION_REQUIRED"
        or handoff.physical_action_issued
        or handoff.physical_proposal_authorized
        or handoff.target_resolution_attested
        or handoff.wal_modified
        or handoff.peer_owner_mutated
        or owner.self_id != prepared.self_id
        or owner.native_session_id != prepared.native_session
        or owner.fresh_native_observation_required
        or physical.current_native_sessions.get(prepared.self_id)
        != prepared.native_session
        or physical.resident_states.get(prepared.self_id) != "ONLINE"
        or not physical.resident_mode
        or physical.active_action_ids
        or observation.kind != "probe"
        or not observation.request_id
        or observation.session_id != prepared.native_session
        or observation.seq < handoff.rechecked_native_seq
        or observation.seq < prepared.first_probe.seq
        or observation.snapshot.time is None
        or observation.snapshot.health <= 0
        or owner.pattern_registry != prepared.restored.semantic.pattern_registry
        or owner.retained != prepared.restored.retained
    ):
        raise Stage27PlaceResolutionRefusal("stale or foreign original WorldBody/Intent source")
    option = prepared.round.frame.options
    if len(option) != 1 or option[0].invocation is None:
        raise Stage27PlaceResolutionRefusal("original single immutable L1 Invocation absent")
    selected = option[0]
    invocation = selected.invocation
    contract = invocation.target.contract
    if (
        not isinstance(invocation, SkillInvocation)
        or contract is None
        or contract.kind is not TargetKind.PLACE
        or contract.reference_frame is not ReferenceFrame.WORLD
        or contract.anchor is None
        or contract.scope != invocation.scope
        or invocation.goal_id != "EXPLORE_WORLD"
        or invocation.skill_id != "MOVE"
        or invocation.skill_version != 1
        or selected.target_kind != "DESTINATION"
        or contract.contract_ref != prepared.original_target.arrival_contract.contract_ref
        or invocation.invocation_ref != handoff.invocation_ref
        or invocation.parameter_preset_ref != handoff.preset_ref
        or invocation.target.ref != handoff.target_ref
        or invocation.target.kind != handoff.target_kind
        or handoff.intent_id is None
        or handoff.skill_execution_id not in owner.skills
        or owner.intent.current_intent is None
        or owner.intent.current_intent.intent_id != handoff.intent_id
        or owner.intent.current_intent.objective != invocation.goal_id
        or owner.intent.pending_reconsideration is not None
    ):
        raise Stage27PlaceResolutionRefusal("selected MOVE/PLACE/Intent was rebound")
    skill = owner.skills[handoff.skill_execution_id]
    if (
        skill.state is not SkillState.STARTED
        or not skill.is_current_snapshot
        or skill.intent_id != handoff.intent_id
        or skill.skill_id != invocation.skill_id
        or owner.supervisor.open_actions
    ):
        raise Stage27PlaceResolutionRefusal("original Self Skill or Action lifecycle changed")
    definition = next(
        (d for d in initial_skill_definitions()
         if d.skill_id == invocation.skill_id and d.version == invocation.skill_version),
        None,
    )
    if definition is None:
        raise Stage27PlaceResolutionRefusal("original innate MOVE definition missing")
    try:
        bind_skill_invocation(definition, invocation)
        PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ).require_clear()
    except (ValueError, RuntimeError) as exc:
        raise Stage27PlaceResolutionRefusal("original MOVE/Preset/WAL invalid") from exc

    assessment = evaluate_target(
        contract,
        TargetBodyObservation(
            scope=contract.scope, seq=observation.seq,
            provenance=observation.provenance,
            position=observation.snapshot.position,
        ),
    )
    position = observation.snapshot.position
    target = contract.anchor
    distance = math.hypot(target.x - position.x, target.z - position.z)
    gap = assessment.gap_to_envelope_m
    if assessment.status is TargetConditionStatus.CONDITION_OBSERVED:
        return Stage27PlaceMotionPlan(
            owner.self_id, prepared.native_session, world_epoch,
            observation.request_id, observation.seq, handoff.decision_request_id,
            handoff.intent_id, handoff.skill_execution_id,
            invocation.invocation_ref, invocation.parameter_preset_ref or "",
            contract.contract_ref, contract.target_ref, 0.0, distance, None,
            assessment.status.value,
            "TARGET_GEOMETRY_OBSERVED_AWAIT_INDEPENDENT_GOAL_EVALUATION",
            preset_max_distance_m=invocation.budget.max_distance_m,
            full_envelope_reachable_within_distance_budget=True,
        )
    if assessment.status is not TargetConditionStatus.OUTSIDE or gap is None:
        raise Stage27PlaceResolutionRefusal(
            f"native PLACE condition {assessment.status.value} cannot be resolved"
        )
    if invocation.budget.max_actions < 1 or invocation.budget.max_duration_ms <= 0:
        raise Stage27PlaceResolutionRefusal("fixed Preset has no finite MOVE budget")
    # A child can attempt a partial MOVE without completing the Goal. Do not
    # confuse an inaccurate/short expected budget with inability to act, but
    # never extend or silently rewrite the immutable budget.
    can_finish_in_budget = (
        invocation.budget.max_distance_m is None
        or gap <= invocation.budget.max_distance_m
    )
    # This is only a geometrically calculated look heading; the actual
    # orientation, terrain clearance, native look acknowledgement and MOVE
    # amount are NOT attested by the current native position-only snapshot.
    yaw = mineflayer_yaw_to_target(position, target)
    return Stage27PlaceMotionPlan(
        owner.self_id, prepared.native_session, world_epoch,
        observation.request_id, observation.seq, handoff.decision_request_id,
        handoff.intent_id, handoff.skill_execution_id,
        invocation.invocation_ref, invocation.parameter_preset_ref or "",
        contract.contract_ref, contract.target_ref, gap, distance,
        yaw, assessment.status.value,
        "NATIVE_LOOK_AND_BOUNDED_MOVE_RESOLUTION_REQUIRED_NOT_ISSUABLE",
        preset_max_distance_m=invocation.budget.max_distance_m,
        full_envelope_reachable_within_distance_budget=can_finish_in_budget,
    )
