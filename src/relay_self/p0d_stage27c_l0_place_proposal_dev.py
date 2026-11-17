"""Stage27c1: original restored L1 MOVE/PLACE -> finite L0 Action PROPOSAL.

A proposal is *not* an Action grant, a WAL PREPARED, a native LOOK or MOVE.
The existing resident issuer rejects this DESTINATION binding; physical
movement must wait for a separate original-owner parametric WAL/STOP path.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.cognitive_minimal_dev import Selection
from relay_self.initial_skill_ir import (
    FiniteSkillInterpreter,
    PhysicalSkillIR,
    SkillCursor,
    compile_invoked_skill,
)
from relay_self.p0d_stage26_gemma_l1_dev import PreparedStage26L1
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.p0d_stage27b_place_motion_dev import (
    Stage27PlaceMotionPlan,
    resolve_stage27_place_motion,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalActionProposalReceipt,
    PhysicalCapability,
    PhysicalReadback,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.skill_invocation import SkillInvocation


class Stage27L0ProposalRefusal(RuntimeError):
    """A fresh original Self MOVE cannot be promoted to a bounded L0 proposal."""


@dataclass(frozen=True, slots=True)
class Stage27L0PlaceProposal:
    self_id: str
    world_epoch: int
    native_session_id: str
    native_probe_seq: int
    original_invocation_ref: str
    original_preset_ref: str
    target_contract_ref: str
    intent_id: str
    skill_execution_id: str
    action_id: str
    ir: PhysicalSkillIR
    cursor: SkillCursor
    interpreter: FiniteSkillInterpreter
    proposal: PhysicalActionProposalReceipt
    native_grant: bool = False
    journal_prepared: bool = False
    physical_effect_sent: bool = False
    status: str = "PROPOSED_NOT_ISSUABLE_UNTIL_ORIGINAL_PLACE_WAL"


def propose_stage27c_original_place_move(
    prepared: PreparedStage26L1,
    handoff: Stage27OwnedMoveIntent,
    planned: Stage27PlaceMotionPlan,
    native: MineflayerObservation,
    *,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    world_epoch: int,
    capability: PhysicalCapability,
    at_ns: int,
    provenance: Provenance,
) -> Stage27L0PlaceProposal:
    """Use the *same* finite interpreter and original ActionPort, no issuance."""
    if (
        not isinstance(prepared, PreparedStage26L1)
        or not isinstance(handoff, Stage27OwnedMoveIntent)
        or not isinstance(planned, Stage27PlaceMotionPlan)
        or not isinstance(native, MineflayerObservation)
        or not isinstance(owner, CheckpointedCognitiveOwner)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(capability, PhysicalCapability)
        or not isinstance(provenance, Provenance)
        or type(at_ns) is not int or at_ns < 0
        or owner is not prepared.original_owner
        or owner.self_id != handoff.self_id
        or owner.fresh_native_observation_required
        or not physical.resident_mode
        or physical.closed
        or physical.active_action_ids
        or physical.current_native_sessions.get(owner.self_id)
        != prepared.native_session
        or physical.resident_states.get(owner.self_id) != "ONLINE"
        or not native.request_id
        or native.kind != "probe"
        or native.session_id != prepared.native_session
        or native.snapshot.time is None
        or native.snapshot.health <= 0
        or native.snapshot.oxygen_level == 0
        or native.provenance.source != "mineflayer"
        or native.provenance.reference != f"{native.session_id}:{native.seq}"
    ):
        raise Stage27L0ProposalRefusal("original Self/native/physical source invalid")
    try:
        computed = resolve_stage27_place_motion(
            prepared, handoff, native, owner=owner,
            physical=physical, world_epoch=world_epoch,
        )
    except (ValueError, RuntimeError) as exc:
        raise Stage27L0ProposalRefusal(
            "original native PLACE Target cannot be revalidated"
        ) from exc
    if (
        computed != planned
        or planned.next_step
        != "NATIVE_LOOK_AND_BOUNDED_MOVE_RESOLUTION_REQUIRED_NOT_ISSUABLE"
        or planned.action_granted or planned.native_effect_issued
        or planned.world_goal_succeeded
        or planned.observation_status != "OUTSIDE"
    ):
        raise Stage27L0ProposalRefusal("original PLACE plan no longer current")
    options = prepared.round.frame.options
    if len(options) != 1 or not isinstance(options[0].invocation, SkillInvocation):
        raise Stage27L0ProposalRefusal("single original L1 MOVE invocation required")
    selected = options[0]
    invocation = selected.invocation
    if (
        invocation.invocation_ref != handoff.invocation_ref
        or invocation.invocation_ref != planned.invocation_ref
        or invocation.scope != prepared.round.frame.scope
        or invocation.target.contract is None
        or invocation.target.contract.contract_ref != planned.target_contract_ref
        or invocation.parameter_preset_ref != planned.parameter_preset_ref
        or selected.target_ref != planned.target_ref
        or capability.capability_ref != "MOVE"
        or capability.version != 1
        or capability.body_channel != "locomotion"
        or capability.target_kind != "DESTINATION"
        or not capability.available
        or at_ns <= owner.skills[handoff.skill_execution_id].events[-1].at_ns
    ):
        raise Stage27L0ProposalRefusal("original Invocation, capability or clock changed")
    PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=owner.self_id,
    ).require_clear()
    choice = Selection("READY", selected, "real Gemma BOUNDED original number 1",
                       invocation.scope)
    readback = PhysicalReadback(
        invocation.scope, native.provenance, native.seq, native.request_id,
        (selected.target_ref,), True,
    )
    ir = compile_invoked_skill(
        choice, definition=prepared.definition, target=invocation.target,
        constraints=invocation.constraints, budget=invocation.budget,
        provenance=invocation.provenance, capability=capability,
        arguments=invocation.arguments,
    )
    interpreter = FiniteSkillInterpreter()
    current_skill = owner.skills[handoff.skill_execution_id]
    deadline_ns = at_ns + invocation.budget.max_duration_ms * 1_000_000
    cursor = interpreter.begin(
        choice, ir=ir, intent_owner=owner.intent,
        skill_execution=current_skill,
        registered_versions=frozenset({("MOVE", 1)}),
        deadline_ns=deadline_ns,
    )
    cursor = interpreter.check_target(
        cursor, readback=readback, intent_owner=owner.intent,
        skill_execution=current_skill, at_ns=at_ns,
    ).cursor
    action_id = f"stage27c-{owner.self_id}-{native.seq}"
    binding = PhysicalActionBinding(
        invocation.scope, handoff.intent_id, invocation.goal_id,
        invocation.skill_id, invocation.skill_version,
        handoff.skill_execution_id, action_id, "MOVE", 1,
        "locomotion", selected.target_kind, selected.target_ref,
        native.seq, native.request_id, native.provenance,
    )
    step = interpreter.propose(
        cursor, binding=binding, capability=capability,
        readback=readback, intent_owner=owner.intent,
        skill_execution=current_skill, supervisor=owner.supervisor,
        at_ns=at_ns + 1, provenance=provenance, place_motion=planned,
    )
    proposal = step.proposal
    if (
        step.status != "PROPOSED_NOT_ISSUED"
        or proposal is None or proposal.binding is not binding
        or proposal.physical_authorized or proposal.physical_issued
        or proposal.preissue_persisted
    ):
        raise Stage27L0ProposalRefusal("finite interpreter returned unauthorized Action")
    return Stage27L0PlaceProposal(
        owner.self_id, world_epoch, prepared.native_session, native.seq,
        invocation.invocation_ref, invocation.parameter_preset_ref or "",
        planned.target_contract_ref, handoff.intent_id,
        handoff.skill_execution_id, action_id, ir, step.cursor,
        interpreter, proposal,
    )
