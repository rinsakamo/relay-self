"""D9-A DEV: after two genuine D8 meals, keep SAME World open to zombie gen3.

Only read native SelfBody/SelfWorld and original Paper server ticks. The third
zombie is NOT attacked and no REST Action is synthesized. Original owner,
physical ledgers and previous actions are preserved.
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
from pathlib import Path

from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from relay_self.action import ActionState
from tools.bug0_d4_oneworld import run as d4_world
from tools.bug0_d6_multigen_world import _tick, _uuid, one_source_line
from tools.bug0_d6_natural_move_world import source_qualified_natural_move
from tools.bug0_d7f_natural_eat import after_real_natural_pickup_eat
from tools.bug0_d8_two_natural_food_world import continue_second_natural_food_cycle
from tools.bug0_zombie_respawn_r1_world import _native_probe


class D9SurvivalRejected(RuntimeError):
    """The third authentic World generation or continued survival is unproven."""


def d9_body_sample(frame) -> dict:
    """An honest read-only native body/world observation (no hidden fatigue)."""
    snapshot = frame.snapshot
    food, health = snapshot.food, snapshot.health
    if (
        frame.kind != "probe" or not frame.request_id
        or not math.isfinite(food) or not math.isfinite(health)
        or food <= 0 or health <= 0 or snapshot.oxygen_level == 0
        or snapshot.nearby_entities_coverage.truncated
        or snapshot.nearby_entities_coverage.candidate_count
            != len(snapshot.nearby_entities)
    ):
        raise D9SurvivalRejected("native SelfBody/World source dead or incomplete")
    meat = sum(
        item.count for item in snapshot.inventory
        if item.name == "rotten_flesh"
    )
    return {
        "session_id": frame.session_id,
        "native_seq": frame.seq,
        "request_id": frame.request_id,
        "food": food,
        "health": health,
        "rotten_flesh": meat,
        "zombie_ids": [
            e.entity_id for e in snapshot.nearby_entities
            if e.name == "zombie"
        ],
    }


def d9_qualify_third_spawn(
    first_paper: str, second_paper: str, second_death: str,
    third_paper: str,
) -> dict:
    """Paper source only: 600 server ticks, one World, three fresh UUIDs."""
    u1 = _uuid(first_paper, "entity")
    u2 = _uuid(second_paper, "entity")
    u3 = _uuid(third_paper, "entity")
    world = _uuid(first_paper, "world")
    if (
        len({u1, u2, u3}) != 3
        or _uuid(second_paper, "world") != world
        or _uuid(second_death, "world") != world
        or _uuid(third_paper, "world") != world
        or _uuid(second_death, "entity") != u2
        or _tick(third_paper) - _tick(second_death) != 600
        or "generation=3 " not in third_paper
        or "killer=" not in second_death
    ):
        raise D9SurvivalRejected("third World zombie did not follow second death")
    return {
        "paper_world_uuid": world,
        "first_zombie_uuid": u1,
        "second_zombie_uuid": u2,
        "third_zombie_uuid": u3,
        "second_death_tick": _tick(second_death),
        "third_spawn_tick": _tick(third_paper),
        "third_spawn_after_death_ticks": 600,
    }


async def continue_d9_until_third_respawn(
    session, server, owner, report: dict, paper_log: Path, *,
    physical_fence, motion_fence, s50_sidecar: Path,
) -> None:
    if os.environ.get("D9_THIRD_RESPAWN_OBSERVATION_WORLD_ONLY") != "1":
        raise D9SurvivalRejected("D9 fresh World observation grant absent")
    await continue_second_natural_food_cycle(
        session, server, owner, report, paper_log,
        physical_fence=physical_fence, motion_fence=motion_fence,
        s50_sidecar=s50_sidecar,
    )
    second = report.get("d8_second_generation")
    two_meals = report.get("d8_second_generation_food_proven") is True
    second_vanilla_zero = (
        not two_meals
        and isinstance(second, dict)
        and second.get("real_rotten_flesh_count") == 0
        and second.get("original_eat_issued") is False
        and report.get("self_eat") is True
        and report.get("d8_original_second_attack_action_id") in owner._dispatched
    )
    if not two_meals and not second_vanilla_zero:
        report["d9_status"] = "NOT_EXERCISED"
        report["d9_classification"] = "D9_FIRST_TWO_REAL_KILLS_NOT_CLOSED"
        return
    receipt = owner._d7_last_verified_eat_receipt
    if (
        owner._intent_epoch != 2
        or owner.supervisor.open_actions
        or physical_fence.unresolved or motion_fence.unresolved
        or (
            two_meals and (
                receipt is None or receipt.terminal.state
                    is not ActionState.OUTCOME
                or not owner._d7_dev_stop_consumed
                or not report.get("d8_original_same_supervisor")
            )
        )
        or (
            second_vanilla_zero and (
                receipt is not None or owner._d7_dev_stop_consumed
                or owner._post_move_settling_unqualified
                or owner._epoch_attack_count != 1
                or len(physical_fence.actions) != owner._attack_count + 1
                or len(motion_fence.actions)
                    != owner._count - owner._attack_count - 1
            )
        )
    ):
        raise D9SurvivalRejected("second real S49 Action/STOP/zero source not closed")
    sid = session.started.session_id
    action_ids = frozenset(owner._dispatched)
    action_count = owner._count
    nonmotion_sha = physical_fence.sha256
    motion_sha = motion_fence.sha256
    original_supervisor = owner.supervisor
    existing_inventory = (
        report["d8_final_rotten_inventory"] if two_meals
        else report["d8_prior_rotten_after_gen1_eat"]
    )
    if type(existing_inventory) is not int or existing_inventory < 0:
        raise D9SurvivalRejected("negative or unknown original natural inventory")
    report["d9_second_vanilla_zero_continued"] = second_vanilla_zero
    report["d9_two_real_meals_proven"] = two_meals

    report["d9_stage"] = "POST_D8_SAME_WORLD_PASSIVE_BODY_MONITOR"
    records = []
    third_paper = None
    previous_seq = -1
    for i in range(60):
        frame = await _correlated_observe(
            session, f"d9-post-second-idle-native-{i:02d}",
        )
        sample = d9_body_sample(frame)
        if (
            frame.session_id != sid or sample["native_seq"] <= previous_seq
            or sample["rotten_flesh"] != existing_inventory
            or owner.supervisor is not original_supervisor
            or owner._count != action_count
            or frozenset(owner._dispatched) != action_ids
            or owner.supervisor.open_actions
            or physical_fence.sha256 != nonmotion_sha
            or motion_fence.sha256 != motion_sha
        ):
            raise D9SurvivalRejected("native monitor changed original physical owner")
        previous_seq = sample["native_seq"]
        records.append(sample)
        raw = paper_log.read_text(encoding="utf8")
        if "RSELF_RESPAWN_FAULT" in raw or "RSELF_NATURAL_DROP_FAULT" in raw:
            raise D9SurvivalRejected("original Paper fault while monitoring")
        third_paper = one_source_line(
            raw, "RSELF_RESPAWN_SPAWN world=", token="generation=3 ",
        )
        if third_paper is not None:
            break
        await asyncio.sleep(1.15)
    report["d9_body_monitor_samples"] = records
    if third_paper is None:
        raise D9SurvivalRejected("third World respawn not observed before bound")
    g2 = report["d8_second_generation"]
    paper_info = d9_qualify_third_spawn(
        report["initial_paper"], report["paper_respawn"],
        g2["paper_respawn_death"], third_paper,
    )
    native = await _native_probe(session, "d9-new-generation3-native")
    fresh = await _correlated_observe(session, "d9-generation3-read-only-l0")
    after = d9_body_sample(fresh)
    if (
        native["session_id"] != sid or fresh.session_id != sid
        or fresh.seq <= previous_seq or fresh.seq <= native["seq"]
        or native["zombie_entity_id"] == report["native_initial"]["zombie_entity_id"]
        or native["zombie_entity_id"] == report["native_respawn"]["zombie_entity_id"]
        or native["zombie_entity_id"] not in after["zombie_ids"]
        or after["rotten_flesh"] != existing_inventory
    ):
        raise D9SurvivalRejected("third generation not newly visible to same native Self")
    shadow = S49BasicPriorityL0(sid, max_decisions=3).decide(fresh)
    if (
        owner.supervisor is not original_supervisor
        or owner._count != action_count
        or frozenset(owner._dispatched) != action_ids
        or physical_fence.sha256 != nonmotion_sha
        or motion_fence.sha256 != motion_sha
        or owner.supervisor.open_actions
    ):
        raise D9SurvivalRejected("read-only third World observation issued Action")
    raw = paper_log.read_text(encoding="utf8")
    if (
        one_source_line(
            raw, "RSELF_RESPAWN_DEATH world=", token="generation=3 ",
        ) is not None
    ):
        raise D9SurvivalRejected("third World zombie died without original S49 ATTACK")

    report["d9_third_paper_spawn"] = third_paper
    report["d9_third_paper_lineage"] = paper_info
    report["d9_third_native"] = native
    report["d9_final_native_body"] = after
    report["d9_read_only_l0"] = {
        "selected": shadow.selected,
        "reason": shadow.reason,
        "provenance": fresh.provenance.reference,
        "actually_dispatched": False,
    }
    report["d9_original_action_count"] = action_count
    report["d9_original_action_ids"] = sorted(action_ids)
    report["d9_nonmotion_sha256"] = nonmotion_sha
    report["d9_motion_sha256"] = motion_sha
    report["d9_physical_action_issued_after_second_generation"] = False
    report["d9_physical_action_issued_after_second_eat"] = (
        False if two_meals else None
    )
    report["d9_autonomous_rest_selected"] = False
    report["d9_passive_wait_input_off_not_rest_authorized"] = True
    report["d9_status"] = "PASS_DEV"
    report["d9_classification"] = (
        "D9_TWO_REAL_EATS_THIRD_RESPAWN_READ_ONLY_SURVIVAL_PASS"
        if two_meals
        else "D9_SECOND_ZERO_DROP_THIRD_RESPAWN_READ_ONLY_SURVIVAL_PASS"
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--nonmotion-fence", type=Path, required=True)
    p.add_argument("--motion-fence", type=Path, required=True)
    p.add_argument("--d7-passive-controls", type=Path, required=True)
    args = p.parse_args()
    if (
        os.environ.get("D9_THIRD_RESPAWN_OBSERVATION_WORLD_ONLY") != "1"
        or os.environ.get("D8_TWO_NATURAL_FOOD_CYCLES_WORLD_ONLY") != "1"
    ):
        raise SystemExit("D9 passive third World gate not granted")
    raise SystemExit(asyncio.run(d4_world(
        args.report, args.server_log,
        nonmotion_fence_path=args.nonmotion_fence,
        motion_fence_path=args.motion_fence,
        post_death_loot_move_dev=source_qualified_natural_move,
        d7_native_controls_path=args.d7_passive_controls,
        d7f_natural_eat_dev=after_real_natural_pickup_eat,
        post_respawn_dev=continue_d9_until_third_respawn,
        d8_two_generation_food_dev=True,
    )))


if __name__ == "__main__":
    main()
