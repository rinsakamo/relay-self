"""M0.2 Paper-only disposable DEV forage: native L0 SEEK -> governed S50 MOVE.

This is not a general pickup authority. The item content is operator-staged
but not visible in the entity observation. Native item disappearance + cooked
beef inventory increase is only a source-consistent *contrast*, not strict
playerCollect item causal attestation or R/V scientific qualification.
No M0/M0.1 virtual ledger exists on this path.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any, Callable

from adapters.mineflayer.b0_ground_foraging import GroundRejected, GroundTarget
from adapters.mineflayer.m02_paper_dev.native_l0 import PaperNativeL0
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.seek_execution import SeekConsequenceKind, execute_seek_step
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.seek_waypoint import SeekCursor, SeekStatus


class PaperForageRejected(ValueError):
    """A fresh Paper-only source did not close the bounded physical forage."""


def cooked_beef_count(probe: MineflayerObservation) -> int:
    return sum(x.count for x in probe.snapshot.inventory if x.name == "cooked_beef")


def paper_pickup_contrast(
    first: MineflayerObservation, after: MineflayerObservation,
    target: GroundTarget,
) -> dict[str, Any]:
    """Correlated disappearance+inventory evidence; no item metadata oracle."""
    if (
        not isinstance(first, MineflayerObservation)
        or not isinstance(after, MineflayerObservation)
        or not isinstance(target, GroundTarget)
        or first.kind != "probe" or after.kind != "probe"
        or first.session_id != target.session_id
        or after.session_id != target.session_id
        or first.seq != target.probe_seq
        or first.request_id != target.request_id
        or first.provenance != target.provenance
        or after.seq <= first.seq
        or not after.request_id
        or after.provenance.source != "mineflayer"
        or first.snapshot.nearby_entities_coverage.truncated
        or after.snapshot.nearby_entities_coverage.truncated
        or cooked_beef_count(first) != 0
        or cooked_beef_count(after) - cooked_beef_count(first) != 1
        or any(e.entity_id == target.entity_id for e in after.snapshot.nearby_entities)
    ):
        raise PaperForageRejected("one native cooked_beef pickup contrast not established")
    return {
        "source_session_id": target.session_id,
        "item_entity_id": target.entity_id,
        "source_before_seq": first.seq,
        "source_after_seq": after.seq,
        "cooked_beef_inventory_delta": 1,
        "source_evidence": "ITEM_DISAPPEARED_AND_INVENTORY_ROSE_ONLY",
        "strict_player_collect_causality": "UNKNOWN",
        "item_content_from_native_entity_metadata": "UNKNOWN",
    }


async def paper_ground_forage(
    session: Any, server: Any, *,
    issuer: Callable[..., Any],
    provenance: Callable[[str], Any],
    trace: dict[str, Any],
    max_actions: int = 8,
) -> dict[str, Any]:
    """Operator-staged item fixture, real hungry L0, no B0 EnergyLedger."""
    if not isinstance(trace, dict) or trace or max_actions != 8:
        raise PaperForageRejected("fresh eight-Action Paper DEV trace required")
    if server.stdin is None:
        raise PaperForageRejected("owned Paper console required")
    trace.update({
        "status": "INCOMPLETE_NOT_PICKUP",
        "stage": "INITIAL_PROBE",
        "movement_outcomes": [],
        "l0_decisions": [],
        "virtual_energy_ledger_used": False,
        "strict_pickup_causality": "UNKNOWN",
        "fixture_food_source": "OPERATOR_STAGED_COOKED_BEEF_NOT_AUTONOMOUS",
    })
    first_empty = await _correlated_observe(session, "m02-paper-forage-item-free")
    if (first_empty.snapshot.nearby_entities_coverage.truncated
            or any(e.name == "item" for e in first_empty.snapshot.nearby_entities)
            or cooked_beef_count(first_empty) != 0):
        raise PaperForageRejected("owned Paper DEV initial World not item-free")
    # Keep this fixture explicit, not an L0 reward/value or new metabolic owner.
    _command(server, "effect give RelaySelf minecraft:hunger 25 20 true")
    await server.stdin.drain()
    hungry = None
    for i in range(16):
        await asyncio.sleep(2)
        p = await _correlated_observe(session, f"m02-paper-forage-hunger-{i:02d}")
        if p.snapshot.food < 14:
            hungry = p
            break
    if hungry is None:
        raise PaperForageRejected("Paper hunger fixture did not produce a hungry native body")
    trace["hunger_source_seq"] = hungry.seq
    trace["hunger_world_food"] = hungry.snapshot.food
    pos = hungry.snapshot.position
    _command(
        server,
        f"summon item {pos.x + 2.5:.3f} {pos.y + 0.2:.3f} {pos.z:.3f} "
        '{Item:{id:"minecraft:cooked_beef",count:1}}',
    )
    await server.stdin.drain()
    l0 = PaperNativeL0(session.started.session_id)
    first = target = None
    for i in range(12):
        probe = await _correlated_observe(session, f"m02-paper-item-discovery-{i:02d}")
        if probe.snapshot.nearby_entities_coverage.truncated:
            raise PaperForageRejected("item probe truncated")
        decision = l0.decide(probe)
        trace["l0_decisions"].append({
            "seq": probe.seq, "kind": decision.kind, "food": decision.world_food,
            "issued_action": False,
        })
        if decision.kind == "SEEK":
            first, target = probe, decision.ground_target
            break
        await asyncio.sleep(0.25)
    if first is None or target is None:
        raise PaperForageRejected("no single native item and hungry L0 SEEK")
    trace.update({
        "stage": "S50_GOVERNED_GROUND_SEEK",
        "item_entity_id": target.entity_id,
        "discovery_seq": first.seq,
    })
    supervisor = ActionSupervisor()
    cursor = SeekCursor(target.session_id)
    contrast = None
    for i in range(max_actions):
        read = await _correlated_observe(session, f"m02-paper-ground-step-{i:02d}")
        if cooked_beef_count(read) > 0:
            contrast = paper_pickup_contrast(first, read, target)
            break
        if (read.snapshot.nearby_entities_coverage.truncated
                or not any(e.entity_id == target.entity_id
                           for e in read.snapshot.nearby_entities)):
            raise PaperForageRejected("ground item disappeared without owned inventory proof")
        decision = l0.decide(read)
        trace["l0_decisions"].append({
            "seq": read.seq, "kind": decision.kind, "food": decision.world_food,
            "issued_action": False,
        })
        if (decision.kind != "SEEK" or decision.ground_target is None
                or decision.ground_target.entity_id != target.entity_id):
            raise PaperForageRejected("native L0 did not select same observed item")
        step = cursor.plan(read, target.waypoint())
        if step.status is SeekStatus.NEEDS_ROUTE:
            raise PaperForageRejected("Paper source needs unavailable route")
        if step.status is SeekStatus.ARRIVED:
            await asyncio.sleep(0.25)
            continue
        # Existing S owner issues/authorizes/records; not Paper plugin control.
        issued = issuer(
            supervisor, f"m02-paper-forage-move-{i}", "seek-waypoint",
            f"m02-paper-forage-intent-{i}", "approach observed single item",
            time_base=200 + i * 20,
        )
        try:
            effect = await execute_seek_step(session, supervisor, issued, step)
            closed = supervisor.record_outcome(
                issued.action_id, at_ns=205 + i * 20,
                provenance=provenance(f"m02-paper-forage-closed-{i}"),
            )
            if closed.state is not ActionState.OUTCOME:
                raise PaperForageRejected("Paper S50 MOVE did not close with OUTCOME")
            trace["movement_outcomes"].append({
                "action_id": issued.action_id,
                "kind": effect.kind.value,
                "progress_blocks": effect.progress_m,
                "before_seq": effect.before_seq,
                "look_seq": effect.look_seq,
                "forward_seq": effect.forward_seq,
                "clear_seq": effect.clear_seq,
                "after_seq": effect.after_seq,
                "terminal": closed.state.value,
            })
            if effect.kind is SeekConsequenceKind.BLOCKED:
                raise PaperForageRejected("blocked ground SEEK; B1 route not authorized here")
        except BaseException:
            if supervisor.get(issued.action_id).state is ActionState.ISSUED:
                supervisor.mark_unknown(
                    issued.action_id, at_ns=205 + i * 20,
                    provenance=provenance(f"m02-paper-forage-unknown-{i}"),
                )
            raise
    if contrast is None:
        last = await _correlated_observe(session, "m02-paper-pickup-final")
        contrast = paper_pickup_contrast(first, last, target)
    if supervisor.open_actions or not trace["movement_outcomes"]:
        raise PaperForageRejected("unclosed or absent original governed MOVE")
    trace.update({"stage": "PICKUP_SOURCE_CONTRAST", "status": "PICKUP_SOURCE_CONSISTENT",
                  "pickup": contrast})
    return {
        "status": "PICKUP_SOURCE_CONSISTENT",
        "source_session": target.session_id,
        "item_entity_id": target.entity_id,
        "origin_food": hungry.snapshot.food,
        "pickup": contrast,
        "movement_outcomes": trace["movement_outcomes"],
        "l0_decisions": trace["l0_decisions"],
        "virtual_energy_ledger_used": False,
        "strict_pickup_causality": "UNKNOWN",
    }
