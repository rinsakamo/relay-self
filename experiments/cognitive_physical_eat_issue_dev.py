"""Single guarded native EAT ActionPort DEV issuer; NO old S49 decision owner.

This is a narrow *opt-in* physical test seam, not a production grant provider.
It does not choose Goal, food, Skill or Target. Real authority/principal
authentication, continuous Body arbiter and QUAL remain open.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    PhysicalGrantStage,
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


class PhysicalEatRefusal(ValueError):
    """Current native source, immutable choice or physical permission failed."""


# Preserve the existing DEV caller API; no new physical grant is created.
PhysicalEatGrant = PhysicalDevGrant


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
    check_physical_source_window(
        proposal, previous, current, capability="EAT",
        target_kind="FOOD", refusal=PhysicalEatRefusal,
    )
    b = proposal.binding
    if not b.target_ref.startswith("inventory:"):
        raise PhysicalEatRefusal("selected food target reference malformed")
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
    check_dev_issuer_preflight(
        session, proposal, intent_owner=intent_owner,
        skill_execution=skill_execution, supervisor=supervisor, journal=journal,
        at_ns=at_ns, provenance=provenance, grant_real_world=grant_real_world,
        acknowledge_dev_unverified_principal=acknowledge_dev_unverified_principal,
        evidence_timeout_s=evidence_timeout_s, refusal=PhysicalEatRefusal,
    )
    binding = proposal.binding
    food, _ = _check_native_window(proposal, previous_probe, current_probe)
    begin_physical_issue_dev(
        session, capability="EAT", proposal=proposal, current_probe=current_probe,
        propose_grant=propose_grant, issue_grant=issue_grant,
        intent_owner=intent_owner, skill_execution=skill_execution,
        supervisor=supervisor, journal=journal, at_ns=at_ns,
        refusal=PhysicalEatRefusal,
    )
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
        terminal = finish_physical_issue_dev(
            action_id=binding.action_id, after=after, supervisor=supervisor,
            journal=journal, at_ns=at_ns,
            close=lambda outcome: journal.close_eat(
                binding, current_probe, equip, consume, after, outcome, supervisor,
            ),
        )
        return PhysicalEatDevReceipt(
            terminal, equip, consume, after, food,
            current_probe.snapshot.food, after.snapshot.food,
            before_count, after_count,
        )
    except BaseException:
        mark_ambiguous_physical_dev(
            action_id=binding.action_id, supervisor=supervisor,
            probe=current_probe, at_ns=at_ns,
        )
        # Never clear the durable PREPARED_UNRESOLVED journal on ambiguity.
        raise
