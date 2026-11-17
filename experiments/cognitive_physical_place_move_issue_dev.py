"""Stage27c2 experimental original-owner PLACE LOOK -> MOVE -> STOP issuer.

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
    native_effect_issued: bool = True
    skill_success_attested: bool = False
    paper_causal_attribution: bool = False


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
        or at_ns >= l0.cursor.deadline_ns
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
    )
    parent = proposal.binding.action_id
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
        await session.send_set_control(start_id, control="forward", state=True)
        start = await _native(
            session, session_id=current_probe.session_id,
            after_seq=look.seq, action_id=start_id,
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
        )
        closed: list[str] = []
        finish_physical_issue_dev(
            action_id=parent, after=settled,
            supervisor=owner.supervisor, journal=journal, at_ns=at_ns,
            close=lambda t: closed.append(journal.close_place_move(
                proposal.binding, invocation, current_probe,
                look, start, stop, initial, first, settled,
                t, owner.supervisor,
            )),
        )
        if len(closed) != 1:
            raise Stage27PlaceMoveRefusal("original PLACE WAL was not closed exactly once")
        a, b = current_probe.snapshot.position, settled.snapshot.position
        return Stage27PlaceMoveReceipt(
            invocation.invocation_ref, invocation.parameter_preset_ref or "",
            motion.target_contract_ref, parent, session.started.session_id,
            look, start, stop, initial, first, settled,
            math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)),
            closed[0], journal.digest, all_stop,
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
