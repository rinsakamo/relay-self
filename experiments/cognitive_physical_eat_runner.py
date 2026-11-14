"""Explicit one-turn L1 EAT -> Physical ActionPort -> durable parent Action.

This is the *single* new opt-in DEV issuer branch. It never calls the old
controlled_minecraft_vertical physical executor, chooses food after L1 or
auto-retries any potentially applied native effect. The old S49 read-only
witness is only a source/target preflight, not an S49 authority.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_minimal_minecraft_dev import WorldStepReceipt
from experiments.cognitive_physical_action_preflight import (
    propose_from_cognitive_readonly_evidence,
)
from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatDevReceipt,
    PhysicalEatGrant,
    PhysicalEatRefusal,
    PhysicalGrantStage,
    issue_selected_eat_dev,
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
class CognitivePhysicalEatResult:
    """One supervised parent Action with verified native children, DEV only."""

    action: PhysicalEatDevReceipt
    intent_id: str
    skill_execution_id: str
    selected_target_ref: str
    action_id: str
    journal_sha256: str
    l0_trace: tuple[L0StepReceipt, ...] = ()
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
    l0_skill_ir_dev: bool = False,
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
        or type(l0_skill_ir_dev) is not bool
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
    # EAT remains an already proven one-parent/two-child WorldBody capability,
    # never an L0 decomposition into unfenced native equip/consume.
    capability = PhysicalCapability("EAT", 1, "hand", "FOOD", True)
    l0: L0SkillInterpreter | None = None
    l0_steps: list[L0StepReceipt] = []
    if l0_skill_ir_dev:
        # Existing source-qualified two-probe handoff remains mandatory:
        # a typed L0/IR alone cannot establish the real Target's authority.
        witness = assess_s49_readonly_handoff(
            receipt.selection,
            original_frame=receipt.initial_frame,
            current_frame=receipt.current_frame,
            previous_probe=previous,
            current_probe=current,
            proposed_intent_id=intent_id,
        )
        option = receipt.selection.option
        assert option is not None
        # The IR is a fixed innate EAT@1 bootstrap for the *already selected*
        # L1 option, not an accepted model-generated skill nor a new food chooser.
        ir = SkillIR(
            skill_id=option.skill_id, version=option.skill_version,
            origin_task_ref=f"dev-innate-eat:{current.session_id}:{current.seq}",
            generation=1, scope=receipt.current_frame.scope,
            goal_id=option.goal_id, target_kind=option.target_kind,
            target_ref=witness.target_ref, provenance=provenance,
            entry="eat-action",
            steps=(
                ActionStep("eat-action", "EAT", 1, "after-action"),
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
        step = l0.tick(now_ns=time.monotonic_ns())
        if step.status != "PROPOSE_ACTION" or step.capability_ref != "EAT":
            raise PhysicalEatRefusal("L0 refused selected EAT capability")
        l0_steps.append(step)
        readback = PhysicalReadback(
            scope=receipt.current_frame.scope, source=current.provenance,
            seq=current.seq, request_id=current.request_id or "",
            observed_target_refs=(witness.target_ref,),
            body_viable=(
                current.snapshot.health > 0
                and current.snapshot.oxygen_level != 0
            ),
        )
        proposal = l0.propose_pending(
            readback=readback, at_ns=3, provenance=provenance,
        )
        if proposal.binding.action_id != step.action_id:
            raise PhysicalEatRefusal("L0 Action identity changed before proposal")
        l0_steps.append(l0.tick(now_ns=time.monotonic_ns()))
        if l0_steps[-1].status != "AWAIT_ACTION":
            raise PhysicalEatRefusal("L0 did not wait for the existing Action owner")
    else:
        action_id = f"cognitive-eat-{uuid.uuid4().hex}"
        proposal = propose_from_cognitive_readonly_evidence(
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
            at_ns=3,
            provenance=provenance,
        ).port_proposal
    action_id = proposal.binding.action_id

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
    if l0 is not None:
        # An OUTCOME from the existing ActionSupervisor, not native ACK alone,
        # advances L0. A terminal is a candidate, never Skill/Intent success.
        advanced = l0.tick(now_ns=time.monotonic_ns())
        l0_steps.append(advanced)
        if advanced.status == "ADVANCED":
            l0_steps.append(l0.tick(now_ns=time.monotonic_ns()))
    return CognitivePhysicalEatResult(
        effect, intent_id, skill.execution_id,
        binding.target_ref, action_id, journal.digest, tuple(l0_steps),
    )
