"""Bounded one-shot native MOVE DEV issuer; no planner or arrival certificate.

Uses the *existing* Action/Intent/SkillSupervisor, the same Self WAL as EAT
and ATTACK, and only Mineflayer look/forward/clear controls. The issuer
does not select a Goal/Skill/destination. This is neither full S49 STOP
settling qualification nor Paper tick-grounded movement.
"""
from __future__ import annotations

import asyncio
import math
import re
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    mineflayer_yaw_to_target,
)
from experiments.cognitive_move_target_resolution import ResolvedMoveTarget
from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatGrant,
    _check_grants,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionProposalReceipt
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


class PhysicalMoveRefusal(ValueError):
    """MOVE admission or source/collision/STOP readback is not demonstrated."""


@dataclass(frozen=True, slots=True)
class PhysicalMoveDevReceipt:
    terminal: ActionLifecycle
    look: MineflayerEffectResult
    forward: MineflayerEffectResult
    progress: MineflayerObservation
    stop: MineflayerEffectResult
    first_stop: MineflayerObservation
    final_stop: MineflayerObservation
    distance_advanced: float
    residual_motion: float
    status: str = "NATIVE_MOVE_PROGRESS_STOP_READBACK_DEV_ONLY"
    arrived_at_destination: bool = False
    paper_stop_settled_attested: bool = False
    qualifying_real_world: bool = False


def _horizontal(a, b) -> float:
    return math.hypot(a.x - b.x, a.z - b.z)


def _spatial(a, b) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def _check_admission(
    proposal: PhysicalActionProposalReceipt, target: ResolvedMoveTarget,
    previous: MineflayerObservation, current: MineflayerObservation,
) -> None:
    b = proposal.binding
    if (
        proposal.proposal.state is not ActionState.PROPOSED
        or not proposal.proposal.is_current_snapshot
        or proposal.physical_authorized or proposal.physical_issued
        or proposal.preissue_persisted
        or proposal.proposal.action_id != b.action_id
        or proposal.proposal.skill_execution_id != b.skill_execution_id
        or proposal.proposal.intent_id != b.intent_id
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,89}", b.action_id)
        or b.skill_id != "MOVE" or b.skill_version != 1
        or b.goal_id != "EXPLORE_WORLD"
        or b.capability_ref != "MOVE" or b.capability_version != 1
        or b.body_channel != "movement" or b.target_kind != "DESTINATION"
        or not isinstance(target, ResolvedMoveTarget)
        or target.physical_issued or target.reached or target.stop_settled_attested
        or target.status != "TARGET_BOUND_NO_PHYSICAL_MOVE_CAPABILITY"
        or target.scope != b.scope
        or target.goal_id != b.goal_id
        or target.skill_id != b.skill_id
        or target.skill_version != b.skill_version
        or target.target_ref != b.target_ref
        or target.native_probe_provenance != b.native_source
        or target.native_seq != b.native_seq
        or target.native_request_id != b.native_request_id
        or not isinstance(previous, MineflayerObservation)
        or not isinstance(current, MineflayerObservation)
        or previous.kind != "probe" or current.kind != "probe"
        or not previous.request_id or not current.request_id
        or previous.request_id == current.request_id
        or previous.session_id != b.scope.world_session_id
        or current.session_id != b.scope.world_session_id
        or not previous.seq < current.seq <= previous.seq + 32
        or current.seq != b.native_seq
        or current.request_id != b.native_request_id
        or current.provenance != b.native_source
        or target.native_position != current.snapshot.position
        or not .4 <= target.horizontal_distance <= 4
        or abs(target.vertical_delta) > .25
        or not math.isfinite(target.yaw_rad)
        or not math.isclose(
            target.horizontal_distance,
            _horizontal(target.native_position, target.destination_position),
            abs_tol=1e-9, rel_tol=0,
        )
        or not math.isclose(
            target.vertical_delta,
            target.destination_position.y - target.native_position.y,
            abs_tol=1e-9, rel_tol=0,
        )
        or not math.isclose(
            target.yaw_rad,
            mineflayer_yaw_to_target(
                target.native_position, target.destination_position,
            ), abs_tol=1e-9, rel_tol=0,
        )
        or previous.snapshot.health <= 0 or current.snapshot.health <= 0
        or previous.snapshot.oxygen_level == 0 or current.snapshot.oxygen_level == 0
        or _horizontal(previous.snapshot.position, current.snapshot.position) > .05
        or abs(previous.snapshot.position.y - current.snapshot.position.y) > .05
    ):
        raise PhysicalMoveRefusal("selected bounded MOVE, Body and native source stale")


async def _read(
    session: MineflayerProcessSession, *, after_seq: int,
    deadline: float,
):
    left = deadline - asyncio.get_running_loop().time()
    if left <= 0:
        raise PhysicalMoveRefusal("bounded native MOVE evidence timed out")
    msg = await asyncio.wait_for(session.receive(), timeout=left)
    if msg.session_id != session.started.session_id or msg.seq <= after_seq:
        raise PhysicalMoveRefusal("foreign/reordered MOVE event")
    if isinstance(msg, MineflayerObservation):
        if (
            msg.kind in {"death", "respawn"}
            or msg.snapshot.health <= 0
            or msg.snapshot.oxygen_level == 0
        ):
            raise PhysicalMoveRefusal("Body died during native MOVE")
    elif not isinstance(msg, MineflayerEffectResult):
        raise PhysicalMoveRefusal("unexpected native MOVE event")
    return msg


async def _ack(session, action_id, effect, *, after_seq, timeout_s):
    deadline = asyncio.get_running_loop().time() + timeout_s
    last = after_seq
    for _ in range(128):
        msg = await _read(session, after_seq=last, deadline=deadline)
        last = msg.seq
        if isinstance(msg, MineflayerEffectResult):
            if (
                msg.action_id != action_id or msg.effect != effect
                or msg.result != "applied"
            ):
                raise PhysicalMoveRefusal("native MOVE effect rejected/uncorrelated")
            return msg
    raise PhysicalMoveRefusal("native MOVE effect ACK horizon exceeded")


async def _progress(session, start, dest, *, after_seq, timeout_s):
    deadline = asyncio.get_running_loop().time() + timeout_s
    last = after_seq
    for _ in range(128):
        msg = await _read(session, after_seq=last, deadline=deadline)
        last = msg.seq
        if isinstance(msg, MineflayerEffectResult):
            raise PhysicalMoveRefusal("unexpected native receipt during motion")
        if (
            msg.kind == "move"
            and _horizontal(start, dest) - _horizontal(
                msg.snapshot.position, dest,
            ) >= .25
            and _horizontal(start, msg.snapshot.position) >= .25
        ):
            return msg
    raise PhysicalMoveRefusal("no target-directed bounded native progress")


async def _probe(session, request_id, *, after_seq, timeout_s):
    await session.send_observe(request_id)
    deadline = asyncio.get_running_loop().time() + timeout_s
    last = after_seq
    for _ in range(128):
        msg = await _read(session, after_seq=last, deadline=deadline)
        last = msg.seq
        if isinstance(msg, MineflayerEffectResult):
            raise PhysicalMoveRefusal("unrelated native effect during STOP readback")
        if msg.kind == "probe":
            if msg.request_id != request_id:
                raise PhysicalMoveRefusal("STOP probe request identity mismatch")
            return msg
    raise PhysicalMoveRefusal("post-STOP probe horizon exceeded")


async def issue_selected_move_dev(
    session: MineflayerProcessSession,
    *,
    proposal: PhysicalActionProposalReceipt,
    target: ResolvedMoveTarget,
    previous_probe: MineflayerObservation,
    current_probe: MineflayerObservation,
    propose_grant: PhysicalEatGrant,
    issue_grant: PhysicalEatGrant,
    intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
    supervisor: ActionSupervisor,
    journal: PhysicalActionJournal,
    at_ns: int,
    provenance: Provenance,
    grant_real_world: bool,
    acknowledge_dev_unverified_principal: bool,
    evidence_timeout_s: float = 2.0,
    stop_probe_interval_s: float = .2,
) -> PhysicalMoveDevReceipt:
    """Guarded short forward burst with exactly one preissue WAL reservation.

    On post-reservation ambiguity no new Action may replay. After a forward
    attempt, send clear_controls ONCE as best-effort even if motion evidence
    fails, but never treat that send as an ACK or an UNKNOWN resolution.
    """
    if (
        grant_real_world is not True
        or acknowledge_dev_unverified_principal is not True
        or not isinstance(session, MineflayerProcessSession)
        or session.process_returncode is not None
        or not isinstance(proposal, PhysicalActionProposalReceipt)
        or not isinstance(intent_owner, IntentCommitment)
        or not isinstance(skill_execution, SkillExecution)
        or not isinstance(supervisor, ActionSupervisor)
        or not isinstance(journal, PhysicalActionJournal)
        or type(at_ns) is not int or at_ns < 0
        or not isinstance(provenance, Provenance)
        or type(evidence_timeout_s) not in (int, float)
        or not .1 <= evidence_timeout_s <= 10
        or type(stop_probe_interval_s) not in (int, float)
        or not .15 <= stop_probe_interval_s <= 1
    ):
        raise PhysicalMoveRefusal("exclusive finite MOVE DEV authority required")
    journal.require_clear()
    _check_admission(proposal, target, previous_probe, current_probe)
    binding = proposal.binding
    _check_grants(binding, propose_grant, issue_grant)
    if (
        session.started.session_id != binding.scope.world_session_id
        or journal._body["self_id"] != binding.scope.self_id
        or intent_owner.current_intent is None
        or intent_owner.current_intent.intent_id != binding.intent_id
        or intent_owner.current_intent.objective != binding.goal_id
        or intent_owner.pending_reconsideration is not None
        or not skill_execution.is_current_snapshot
        or skill_execution.state is not SkillState.STARTED
        or skill_execution.execution_id != binding.skill_execution_id
        or skill_execution.skill_id != binding.skill_id
        or skill_execution.intent_id != binding.intent_id
        or supervisor.open_actions or supervisor.recorded_actions
        or at_ns < max(intent_owner.last_at_ns or 0, skill_execution.events[-1].at_ns)
        or (journal.records
            and journal.records[-1]["session_id"] == current_probe.session_id
            and journal.records[-1]["after_seq"] >= current_probe.seq)
    ):
        raise PhysicalMoveRefusal("current MOVE owner/channel or native seq busy/stale")

    authorized = proposal.proposal.authorize(
        at_ns=at_ns, provenance=propose_grant.provenance,
        authority=propose_grant.authority_id,
    )
    journal.prepare_move(
        binding, current_probe,
        destination_id=target.target_ref.removeprefix("destination:").split("@", 1)[0],
        destination=target.destination_position,
        destination_source=target.destination_provenance,
    )
    issued = supervisor.issue(
        authorized, at_ns=at_ns + 1, deadline_ns=at_ns + 1000,
        provenance=issue_grant.provenance,
    )
    assert supervisor.get(binding.action_id) is issued
    forward_attempted = False
    stop_attempted = False
    stop_id = binding.action_id + "-stop"
    try:
        look_id = binding.action_id + "-look"
        await session.send_look(look_id, yaw=target.yaw_rad, pitch=0)
        look = await _ack(
            session, look_id, "look",
            after_seq=current_probe.seq, timeout_s=evidence_timeout_s,
        )
        forward_id = binding.action_id + "-forward"
        forward_attempted = True
        await session.send_set_control(forward_id, control="forward", state=True)
        forward = await _ack(
            session, forward_id, "set_control",
            after_seq=look.seq, timeout_s=evidence_timeout_s,
        )
        progress = await _progress(
            session, target.native_position, target.destination_position,
            after_seq=forward.seq, timeout_s=evidence_timeout_s,
        )
        # Even if the stop send throws or its ACK is lost it is NOT retried.
        stop_attempted = True
        await session.send_clear_controls(stop_id)
        stop = await _ack(
            session, stop_id, "clear_controls",
            after_seq=progress.seq, timeout_s=evidence_timeout_s,
        )
        first_stop = await _probe(
            session, binding.action_id + "-after-stop-00",
            after_seq=stop.seq, timeout_s=evidence_timeout_s,
        )
        await asyncio.sleep(stop_probe_interval_s)
        final_stop = await _probe(
            session, binding.action_id + "-after-stop-01",
            after_seq=first_stop.seq, timeout_s=evidence_timeout_s,
        )
        advanced = _horizontal(
            target.native_position, target.destination_position,
        ) - _horizontal(
            progress.snapshot.position, target.destination_position,
        )
        residual = _spatial(
            first_stop.snapshot.position, final_stop.snapshot.position,
        )
        if advanced < .25 or residual > .05:
            raise PhysicalMoveRefusal("MOVE progress or STOP native stability unverified")
        terminal = supervisor.record_outcome(
            binding.action_id, at_ns=at_ns + 2, provenance=final_stop.provenance,
        )
        journal.close_move(
            binding, current_probe, look, forward, progress, stop,
            first_stop, final_stop, terminal, supervisor,
        )
        return PhysicalMoveDevReceipt(
            terminal, look, forward, progress, stop, first_stop,
            final_stop, advanced, residual,
        )
    except BaseException:
        if forward_attempted and not stop_attempted:
            stop_attempted = True
            try:
                # Cancellation/transport fault: best-effort STOP, not authority
                # to reissue and never a substitute for STOP readback.
                await asyncio.wait_for(
                    asyncio.shield(session.send_clear_controls(stop_id)),
                    timeout=.5,
                )
            except BaseException:
                pass
        if supervisor.get(binding.action_id).state is ActionState.ISSUED:
            supervisor.mark_unknown(
                binding.action_id, at_ns=at_ns + 2,
                provenance=current_probe.provenance,
            )
        # Preserve PREPARED_UNRESOLVED on disk; never auto-retry.
        raise
