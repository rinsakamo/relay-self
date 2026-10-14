"""B0 opt-in isolated ground rotten-flesh acquisition by existing S50 issuer.

Operator-owned fixture only. Do not confuse server-summoned item with zombie
drop, native item metadata identity, source-authenticated intake or live proof.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import asdict
from typing import Any

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b1_local_adaptation import B1LocalCandidate
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



def nonforcing_ground_decision(
    ledger: B0EnergyLedger, probe: Any, expected: Any,
) -> dict[str, Any]:
    """Native observed WAIT is valid and costs M0 energy, never an Action."""
    if not isinstance(ledger, B0EnergyLedger) or ledger.body.terminal:
        raise GroundRejected("living M0 owner required for nonforcing ground")
    observed = select_ground_target(probe)
    if (
        observed.session_id != expected.session_id
        or observed.entity_id != expected.entity_id
    ):
        raise GroundRejected("source-observed item entity changed")
    decision = ledger.decide(probe)
    if decision.kind not in ("WAIT", "SEEK"):
        raise GroundRejected("unexpected ground L0 choice")
    if decision.kind == "SEEK" and (
        decision.ground_target is None
        or decision.ground_target.entity_id != expected.entity_id
    ):
        raise GroundRejected("native L0 chose different ground target")
    row: dict[str, Any] = {
        "probe_seq": probe.seq, "kind": decision.kind,
        "world_food": probe.snapshot.food,
        "item_entity_id": expected.entity_id,
        "energy_sensor": decision.sensor_reading,
        "m0_energy_before": ledger.body.energy,
        "m0_tick_before": ledger.body.tick,
        "issued_action": False,
    }
    if decision.kind == "WAIT":
        transition = ledger.step("WAIT")
        if transition.intake != 0 or transition.expenditure != ledger.config.basal_cost:
            raise GroundRejected("invalid nonissued WAIT metabolism")
        row.update({
            "m0_energy_after": transition.after.energy,
            "m0_tick_after": transition.after.tick,
            "m0_terminal_now": transition.terminal_now,
            "intake": transition.intake,
            "expenditure": transition.expenditure,
        })
    return row


async def acquire_staged_ground_flesh(
    session: Any, server: Any, *, energy_ledger: B0EnergyLedger | None = None,
    epoch: int = 0, nonforcing: bool = False,
    global_m0_horizon: int | None = None,
    global_move_limit: int | None = None,
    source_time_bracket: dict[str, Any] | None = None,
    b1_local: B1LocalCandidate | None = None,
    b1_obstacle: bool = False,
) -> dict[str, Any]:
    """One fixture with bounded native L0 nonissuance or issued SEEK."""
    if type(nonforcing) is not bool or (nonforcing and energy_ledger is None):
        raise GroundRejected("nonforcing needs a real typed M0 owner")
    if type(b1_obstacle) is not bool or (
        b1_obstacle and (b1_local is None or nonforcing or epoch != 0)
    ) or (b1_local is not None and (
        not isinstance(b1_local, B1LocalCandidate)
        or energy_ledger is None
        or b1_local.session_id != energy_ledger.session_id
        or nonforcing
    )):
        raise GroundRejected("B1 local adaptation requires one typed DEV source")
    if global_m0_horizon is not None or global_move_limit is not None:
        if (
            nonforcing is not True
            or global_m0_horizon != 16 or global_move_limit != 8
            or energy_ledger is None or energy_ledger.body.tick >= 16
        ):
            raise GroundRejected("prospective global V2 M0 tick/MOVE bounds required")
    if source_time_bracket is not None and (
        type(source_time_bracket) is not dict
        or source_time_bracket
        or nonforcing is not True
        or global_m0_horizon != 16
        or global_move_limit != 8
    ):
        raise GroundRejected("V2 clock bracket requires fresh fixed-budget source")
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
    if source_time_bracket is not None:
        if origin.snapshot.time is None:
            raise GroundRejected("V2 requires native pre-fixture World clock")
        source_time_bracket.update({
            "before_fixture_session_id": origin.session_id,
            "before_fixture_probe_seq": origin.seq,
            "before_fixture_request_id": origin.request_id,
            "before_fixture_native_world_time": asdict(origin.snapshot.time),
            "before_fixture_m0_tick": energy_ledger.body.tick,
            "fixture_command_ack": "NOT_NATIVE_ATTESTED",
            "minecraft_world_elapsed_tick_parity": "NOT_QUALIFIED",
        })
    # B1 requests a short stone wall across the direct ground-item line.
    # Console write is NOT independent native block-effect attestation.
    position = origin.snapshot.position
    obstacle_request = None
    if b1_obstacle:
        bx = math.floor(position.x + 1.5)
        by = math.floor(position.y)
        bz = math.floor(position.z)
        obstacle_request = {
            "x": bx, "y": by, "z": bz,
            "effect_attestation": "NOT_NATIVE_ATTESTED",
        }
        _command(
            server, f"fill {bx} {by} {bz} {bx} {by + 1} {bz} minecraft:stone",
        )
        await server.stdin.drain()
    # A new operator-summoned ground item; NOT a zombie drop.
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
    if source_time_bracket is not None:
        if first.snapshot.time is None:
            raise GroundRejected("V2 requires native post-fixture World clock")
        source_time_bracket.update({
            "after_visible_session_id": first.session_id,
            "after_visible_probe_seq": first.seq,
            "after_visible_request_id": first.request_id,
            "after_visible_native_world_time": asdict(first.snapshot.time),
            "after_visible_m0_tick": energy_ledger.body.tick,
            "observed_item_entity_id": target.entity_id,
            "world_command_effect_timing": "BRACKET_ONLY_NOT_EXACT",
        })

    # Legacy mode retains its strict SEEK gate. The opt-in mode records
    # genuine nonissued WAIT until L0 elects SEEK, M0 terminal or horizon.
    l0_trace: list[dict[str, Any]] = []
    if nonforcing:
        for n in range(24):
            if (
                global_m0_horizon is not None
                and energy_ledger.body.tick >= global_m0_horizon
            ):
                return {
                    "status": "HORIZON_CENSORED_NO_PICKUP", "epoch": epoch,
                    "item_entity_id": target.entity_id,
                    "source_probe_seq": first.seq,
                    "l0_ground_seek_trace": l0_trace,
                    "movement_outcomes": [],
                    "pickup_inventory_delta": 0,
                    "pickup_evidence": "NOT_OBSERVED",
                    "m_energy_credited": False,
                }
            read = first if n == 0 else await _correlated_observe(
                session, f"{namespace}-nf-wait-{n:02d}",
            )
            row = nonforcing_ground_decision(energy_ledger, read, target)
            l0_trace.append(row)
            if row["kind"] == "SEEK":
                break
            if row["m0_terminal_now"]:
                return {
                    "status": "M0_TERMINAL_NO_PICKUP", "epoch": epoch,
                    "item_entity_id": target.entity_id,
                    "source_probe_seq": first.seq,
                    "l0_ground_seek_trace": l0_trace,
                    "movement_outcomes": [],
                    "pickup_inventory_delta": 0,
                    "pickup_evidence": "NOT_OBSERVED",
                    "m_energy_credited": False,
                }
        else:
            return {
                "status": "HORIZON_CENSORED_NO_PICKUP", "epoch": epoch,
                "item_entity_id": target.entity_id,
                "source_probe_seq": first.seq,
                "l0_ground_seek_trace": l0_trace,
                "movement_outcomes": [],
                "pickup_inventory_delta": 0,
                "pickup_evidence": "NOT_OBSERVED",
                "m_energy_credited": False,
            }
    else:
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
    b1_decisions: list[dict[str, Any]] = []
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
        if global_m0_horizon is not None and energy_ledger.body.tick >= global_m0_horizon:
            return {
                "status": "HORIZON_CENSORED_NO_PICKUP", "epoch": epoch,
                "item_entity_id": target.entity_id,
                "source_probe_seq": first.seq,
                "l0_ground_seek_trace": l0_trace,
                "movement_outcomes": movements,
                "pickup_inventory_delta": 0,
                "pickup_evidence": "NOT_OBSERVED",
                "m_energy_credited": False,
            }
        if global_move_limit is not None and len(movements) >= global_move_limit:
            raise GroundRejected("V2 global MOVE budget reached before pickup")
        if nonforcing:
            row = nonforcing_ground_decision(energy_ledger, read, target)
            l0_trace.append(row)
            if row["kind"] == "WAIT":
                if row["m0_terminal_now"]:
                    return {
                        "status": "M0_TERMINAL_NO_PICKUP", "epoch": epoch,
                        "item_entity_id": target.entity_id,
                        "source_probe_seq": first.seq,
                        "l0_ground_seek_trace": l0_trace,
                        "movement_outcomes": movements,
                        "pickup_inventory_delta": 0,
                        "pickup_evidence": "NOT_OBSERVED",
                        "m_energy_credited": False,
                    }
                continue
        else:
            l0_trace.append(_admit_native_l0_seek(energy_ledger, read, target))
        waypoint = (
            b1_local.next_waypoint(read, target)
            if b1_local is not None else target.waypoint()
        )
        if b1_local is not None:
            b1_decisions.append({
                "probe_seq": read.seq,
                "target_entity_id": target.entity_id,
                "waypoint_id": waypoint.goal_id,
                "retained_memory_count": len(b1_local.cognition.memories),
                "l1_candidate_only": True,
                "issued_action": False,
            })
        step = cursor.plan(read, waypoint)
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
            if effect.kind is SeekConsequenceKind.BLOCKED and b1_local is None:
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
                "waypoint_id": waypoint.goal_id,
                "source_outcome_not_goal_success": True,
            })
            if b1_local is not None:
                if waypoint.goal_id == "b1-local-lateral":
                    b1_local.record_alternative_outcome(effect)
                    if effect.kind is SeekConsequenceKind.BLOCKED:
                        raise GroundRejected("B1 lateral Action also BLOCKED; safe stop")
                elif effect.kind is SeekConsequenceKind.BLOCKED:
                    followup = await _correlated_observe(
                        session, f"{namespace}-b1-blocked-followup-{i:02d}",
                    )
                    b1_local.record_blocked(read, effect, followup, target)
        except BaseException:
            if supervisor.get(issued.action_id).state is ActionState.ISSUED:
                supervisor.mark_unknown(
                    issued.action_id, at_ns=14+i*10,
                    provenance=_p(f"unknown-{i}"),
                )
            raise
    if picked is None:
        if global_m0_horizon is not None:
            if energy_ledger.body.tick >= global_m0_horizon:
                return {
                    "status": "HORIZON_CENSORED_NO_PICKUP", "epoch": epoch,
                    "item_entity_id": target.entity_id,
                    "source_probe_seq": first.seq,
                    "l0_ground_seek_trace": l0_trace,
                    "movement_outcomes": movements,
                    "pickup_inventory_delta": 0,
                    "pickup_evidence": "NOT_OBSERVED",
                    "m_energy_credited": False,
                }
            raise GroundRejected("V2 item not acquired within MOVE source bound")
        after = await _correlated_observe(session, f"{namespace}-ground-last-pickup")
        picked = compare_pickup(first, after, target)
    if supervisor.open_actions:
        raise GroundRejected("unclosed ground Action")

    return {
        "epoch": epoch,
        "status": "PICKUP_SOURCE_CONSISTENT",
        "item_entity_id": target.entity_id,
        "source_probe_seq": first.seq,
        "pickup_probe_seq": picked.after_seq,
        "pickup_inventory_delta": picked.rotten_flesh_inventory_delta,
        "pickup_evidence": picked.evidence_kind,
        "movement_outcomes": movements,
        "l0_ground_seek_trace": l0_trace,
        "selection_policy": "B1_L1_CANDIDATE_NOT_QUALIFIED" if b1_local
                            else "DESIGNED_NATIVE_L0_SEEK_NOT_LEARNED",
        "b1_obstacle_request": obstacle_request,
        "b1_local_decisions": b1_decisions,
        "b1_local_evidence": b1_local.evidence() if b1_local else None,
        "item_contents_from_entity_metadata": "UNKNOWN",
        "zombie_drop_observed": False,
        "m_energy_credited": False,
    }
