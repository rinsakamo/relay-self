"""Selected one-turn L1 MOVE → existing CPU Skill IR → guarded motor parent.

This opt-in DEV path issues through the *same* physical ActionPort and
Self-owned journal as EAT and ATTACK. No S49 movement chooser is revived.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_minimal_minecraft_dev import WorldStepReceipt
from experiments.cognitive_move_paper_witness_dev import PaperMoveWitnessSession
from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatGrant,
    PhysicalGrantStage,
)
from experiments.cognitive_physical_move_issue_dev import (
    PhysicalMoveDevReceipt,
    PhysicalMoveRefusal,
    issue_selected_move_dev,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.initial_skill_ir import (
    ActionOutcomeWitness,
    FiniteSkillInterpreter,
    compile_initial_skill,
)
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalCapability,
    PhysicalReadback,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


@dataclass(frozen=True, slots=True)
class CognitivePhysicalMoveResult:
    action: PhysicalMoveDevReceipt
    intent_id: str
    skill_execution_id: str
    selected_target_ref: str
    action_id: str
    journal_sha256: str
    initial_skill_ir: str
    initial_skill_step_status: str
    initial_skill_evaluation_status: str
    original_s49_authorized: bool = False
    qualifying_real_world: bool = False


async def issue_move_from_selected_l1_dev(
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
    paper_move_spool: Path | None = None,
    paper_move_owned_log: Path | None = None,
    paper_world_uuid: str | None = None,
    paper_actor_uuid: str | None = None,
) -> CognitivePhysicalMoveResult:
    """One complete selected MOVE parent; never infer destination arrival."""
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
        or receipt.status != "MOVE_TARGET_BOUND_NO_ISSUE"
        or receipt.move_target is None
        or len(receipt.native_probe_trace) != 2
        or receipt.current_frame is None
        or receipt.selection.option is None
        or receipt.selection.option.skill_id != "MOVE"
        or receipt.selection.option.skill_version != 1
        or receipt.selection.option.target_kind != "DESTINATION"
        or receipt.selection.option.target_ref != receipt.move_target.target_ref
        or receipt.current_frame.scope.self_id != self_id
        or intent_owner.current_intent is not None
        or supervisor.recorded_actions or supervisor.open_actions
    ):
        raise PhysicalMoveRefusal("only selected MOVE and exclusive physical owner admitted")
    journal.require_clear()
    previous, current = receipt.native_probe_trace
    if (
        session.started.session_id != current.session_id
        or receipt.move_target.native_probe_provenance != current.provenance
        or receipt.move_target.native_seq != current.seq
    ):
        raise PhysicalMoveRefusal("native MOVE session/source changed")
    provenance = Provenance(
        "cognitive-physical-move-dev", f"{current.session_id}:{current.seq}",
    )
    intent_owner.commit(
        intent_id, objective=receipt.selection.option.goal_id,
        at_ns=1, provenance=provenance,
    )
    skill = SkillExecution.start(
        f"cognitive-move-{uuid.uuid4().hex}",
        skill_id="MOVE", intent_commitment=intent_owner,
        at_ns=2, provenance=provenance,
    )
    action_id = f"cognitive-move-{uuid.uuid4().hex}"
    cap = PhysicalCapability("MOVE", 1, "movement", "DESTINATION", True)
    binding = PhysicalActionBinding(
        scope=receipt.current_frame.scope,
        intent_id=intent_id,
        goal_id=receipt.selection.option.goal_id,
        skill_id="MOVE", skill_version=1,
        skill_execution_id=skill.execution_id,
        action_id=action_id, capability_ref="MOVE", capability_version=1,
        body_channel="movement", target_kind="DESTINATION",
        target_ref=receipt.move_target.target_ref,
        native_seq=current.seq,
        native_request_id=current.request_id or "",
        native_source=current.provenance,
    )
    readback = PhysicalReadback(
        binding.scope, current.provenance,
        current.seq, current.request_id or "",
        (binding.target_ref,),
        current.snapshot.health > 0 and current.snapshot.oxygen_level != 0,
    )
    ir = compile_initial_skill(receipt.selection.option, capability=cap)
    interpreter = FiniteSkillInterpreter()
    cursor = interpreter.begin(
        receipt.selection, ir=ir, intent_owner=intent_owner,
        skill_execution=skill, registered_versions=frozenset({("MOVE", 1)}),
        deadline_ns=1000,
    )
    checked = interpreter.check_target(
        cursor, readback=readback, intent_owner=intent_owner,
        skill_execution=skill, at_ns=3,
    )
    proposed = interpreter.propose(
        checked.cursor, binding=binding, capability=cap, readback=readback,
        intent_owner=intent_owner, skill_execution=skill, supervisor=supervisor,
        at_ns=3, provenance=provenance,
    )
    assert proposed.proposal is not None

    def grant(stage: PhysicalGrantStage, authority: str) -> PhysicalEatGrant:
        return PhysicalEatGrant(
            stage, authority,
            Provenance(
                "operator-cli-unverified-" + stage.value.lower(),
                f"{current.session_id}:{current.seq}",
            ),
            intent_id, action_id, current.session_id,
            current.seq, current.request_id or "", binding.target_ref, True,
        )

    paper_witness = None
    if any(v is not None for v in (
        paper_move_spool, paper_move_owned_log, paper_world_uuid, paper_actor_uuid,
    )):
        if (
            not isinstance(paper_move_spool, Path)
            or not isinstance(paper_move_owned_log, Path)
            or not isinstance(paper_world_uuid, str)
            or not isinstance(paper_actor_uuid, str)
            or paper_move_owned_log.is_symlink()
            or not paper_move_owned_log.is_file()
        ):
            raise PhysicalMoveRefusal("all four independent Paper witness inputs required")
        paper_witness = PaperMoveWitnessSession(
            paper_move_spool, world_uuid=paper_world_uuid,
            actor_uuid=paper_actor_uuid, action_id=action_id,
            native_session_id=current.session_id,
            native_start=receipt.move_target.native_position,
            native_target=receipt.move_target.destination_position,
            read_owned_log=paper_move_owned_log.read_bytes,
        )
    effect = await issue_selected_move_dev(
        session, proposal=proposed.proposal,
        target=receipt.move_target,
        previous_probe=previous,
        current_probe=current,
        propose_grant=grant(PhysicalGrantStage.PROPOSE, propose_authority_id),
        issue_grant=grant(PhysicalGrantStage.ISSUE, issue_authority_id),
        intent_owner=intent_owner, skill_execution=skill,
        supervisor=supervisor, journal=journal, at_ns=4,
        provenance=provenance, grant_real_world=dev_physical_grant,
        acknowledge_dev_unverified_principal=acknowledge_unverified_principal,
        paper_witness=paper_witness,
    )
    persisted = PhysicalActionJournal.restore(journal.path, self_id=self_id)
    row = persisted.records[-1] if persisted.records else {}
    motion = row.get("motion") or {}
    if (
        persisted.digest != journal.digest or persisted.unresolved
        or effect.terminal.state is not ActionState.OUTCOME
        or supervisor.get(action_id) is not effect.terminal
        or row.get("status") != "NATIVE_MOVE_PROGRESS_STOP_READBACK"
        or row.get("capability") != "MOVE"
        or row.get("action_id") != action_id
        or row.get("intent_id") != intent_id
        or row.get("skill_execution_id") != skill.execution_id
        or row.get("session_id") != current.session_id
        or row.get("target_ref") != binding.target_ref
        or row.get("source_ref") != binding.native_source.reference
        or row.get("probe_seq") != current.seq
        or row.get("probe_request_id") != current.request_id
        or row.get("effect_seqs") != [
            effect.look.seq, effect.forward.seq, effect.stop.seq,
        ]
        or row.get("after_seq") != effect.final_stop.seq
        or motion.get("progress_seq") != effect.progress.seq
        or motion.get("stop_probe_seqs") != [
            effect.first_stop.seq, effect.final_stop.seq,
        ]
    ):
        raise PhysicalMoveRefusal("restored MOVE WAL does not match physical ACK/probes")
    evaluated = interpreter.observe_action(
        proposed.cursor, action=effect.terminal,
        witness=ActionOutcomeWitness(
            binding.scope, action_id, binding.native_source,
            journal_closed=True, effect_correlated=True,
        ),
        intent_owner=intent_owner, skill_execution=skill, at_ns=7,
    )
    if evaluated.status != "YIELD_EVALUATION":
        raise PhysicalMoveRefusal("MOVE parent not yielded to evaluation")
    return CognitivePhysicalMoveResult(
        effect, intent_id, skill.execution_id, binding.target_ref,
        action_id, journal.digest, "MOVE@1",
        proposed.status, evaluated.status,
    )
