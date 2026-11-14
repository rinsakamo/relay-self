"""#843: single opt-in bounded native ATTACK issuer, shared Self-owned WAL.

This is DEV_ONLY: Mineflayer's source-attributed entity_hurt is not an
independent native Health/damage amount. Never claim damage or target death.
No retry after an uncertain native command and no separate physical owner.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerEntityHurt,
    MineflayerObservation,
)
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


class PhysicalAttackRefusal(ValueError):
    """A bounded DEV ATTACK lacks admissible current source/effect evidence."""


@dataclass(frozen=True, slots=True)
class PhysicalAttackDevReceipt:
    terminal: ActionLifecycle
    ack: MineflayerEffectResult
    hurt: MineflayerEntityHurt
    after: MineflayerObservation
    entity_id: int
    status: str = "NATIVE_ATTACK_HURT_OBSERVED_DEV_ONLY"
    independent_damage_attested: bool = False


def _check_window(
    proposal: PhysicalActionProposalReceipt,
    previous: MineflayerObservation,
    current: MineflayerObservation,
) -> int:
    if not isinstance(proposal, PhysicalActionProposalReceipt):
        raise PhysicalAttackRefusal("Physical ActionPort proposal required")
    b = proposal.binding
    if (
        proposal.proposal.state is not ActionState.PROPOSED
        or not proposal.proposal.is_current_snapshot
        or proposal.physical_authorized or proposal.physical_issued
        or proposal.preissue_persisted
        or proposal.proposal.action_id != b.action_id
        or proposal.proposal.intent_id != b.intent_id
        or proposal.proposal.skill_execution_id != b.skill_execution_id
        or b.skill_id != "ATTACK" or b.skill_version != 1
        or b.capability_ref != "ATTACK" or b.capability_version != 1
        or b.target_kind != "ZOMBIE" or b.body_channel != "hand"
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,89}", b.action_id)
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
    ):
        raise PhysicalAttackRefusal("selected ATTACK/native correlated window not current")
    match = re.fullmatch(r"entity:(0|[1-9][0-9]{0,9})", b.target_ref)
    if match is None:
        raise PhysicalAttackRefusal("canonical bounded target entity ID required")
    target_id = int(match.group(1))
    positions = []
    for obs in (previous, current):
        c = obs.snapshot.nearby_entities_coverage
        entities = obs.snapshot.nearby_entities
        if (
            obs.snapshot.health <= 0 or obs.snapshot.oxygen_level == 0
            or c.truncated or c.candidate_count != 1 or len(entities) != 1
            or entities[0].name != "zombie"
            or entities[0].entity_id != target_id
            or not 0.1 <= entities[0].distance <= 2.8
        ):
            raise PhysicalAttackRefusal("same single in-range zombie required")
        positions.append(entities[0].position)
    for axis in ("x", "y", "z"):
        if abs(getattr(previous.snapshot.position, axis) -
               getattr(current.snapshot.position, axis)) > .05:
            raise PhysicalAttackRefusal("Self moved before ATTACK")
        if abs(getattr(positions[0], axis) -
               getattr(positions[1], axis)) > .25:
            raise PhysicalAttackRefusal("selected zombie position changed")
    return target_id


async def _expect_native_attack(
    session: MineflayerProcessSession,
    parent_id: str,
    target_id: int,
    *, after_seq: int, timeout_s: float,
) -> tuple[MineflayerEffectResult, MineflayerEntityHurt]:
    deadline = asyncio.get_running_loop().time() + timeout_s
    ack: MineflayerEffectResult | None = None
    hurt: MineflayerEntityHurt | None = None
    last_seq = after_seq
    for _ in range(128):
        left = deadline - asyncio.get_running_loop().time()
        if left <= 0:
            break
        frame = await asyncio.wait_for(session.receive(), timeout=left)
        if frame.session_id != session.started.session_id or frame.seq <= last_seq:
            raise PhysicalAttackRefusal("foreign/nonmonotonic ATTACK native stream")
        last_seq = frame.seq
        if isinstance(frame, MineflayerEffectResult):
            if (
                ack is not None or frame.action_id != parent_id + "-attack"
                or frame.effect != "attack_entity" or frame.result != "applied"
            ):
                raise PhysicalAttackRefusal("ATTACK native ACK rejected/foreign/duplicate")
            ack = frame
        elif isinstance(frame, MineflayerEntityHurt):
            if (
                hurt is not None or frame.entity_id != target_id
                or frame.source_entity_id is None
                or frame.source_entity_id != frame.actor_entity_id
                or frame.actor_entity_id == target_id
            ):
                raise PhysicalAttackRefusal(
                    "ATTACK hurt event not source-attributed to active Self"
                )
            hurt = frame
        elif isinstance(frame, MineflayerObservation):
            if frame.kind in {"death", "respawn"} or frame.snapshot.health <= 0:
                raise PhysicalAttackRefusal("Self died during ATTACK")
        elif isinstance(frame, (
            MineflayerConnectionEnd, MineflayerCommandError,
            MineflayerAdapterErrorMessage,
        )):
            raise PhysicalAttackRefusal("ATTACK native stream unavailable")
        else:
            raise PhysicalAttackRefusal("unexpected ATTACK native message")
        if ack is not None and hurt is not None:
            return ack, hurt
    raise PhysicalAttackRefusal("attributed hurt and ACK not both established")


async def _after_attack(
    session: MineflayerProcessSession, action_id: str,
    *, after_seq: int, timeout_s: float,
) -> MineflayerObservation:
    request_id = action_id + "-after-attack"
    await session.send_observe(request_id)
    deadline = asyncio.get_running_loop().time() + timeout_s
    last_seq = after_seq
    for _ in range(128):
        left = deadline - asyncio.get_running_loop().time()
        if left <= 0:
            break
        frame = await asyncio.wait_for(session.receive(), timeout=left)
        if frame.session_id != session.started.session_id or frame.seq <= last_seq:
            raise PhysicalAttackRefusal("foreign/nonmonotonic after-ATTACK stream")
        last_seq = frame.seq
        if isinstance(frame, MineflayerObservation):
            if frame.kind in {"death", "respawn"} or frame.snapshot.health <= 0:
                raise PhysicalAttackRefusal("Self died before after-ATTACK readback")
            if frame.kind == "probe":
                if frame.request_id != request_id:
                    raise PhysicalAttackRefusal("uncorrelated after-ATTACK probe")
                return frame
        elif isinstance(frame, (MineflayerEffectResult, MineflayerEntityHurt)):
            raise PhysicalAttackRefusal("unexpected native effect during after-ATTACK")
        else:
            raise PhysicalAttackRefusal("after-ATTACK WorldBody unavailable")
    raise PhysicalAttackRefusal("no correlated after-ATTACK observation")


async def issue_selected_attack_dev(
    session: MineflayerProcessSession,
    *, proposal: PhysicalActionProposalReceipt,
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
    evidence_timeout_s: float = 9.0,
) -> PhysicalAttackDevReceipt:
    if (
        type(grant_real_world) is not bool or not grant_real_world
        or type(acknowledge_dev_unverified_principal) is not bool
        or not acknowledge_dev_unverified_principal
        or not isinstance(session, MineflayerProcessSession)
        or session.process_returncode is not None
        or not isinstance(intent_owner, IntentCommitment)
        or not isinstance(skill_execution, SkillExecution)
        or not isinstance(supervisor, ActionSupervisor)
        or not isinstance(journal, PhysicalActionJournal)
        or type(at_ns) is not int or at_ns < 0
        or not isinstance(provenance, Provenance)
        or type(evidence_timeout_s) not in (int, float)
        or not 0 < evidence_timeout_s <= 30
    ):
        raise PhysicalAttackRefusal("explicit single-owner DEV physical grant required")
    journal.require_clear()
    entity_id = _check_window(proposal, previous_probe, current_probe)
    b = proposal.binding
    # Reuse the *exact* EAT DEV envelope validator, not its physical policy.
    # Grants remain unverified caller-provided labels, not authenticated IDs.
    _check_grants(b, propose_grant, issue_grant)
    owner = intent_owner.current_intent
    if (
        session.started.session_id != b.scope.world_session_id
        or journal._body["self_id"] != b.scope.self_id
        or owner is None or owner.intent_id != b.intent_id
        or owner.objective != b.goal_id
        or intent_owner.pending_reconsideration is not None
        or not skill_execution.is_current_snapshot
        or skill_execution.state is not SkillState.STARTED
        or skill_execution.execution_id != b.skill_execution_id
        or skill_execution.skill_id != "ATTACK"
        or skill_execution.intent_id != b.intent_id
        or supervisor.open_actions or supervisor.recorded_actions
        or proposal.proposal.action_id != b.action_id
        or not proposal.proposal.is_current_snapshot
        or at_ns < max(intent_owner.last_at_ns or 0, skill_execution.events[-1].at_ns)
    ):
        raise PhysicalAttackRefusal("ATTACK physical owner/Skill/Intent no longer eligible")
    journal.require_clear()
    authorized = proposal.proposal.authorize(
        at_ns=at_ns, provenance=propose_grant.provenance,
        authority=propose_grant.authority_id,
    )
    # This is the *same journal* as EAT; the shared CAS/fsync/unknown STOP
    # cannot be bypassed by a different physical capability.
    journal.prepare_attack(b, current_probe)
    issued = supervisor.issue(
        authorized, at_ns=at_ns + 1, deadline_ns=at_ns + 1000,
        provenance=issue_grant.provenance,
    )
    assert supervisor.get(b.action_id) is issued
    try:
        await session.send_attack_entity(b.action_id + "-attack", entity_id=entity_id)
        ack, hurt = await _expect_native_attack(
            session, b.action_id, entity_id,
            after_seq=current_probe.seq, timeout_s=evidence_timeout_s,
        )
        after = await _after_attack(
            session, b.action_id,
            after_seq=max(ack.seq, hurt.seq), timeout_s=evidence_timeout_s,
        )
        terminal = supervisor.record_outcome(
            b.action_id, at_ns=at_ns + 2, provenance=after.provenance,
        )
        journal.close_attack(
            b, current_probe, ack, hurt, after, terminal, supervisor,
        )
        return PhysicalAttackDevReceipt(terminal, ack, hurt, after, entity_id)
    except BaseException:
        if supervisor.get(b.action_id).state is ActionState.ISSUED:
            supervisor.mark_unknown(
                b.action_id, at_ns=at_ns + 2, provenance=current_probe.provenance,
            )
        # PREPARED_UNRESOLVED stays durable. Never reissue.
        raise
