"""I Unified Q4: restored historical Stage27 PLACE receipt/executor bridge.

The file was absent from Unified I despite an existing caller import.
Preserved as a historical DEV implementation: it MUST be invoked only after
the ORIGINAL B Owner/WAL/physical lease has authorized and bound its child
effects. It never grants original real S2/World admission by import alone.


This is a DEV-only finite physical motor path, not navigation or autonomous
Goal success. It retains the original Stage26 Self-selected Invocation, records
one schema-v2 canonical WAL parent, and never silently calls the old RELATIVE
issuer. Real Paper and Gemma qualification must be run on the local host.
"""
from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    begin_physical_issue_dev,
    check_dev_issuer_preflight,
    check_physical_source_window,
    finish_physical_issue_dev,
    mark_ambiguous_physical_dev,
)
from experiments.cognitive_physical_move_issue_dev import _native, _settled
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.initial_skill_ir import ActionOutcomeWitness
from relay_self.p0d_stage26_gemma_l1_dev import PreparedStage26L1
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.p0d_stage27b_place_motion_dev import Stage27PlaceMotionPlan
from relay_self.p0d_stage27c_l0_place_proposal_dev import Stage27L0PlaceProposal
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionProposalReceipt
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.skill_invocation import SkillInvocation


class Stage27PlaceMoveRefusal(ValueError):
    """Original PLACE physical MOVE source/issuer is not eligible."""


@dataclass(frozen=True, slots=True)
class Stage27PlaceMoveReceipt:
    original_invocation_ref: str
    original_preset_ref: str
    target_contract_ref: str
    action_id: str
    native_session_id: str
    look_ack: MineflayerEffectResult
    start_ack: MineflayerEffectResult
    stop_ack: MineflayerEffectResult
    initial_stop_probe: MineflayerObservation
    first_stable_probe: MineflayerObservation
    settled_probe: MineflayerObservation
    displacement_m: float
    journal_status: str
    journal_sha256: str
    all_stop_probes: tuple[MineflayerObservation, ...]
    l0_step_status: str = "YIELD_EVALUATION"
    l0_goal_succeeded: bool = False
    native_effect_issued: bool = True
    skill_success_attested: bool = False
    paper_causal_attribution: bool = False
    gait_mode: str = "WALK"
    gait_control_ack: MineflayerEffectResult | None = None


async def issue_selected_place_move_dev(
    session: MineflayerProcessSession,
    *,
    proposal: PhysicalActionProposalReceipt,
    l0: Stage27L0PlaceProposal,
    prepared: PreparedStage26L1,
    handoff: Stage27OwnedMoveIntent,
    motion: Stage27PlaceMotionPlan,
    previous_probe: MineflayerObservation,
    current_probe: MineflayerObservation,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    propose_grant: PhysicalDevGrant,
    issue_grant: PhysicalDevGrant,
    journal: PhysicalActionJournal,
    at_ns: int,
    provenance: Provenance,
    grant_real_world: bool,
    acknowledge_dev_unverified_principal: bool,
    evidence_timeout_s: float = 15.0,
    pulse_seconds: float = 0.15,
    bind_native_children: Callable[[str], None] | None = None,
    pre_native_evidence: Callable[[PhysicalActionJournal, str], None] | None = None,
    allow_prior_terminal_place_actions: bool = False,
    settlement_probe_limit: int | None = None,
    precision_gait: str | None = None,
) -> Stage27PlaceMoveReceipt:
    """Only call through PhysicalIssueAdmission.issue_place_move and its lease."""
    if (
        not isinstance(session, MineflayerProcessSession)
        or not isinstance(proposal, PhysicalActionProposalReceipt)
        or not isinstance(l0, Stage27L0PlaceProposal)
        or not isinstance(prepared, PreparedStage26L1)
        or not isinstance(handoff, Stage27OwnedMoveIntent)
        or not isinstance(motion, Stage27PlaceMotionPlan)
        or not isinstance(owner, CheckpointedCognitiveOwner)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(journal, PhysicalActionJournal)
        or type(pulse_seconds) not in (float, int)
        or not math.isfinite(pulse_seconds)
        or type(allow_prior_terminal_place_actions) is not bool
        or precision_gait not in (None, "WALK", "SNEAK")
        or (settlement_probe_limit is not None and (
            type(settlement_probe_limit) is not int
            or not 3 <= settlement_probe_limit <= 4096
        ))
        or not 0.15 <= pulse_seconds <= 0.75
        or owner is not prepared.original_owner
        or owner.self_id != handoff.self_id
        or owner.self_id != l0.self_id
        or session.started.session_id != prepared.native_session
        or motion.self_id != l0.self_id
        or motion.native_probe_seq != l0.native_probe_seq
        or motion.invocation_ref != l0.original_invocation_ref
        or motion.parameter_preset_ref != l0.original_preset_ref
        or motion.target_contract_ref != l0.target_contract_ref
        or motion.intent_id != l0.intent_id
        or motion.skill_execution_id != l0.skill_execution_id
        or motion.world_epoch != l0.world_epoch
        or l0.proposal is not proposal
        or proposal.binding.action_id != l0.action_id
        or proposal.binding.scope.self_id != owner.self_id
        or proposal.binding.scope.world_session_id != prepared.native_session
        or proposal.binding.target_kind != "DESTINATION"
        or proposal.binding.target_ref != motion.target_ref
        or proposal.binding.native_seq != current_probe.seq
        or proposal.binding.native_request_id != current_probe.request_id
        or physical.current_native_sessions.get(owner.self_id)
        != session.started.session_id
        or physical.resident_states.get(owner.self_id) != "ONLINE"
        or physical.active_action_ids != (proposal.binding.action_id,)
    ):
        raise Stage27PlaceMoveRefusal("original PLACE physical owner and bounded source invalid")
    opts = prepared.round.frame.options
    if len(opts) != 1 or not isinstance(opts[0].invocation, SkillInvocation):
        raise Stage27PlaceMoveRefusal("original complete MOVE invocation missing")
    invocation = opts[0].invocation
    if (
        l0.ir.invocation is not invocation
        or invocation.invocation_ref != motion.invocation_ref
        or invocation.parameter_preset_ref != motion.parameter_preset_ref
        or l0.cursor.pending_action_id != l0.action_id
        or l0.cursor.action_count != 1
        or l0.cursor.blocked
        or type(at_ns) is not int
        or at_ns + 2 >= l0.cursor.deadline_ns
        or pulse_seconds * 1000 > invocation.budget.max_duration_ms
        or invocation.budget.max_actions < 1
        or current_probe.snapshot.time is None
        or current_probe.snapshot.health <= 0
        or current_probe.snapshot.oxygen_level == 0
        or owner.intent.current_intent is None
        or owner.intent.current_intent.intent_id != handoff.intent_id
        or handoff.skill_execution_id not in owner.skills
        or owner.skills[handoff.skill_execution_id] is not
        owner.skills[l0.skill_execution_id]
    ):
        raise Stage27PlaceMoveRefusal("original Invocation/budget/lifecycle invalid")
    try:
        # The original admission wrapper already revalidated the exact
        # native PLACE result immediately before acquiring this exclusive
        # lease. The lease itself would make a second Stage27b call fail.
        l0.interpreter._require_cursor(
            l0.cursor, at_ns=at_ns,
            intent_owner=owner.intent,
            skill_execution=owner.skills[handoff.skill_execution_id],
        )
    except (RuntimeError, ValueError) as exc:
        raise Stage27PlaceMoveRefusal(
            "original native PLACE motion and L0 cursor changed before issue"
        ) from exc
    if motion.action_granted or motion.native_effect_issued:
        raise Stage27PlaceMoveRefusal("original native PLACE motion plan already consumed")
    check_dev_issuer_preflight(
        session, proposal, intent_owner=owner.intent,
        skill_execution=owner.skills[handoff.skill_execution_id],
        supervisor=owner.supervisor, journal=journal,
        at_ns=at_ns, provenance=provenance,
        grant_real_world=grant_real_world,
        acknowledge_dev_unverified_principal=acknowledge_dev_unverified_principal,
        evidence_timeout_s=evidence_timeout_s, refusal=Stage27PlaceMoveRefusal,
    )
    check_physical_source_window(
        proposal, previous_probe, current_probe,
        capability="MOVE", target_kind="DESTINATION",
        refusal=Stage27PlaceMoveRefusal,
    )
    begin_physical_issue_dev(
        session, capability="MOVE", proposal=proposal,
        current_probe=current_probe, propose_grant=propose_grant,
        issue_grant=issue_grant, intent_owner=owner.intent,
        skill_execution=owner.skills[handoff.skill_execution_id],
        supervisor=owner.supervisor, journal=journal, at_ns=at_ns,
        refusal=Stage27PlaceMoveRefusal,
        place_invocation=invocation, place_motion=motion,
        allow_prior_original_place_terminals=allow_prior_terminal_place_actions,
        place_gait_mode=precision_gait,
    )
    return await complete_prepared_place_move_dev(
        session, proposal=proposal, l0=l0, handoff=handoff,
        motion=motion, current_probe=current_probe, owner=owner,
        journal=journal, invocation=invocation, at_ns=at_ns,
        evidence_timeout_s=evidence_timeout_s, pulse_seconds=pulse_seconds,
        bind_native_children=bind_native_children,
        pre_native_evidence=pre_native_evidence,
        settlement_probe_limit=settlement_probe_limit,
        precision_gait=precision_gait,
    )


async def complete_prepared_place_move_dev(
    session: MineflayerProcessSession, *,
    proposal: PhysicalActionProposalReceipt,
    l0: Stage27L0PlaceProposal,
    handoff: Stage27OwnedMoveIntent,
    motion: Stage27PlaceMotionPlan,
    current_probe: MineflayerObservation,
    owner: CheckpointedCognitiveOwner,
    journal: PhysicalActionJournal,
    invocation: SkillInvocation,
    at_ns: int,
    evidence_timeout_s: float,
    pulse_seconds: float,
    bind_native_children: Callable[[str], None] | None,
    pre_native_evidence: Callable[[PhysicalActionJournal, str], None] | None,
    settlement_probe_limit: int | None,
    precision_gait: str | None,
) -> Stage27PlaceMoveReceipt:
    """Shared original LOOK/forward/STOP/settle/terminal WAL implementation.

    Called by the existing Stage27 issuer, or by I4a *within the same*
    original physical lease that created its canonical PREPARED row.
    A historical PREPARED from an earlier call cannot be resumed here.
    """
    from relay_self.action import ActionState

    parent = proposal.binding.action_id
    rows = journal.records
    if (
        not rows or not journal.unresolved
        or rows[-1]["action_id"] != parent
        or rows[-1]["status"] != "PREPARED_UNRESOLVED"
        or rows[-1]["skill_execution_id"] != handoff.skill_execution_id
        or rows[-1]["intent_id"] != handoff.intent_id
        or owner.supervisor.get(parent).state is not ActionState.ISSUED
    ):
        raise Stage27PlaceMoveRefusal("original PREPARED parent not current")
    # Optional operator DEV evidence tap runs only after the original fsynced
    # PREPARED WAL and strictly before any native LOOK/forward/STOP write.
    # Failure keeps the original WAL unresolved; it never licenses a retry.
    if pre_native_evidence is not None:
        pre_native_evidence(journal, parent)
    look_id, start_id, stop_id = (
        parent + "-look", parent + "-start", parent + "-stop",
    )
    attempted_stop = False
    try:
        if bind_native_children is None:
            raise Stage27PlaceMoveRefusal("original LOOK/start/STOP child binding absent")
        bind_native_children(parent)
        assert motion.desired_mineflayer_yaw_rad is not None
        await session.send_look(
            look_id, yaw=motion.desired_mineflayer_yaw_rad, pitch=0.0,
        )
        look = await _native(
            session, session_id=current_probe.session_id,
            after_seq=current_probe.seq, action_id=look_id,
            effect="look", request_id=None, timeout_s=evidence_timeout_s,
        )
        assert isinstance(look, MineflayerEffectResult)
        gait_ack: MineflayerEffectResult | None = None
        if precision_gait == "SNEAK":
            # Separate ONE-SHOT child admitted only from the fsynced SNEAK
            # PREPARED row under the same original parent Action. STOP clears
            # both sneak and forward controls; no speed command is unbound.
            sneak_id = parent + "-sneak"
            await session.send_set_control(
                sneak_id, control="sneak", state=True,
            )
            gait_result = await _native(
                session, session_id=current_probe.session_id,
                after_seq=look.seq, action_id=sneak_id,
                effect="set_control", request_id=None,
                timeout_s=evidence_timeout_s,
            )
            assert isinstance(gait_result, MineflayerEffectResult)
            gait_ack = gait_result
        await session.send_set_control(start_id, control="forward", state=True)
        start = await _native(
            session, session_id=current_probe.session_id,
            after_seq=gait_ack.seq if gait_ack is not None else look.seq,
            action_id=start_id,
            effect="set_control", request_id=None, timeout_s=evidence_timeout_s,
        )
        assert isinstance(start, MineflayerEffectResult)
        await asyncio.sleep(pulse_seconds)
        attempted_stop = True
        await session.send_clear_controls(stop_id)
        stop = await _native(
            session, session_id=current_probe.session_id,
            after_seq=start.seq, action_id=stop_id,
            effect="clear_controls", request_id=None, timeout_s=evidence_timeout_s,
        )
        assert isinstance(stop, MineflayerEffectResult)
        initial, first, settled, all_stop = await _settled(
            session, native=current_probe.session_id,
            stop_seq=stop.seq, timeout_s=evidence_timeout_s,
            max_probe_requests=settlement_probe_limit,
        )
        closed: list[str] = []
        terminal = finish_physical_issue_dev(
            action_id=parent, after=settled,
            supervisor=owner.supervisor, journal=journal, at_ns=at_ns,
            close=lambda t: closed.append(journal.close_place_move(
                proposal.binding, invocation, current_probe,
                look, start, stop, initial, first, settled,
                t, owner.supervisor, gait_ack=gait_ack,
            )),
        )
        if len(closed) != 1:
            raise Stage27PlaceMoveRefusal("original PLACE WAL was not closed exactly once")
        # The real original finite Skill controller observes the same terminal
        # Action and canonical WAL consequence. It yields to Self evaluation,
        # without asserting that the Goal/Skill succeeded.
        step = l0.interpreter.observe_action(
            l0.cursor, action=terminal,
            witness=ActionOutcomeWitness(
                scope=proposal.binding.scope, action_id=parent,
                native_source=current_probe.provenance,
                journal_closed=True, effect_correlated=True,
            ),
            intent_owner=owner.intent,
            skill_execution=owner.skills[handoff.skill_execution_id],
            at_ns=at_ns + 2,
        )
        if step.status != "YIELD_EVALUATION":
            raise Stage27PlaceMoveRefusal("original L0 did not yield after physical Outcome")
        a, b = current_probe.snapshot.position, settled.snapshot.position
        return Stage27PlaceMoveReceipt(
            invocation.invocation_ref, invocation.parameter_preset_ref or "",
            motion.target_contract_ref, parent, session.started.session_id,
            look, start, stop, initial, first, settled,
            math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)),
            closed[0], journal.digest, all_stop,
            gait_mode=precision_gait or "WALK",
            gait_control_ack=gait_ack,
        )
    except BaseException:
        if not attempted_stop:
            # One best-effort emergency STOP; its original issue child is
            # consumed at most once and WAL remains PREPARED_UNRESOLVED.
            try:
                await session.send_clear_controls(stop_id)
            except BaseException:
                pass
        try:
            mark_ambiguous_physical_dev(
                action_id=parent, supervisor=owner.supervisor,
                probe=current_probe, at_ns=at_ns,
            )
        except BaseException:
            pass
        raise
