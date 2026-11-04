"""One passive REST interval chosen by original S49 native L0 (DEV only).

REST is an explicit non-Action hold: no movement/attack/eat commands, no
ActionSupervisor issuance, no energy/fatigue credit. Original Paper server
game-time and native position endpoints are observed; full-tick inactivity
and P1 owner integration remain unproven.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from adapters.mineflayer.s49_rest_paper_time import read_game_time


class S49RestRejected(ValueError):
    """Passive REST World or S49 native source does not meet strict bounds."""


def safe_rest_decision(
    owner: NormalSessionActionExecutor,
    policy: S49BasicPriorityL0,
    probe: MineflayerObservation,
) -> dict[str, object]:
    """Check an explicit REST request while preserving the sole S49 issuer."""
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or not isinstance(policy, S49BasicPriorityL0)
        or not isinstance(probe, MineflayerObservation)
        or probe.session_id != owner.session_id
        or policy.session_id != owner.session_id
        or probe.kind != "probe" or not probe.request_id
        or owner._count != 0 or owner._dispatched
        or owner.supervisor.open_actions
        or owner._post_move_settling_unqualified
    ):
        raise S49RestRejected("original S49 REST source/Action owner not fresh")
    decision = policy.decide(probe, rest_requested=True)
    snap = probe.snapshot
    if (
        decision.selected != "DEFER"
        or decision.preferred != "REST"
        or decision.reason != "REST_EXECUTOR_NOT_CONNECTED"
        or snap.health <= 0
        or snap.food < 14
        or snap.nearby_entities_coverage.truncated
        or snap.nearby_entities_coverage.candidate_count != 0
        or snap.nearby_entities
        or decision.action_issued or decision.permission_granted
    ):
        raise S49RestRejected("unsafe or unqualified REST candidate")
    return {
        "probe_seq": probe.seq, "request_id": probe.request_id,
        "decision": decision.selected, "preferred": decision.preferred,
        "reason": decision.reason, "food": snap.food,
        "health": snap.health, "entity_candidates": 0,
        "native_source_scope": snap.nearby_entities_coverage.source_scope,
        "position": asdict(snap.position),
        "action_issued": False,
    }


def bounded_rest_interval(before_tick: int, after_tick: int) -> int:
    if (type(before_tick) is not int or type(after_tick) is not int
            or before_tick < 0 or not 8 <= after_tick-before_tick <= 100):
        raise S49RestRejected("real Paper REST interval must cover 8..100 World ticks")
    return after_tick - before_tick


async def run_s49_rest_dev(
    session: MineflayerProcessSession, server: object,
    owner: NormalSessionActionExecutor, report: dict[str, Any],
    *, server_log: Path,
) -> None:
    if (
        not isinstance(session, MineflayerProcessSession)
        or not isinstance(owner, NormalSessionActionExecutor)
        or session.started.session_id != owner.session_id
        or session.process_returncode is not None
        or getattr(server, "stdin", None) is None
        or owner._count != 0 or owner._dispatched
        or owner.supervisor.open_actions
        or not isinstance(server_log, Path)
    ):
        raise S49RestRejected("original S49 physical source/owner needed")
    report["stage"] = "BUG0_S49_REST_DEV_WORLD_PREP"
    report["actual_native_actions"] = []
    report["rest_action_issued"] = False
    report["rest_p1_profile_sha256"] = None
    report["rest_p1_model_integrated"] = False
    report["rest_p1_fatigue_before"] = None
    report["rest_p1_fatigue_after"] = None
    report["rest_p1_fatigue_recovered"] = 0
    report["rest_full_tick_inactivity_attested"] = False
    report["rest_world_source_independently_attested"] = False
    report["rest_energy_debit"] = 0
    report["real_model_calls"] = 0
    report["learning_in_world"] = False
    report["m_energy_credited"] = False
    report["rest_world_operator_commands"] = []
    async def stage(*cmds: str) -> None:
        for cmd in cmds:
            _command(server, cmd)
            report["rest_world_operator_commands"].append(cmd)
        await server.stdin.drain()

    # Initial World staging is operator-only; S49 issues no Action.
    await stage(
        "gamerule doMobSpawning false",
        "kill @e[type=!minecraft:player]",
        "gamemode survival RelaySelf",
        "effect clear RelaySelf minecraft:hunger",
    )
    await asyncio.sleep(2.0)
    sid = owner.session_id
    policy = S49BasicPriorityL0(sid, max_decisions=10)
    initial = await _correlated_observe(
        session, f"s49-rest-{sid}-initial",
    )
    initial_decision = safe_rest_decision(owner, policy, initial)
    before = await _correlated_observe(
        session, f"s49-rest-{sid}-before",
    )
    before_decision = safe_rest_decision(owner, policy, before)
    if before.seq <= initial.seq:
        raise S49RestRejected("stale initial native REST observation")
    nonce = sid.replace("-", "")[:20]
    time_before = await read_game_time(
        server, server_log, phase="before", nonce=nonce,
    )
    report["rest_paper_time_before"] = asdict(time_before)
    report["rest_original_native_before"] = before_decision
    report["rest_initial_native"] = initial_decision
    report["stage"] = "BUG0_S49_REST_PASSIVE_HOLD"
    # No set_control / clear_controls / attack / consume. Simply idle with
    # S49 original session alive and no outstanding physical Action.
    await asyncio.sleep(0.75)
    time_after = await read_game_time(
        server, server_log, phase="after", nonce=nonce,
    )
    report["rest_paper_time_after"] = asdict(time_after)
    report["rest_paper_elapsed_ticks"] = bounded_rest_interval(
        time_before.tick, time_after.tick,
    )
    after = await _correlated_observe(
        session, f"s49-rest-{sid}-after",
    )
    after_decision = safe_rest_decision(owner, policy, after)
    if after.seq <= before.seq:
        raise S49RestRejected("REST after-native observation was stale")
    delta = math.dist(
        tuple(getattr(before.snapshot.position, c) for c in ("x", "y", "z")),
        tuple(getattr(after.snapshot.position, c) for c in ("x", "y", "z")),
    )
    report["rest_endpoint_position_delta_m"] = delta
    report["rest_original_native_after"] = after_decision
    if (
        delta > 0.03
        or before.snapshot.health != after.snapshot.health
        or before.snapshot.food != after.snapshot.food
        or owner._count != 0 or owner._dispatched
        or owner.supervisor.open_actions
    ):
        raise S49RestRejected("REST source changed body or original Action authority")
    report["rest_endpoint_stationary_observed"] = True
    report["rest_physical_scope"] = (
        "PAPER_TIME_PLUS_NATIVE_STATIONARY_ENDPOINTS_ONLY"
    )
    report["rest_source_risks"] = [
        "NO_CONTINUOUS_WORLD_TICK_BODY_INACTIVITY_WITNESS",
        "P1_ORIGINAL_OWNER_NOT_INTEGRATED",
        "NO_PHYSIOLOGICAL_FATIGUE_RECOVERY_ATTESTATION",
        "NO_INDEPENDENT_SOURCE_ATTESTATION",
    ]
    report["stage"] = "BUG0_S49_REST_PASSIVE_ENDPOINTS_CLOSED"
