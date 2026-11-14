"""One selected L1 ATTACK@1 -> existing L0 -> shared WAL physical issuer.

No target/Goal reselection, second Action owner or autonomous attack policy.
The DEV outcome is *attributed Mineflayer hurt observed*, NOT damage magnitude.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_minimal_minecraft_dev import WorldStepReceipt
from experiments.cognitive_physical_attack_issue_dev import (
    PhysicalAttackDevReceipt,
    PhysicalAttackRefusal,
    issue_selected_attack_dev,
)
from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatGrant,
    PhysicalGrantStage,
)
from experiments.cognitive_s49_readonly_handoff import assess_s49_readonly_handoff
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability, PhysicalReadback
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution
from relay_self.skill_ir_l0 import (
    ActionStep,
    EndStep,
    L0SkillInterpreter,
    L0StepReceipt,
    SkillIR,
    compile_skill_ir,
)


@dataclass(frozen=True, slots=True)
class CognitivePhysicalAttackResult:
    action: PhysicalAttackDevReceipt
    intent_id: str
    skill_execution_id: str
    selected_target_ref: str
    action_id: str
    journal_sha256: str
    l0_trace: tuple[L0StepReceipt, ...]
    qualification_attested: bool = False
    skill_execution_snapshot: SkillExecution | None = field(
        default=None, repr=False, compare=False,
    )


async def issue_attack_from_selected_l1_dev(
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
) -> CognitivePhysicalAttackResult:
    if (
        not isinstance(session, MineflayerProcessSession)
        or not isinstance(receipt, WorldStepReceipt)
        or not isinstance(intent_owner, IntentCommitment)
        or not isinstance(supervisor, ActionSupervisor)
        or not isinstance(journal, PhysicalActionJournal)
        or type(self_id) is not str or not self_id
        or type(intent_id) is not str or not intent_id
        or type(propose_authority_id) is not str or not propose_authority_id
        or type(issue_authority_id) is not str or not issue_authority_id
        or propose_authority_id == issue_authority_id
        or dev_physical_grant is not True
        or acknowledge_unverified_principal is not True
        or receipt.status != "S49_SHADOW_READY"
        or receipt.s49_readonly_handoff is None
        or len(receipt.native_probe_trace) != 2
        or receipt.current_frame is None
        or receipt.selection.option is None
        or receipt.selection.option.skill_id != "ATTACK"
        or receipt.selection.option.skill_version != 1
        or receipt.selection.option.target_kind != "ZOMBIE"
        or receipt.s49_readonly_handoff.proposed_intent_id != intent_id
        or receipt.current_frame.scope.self_id != self_id
        or intent_owner.current_intent is not None
        or supervisor.recorded_actions
    ):
        raise PhysicalAttackRefusal(
            "real selected ATTACK and exclusive DEV physical owner required"
        )
    journal.require_clear()
    previous, current = receipt.native_probe_trace
    if session.started.session_id != current.session_id:
        raise PhysicalAttackRefusal("native World session changed after L1 choice")
    witness = assess_s49_readonly_handoff(
        receipt.selection,
        original_frame=receipt.initial_frame,
        current_frame=receipt.current_frame,
        previous_probe=previous,
        current_probe=current,
        proposed_intent_id=intent_id,
    )
    if witness.target_entity_id is None:
        raise PhysicalAttackRefusal("selected zombie identity not observed")
    option = receipt.selection.option
    provenance = Provenance(
        "cognitive-physical-attack-dev",
        f"{current.session_id}:{current.seq}",
    )
    intent_owner.commit(
        intent_id, objective=option.goal_id, at_ns=1, provenance=provenance,
    )
    skill = SkillExecution.start(
        f"cognitive-attack-{uuid.uuid4().hex}",
        skill_id=option.skill_id, intent_commitment=intent_owner,
        at_ns=2, provenance=provenance,
    )
    capability = PhysicalCapability("ATTACK", 1, "hand", "ZOMBIE", True)
    ir = SkillIR(
        skill_id=option.skill_id, version=option.skill_version,
        origin_task_ref=f"dev-innate-attack:{current.session_id}:{current.seq}",
        generation=1, scope=receipt.current_frame.scope,
        goal_id=option.goal_id, target_kind=option.target_kind,
        target_ref=witness.target_ref, provenance=provenance,
        entry="attack-action",
        steps=(
            ActionStep("attack-action", "ATTACK", 1, "after-action"),
            EndStep("after-action", "SUCCESS_CANDIDATE"),
        ),
        max_actions=1, max_duration_ns=60_000_000_000,
    )
    compiled = compile_skill_ir(
        ir, capabilities=(capability,), predicate_refs=frozenset(),
    )
    l0 = L0SkillInterpreter(
        compiled, intent_owner=intent_owner, skill_execution=skill,
        supervisor=supervisor, scope=receipt.current_frame.scope,
        admitted_version=option.skill_version, admitted_generation=1,
        started_ns=time.monotonic_ns(),
    )
    steps: list[L0StepReceipt] = []
    request = l0.tick(now_ns=time.monotonic_ns())
    if request.status != "PROPOSE_ACTION" or request.capability_ref != "ATTACK":
        raise PhysicalAttackRefusal("L0 refused selected ATTACK capability")
    steps.append(request)
    readback = PhysicalReadback(
        scope=receipt.current_frame.scope, source=current.provenance,
        seq=current.seq, request_id=current.request_id or "",
        observed_target_refs=(witness.target_ref,),
        body_viable=(
            current.snapshot.health > 0 and current.snapshot.oxygen_level != 0
        ),
    )
    proposed = l0.propose_pending(readback=readback, at_ns=3, provenance=provenance)
    if proposed.binding.action_id != request.action_id:
        raise PhysicalAttackRefusal("L0 ATTACK identity changed before proposal")
    waiting = l0.tick(now_ns=time.monotonic_ns())
    if waiting.status != "AWAIT_ACTION":
        raise PhysicalAttackRefusal("L0 did not wait for physical ATTACK owner")
    steps.append(waiting)

    binding = proposed.binding

    def grant(stage: PhysicalGrantStage, label: str) -> PhysicalEatGrant:
        return PhysicalEatGrant(
            stage=stage, authority_id=label,
            provenance=Provenance(
                "operator-cli-unverified-" + stage.value.lower(),
                f"{binding.scope.world_session_id}:{binding.native_seq}",
            ),
            intent_id=binding.intent_id, action_id=binding.action_id,
            session_id=binding.scope.world_session_id or "",
            probe_seq=binding.native_seq, probe_request_id=binding.native_request_id,
            selected_target_ref=binding.target_ref, granted=True,
        )

    effect = await issue_selected_attack_dev(
        session, proposal=proposed, previous_probe=previous,
        current_probe=current,
        propose_grant=grant(PhysicalGrantStage.PROPOSE, propose_authority_id),
        issue_grant=grant(PhysicalGrantStage.ISSUE, issue_authority_id),
        intent_owner=intent_owner, skill_execution=skill,
        supervisor=supervisor, journal=journal, at_ns=4,
        provenance=provenance, grant_real_world=dev_physical_grant,
        acknowledge_dev_unverified_principal=acknowledge_unverified_principal,
    )
    advanced = l0.tick(now_ns=time.monotonic_ns())
    steps.append(advanced)
    if advanced.status == "ADVANCED":
        steps.append(l0.tick(now_ns=time.monotonic_ns()))
    return CognitivePhysicalAttackResult(
        effect, intent_id, skill.execution_id, binding.target_ref,
        binding.action_id, journal.digest, tuple(steps),
        skill_execution_snapshot=skill,
    )
