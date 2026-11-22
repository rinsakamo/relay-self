"""I4a DEV: S2 first MOVE candidate on the ORIGINAL finite ActionPort.

Only a PROPOSED/UNAUTHORIZED Action, NEVER a physical issuer, WAL PREPARED,
native control, authenticated terrain clearance or Goal result.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    mineflayer_yaw_to_target,
)
from relay_self.cognitive_minimal_dev import Selection
from relay_self.i_lane_i4a_s2_owner_handoff_dev import I4ANextWitness
from relay_self.i_lane_i4a_s2_run_boundary_dev import (
    I4AS2EmptyRunBoundary,
    I4AS2RunBoundaryHold,
    verify_i4a_s2_empty_run_boundary,
)
from relay_self.initial_skill_ir import (
    FiniteSkillInterpreter,
    PhysicalSkillIR,
    SkillCursor,
    compile_invoked_skill,
)
from relay_self.p0d_stage27b_place_motion_dev import Stage27PlaceMotionPlan
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalActionProposalReceipt,
    PhysicalCapability,
    PhysicalReadback,
)
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.provenance import Provenance
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillInvocation
from relay_self.target_contract import (
    TargetBodyObservation,
    TargetConditionStatus,
    evaluate_target,
)


class I4AS2MotorProposalHold(RuntimeError):
    """The original S2 source cannot support a non-issuing L0 proposal."""


@dataclass(frozen=True, slots=True, eq=False)
class I4AS2FirstMoveProposal:
    """Typed original L0 proposal with explicit *no effect* flags."""

    boundary: I4AS2EmptyRunBoundary
    source_probe: MineflayerObservation
    action_id: str
    invocation_ref: str
    motion: Stage27PlaceMotionPlan
    ir: PhysicalSkillIR
    cursor: SkillCursor
    interpreter: FiniteSkillInterpreter
    proposal: PhysicalActionProposalReceipt
    target_clearance_attested: bool = False
    physical_authorized: bool = False
    physical_issued: bool = False
    wal_modified: bool = False


def propose_s2_first_original_place_move(
    boundary: I4AS2EmptyRunBoundary,
    witness: I4ANextWitness,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    native: MineflayerObservation,
    capability: PhysicalCapability,
    at_ns: int,
    provenance: Provenance,
) -> I4AS2FirstMoveProposal:
    """Reuse original finite interpreter/ActionPort, not a duplicate issuer.

    The current Schema's target is merely a Self-generated exploration
    candidate. No independent terrain or destination source is attested by
    this function. Therefore output CANNOT be issued as a physical Action.
    """
    if (
        not isinstance(boundary, I4AS2EmptyRunBoundary)
        or not isinstance(witness, I4ANextWitness)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or not isinstance(native, MineflayerObservation)
        or not isinstance(capability, PhysicalCapability)
        or not isinstance(provenance, Provenance)
        or type(at_ns) is not int or at_ns < 0
        or witness.prepared.owner is not boundary.owner
        or witness.prepared.physical is not physical
        or witness.prepared.lane is not lane
        or witness.ticket.request_id != boundary.decision_request_id
        or witness.after_probe is not native
        or native.request_id != boundary.post_model_probe_id
        or native.seq != boundary.post_model_probe_seq
        or native.session_id != boundary.native_session_id
        or native.kind != "probe" or native.snapshot.time is None
        or native.snapshot.health <= 0 or native.snapshot.oxygen_level == 0
        or native.provenance.source != "mineflayer"
        or native.provenance.reference != f"{native.session_id}:{native.seq}"
        or not capability.available or capability.capability_ref != "MOVE"
        or capability.version != 1 or capability.body_channel != "locomotion"
        or capability.target_kind != "DESTINATION"
    ):
        raise I4AS2MotorProposalHold("original scoped S2 source/capability absent")
    owner = boundary.owner
    if owner.cohort is None:
        raise I4AS2MotorProposalHold("original Owner cohort absent")
    with owner.cohort.lock:
        try:
            verify_i4a_s2_empty_run_boundary(
                boundary, physical=physical, lane=lane,
            )
        except I4AS2RunBoundaryHold as exc:
            raise I4AS2MotorProposalHold("S1 WAL/S2 Owner boundary stale") from exc
        option, = witness.prepared.round.frame.options
        invocation = option.invocation
        if (
            not isinstance(invocation, SkillInvocation)
            or invocation.invocation_ref != boundary.invocation_ref
            or invocation.parameter_preset_ref != boundary.preset_ref
            or invocation.target.ref != boundary.target_ref
            or invocation.scope.self_id != owner.self_id
            or invocation.scope.world_session_id != boundary.native_session_id
            or invocation.target.contract is None
            or at_ns <= owner.skills[boundary.new_skill_id].events[-1].at_ns
            or owner.skills[boundary.new_skill_id].state is not SkillState.STARTED
        ):
            raise I4AS2MotorProposalHold("current bounded S2 Invocation changed")
        contract = invocation.target.contract
        assessment = evaluate_target(
            contract, TargetBodyObservation(
                scope=invocation.scope, seq=native.seq,
                provenance=native.provenance,
                position=native.snapshot.position,
            ),
        )
        target = contract.anchor
        pos = native.snapshot.position
        if (
            assessment.status is not TargetConditionStatus.OUTSIDE
            or target is None
            or math.hypot(target.x-pos.x, target.z-pos.z) <= 0
            or invocation.budget.max_actions < 1
            or invocation.budget.max_duration_ms <= 0
        ):
            raise I4AS2MotorProposalHold("S2 position/target cannot be resolved")
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id,
                native_session_id=owner.native_session_id,
            ):
                # Recheck under exactly the participating original issuer's
                # serialization gate before a non-authorizing proposal.
                verify_i4a_s2_empty_run_boundary(
                    boundary, physical=physical, lane=lane,
                )
                journal = PhysicalActionJournal.restore(
                    owner.files.physical_wal_file, self_id=owner.self_id,
                )
                journal.require_clear()
                if journal.digest != boundary.prefix_digest:
                    raise I4AS2MotorProposalHold("original physical history changed")
                choice = Selection(
                    "READY", option, "new current Owner bounded L1 number 1",
                    invocation.scope,
                )
                # A Schema candidate ref is NOT independent WorldBody
                # clearance; the original ActionPort merely names it.
                readback = PhysicalReadback(
                    invocation.scope, native.provenance, native.seq,
                    native.request_id, (option.target_ref,), True,
                )
                ir = compile_invoked_skill(
                    choice, definition=witness.prepared.definition,
                    target=invocation.target,
                    constraints=invocation.constraints,
                    budget=invocation.budget,
                    provenance=invocation.provenance,
                    capability=capability, arguments=invocation.arguments,
                )
                interpreter = FiniteSkillInterpreter()
                skill = owner.skills[boundary.new_skill_id]
                cursor = interpreter.begin(
                    choice, ir=ir, intent_owner=owner.intent,
                    skill_execution=skill,
                    registered_versions=frozenset({("MOVE", 1)}),
                    deadline_ns=at_ns + invocation.budget.max_duration_ms * 1_000_000,
                )
                cursor = interpreter.check_target(
                    cursor, readback=readback, intent_owner=owner.intent,
                    skill_execution=skill, at_ns=at_ns,
                ).cursor
                action_id = f"i4a-s2-{owner.self_id}-{native.seq}"
                if action_id in {x.action_id for x in owner.supervisor.recorded_actions}:
                    raise I4AS2MotorProposalHold("S2 Action ID already owned")
                binding = PhysicalActionBinding(
                    invocation.scope, boundary.new_intent_id, invocation.goal_id,
                    invocation.skill_id, invocation.skill_version,
                    boundary.new_skill_id, action_id, "MOVE", 1,
                    "locomotion", option.target_kind, option.target_ref,
                    native.seq, native.request_id, native.provenance,
                )
                motion = Stage27PlaceMotionPlan(
                    self_id=owner.self_id,
                    native_session_id=boundary.native_session_id,
                    world_epoch=boundary.world_epoch,
                    native_probe_request_id=native.request_id,
                    native_probe_seq=native.seq,
                    inference_request_id=boundary.decision_request_id,
                    intent_id=boundary.new_intent_id,
                    skill_execution_id=boundary.new_skill_id,
                    invocation_ref=invocation.invocation_ref,
                    parameter_preset_ref=invocation.parameter_preset_ref,
                    target_contract_ref=contract.contract_ref,
                    target_ref=option.target_ref,
                    gap_to_arrival_envelope_m=assessment.gap_to_envelope_m,
                    horizontal_distance_m=math.hypot(target.x-pos.x, target.z-pos.z),
                    desired_mineflayer_yaw_rad=mineflayer_yaw_to_target(pos, target),
                    observation_status="OUTSIDE",
                    next_step=(
                        "NATIVE_LOOK_AND_BOUNDED_MOVE_RESOLUTION_REQUIRED_NOT_ISSUABLE"
                    ),
                    preset_max_distance_m=invocation.budget.max_distance_m,
                    full_envelope_reachable_within_distance_budget=(
                        assessment.gap_to_envelope_m
                        <= invocation.budget.max_distance_m
                    ),
                )
                step = interpreter.propose(
                    cursor, binding=binding, capability=capability,
                    readback=readback, intent_owner=owner.intent,
                    skill_execution=skill, supervisor=owner.supervisor,
                    at_ns=at_ns+1, provenance=provenance,
                    place_motion=motion,
                )
                proposal = step.proposal
                if (
                    step.status != "PROPOSED_NOT_ISSUED"
                    or proposal is None or proposal.binding is not binding
                    or proposal.physical_authorized or proposal.physical_issued
                    or proposal.preissue_persisted
                ):
                    raise I4AS2MotorProposalHold(
                        "original ActionPort did not return unissued proposal"
                    )
                return I4AS2FirstMoveProposal(
                    boundary, native, action_id, invocation.invocation_ref,
                    motion, ir, step.cursor, interpreter, proposal,
                )
        except (PhysicalIssueFenceError, I4AS2RunBoundaryHold) as exc:
            raise I4AS2MotorProposalHold("original issuer or WAL source not clear") from exc
