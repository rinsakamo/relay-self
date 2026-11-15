"""One-shot ATTACK through existing Physical ActionPort / Self WAL, DEV only.

A native attack_entity ACK is NOT proof of damage. Require a matching,
source-attributed entity_hurt and subsequent current native probe merely to
close the parent as CORRELATED_HURT; Paper damage/kill remains NOT_ATTESTED.
No target selection, owner, L0 policy, physical grant authority or retry here.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
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
    """The selected one-shot ATTACK is stale, unsafe or not attributable."""


@dataclass(frozen=True, slots=True)
class PhysicalAttackDevReceipt:
    terminal: ActionLifecycle
    ack: MineflayerEffectResult
    hurt: MineflayerEntityHurt
    after: MineflayerObservation
    target_entity_id: int
    status: str = "NATIVE_ATTACK_HURT_CORRELATED_DEV_ONLY"
    damage_attested: bool = False
    qualifying_real_world: bool = False


def _check_native_window(
    proposal: PhysicalActionProposalReceipt,
    previous: MineflayerObservation, current: MineflayerObservation,
) -> int:
    binding = proposal.binding
    if (
        proposal.proposal.state is not ActionState.PROPOSED
        or not proposal.proposal.is_current_snapshot
        or proposal.physical_authorized or proposal.physical_issued
        or proposal.preissue_persisted
        or proposal.proposal.action_id != binding.action_id
        or proposal.proposal.intent_id != binding.intent_id
        or proposal.proposal.skill_execution_id != binding.skill_execution_id
        or binding.skill_id != "ATTACK" or binding.skill_version != 1
        or binding.capability_ref != "attack_entity"
        or binding.capability_version != 1
        or binding.body_channel != "hand" or binding.target_kind != "ZOMBIE"
        or not re.fullmatch(r"entity:(0|[1-9][0-9]*)", binding.target_ref)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,89}", binding.action_id)
        or not isinstance(previous, MineflayerObservation)
        or not isinstance(current, MineflayerObservation)
        or previous.kind != "probe" or current.kind != "probe"
        or not previous.request_id or not current.request_id
        or previous.request_id == current.request_id
        or previous.session_id != binding.scope.world_session_id
        or current.session_id != binding.scope.world_session_id
        or not previous.seq < current.seq <= previous.seq + 32
        or current.seq != binding.native_seq
        or current.request_id != binding.native_request_id
        or current.provenance != binding.native_source
    ):
        raise PhysicalAttackRefusal("selected ATTACK/native source not current")
    entity_id = int(binding.target_ref.removeprefix("entity:"))
    for probe in (previous, current):
        coverage = probe.snapshot.nearby_entities_coverage
        entities = probe.snapshot.nearby_entities
        if (
            probe.snapshot.health <= 0 or probe.snapshot.oxygen_level == 0
            or coverage.truncated or coverage.candidate_count != 1
            or len(entities) != 1
            or entities[0].name != "zombie"
            or entities[0].entity_id != entity_id
        ):
            raise PhysicalAttackRefusal("selected zombie or Body coverage stale")
    if any(
        abs(getattr(previous.snapshot.position, axis)
            - getattr(current.snapshot.position, axis)) > .05
        or abs(getattr(previous.snapshot.nearby_entities[0].position, axis)
               - getattr(current.snapshot.nearby_entities[0].position, axis)) > .25
        for axis in ("x", "y", "z")
    ):
        raise PhysicalAttackRefusal("selected Body/target moved in native window")
    # Neither this issuer nor its IR invent a melee reach or damage threshold.
    # The caller's existing read-only selected-target window sets the reach
    # constraints and the native adapter enforces actual target availability.
    return entity_id


async def _correlated_native_ack_and_hurt(
    session: MineflayerProcessSession, parent_id: str, entity_id: int,
    *, after_seq: int, timeout_s: float,
) -> tuple[MineflayerEffectResult, MineflayerEntityHurt]:
    deadline = asyncio.get_running_loop().time() + timeout_s
    ack: MineflayerEffectResult | None = None
    hurt: MineflayerEntityHurt | None = None
    for _ in range(128):
        left = deadline - asyncio.get_running_loop().time()
        if left <= 0:
            raise PhysicalAttackRefusal("native ATTACK ACK/hurt timed out")
        frame = await asyncio.wait_for(session.receive(), timeout=left)
        if frame.session_id != session.started.session_id or frame.seq <= after_seq:
            raise PhysicalAttackRefusal("foreign/stale ATTACK frame")
        if isinstance(frame, MineflayerEffectResult):
            if (
                ack is not None or frame.action_id != parent_id + "-attack"
                or frame.effect != "attack_entity" or frame.result != "applied"
            ):
                raise PhysicalAttackRefusal("native ATTACK ACK rejected/uncorrelated")
            ack = frame
        elif isinstance(frame, MineflayerEntityHurt):
            if (
                hurt is not None or frame.entity_id != entity_id
                or frame.source_entity_id is None
                or frame.source_entity_id != frame.actor_entity_id
                or frame.actor_entity_id == entity_id
            ):
                raise PhysicalAttackRefusal("native hurt cannot be assigned to Self")
            hurt = frame
        elif (
            not isinstance(frame, MineflayerObservation)
            or frame.kind in {"death", "respawn"}
            or frame.snapshot.health <= 0
        ):
            raise PhysicalAttackRefusal("native ATTACK stream/body unavailable")
        if ack is not None and hurt is not None:
            return ack, hurt
    raise PhysicalAttackRefusal("bounded native ATTACK ACK/hurt not received")


async def _after_probe(
    session: MineflayerProcessSession, request_id: str,
    *, after_seq: int, timeout_s: float,
) -> MineflayerObservation:
    await session.send_observe(request_id)
    deadline = asyncio.get_running_loop().time() + timeout_s
    for _ in range(128):
        left = deadline - asyncio.get_running_loop().time()
        if left <= 0:
            raise PhysicalAttackRefusal("after-ATTACK probe timed out")
        frame = await asyncio.wait_for(session.receive(), timeout=left)
        if frame.session_id != session.started.session_id or frame.seq <= after_seq:
            raise PhysicalAttackRefusal("foreign/stale after-ATTACK frame")
        if isinstance(frame, MineflayerObservation):
            if frame.kind in {"death", "respawn"} or frame.snapshot.health <= 0:
                raise PhysicalAttackRefusal("Self died during ATTACK")
            if frame.kind == "probe":
                if frame.request_id != request_id:
                    raise PhysicalAttackRefusal("uncorrelated after-ATTACK probe")
                return frame
        else:
            raise PhysicalAttackRefusal("unexpected native frame after ATTACK")
    raise PhysicalAttackRefusal("no correlated after-ATTACK readback")


async def issue_selected_attack_dev(
    session: MineflayerProcessSession,
    *,
    proposal: PhysicalActionProposalReceipt,
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
    evidence_timeout_s: float = 9,
) -> PhysicalAttackDevReceipt:
    """One ATTACK, pre-ISSUE fsynced and never repeated on ambiguity."""
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
        or not 0 < evidence_timeout_s <= 30
    ):
        raise PhysicalAttackRefusal("explicit single-owner DEV physical grant required")
    journal.require_clear()
    binding = proposal.binding
    target = _check_native_window(proposal, previous_probe, current_probe)
    # The EAT grant is an existing generic pair of scoped claim fields;
    # it is not independently authenticated and is not a new grant owner.
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
        or proposal.proposal.action_id != binding.action_id
        or not proposal.proposal.is_current_snapshot
    ):
        raise PhysicalAttackRefusal("ATTACK physical owner no longer eligible")
    journal.require_clear()
    if (
        journal.records
        and journal.records[-1]["session_id"] == current_probe.session_id
        and journal.records[-1]["after_seq"] >= current_probe.seq
    ):
        raise PhysicalAttackRefusal("previous physical source not yet advanced")
    if at_ns < max(intent_owner.last_at_ns or 0, skill_execution.events[-1].at_ns):
        raise PhysicalAttackRefusal("physical time precedes current owner")
    authorized = proposal.proposal.authorize(
        at_ns=at_ns, provenance=propose_grant.provenance,
        authority=propose_grant.authority_id,
    )
    journal.prepare_attack(binding, current_probe)
    issued = supervisor.issue(
        authorized, at_ns=at_ns + 1, deadline_ns=at_ns + 1000,
        provenance=issue_grant.provenance,
    )
    assert supervisor.get(binding.action_id) is issued
    try:
        await session.send_attack_entity(binding.action_id + "-attack", entity_id=target)
        ack, hurt = await _correlated_native_ack_and_hurt(
            session, binding.action_id, target,
            after_seq=current_probe.seq, timeout_s=evidence_timeout_s,
        )
        after = await _after_probe(
            session, binding.action_id + "-after-attack-00",
            after_seq=max(ack.seq, hurt.seq), timeout_s=evidence_timeout_s,
        )
        terminal = supervisor.record_outcome(
            binding.action_id, at_ns=at_ns + 2, provenance=after.provenance,
        )
        journal.close_attack(
            binding, current_probe, ack, hurt, after, terminal, supervisor,
        )
        return PhysicalAttackDevReceipt(terminal, ack, hurt, after, target)
    except BaseException:
        if supervisor.get(binding.action_id).state is ActionState.ISSUED:
            supervisor.mark_unknown(
                binding.action_id, at_ns=at_ns + 2,
                provenance=current_probe.provenance,
            )
        # No journal reset on a potentially emitted physical strike.
        raise
