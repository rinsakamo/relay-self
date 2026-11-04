"""Bug-0: S49 original World, one bounded no-EAT condition matrix (DEV).

Reuses original live S49 Mineflayer session and ActionSupervisor; native probes
are never reconstructed. World authority stages full, no-bread, and a stationary
zombie. No Action or learning is allowed by this DEV branch.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0


class S49FoodRefusalFailure(RuntimeError):
    """One of the requested native no-eating conditions was unverified."""


async def run_s49_food_refusal_matrix(
    session: object, server: object, owner: NormalSessionActionExecutor,
    report: dict[str, Any],
) -> None:
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or getattr(getattr(session, "started", None), "session_id", None)
        != owner.session_id
        or getattr(server, "stdin", None) is None
        or owner._count != 0 or owner.supervisor.open_actions
    ):
        raise S49FoodRefusalFailure("fresh original S49 owner and native session required")
    policy = S49BasicPriorityL0(owner.session_id)
    trace: list[dict[str, object]] = []
    report["stage"] = "S49_BUG0_REFUSAL_STAGING"
    report["refusal_trace"] = trace
    report["actual_native_actions"] = []
    report["operator_world_commands"] = []
    report["food_commands_issued"] = 0
    report["automatic_goal_selection"] = False
    report["independent_eat_grant_attested"] = False
    report["m_energy_credited"] = False
    report["learning_in_world"] = False
    report["real_model_calls"] = 0

    async def stage(*commands: str) -> None:
        for command in commands:
            report["operator_world_commands"].append(command)
            _command(server, command)
        await server.stdin.drain()

    async def observe(label: str, *, rest_requested: bool = False):
        probe = await _correlated_observe(session, f"s49-refusal-{label}")
        decision = policy.decide(probe, rest_requested=rest_requested)
        row = asdict(decision)
        row["name"] = label
        row["native_source_ref"] = probe.provenance.reference
        row["bread_count"] = sum(
            x.count for x in probe.snapshot.inventory if x.name == "bread"
        )
        row["native_nearby"] = [
            {"name": x.name, "entity_id": x.entity_id, "distance": x.distance}
            for x in probe.snapshot.nearby_entities
        ]
        trace.append(row)
        if (
            owner._count != 0 or owner._dispatched
            or owner.supervisor.open_actions
            or decision.action_issued or decision.permission_granted
        ):
            raise S49FoodRefusalFailure("no-EAT matrix emitted an Action or grant")
        return row

    # Use a fresh World and an operator-given inventory, never an inferred
    # action or a learned food acquisition plan.
    await stage(
        "gamerule doMobSpawning false",
        "gamemode survival RelaySelf",
        "effect clear RelaySelf minecraft:hunger",
        "kill @e[type=minecraft:zombie]",
        "give RelaySelf minecraft:bread 3",
    )
    await asyncio.sleep(2)
    full = await observe("full-bread")
    if (
        full["selected"] != "WAIT" or full["reason"] != "NOT_HUNGRY"
        or full["food"] != 20.0 or full["bread_count"] < 1
    ):
        raise S49FoodRefusalFailure("FULL + bread did not yield native WAIT")

    await stage(
        "clear RelaySelf minecraft:bread",
        "effect give RelaySelf minecraft:hunger 25 20 true",
    )
    no_food = None
    for attempt in range(16):
        await asyncio.sleep(2)
        current = await observe(f"no-food-{attempt:02d}")
        if current["food"] < 14:
            no_food = current
            break
    if (
        no_food is None or no_food["selected"] != "WAIT"
        or no_food["reason"] != "NO_INVENTORY_FOOD"
        or no_food["bread_count"] != 0
    ):
        raise S49FoodRefusalFailure("HUNGRY without food did not yield native WAIT")

    await stage(
        "give RelaySelf minecraft:bread 3",
        "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
        "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
    )
    dangerous = None
    for attempt in range(8):
        await asyncio.sleep(1)
        current = await observe(f"zombie-{attempt:02d}")
        if any(e["name"] == "zombie" for e in current["native_nearby"]):
            dangerous = current
            break
    if (
        dangerous is None or dangerous["food"] >= 14
        or dangerous["bread_count"] < 1
        or dangerous["selected"] != "DEFER"
        or dangerous["reason"] != "ZOMBIE_PRESENT_NO_DEFENSE_ADMISSION"
        or dangerous["preferred"] != "MOVE_AWAY"
        or dangerous["fallback"] != "ATTACK"
    ):
        raise S49FoodRefusalFailure(
            "observed nearby zombie did not suppress EAT (defense deferred)"
        )
    await stage(
        "effect clear RelaySelf minecraft:hunger",
        "kill @e[type=minecraft:zombie]",
    )
    report["refusal_outcomes"] = {
        "full": full["reason"], "hungry_without_food": no_food["reason"],
        "hungry_with_zombie": dangerous["reason"],
        "native_probe_seqs": [
            full["probe_seq"], no_food["probe_seq"], dangerous["probe_seq"],
        ],
        "no_s49_action_or_native_eat": True,
        "operator_staged_world": True,
    }
    report["stage"] = "S49_BUG0_REFUSAL_COMPLETE"
