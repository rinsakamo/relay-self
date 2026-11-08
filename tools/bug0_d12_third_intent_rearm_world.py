"""D12 DEV: genuine two S51 meals -> third World respawn -> original Intent rearm.

Reuses D8 for BOTH physical food cycles. D12 only verifies the next
600-tick World zombie and performs the original S49 owner Intent transition.
No new third physical action, EAT, food, random-drop or model call.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from relay_self.action import ActionState
from relay_self.provenance import Provenance
from tools.bug0_d4_oneworld import run
from tools.bug0_d6_multigen_world import _tick, _uuid, wait_paper
from tools.bug0_d6_natural_move_world import source_qualified_natural_move
from tools.bug0_d7f_natural_eat import after_real_natural_pickup_eat
from tools.bug0_d8_two_natural_food_world import continue_second_natural_food_cycle
from tools.bug0_zombie_respawn_r1_world import _native_probe


class D12ThirdRearmRejected(RuntimeError):
    """Unverified source, prior S51 outcome, or duplicated physical authority."""


async def second_food_then_third_rearm(
    session, server, owner: NormalSessionActionExecutor,
    report: dict, paper_log: Path, *, physical_fence,
    motion_fence, s50_sidecar: Path,
) -> None:
    if os.environ.get("D12_THIRD_INTENT_REARM_WORLD_ONLY") != "1":
        raise D12ThirdRearmRejected("D12 grant missing before second food")
    report["d12_third_rearm_proven"] = False
    report["d12_third_rearm_stage"] = "AWAIT_SECOND_TRUE_FOOD"
    await continue_second_natural_food_cycle(
        session, server, owner, report, paper_log,
        physical_fence=physical_fence,
        motion_fence=motion_fence,
        s50_sidecar=s50_sidecar,
    )
    if report.get("d8_second_generation_food_proven") is not True:
        report["d12_third_rearm_stage"] = "SECOND_TRUE_ZERO_NO_REARM_EXERCISED"
        return

    sid = owner.session_id
    g2 = report["d8_second_generation"]
    last_eat = owner._d7_last_verified_eat_receipt
    previous_count = owner._count
    previous_ids = set(owner._dispatched)
    previous_nonmotion = tuple(physical_fence.actions)
    previous_motion = tuple(motion_fence.actions)
    preserved_supervisor = owner.supervisor
    if (
        owner._intent_epoch != 2
        or not owner._d7_dev_stop_consumed
        or last_eat is None
        or last_eat.terminal.state is not ActionState.OUTCOME
        or last_eat.outcome.count_before != last_eat.outcome.count_after + 1
        or last_eat.outcome.food_after <= last_eat.outcome.food_before
        or not owner._post_move_settling_unqualified
        or owner.supervisor.open_actions
        or physical_fence.unresolved or motion_fence.unresolved
        or len(previous_nonmotion) != owner._attack_count + 2
        or len(previous_motion) != previous_count - owner._attack_count - 2
        or g2.get("d7f_eat_terminal") != "outcome"
        or g2["d7f_eat_outcome"]["action_id"] != last_eat.terminal.action_id
    ):
        raise D12ThirdRearmRejected("second source-qualified S51 owner closure absent")

    report["d12_third_rearm_stage"] = "WAIT_REAL_THIRD_WORLD_SPAWN"
    spawned = await wait_paper(
        paper_log, "RSELF_RESPAWN_SPAWN world=",
        token="generation=3 ", seconds=90,
    )
    third_world = _uuid(spawned, "world")
    third_uuid = _uuid(spawned, "entity")
    if (
        _tick(spawned) - g2["death_tick"] != 600
        or third_world != _uuid(report["initial_paper"], "world")
        or third_uuid in (
            _uuid(report["initial_paper"], "entity"),
            g2["paper_zombie_uuid"],
        )
    ):
        raise D12ThirdRearmRejected("original Paper genuine third spawn invalid")
    next_native = await _native_probe(session, "d12-third-native-new-world")
    fresh = await _correlated_observe(session, "d12-third-new-intent-native")
    zombie_ids = [
        e.entity_id for e in fresh.snapshot.nearby_entities
        if e.name == "zombie"
    ]
    if (
        next_native["session_id"] != sid
        or next_native["zombie_entity_id"] == report["native_initial"]["zombie_entity_id"]
        or fresh.session_id != sid
        or fresh.seq <= next_native["seq"]
        or zombie_ids != [next_native["zombie_entity_id"]]
        or fresh.snapshot.nearby_entities_coverage.truncated
        or fresh.snapshot.nearby_entities_coverage.candidate_count
            != len(fresh.snapshot.nearby_entities)
        or fresh.snapshot.health <= 0
        or fresh.snapshot.oxygen_level == 0
    ):
        raise D12ThirdRearmRejected("fresh original native third zombie absent")

    previous_intent = owner.intent.current_intent
    if previous_intent is None:
        raise D12ThirdRearmRejected("original second Intent missing")
    owner.intent.complete(
        previous_intent.intent_id,
        reason="second real S49/S51 food cycle completed; next World zombie observed",
        at_ns=owner.intent.last_at_ns + 1,
        provenance=Provenance("d12-original-s49-owner", "second-food-closed"),
    )
    third_intent = owner.intent.commit(
        f"d12-third-zombie-{sid}",
        objective="respond to genuine third World zombie and continue survival",
        at_ns=owner.intent.last_at_ns + 1,
        provenance=Provenance("d12-original-s49-owner", "third-world-experience"),
    )
    report["d12_third_rearm_stage"] = "ORIGINAL_S49_REARM_WITH_SECOND_EAT_RECEIPT"
    rearm = owner.advance_intent_epoch(
        fresh,
        previous_zombie_entity_id=report["native_respawn"]["zombie_entity_id"],
        verified_prior_d7_eat=last_eat,
    )
    if (
        rearm.next_epoch != 3
        or owner._intent_epoch != 3
        or rearm.completed_action_count != previous_count
        or rearm.completed_intent_id != previous_intent.intent_id
        or rearm.next_intent_id != third_intent.intent_id
        or rearm.next_zombie_entity_id != next_native["zombie_entity_id"]
        or rearm.physically_issued
        or owner.supervisor is not preserved_supervisor
        or owner._count != previous_count
        or owner._dispatched != previous_ids
        or tuple(physical_fence.actions) != previous_nonmotion
        or tuple(motion_fence.actions) != previous_motion
        or physical_fence.unresolved or motion_fence.unresolved
        or owner.supervisor.open_actions
        or owner._d7_last_verified_eat_receipt is not None
        or owner._d7_dev_stop_consumed
        or owner._post_move_settling_unqualified
    ):
        raise D12ThirdRearmRejected("same S49 retained history / one-use EAT rearm failed")
    report["d12_third_paper_spawn"] = spawned
    report["d12_third_rearm"] = {
        "session_id": sid,
        "same_supervisor": True,
        "same_world": True,
        "original_s49_epoch": 3,
        "completed_intent_id": rearm.completed_intent_id,
        "new_intent_id": rearm.next_intent_id,
        "third_zombie_native_id": next_native["zombie_entity_id"],
        "previous_zombie_native_id": rearm.previous_zombie_entity_id,
        "third_paper_zombie_uuid": third_uuid,
        "native_source_seq": fresh.seq,
        "native_request_id": fresh.request_id,
        "paper_spawn_tick": _tick(spawned),
        "second_death_tick": g2["death_tick"],
        "prior_original_action_count": previous_count,
        "after_rearm_original_action_count": owner._count,
        "third_physical_action_count": 0,
        "prior_second_s51_action_id": last_eat.terminal.action_id,
        "prior_s51_receipt_consumed": True,
        "no_physical_reissue": True,
        "no_new_learning": True,
    }
    report["d12_third_rearm_proven"] = True
    report["d12_third_rearm_stage"] = "THIRD_WORLD_NEW_INTENT_NO_ACTION_DEV_PASS"


def main() -> None:
    parser = argparse.ArgumentParser()
    for field in (
        "report", "server-log", "nonmotion-fence", "motion-fence",
        "d7-passive-controls",
    ):
        parser.add_argument("--" + field, required=True, type=Path)
    args = parser.parse_args()
    for name in (
        "D12_THIRD_INTENT_REARM_WORLD_ONLY",
        "D8_TWO_NATURAL_FOOD_CYCLES_WORLD_ONLY",
        "D7F_NATURAL_S49_S51_WORLD_ONLY",
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
    ):
        if os.environ.get(name) != "1":
            raise SystemExit("explicit DEV World grant missing: " + name)
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
    )))


if __name__ == "__main__":
    main()
