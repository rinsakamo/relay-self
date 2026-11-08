"""D14 one-World 10000 Paper-tick observation after existing original S49.

No invented zombie death, no extra S49 Actions, no model calls or learning.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import time
from pathlib import Path

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from tools.bug0_d12_third_intent_rearm_world import second_food_then_third_rearm
from tools.bug0_d4_oneworld import run
from tools.bug0_d6_multigen_world import _tick, _uuid
from tools.bug0_d6_natural_move_world import source_qualified_natural_move
from tools.bug0_d7f_natural_eat import after_real_natural_pickup_eat


class D14HorizonRejected(RuntimeError):
    """Missing original Paper tick, source scope, or single Self owner."""


def parse_endurance_marker(log: str, marker: str) -> str | None:
    found = [line for line in log.splitlines() if marker in line]
    if len(found) > 1:
        raise D14HorizonRejected("DUPLICATED_WORLD_TICK_MARKER")
    return found[0] if found else None


def _field(line: str, name: str) -> int:
    match = re.search(rf"(?:^| ){re.escape(name)}=(-?\d+)(?: |$)", line)
    if not match:
        raise D14HorizonRejected("MISSING_PAPER_FIELD_" + name)
    return int(match.group(1))


async def observe_to_10000_world_ticks(
    session, server, owner: NormalSessionActionExecutor,
    report: dict, paper_log: Path,
) -> None:
    if (
        os.environ.get("D14_10000_TICK_WORLD_ONLY") != "1"
        or report.get("d14_tick_horizon_optin") is not True
        or report.get("d14_tick_horizon_requested") != 10000
        or not isinstance(owner, NormalSessionActionExecutor)
        or owner.session_id != session.started.session_id
        or owner.supervisor.open_actions
    ):
        raise D14HorizonRejected("SINGLE_ORIGINAL_OWNER_AND_TICK_GRANT_REQUIRED")
    report["d14_tick_horizon_proven"] = False
    report["d14_stage"] = "WATCHING_WORLD_10000_TICKS"
    report["d14_self_continuous_action_policy_enabled"] = False
    report["d14_additional_native_actions"] = 0
    report["d14_heartbeat_observations"] = []
    report["d14_start_action_count"] = owner._count
    original_ids = frozenset(owner._dispatched)
    original_supervisor = owner.supervisor
    started = time.monotonic()
    seen_ticks: set[int] = set()
    start_line = None
    final_line = None
    while time.monotonic() - started < 900:
        if server.returncode is not None:
            raise D14HorizonRejected("PAPER_SERVER_EXITED_BEFORE_10000_TICKS")
        raw = paper_log.read_text(encoding="utf8") if paper_log.is_file() else ""
        if "RSELF_RESPAWN_FAULT" in raw or "RSELF_NATURAL_DROP_FAULT" in raw:
            raise D14HorizonRejected("WORLD_SOURCE_FAULT")
        start_line = parse_endurance_marker(raw, "RSELF_ENDURANCE_START world=")
        if start_line:
            samples = [
                line for line in raw.splitlines()
                if "RSELF_ENDURANCE_SAMPLE world=" in line
            ]
            for line in samples:
                sample_tick = _field(line, "tick")
                if sample_tick in seen_ticks:
                    continue
                if (
                    _uuid(line, "world") != _uuid(start_line, "world")
                    or _field(line, "elapsed_ticks") != (
                        sample_tick - _field(start_line, "start_tick")
                    )
                    or _field(line, "elapsed_ticks") % 200 != 0
                ):
                    raise D14HorizonRejected("PAPER_WORLD_HEARTBEAT_BAD_TICK")
                seen_ticks.add(sample_tick)
                view = await _correlated_observe(
                    session, f"d14-world-tick-{sample_tick}-passive",
                )
                if (
                    view.session_id != owner.session_id
                    or view.snapshot.health <= 0
                    or owner.supervisor.open_actions
                    or owner.supervisor is not original_supervisor
                    or owner._dispatched != original_ids
                    or owner._count != report["d14_start_action_count"]
                ):
                    raise D14HorizonRejected("ORIGINAL_SELF_SOURCE_OR_ACTION_CHANGED")
                report["d14_heartbeat_observations"].append({
                    "paper_tick": sample_tick,
                    "elapsed_world_ticks": _field(line, "elapsed_ticks"),
                    "generation": _field(line, "generation"),
                    "paper_living": line.split(" living=")[1].split()[0],
                    "native_seq": view.seq,
                    "native_request_id": view.request_id,
                    "native_food": view.snapshot.food,
                    "native_health": view.snapshot.health,
                    "native_oxygen": view.snapshot.oxygen_level,
                    "native_inventory_rotten": sum(
                        x.count for x in view.snapshot.inventory
                        if x.name == "rotten_flesh"
                    ),
                })
            final_line = parse_endurance_marker(raw, "RSELF_ENDURANCE_LIMIT world=")
            if final_line:
                break
        await asyncio.sleep(0.8)
    if start_line is None or final_line is None:
        raise D14HorizonRejected("EXACT_10000_WORLD_TICK_END_NOT_OBSERVED")
    start_tick = _field(start_line, "start_tick")
    stop_tick = _field(start_line, "stop_tick")
    observed_tick = _field(final_line, "observed_tick")
    if (
        stop_tick != start_tick + 10000
        or _field(final_line, "elapsed_ticks") != 10000
        or observed_tick != stop_tick
        or _field(final_line, "start_tick") != start_tick
        or _field(final_line, "end_tick") != stop_tick
        or _uuid(start_line, "world") != _uuid(final_line, "world")
        or "stop_new_spawns=true no_forced_death=true" not in final_line
        or owner._count != report["d14_start_action_count"]
        or owner._dispatched != original_ids
        or owner.supervisor.open_actions
    ):
        raise D14HorizonRejected("TICK_LIMIT_OR_OWNER_CHANGED")
    report["d14_tick_horizon"] = {
        "world_uuid": _uuid(start_line, "world"),
        "start_tick": start_tick,
        "end_tick": observed_tick,
        "world_ticks": 10000,
        "final_generation": _field(final_line, "generation"),
        "final_living": final_line.split(" living=")[1].split()[0],
        "periodic_source_samples": len(seen_ticks),
        "original_s49_action_count": owner._count,
        "native_new_actions_issued_by_horizon": 0,
        "source_original_start": start_line,
        "source_original_end": final_line,
    }
    report["d14_tick_horizon_proven"] = True
    report["d14_stage"] = "PAPER_WORLD_TICK_LIMIT_REACHED"
    report["d14_l2_calls"] = 0
    report["d14_learning_updates"] = 0


def main() -> None:
    p = argparse.ArgumentParser()
    for arg in ("report", "server-log", "nonmotion-fence",
                "motion-fence", "d7-passive-controls"):
        p.add_argument("--" + arg, type=Path, required=True)
    args = p.parse_args()
    required = (
        "D14_10000_TICK_WORLD_ONLY",
        "D12_THIRD_INTENT_REARM_WORLD_ONLY",
        "D8_TWO_NATURAL_FOOD_CYCLES_WORLD_ONLY",
        "D7F_NATURAL_S49_S51_WORLD_ONLY",
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
    )
    if any(os.environ.get(key) != "1" for key in required):
        raise SystemExit("explicit D14 plus inherited D12/D8 DEV grants required")
    raise SystemExit(asyncio.run(run(
        args.report, args.server_log,
        post_respawn_dev=second_food_then_third_rearm,
        nonmotion_fence_path=args.nonmotion_fence,
        motion_fence_path=args.motion_fence,
        post_death_loot_move_dev=source_qualified_natural_move,
        d7_native_controls_path=args.d7_passive_controls,
        d7f_natural_eat_dev=after_real_natural_pickup_eat,
        d8_two_generation_food_dev=True,
        d12_third_intent_rearm_dev=True,
        d14_tick_endurance_dev=True,
        post_tick_horizon_dev=observe_to_10000_world_ticks,
    )))


if __name__ == "__main__":
    main()
