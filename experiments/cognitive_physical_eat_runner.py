"""Explicit one-turn L1 EAT -> Physical ActionPort -> durable parent Action.

This is the *single* new opt-in DEV issuer branch. It never calls the old
controlled_minecraft_vertical physical executor, chooses food after L1 or
auto-retries any potentially applied native effect. The old S49 read-only
witness is only a source/target preflight, not an S49 authority.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_minimal_minecraft_dev import WorldStepReceipt
from experiments.cognitive_physical_action_preflight import (
    propose_initial_skill_from_cognitive_readonly_evidence,
)
from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatDevReceipt,
    PhysicalEatGrant,
    PhysicalEatRefusal,
    PhysicalGrantStage,
    issue_selected_eat_dev,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.initial_skill_ir import ActionOutcomeWitness
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


@dataclass(frozen=True, slots=True)
class CognitivePhysicalEatResult:
    """One supervised parent Action with verified native children, DEV only."""

    action: PhysicalEatDevReceipt
    intent_id: str
    skill_execution_id: str
    selected_target_ref: str
    action_id: str
    journal_sha256: str
    initial_skill_ir: str
    initial_skill_step_status: str
    initial_skill_evaluation_status: str
    original_s49_authorized: bool = False
    qualification_attested: bool = False


async def issue_eat_from_selected_l1_dev(
    session: MineflayerProcessSession,
    receipt: WorldStepReceipt,
    *,
    intent_owner: IntentCommitment,
    supervisor: ActionSupervisor,
    journal: PhysicalActionJournal,
    self_id: str,
    intent_id: str,
    propose_authority_id: str,
    issue_authority_id: str,
    dev_physical_grant: bool,
    acknowledge_unverified_principal: bool,
) -> CognitivePhysicalEatResult:
    """Never issue unless the *real* L1 choice and both probes are EAT-ready.

    The caller must have independently validated the actual operator's grant,
    isolated test World ownership and the correct resumed Self journal. CLI
    authority labels are explicitly not cryptographic proof of principal.
    """
    if (
        not isinstance(session, MineflayerProcessSession)
        or not isinstance(receipt, WorldStepReceipt)
        or not isinstance(intent_owner, IntentCommitment)
        or not isinstance(supervisor, ActionSupervisor)
        or not isinstance(journal, PhysicalActionJournal)
        or not isinstance(self_id, str) or not self_id
        or not isinstance(intent_id, str) or not intent_id
        or not isinstance(propose_authority_id, str) or not propose_authority_id
        or not isinstance(issue_authority_id, str) or not issue_authority_id
        or propose_authority_id == issue_authority_id
        or dev_physical_grant is not True
        or acknowledge_unverified_principal is not True
        or receipt.status != "S49_SHADOW_READY"
        or receipt.s49_readonly_handoff is None
        or len(receipt.native_probe_trace) != 2
        or receipt.current_frame is None
        or receipt.selection.option is None
        or receipt.selection.option.skill_id != "EAT"
        or receipt.selection.option.skill_version != 1
        or receipt.selection.option.target_kind != "FOOD"
        or receipt.s49_readonly_handoff.proposed_intent_id != intent_id
        or receipt.current_frame.scope.self_id != self_id
        or intent_owner.current_intent is not None
        or supervisor.recorded_actions
    ):
        raise PhysicalEatRefusal("real selected EAT and exclusive DEV physical owner required")
    # Restore checked above the World launch; check again immediately before
    # mutating Intent or attempting durable PRE-ISSUE reservation.
    journal.require_clear()
    previous, current = receipt.native_probe_trace
    if session.started.session_id != current.session_id:
        raise PhysicalEatRefusal("native World session changed after L1 choice")

    provenance = Provenance(
        "cognitive-physical-eat-dev",
        f"{current.session_id}:{current.seq}",
    )
    # Logical ordering inside a one-shot root (not host/World wall clock).
    intent_owner.commit(
        intent_id, objective=receipt.selection.option.goal_id,
        at_ns=1, provenance=provenance,
    )
    skill = SkillExecution.start(
        f"cognitive-eat-{uuid.uuid4().hex}",
        skill_id=receipt.selection.option.skill_id,
        intent_commitment=intent_owner, at_ns=2, provenance=provenance,
    )
    action_id = f"cognitive-eat-{uuid.uuid4().hex}"
    # EAT parent = an existing WorldBody-controlled, ordered
    # equip_item->consume_held capability, not an extra food-choice policy.
    capability = PhysicalCapability("EAT", 1, "hand", "FOOD", True)
    interpreted = propose_initial_skill_from_cognitive_readonly_evidence(
        receipt.selection,
        original_frame=receipt.initial_frame,
        current_frame=receipt.current_frame,
        previous_probe=previous, current_probe=current,
        selected_intent_id=intent_id,
        capability=capability,
        action_id=action_id,
        intent_owner=intent_owner,
        skill_execution=skill,
        supervisor=supervisor,
        registered_versions=frozenset({("EAT", 1)}),
        at_ns=3, deadline_ns=1000,
        provenance=provenance,
    )
    proposal = interpreted.port_proposal
    binding = proposal.binding
    def grant(stage: PhysicalGrantStage, authority: str) -> PhysicalEatGrant:
        return PhysicalEatGrant(
            stage=stage,
            authority_id=authority,
            provenance=Provenance(
                "operator-cli-unverified-" + stage.value.lower(),
                f"{binding.scope.world_session_id}:{binding.native_seq}",
            ),
            intent_id=binding.intent_id,
            action_id=binding.action_id,
            session_id=binding.scope.world_session_id or "",
            probe_seq=binding.native_seq,
            probe_request_id=binding.native_request_id,
            selected_target_ref=binding.target_ref,
            granted=True,
        )

    effect = await issue_selected_eat_dev(
        session,
        proposal=proposal,
        previous_probe=previous,
        current_probe=current,
        propose_grant=grant(PhysicalGrantStage.PROPOSE, propose_authority_id),
        issue_grant=grant(PhysicalGrantStage.ISSUE, issue_authority_id),
        intent_owner=intent_owner,
        skill_execution=skill,
        supervisor=supervisor,
        journal=journal,
        at_ns=4,
        provenance=provenance,
        grant_real_world=dev_physical_grant,
        acknowledge_dev_unverified_principal=acknowledge_unverified_principal,
    )
    # A successful return from the existing physical issuer is not alone a
    # Skill/Goal success. Read back the persisted WAL independently of its
    # in-memory journal snapshot; correlate the exact original parent Action,
    # native child ACKs and later food/inventory evidence before L0 advances.
    persisted = PhysicalActionJournal.restore(journal.path, self_id=self_id)
    row = persisted.records[-1] if persisted.records else {}
    if (
        persisted.digest != journal.digest or persisted.unresolved
        or effect.terminal.state is not ActionState.OUTCOME
        or supervisor.get(binding.action_id) is not effect.terminal
        or row.get("status") != "NATIVE_EAT_OUTCOME"
        or row.get("action_id") != binding.action_id
        or row.get("intent_id") != binding.intent_id
        or row.get("skill_execution_id") != binding.skill_execution_id
        or row.get("target_ref") != binding.target_ref
        or row.get("session_id") != binding.scope.world_session_id
        or row.get("source_ref") != binding.native_source.reference
        or row.get("probe_seq") != binding.native_seq
        or row.get("probe_request_id") != binding.native_request_id
        or row.get("effect_seqs") != [effect.equip.seq, effect.consume.seq]
        or row.get("after_seq") != effect.after.seq
        or row.get("count_before") != effect.item_count_before
        or row.get("count_after") != effect.item_count_after
        or row.get("food_before") != int(effect.food_before)
        or row.get("food_after") != int(effect.food_after)
    ):
        raise PhysicalEatRefusal("terminal EAT does not match restored physical WAL")
    step = interpreted.interpreter.observe_action(
        interpreted.cursor,
        action=effect.terminal,
        witness=ActionOutcomeWitness(
            binding.scope, binding.action_id, binding.native_source,
            journal_closed=True, effect_correlated=True,
        ),
        intent_owner=intent_owner, skill_execution=skill,
        at_ns=7,  # logical Action time only, not measured latency
    )
    if step.status != "YIELD_EVALUATION":
        raise PhysicalEatRefusal("EAT Skill IR did not yield terminal evaluation")
    return CognitivePhysicalEatResult(
        effect, intent_id, skill.execution_id,
        binding.target_ref, action_id, journal.digest,
        f"{interpreted.ir.skill_id}@{interpreted.ir.version}",
        interpreted.status, step.status,
    )
