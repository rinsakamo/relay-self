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
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    begin_physical_issue_dev,
    check_dev_issuer_preflight,
    check_physical_source_window,
    finish_physical_issue_dev,
    mark_ambiguous_physical_dev,
)
from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionProposalReceipt
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


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
    check_physical_source_window(
        proposal, previous, current, capability="ATTACK",
        target_kind="ZOMBIE", refusal=PhysicalAttackRefusal,
    )
    b = proposal.binding
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
    propose_grant: PhysicalDevGrant,
    issue_grant: PhysicalDevGrant,
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
    check_dev_issuer_preflight(
        session, proposal, intent_owner=intent_owner,
        skill_execution=skill_execution, supervisor=supervisor, journal=journal,
        at_ns=at_ns, provenance=provenance, grant_real_world=grant_real_world,
        acknowledge_dev_unverified_principal=acknowledge_dev_unverified_principal,
        evidence_timeout_s=evidence_timeout_s, refusal=PhysicalAttackRefusal,
    )
    entity_id = _check_window(proposal, previous_probe, current_probe)
    b = proposal.binding
    begin_physical_issue_dev(
        session, capability="ATTACK", proposal=proposal,
        current_probe=current_probe,
        propose_grant=propose_grant, issue_grant=issue_grant,
        intent_owner=intent_owner, skill_execution=skill_execution,
        supervisor=supervisor, journal=journal, at_ns=at_ns,
        refusal=PhysicalAttackRefusal,
    )
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
        terminal = finish_physical_issue_dev(
            action_id=b.action_id, after=after, supervisor=supervisor,
            journal=journal, at_ns=at_ns,
            close=lambda outcome: journal.close_attack(
                b, current_probe, ack, hurt, after, outcome, supervisor,
            ),
        )
        return PhysicalAttackDevReceipt(terminal, ack, hurt, after, entity_id)
    except BaseException:
        mark_ambiguous_physical_dev(
            action_id=b.action_id, supervisor=supervisor,
            probe=current_probe, at_ns=at_ns,
        )
        # PREPARED_UNRESOLVED stays durable. Never reissue.
        raise
