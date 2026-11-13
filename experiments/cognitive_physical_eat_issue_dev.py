"""Single guarded native EAT ActionPort DEV issuer; NO old S49 decision owner.

This is a narrow *opt-in* physical test seam, not a production grant provider.
It does not choose Goal, food, Skill or Target. Real authority/principal
authentication, continuous Body arbiter and QUAL remain open.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionProposalReceipt
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


class PhysicalEatRefusal(ValueError):
    """Current native source, immutable choice or physical permission failed."""


class PhysicalGrantStage(str, Enum):
    PROPOSE = "PROPOSE"
    ISSUE = "ISSUE"


@dataclass(frozen=True, slots=True)
class PhysicalEatGrant:
    """Caller-claimed external approval; NOT cryptographically authenticated."""

    stage: PhysicalGrantStage
    authority_id: str
    provenance: Provenance
    intent_id: str
    action_id: str
    session_id: str
    probe_seq: int
    probe_request_id: str
    selected_target_ref: str
    granted: bool


@dataclass(frozen=True, slots=True)
class PhysicalEatDevReceipt:
    """Actual native ACK + food readback. No independent tick attestation."""

    terminal: ActionLifecycle
    equip: MineflayerEffectResult
    consume: MineflayerEffectResult
    after: MineflayerObservation
    item: str
    food_before: float
    food_after: float
    item_count_before: int
    item_count_after: int
    status: str = "NATIVE_EAT_OUTCOME_DEV_ONLY"
    qualifying_real_world: bool = False


def _check_native_window(
    proposal: PhysicalActionProposalReceipt,
    previous: MineflayerObservation,
    current: MineflayerObservation,
) -> tuple[str, int]:
    b = proposal.binding
    if (
        proposal.proposal.state is not ActionState.PROPOSED
        or not proposal.proposal.is_current_snapshot
        or proposal.physical_authorized or proposal.physical_issued
        or proposal.preissue_persisted
        or proposal.proposal.action_id != b.action_id
        or proposal.proposal.intent_id != b.intent_id
        or proposal.proposal.skill_execution_id != b.skill_execution_id
        or b.skill_id != "EAT" or b.skill_version != 1
        or b.capability_ref != "EAT" or b.capability_version != 1
        or b.body_channel != "hand" or b.target_kind != "FOOD"
        or not b.target_ref.startswith("inventory:")
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
        raise PhysicalEatRefusal("selected EAT/native correlated window not current")
    food = b.target_ref.removeprefix("inventory:")
    slots: list[int] = []
    for obs in (previous, current):
        coverage = obs.snapshot.nearby_entities_coverage
        if (
            obs.snapshot.health <= 0 or obs.snapshot.oxygen_level == 0
            or obs.snapshot.food >= 20
            or coverage.truncated or coverage.candidate_count != 0
            or obs.snapshot.nearby_entities
        ):
            raise PhysicalEatRefusal("unsafe/incomplete native EAT Body evidence")
        locations = {
            i.slot for i in obs.snapshot.inventory
            if i.name == food and i.count > 0
        }
        if len(locations) != 1:
            raise PhysicalEatRefusal("chosen food absent or ambiguous in inventory")
        slots.append(next(iter(locations)))
    if slots[0] != slots[1] or any(
        abs(getattr(previous.snapshot.position, axis)
            - getattr(current.snapshot.position, axis)) > .05
        for axis in ("x", "y", "z")
    ):
        raise PhysicalEatRefusal("EAT food slot/body changed")
    return food, slots[1]


def _check_grants(
    binding, propose: PhysicalEatGrant, issue: PhysicalEatGrant,
) -> None:
    if (
        not isinstance(propose, PhysicalEatGrant)
        or not isinstance(issue, PhysicalEatGrant)
        or propose.stage is not PhysicalGrantStage.PROPOSE
        or issue.stage is not PhysicalGrantStage.ISSUE
        or not propose.granted or not issue.granted
        or not propose.authority_id or not issue.authority_id
        or propose.authority_id == issue.authority_id
        or not isinstance(propose.provenance, Provenance)
        or not isinstance(issue.provenance, Provenance)
        or propose.provenance == issue.provenance
        or propose.provenance.source == "mineflayer"
        or issue.provenance.source == "mineflayer"
    ):
        raise PhysicalEatRefusal("independent scoped external physical grants required")
    for grant in (propose, issue):
        if any((
            grant.intent_id != binding.intent_id,
            grant.action_id != binding.action_id,
            grant.session_id != binding.scope.world_session_id,
            grant.probe_seq != binding.native_seq,
            grant.probe_request_id != binding.native_request_id,
            grant.selected_target_ref != binding.target_ref,
        )):
            raise PhysicalEatRefusal("physical grant is foreign/stale/retargeted")


async def _expect_applied(
    session: MineflayerProcessSession, action_id: str, effect: str,
    *, after_seq: int, timeout_s: float,
) -> MineflayerEffectResult:
    deadline = asyncio.get_running_loop().time() + timeout_s
    for _ in range(128):
        left = deadline - asyncio.get_running_loop().time()
        if left <= 0:
            raise PhysicalEatRefusal("native EAT effect ACK timed out")
        frame = await asyncio.wait_for(session.receive(), timeout=left)
        if frame.session_id != session.started.session_id or frame.seq <= after_seq:
            raise PhysicalEatRefusal("foreign/stale native EAT ACK")
        if isinstance(frame, MineflayerEffectResult):
            if (
                frame.action_id != action_id or frame.effect != effect
                or frame.result != "applied"
            ):
                raise PhysicalEatRefusal("native EAT effect ACK not applied")
            return frame
        if (
            not isinstance(frame, MineflayerObservation)
            or frame.kind in {"death", "respawn"} or frame.snapshot.health <= 0
        ):
            raise PhysicalEatRefusal("native EAT stream/body became unavailable")
    raise PhysicalEatRefusal("EAT ACK not found within bounded native traffic")


async def _after_probe(
    session: MineflayerProcessSession, request_id: str,
    *, after_seq: int, timeout_s: float,
) -> MineflayerObservation:
    await session.send_observe(request_id)
    deadline = asyncio.get_running_loop().time() + timeout_s
    for _ in range(128):
        left = deadline - asyncio.get_running_loop().time()
        if left <= 0:
            raise PhysicalEatRefusal("native after-EAT probe timed out")
        frame = await asyncio.wait_for(session.receive(), timeout=left)
        if frame.session_id != session.started.session_id or frame.seq <= after_seq:
            raise PhysicalEatRefusal("foreign/stale after-EAT message")
        if isinstance(frame, MineflayerObservation):
            if frame.kind in {"death", "respawn"} or frame.snapshot.health <= 0:
                raise PhysicalEatRefusal("Self died during EAT")
            if frame.kind == "probe":
                if frame.request_id != request_id:
                    raise PhysicalEatRefusal("uncorrelated after-EAT probe")
                return frame
        else:
            raise PhysicalEatRefusal("unexpected native EAT receipt during readback")
    raise PhysicalEatRefusal("no correlated after-EAT probe")


async def issue_selected_eat_dev(
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
) -> PhysicalEatDevReceipt:
    """One real EAT, fsynced before any native IO; *DEV only* by explicit grants.

    A persisted UNKNOWN is permanent STOP until an operator independently
    reconciles it; this function does not provide such a reconciliation API.
    The input proposal must come from the same physical port owner, not a
    synthetic replacement. Replaying this call never retries EAT.
    """
    if (
        not grant_real_world or not acknowledge_dev_unverified_principal
        or type(grant_real_world) is not bool
        or type(acknowledge_dev_unverified_principal) is not bool
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
        raise PhysicalEatRefusal("explicit single-owner DEV physical grant required")
    # A restored unresolved ledger has priority over a stale in-memory
    # proposal: STOP/UNKNOWN is never converted into a retryable refusal.
    journal.require_clear()
    binding = proposal.binding
    food, _ = _check_native_window(proposal, previous_probe, current_probe)
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
        raise PhysicalEatRefusal("physical owner/Skill/Intent no longer eligible")
    journal.require_clear()
    if (
        journal.records
        and journal.records[-1]["session_id"] == current_probe.session_id
        and journal.records[-1]["after_seq"] >= current_probe.seq
    ):
        raise PhysicalEatRefusal("previous physical EAT source not yet advanced")
    if at_ns < max(intent_owner.last_at_ns or 0, skill_execution.events[-1].at_ns):
        raise PhysicalEatRefusal("physical time precedes selected owner/Skill")

    authorized = proposal.proposal.authorize(
        at_ns=at_ns, provenance=propose_grant.provenance,
        authority=propose_grant.authority_id,
    )
    # S49 #767 invariant: fsync PREPARED_UNRESOLVED before ISSUE or any
    # external effect. A disk exception means ZERO issue; reservations
    # already written are never silently undone.
    journal.prepare_eat(binding, current_probe)
    issued = supervisor.issue(
        authorized, at_ns=at_ns + 1, deadline_ns=at_ns + 1000,
        provenance=issue_grant.provenance,
    )
    assert supervisor.get(binding.action_id) is issued
    before_count = sum(
        i.count for i in current_probe.snapshot.inventory if i.name == food
    )
    try:
        equip_id = binding.action_id + "-equip"
        consume_id = binding.action_id + "-consume"
        await session.send_equip_item(equip_id, item_name=food)
        equip = await _expect_applied(
            session, equip_id, "equip_item",
            after_seq=current_probe.seq, timeout_s=evidence_timeout_s,
        )
        await session.send_consume_held(consume_id)
        consume = await _expect_applied(
            session, consume_id, "consume_held",
            after_seq=equip.seq, timeout_s=evidence_timeout_s,
        )
        for n in range(8):
            after = await _after_probe(
                session, f"{binding.action_id}-after-eat-{n:02d}",
                after_seq=consume.seq,
                timeout_s=evidence_timeout_s,
            )
            after_count = sum(
                i.count for i in after.snapshot.inventory if i.name == food
            )
            if (
                after.snapshot.food > current_probe.snapshot.food
                and after.snapshot.food <= 20
                and after_count < before_count
            ):
                break
            await asyncio.sleep(.25)
        else:
            raise PhysicalEatRefusal("native EAT effects applied but nutrition unverified")
        terminal = supervisor.record_outcome(
            binding.action_id, at_ns=at_ns + 2, provenance=after.provenance,
        )
        journal.close_eat(
            binding, current_probe, equip, consume, after, terminal, supervisor,
        )
        return PhysicalEatDevReceipt(
            terminal, equip, consume, after, food,
            current_probe.snapshot.food, after.snapshot.food,
            before_count, after_count,
        )
    except BaseException:
        if supervisor.get(binding.action_id).state is ActionState.ISSUED:
            supervisor.mark_unknown(
                binding.action_id,
                at_ns=at_ns + 2, provenance=current_probe.provenance,
            )
        # Never clear the durable PREPARED_UNRESOLVED journal on ambiguity.
        raise
