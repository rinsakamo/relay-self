"""M0.2 Paper-only disposable DEV forage: native L0 SEEK -> governed S50 MOVE.

This is not a general pickup authority. The item content is operator-staged
but not visible in the entity observation. Native item disappearance + cooked
beef inventory increase is only a source-consistent *contrast*, not strict
playerCollect item causal attestation or R/V scientific qualification.
No M0/M0.1 virtual ledger exists on this path.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
from dataclasses import asdict
from typing import Any, BinaryIO, Callable

from adapters.mineflayer.b0_ground_foraging import GroundTarget
from adapters.mineflayer.b1_local_adaptation import B1LocalCandidate
from adapters.mineflayer.m02_paper_dev.native_l0 import PaperNativeL0
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.seek_execution import SeekConsequenceKind, execute_seek_step
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.seek_waypoint import SeekCursor, SeekStatus


class PaperForageRejected(ValueError):
    """A fresh Paper-only source did not close the bounded physical forage."""


def append_b1_original(stream: BinaryIO, record: dict[str, Any]) -> None:
    """Persist original S memory/choice bytes *when observed*, before next MOVE.

    Source evidence only; this is not independent R provenance attestation.
    """
    if not isinstance(record, dict) or record.get("event") not in (
        "BLOCKED_MEMORY_RETAINED", "LATERAL_ACTION_ISSUED",
    ):
        raise PaperForageRejected("invalid Paper B1 original journal event")
    raw = (json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)
           + "\n").encode("utf-8")
    if len(raw) > 32768:
        raise PaperForageRejected("oversized Paper B1 original journal event")
    stream.write(raw)
    stream.flush()
    os.fsync(stream.fileno())


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
    fixed_food_position: tuple[float, float, float] | None = None,
    b1_retention: bool | None = None,
    b1_memory_original: BinaryIO | None = None,
) -> dict[str, Any]:
    """Operator-staged item fixture, real hungry L0, no B0 EnergyLedger."""
    if (not isinstance(trace, dict) or trace or max_actions != 8
            or (b1_retention is not None and type(b1_retention) is not bool)
            or (b1_retention is None and b1_memory_original is not None)
            or (b1_retention is not None and b1_memory_original is None)):
        raise PaperForageRejected("fresh bounded Paper DEV trace and explicit B1 switch required")
    if fixed_food_position is not None and (
            len(fixed_food_position) != 3
            or not all(type(v) in (int, float) and math.isfinite(v)
                       for v in fixed_food_position)):
        raise PaperForageRejected("invalid fixed operator food position")
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
        "paper_b1_retention": b1_retention,
        "b1_fixture_wall": None,
        "b1_evidence": None,
        "b1_decisions": [],
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
    if b1_retention is not None:
        # The collision face precedes the item pickup radius; command write
        # alone is not block-effect attestation. Only native S50 BLOCKED counts.
        bx, by, bz = math.floor(pos.x) + 1, math.floor(pos.y), math.floor(pos.z)
        _command(server, f"fill {bx} {by} {bz} {bx} {by + 1} {bz} minecraft:stone")
        await server.stdin.drain()
        trace["b1_fixture_wall"] = {
            "x": bx, "y": by, "z": bz,
            "effect_attestation": "NOT_NATIVE_ATTESTED",
        }
    food_xyz = fixed_food_position or (pos.x + 2.5, pos.y + 0.2, pos.z)
    trace["operator_food_fixture"] = {
        "item": "cooked_beef", "count": 1, "summon_xyz": list(food_xyz),
        "placement": "FIXED_ABSOLUTE" if fixed_food_position else "RELATIVE_TO_NATIVE_BODY",
    }
    _command(
        server,
        f"summon item {food_xyz[0]:.3f} {food_xyz[1]:.3f} {food_xyz[2]:.3f} "
        '{Item:{id:"minecraft:cooked_beef",count:1}}',
    )
    await server.stdin.drain()
    # Explicit operator fixture: preserve the first native item pose and its
    # pose after free fall, plus Self feet, before issuing any movement.
    initial_item = await _correlated_observe(session, "m02-paper-item-initial")
    trace["food_initial_native"] = asdict(initial_item)
    await asyncio.sleep(0.75)
    settled_item = await _correlated_observe(session, "m02-paper-item-after-fall")
    trace["food_after_fall_native"] = asdict(settled_item)
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
    b1 = (B1LocalCandidate(target.session_id, retain=b1_retention)
          if b1_retention is not None else None)
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
        waypoint = b1.next_waypoint(read, target) if b1 is not None else target.waypoint()
        if b1 is not None:
            trace["b1_decisions"].append({
                "source_seq": read.seq,
                "waypoint_id": waypoint.goal_id,
                "retained_memory_count": len(b1.cognition.memories),
                "issued_action": False,
                "policy": "MEMORY_MINUS_Z" if b1.retain else "FIXED_PLUS_Z",
            })
        step = cursor.plan(read, waypoint)
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
        if b1 is not None and waypoint.goal_id == "b1-local-lateral":
            memory = b1.cognition.memories[0] if b1.retain else None
            append_b1_original(b1_memory_original, {
                "event": "LATERAL_ACTION_ISSUED",
                "session_id": target.session_id,
                "action_id": issued.action_id,
                "source_probe_seq": read.seq,
                "source_target_entity_id": target.entity_id,
                "waypoint": {"x": waypoint.target.x, "y": waypoint.target.y,
                             "z": waypoint.target.z},
                "memory_content_sha256": (
                    hashlib.sha256(memory.content.encode("utf-8")).hexdigest()
                    if memory else None
                ),
                "retention_enabled": b1.retain,
            })
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
            if b1 is not None:
                if waypoint.goal_id == "b1-local-lateral":
                    b1.record_alternative_outcome(effect)
                    if effect.kind is SeekConsequenceKind.BLOCKED:
                        raise PaperForageRejected("B1 alternate Paper MOVE BLOCKED")
                elif effect.kind is SeekConsequenceKind.BLOCKED:
                    followup = await _correlated_observe(
                        session, f"m02-paper-b1-blocked-followup-{i:02d}",
                    )
                    b1.record_blocked(read, effect, followup, target)
                    memory = b1.cognition.memories[0] if b1.retain else None
                    append_b1_original(b1_memory_original, {
                        "event": "BLOCKED_MEMORY_RETAINED",
                        "session_id": target.session_id,
                        "blocked_action_id": effect.action_id,
                        "source_before_seq": read.seq,
                        "effect_after_seq": effect.after_seq,
                        "correlated_followup_seq": followup.seq,
                        "source_target_entity_id": target.entity_id,
                        "memory": (
                            {"memory_id": memory.memory_id,
                             "content": memory.content,
                             "source_provenance": asdict(memory.source_provenance),
                             "integration_provenance": asdict(memory.integration_provenance)}
                            if memory else None
                        ),
                        "retention_enabled": b1.retain,
                    })
                trace["b1_evidence"] = b1.evidence()
            elif effect.kind is SeekConsequenceKind.BLOCKED:
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
    if b1 is not None:
        trace["b1_evidence"] = b1.evidence()
        if (b1.blocked_count != 1 or b1.reuse_count != 1
                or b1.alternative_progressed < 1
                or len(b1.cognition.memories) != (1 if b1.retain else 0)):
            raise PaperForageRejected("B1 bounded native BLOCKED/retention/lateral evidence absent")
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
        "b1_evidence": b1.evidence() if b1 is not None else None,
        "b1_decisions": trace["b1_decisions"],
        "b1_fixture_wall": trace["b1_fixture_wall"],
    }
