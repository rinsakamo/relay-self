"""B0 opt-in isolated ground rotten-flesh acquisition by existing S50 issuer.

Operator-owned fixture only. Do not confuse server-summoned item with zombie
drop, native item metadata identity, source-authenticated intake or live proof.
"""
from __future__ import annotations

import asyncio
from typing import Any

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b0_ground_foraging import (
    GroundRejected,
    compare_pickup,
    select_ground_target,
)
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.seek_execution import SeekConsequenceKind, execute_seek_step
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.seek_waypoint import SeekCursor, SeekStatus
from relay_self.skill import SkillExecution


def _p(name: str) -> Provenance:
    return Provenance("b0-explicit-operator", name)


def _admit_native_l0_seek(
    ledger: B0EnergyLedger, probe: Any, target: Any,
) -> dict[str, Any]:
    """A source-bound designed L0 SEEK; never an Action authorization."""
    if not isinstance(ledger, B0EnergyLedger):
        raise GroundRejected("live session energy ledger required for ground SEEK")
    decision = ledger.decide(probe)
    if (
        decision.kind != "SEEK"
        or decision.ground_target is None
        or decision.ground_target.entity_id != target.entity_id
        or decision.ground_target.session_id != target.session_id
        or decision.probe_seq != probe.seq
        or ledger.body.terminal
    ):
        raise GroundRejected("native L0 did not choose the observed ground target")
    return {
        "probe_seq": decision.probe_seq,
        "l0_kind": decision.kind,
        "entity_id": decision.ground_target.entity_id,
        "energy_sensor_reading": decision.sensor_reading,
        "metabolic_tick": decision.body_tick,
        "issued_action": False,
    }


async def acquire_staged_ground_flesh(
    session: Any, server: Any, *, energy_ledger: B0EnergyLedger | None = None,
    epoch: int = 0,
) -> dict[str, Any]:
    """One fixture/epoch, <=8 distinct issued moves; no retry or credit."""
    if type(epoch) is not int or not 0 <= epoch <= 7:
        raise GroundRejected("bounded ground epoch namespace required")
    namespace = "b0" if epoch == 0 else f"b0-e{epoch}"
    if server.stdin is None:
        raise GroundRejected("server console owner absent")
    origin = await _correlated_observe(session, f"{namespace}-initial-item-free")
    coverage = origin.snapshot.nearby_entities_coverage
    if (
        coverage.truncated
        or any(e.name == "item" for e in origin.snapshot.nearby_entities)
        or any(i.name == "rotten_flesh" for i in origin.snapshot.inventory)
    ):
        raise GroundRejected("ground fixture requires item-free initial World")
    # A new operator-summoned ground item; NOT a zombie drop.
    position = origin.snapshot.position
    _command(
        server,
        f"summon item {position.x + 2.5:.3f} "
        f"{position.y + 0.2:.3f} {position.z:.3f} "
        '{Item:{id:"minecraft:rotten_flesh",count:1}}',
    )
    await server.stdin.drain()
    first = target = None
    for i in range(8):
        probe = await _correlated_observe(session, f"{namespace}-item-discovery-{i:02d}")
        try:
            target = select_ground_target(probe)
        except GroundRejected:
            await asyncio.sleep(0.25)
        else:
            first = probe
            break
    if first is None or target is None:
        raise GroundRejected("single ground item not visible in bounded probes")

    # No operator-forced SEEK: the cheap L0 must actually select the one
    # native-observed item before any proposal/authorization/World movement.
    l0_trace = [_admit_native_l0_seek(energy_ledger, first, target)]
    intent = IntentCommitment()
    intent.commit(
        f"{namespace}-staged-ground-item", objective="approach the one observed ground item",
        at_ns=1, provenance=_p("operator-item-intent"),
    )
    supervisor = ActionSupervisor()
    cursor = SeekCursor(target.session_id)
    movements: list[dict[str, Any]] = []
    picked = None
    for i in range(8):
        read = await _correlated_observe(session, f"{namespace}-ground-step-{i:02d}")
        if any(x.name == "rotten_flesh" and x.count > 0 for x in read.snapshot.inventory):
            picked = compare_pickup(first, read, target)
            break
        if (
            read.snapshot.nearby_entities_coverage.truncated
            or not any(
                e.entity_id == target.entity_id
                for e in read.snapshot.nearby_entities
            )
        ):
            raise GroundRejected("ground item vanished without pickup evidence")
        l0_trace.append(_admit_native_l0_seek(energy_ledger, read, target))
        step = cursor.plan(read, target.waypoint())
        if step.status is SeekStatus.NEEDS_ROUTE:
            raise GroundRejected("no pathfinding authority for vertical route")
        if step.status is SeekStatus.ARRIVED:
            # Nonissuance; do not manufacture an S16 WAIT Action outcome.
            if energy_ledger is not None and energy_ledger.step("WAIT").terminal_now:
                raise GroundRejected("M0 terminal during WAIT")
            await asyncio.sleep(0.25)
            continue
        skill = SkillExecution.start(
            f"{namespace}-ground-seek-skill-{i}", skill_id="seek-waypoint",
            intent_commitment=intent, at_ns=10+i*10,
            provenance=_p(f"skill-{i}"),
        )
        proposed = ActionLifecycle.propose(
            f"{namespace}-ground-seek-action-{i}", skill_execution=skill,
            intent_commitment=intent, at_ns=11+i*10,
            provenance=_p(f"proposal-{i}"),
        )
        authorized = proposed.authorize(
            at_ns=12+i*10, authority=f"b0-independent-operator-grant-{i}",
            provenance=_p(f"authorization-{i}"),
        )
        issued = supervisor.issue(
            authorized, at_ns=13+i*10, deadline_ns=1000+i*10,
            provenance=_p(f"issue-{i}"),
        )
        try:
            effect = await execute_seek_step(session, supervisor, issued, step)
            if effect.kind is SeekConsequenceKind.BLOCKED:
                raise GroundRejected("issued SEEK did not make progress")
            closed = supervisor.record_outcome(
                issued.action_id, at_ns=14+i*10,
                provenance=_p(f"closed-{i}"),
            )
            if closed.state is not ActionState.OUTCOME:
                raise GroundRejected("SEEK not closed with a World consequence")
            if energy_ledger is not None and energy_ledger.step("MOVE").terminal_now:
                raise GroundRejected("M0 terminal after issued SEEK")
            movements.append({
                "action_id": issued.action_id,
                "before_seq": effect.before_seq,
                "after_seq": effect.after_seq,
                "kind": effect.kind.value,
                "progress_m": effect.progress_m,
            })
        except BaseException:
            if supervisor.get(issued.action_id).state is ActionState.ISSUED:
                supervisor.mark_unknown(
                    issued.action_id, at_ns=14+i*10,
                    provenance=_p(f"unknown-{i}"),
                )
            raise
    if picked is None:
        after = await _correlated_observe(session, f"{namespace}-ground-last-pickup")
        picked = compare_pickup(first, after, target)
    if supervisor.open_actions:
        raise GroundRejected("unclosed ground Action")

    return {
        "epoch": epoch,
        "item_entity_id": target.entity_id,
        "source_probe_seq": first.seq,
        "pickup_probe_seq": picked.after_seq,
        "pickup_inventory_delta": picked.rotten_flesh_inventory_delta,
        "pickup_evidence": picked.evidence_kind,
        "movement_outcomes": movements,
        "l0_ground_seek_trace": l0_trace,
        "selection_policy": "DESIGNED_NATIVE_L0_SEEK_NOT_LEARNED",
        "item_contents_from_entity_metadata": "UNKNOWN",
        "zombie_drop_observed": False,
        "m_energy_credited": False,
    }
