"""Bug-0 REST intent and bounded original S49 native stationary observations.

REST is a cognitive choice. P1 physical fatigue recovers on independently
verified full-tick WAIT, NOT on REST intent or on missing Action commands.
This DEV adapter does not mint Action, grant, P1 state or energy credit.
"""
from __future__ import annotations

import asyncio
import math
from typing import Any, Sequence

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0


class S49RestDevRejected(RuntimeError):
    """Original owner, current native source or stationary candidate invalid."""


def inspect_rest_native_samples(
    observations: Sequence[MineflayerObservation], *, session_id: str,
) -> dict[str, Any]:
    """Validate nine correlated original probes (baseline and eight samples).

    This is intentionally NOT proof of eight fully inactive World ticks:
    a sequence of snapshots cannot exclude activity BETWEEN the snapshots.
    """
    if not isinstance(session_id, str) or not session_id:
        raise S49RestDevRejected("original session identity required")
    if not isinstance(observations, (tuple, list)) or len(observations) != 9:
        raise S49RestDevRejected("one baseline and exactly eight native probes required")
    samples: list[dict[str, Any]] = []
    seen_requests: set[str] = set()
    last_seq = -1
    previous = None
    base = None
    for index, probe in enumerate(observations):
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe"
            or probe.session_id != session_id
            or probe.provenance.source != "mineflayer"
            or probe.provenance.reference != f"{session_id}:{probe.seq}"
            or type(probe.seq) is not int
            or probe.seq <= last_seq
            or not isinstance(probe.request_id, str)
            or not probe.request_id
            or probe.request_id in seen_requests
            or probe.snapshot.nearby_entities_coverage.truncated
            or probe.snapshot.nearby_entities
            or probe.snapshot.health <= 0
            or probe.snapshot.oxygen_level == 0
        ):
            raise S49RestDevRejected("foreign, stale, unsafe or incomplete REST observation")
        last_seq = probe.seq
        seen_requests.add(probe.request_id)
        xyz = probe.snapshot.position
        point = (xyz.x, xyz.y, xyz.z)
        if not all(math.isfinite(v) for v in point):
            raise S49RestDevRejected("nonfinite native position")
        if previous is not None:
            delta = math.dist(point, previous)
            if delta > 0.015:
                raise S49RestDevRejected("native movement during REST candidate")
        if base is None:
            base = point
        elif math.dist(point, base) > 0.03:
            raise S49RestDevRejected("cumulative drift during REST candidate")
        previous = point
        samples.append({
            "index": index, "session_id": probe.session_id,
            "native_seq": probe.seq, "native_request_id": probe.request_id,
            "native_source_ref": probe.provenance.reference,
            "position": {"x": xyz.x, "y": xyz.y, "z": xyz.z},
            "health": probe.snapshot.health, "food": probe.snapshot.food,
        })
    return {
        "native_source": "ORIGINAL_MINEFLAYER_CORRELATED_PROBES",
        "native_stationary_sample_candidate": True,
        "sample_count": 9,
        "samples": samples,
        "physical_wait_full_tick_attested": False,
        "physical_inactivity_between_samples_attested": False,
        "p1_owner_integrated": False,
        "p1_fatigue_before": None,
        "p1_fatigue_after": None,
        "p1_fatigue_recovery_attested": False,
        "m_basal_cost_waived": False,
        "source_independently_attested": False,
    }


async def run_s49_rest_dev(
    session: MineflayerProcessSession, server: object,
    owner: NormalSessionActionExecutor, report: dict[str, Any],
) -> None:
    """Run one explicit REST choice and observe, using original S49 custody."""
    if (
        not isinstance(session, MineflayerProcessSession)
        or not isinstance(owner, NormalSessionActionExecutor)
        or session.started.session_id != owner.session_id
        or session.process_returncode is not None
        or getattr(server, "stdin", None) is None
        or owner._count != 0
        or owner._dispatched
        or owner.supervisor.open_actions
        or owner._post_move_settling_unqualified
        or owner.intent.current_intent is None
        or owner.intent.current_intent.intent_id != "rest-observe"
    ):
        raise S49RestDevRejected("fresh original S49 REST intent/sole owner required")
    sid = owner.session_id
    report["stage"] = "BUG0_S49_REST_NATIVE_STAGING"
    report["rest_intent_selected"] = False
    report["rest_action_issued"] = False
    report["m_energy_credited"] = False
    report["learning_in_world"] = False
    report["operator_world_commands"] = []
    # Prepare only an empty, bounded developer arena. This is operator World
    # staging, not an S49 issued physical Action.
    for command in (
        "gamerule doMobSpawning false",
        "gamerule doDaylightCycle false",
        "kill @e[type=!minecraft:player]",
        "gamemode survival RelaySelf",
        "effect clear RelaySelf minecraft:hunger",
    ):
        _command(server, command)
        report["operator_world_commands"].append(command)
    await server.stdin.drain()
    await asyncio.sleep(2.0)
    first = await _correlated_observe(session, f"s49-bug0-rest-{sid}-baseline")
    policy = S49BasicPriorityL0(sid, max_decisions=12)
    choice = policy.decide(first, rest_requested=True)
    report["rest_choice"] = {
        "selected": choice.selected, "preferred": choice.preferred,
        "reason": choice.reason, "probe_seq": choice.probe_seq,
        "native_source_ref": first.provenance.reference,
        "action_issued": choice.action_issued,
        "permission_granted": choice.permission_granted,
    }
    if (
        choice.selected != "REST"
        or choice.preferred != "REST"
        or choice.action_issued or choice.permission_granted
        or owner._count != 0 or owner.supervisor.open_actions
    ):
        raise S49RestDevRejected("original native L0 did not select safe REST intent")
    report["rest_intent_selected"] = True
    observations = [first]
    report["stage"] = "BUG0_S49_REST_STATIONARY_NATIVE_SAMPLES"
    for index in range(8):
        await asyncio.sleep(0.4)
        observations.append(await _correlated_observe(
            session, f"s49-bug0-rest-{sid}-{index:02d}",
        ))
    candidate = inspect_rest_native_samples(observations, session_id=sid)
    report["rest_observation"] = candidate
    if owner._count != 0 or owner._dispatched or owner.supervisor.open_actions:
        raise S49RestDevRejected("REST observation must never mint an S49 Action")
    report["stage"] = "BUG0_S49_REST_NATIVE_SAMPLES_CLOSED"
