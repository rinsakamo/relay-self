"""D8 DEV: a true second-generation natural zombie food cycle on original S49.

Continues the SAME running Paper World after first D7-F true natural EAT,
through World-owned 600tick respawn, newly committed Intent, new ATTACK,
genuine vanilla drop/pickup, last original MOVE STOP and second native EAT.
No additional physical issuer, item staging, direct food modification or
unrecorded native Action. Exact two cycles only if BOTH true drops are positive.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from adapters.mineflayer.normal_action import (
    NormalActionStage,
    NormalAttackingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from relay_self.action import ActionState
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.provenance import Provenance
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d4_oneworld import (
    _target,
    qualified_native_precombat_hunger,
)
from tools.bug0_d4_oneworld import (
    run as d4_world,
)
from tools.bug0_d6_multigen_world import _rotten, _tick, _uuid, wait_paper
from tools.bug0_d6_natural_move_world import source_qualified_natural_move
from tools.bug0_d7f_natural_eat import after_real_natural_pickup_eat
from tools.bug0_pickup_d1_world import _inventory


class D8TwoCycleRejected(RuntimeError):
    """Second actual World zombie/food/Action lineage is not qualified."""


async def continue_second_natural_food_cycle(
    session, server, owner: NormalSessionActionExecutor,
    report: dict, paper_log: Path, *,
    physical_fence: OriginalS49NonMotionFence,
    motion_fence: OriginalS49PhysicalFence,
    s50_sidecar: Path,
) -> None:
    sid = session.started.session_id
    previous_owner = owner.supervisor
    prior = owner._d7_last_verified_eat_receipt
    previous_id = report.get("native_initial", {}).get("zombie_entity_id")
    previous_paper_death = report["paper_respawn_death"]
    next_native = report["native_respawn"]
    next_spawn = report["paper_respawn"]
    prior_rotten = report.get("d7f_native_after_eat", {}).get("rotten_flesh")
    initial_world = _uuid(report["initial_paper"], "world")
    prior_paper_zombie = _uuid(report["initial_paper"], "entity")
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or owner.session_id != sid or owner._intent_epoch != 1
        or owner.supervisor.open_actions
        or not owner._d7_dev_stop_consumed
        or prior is None or prior.terminal.state is not ActionState.OUTCOME
        or not isinstance(physical_fence, OriginalS49NonMotionFence)
        or not isinstance(motion_fence, OriginalS49PhysicalFence)
        or physical_fence.unresolved or motion_fence.unresolved
        or len(physical_fence.actions) != owner._attack_count + 1
        or len(motion_fence.actions) != (
            owner._count - owner._attack_count - 1
        )
        or report.get("self_eat") is not True
        or report.get("real_rotten_flesh_count") not in (1, 2)
        or type(prior_rotten) is not int
        or prior_rotten != report["real_rotten_flesh_count"] - 1
        or next_native["session_id"] != sid
        or next_native["zombie_entity_id"] == previous_id
        or _uuid(next_spawn, "world") != initial_world
        or _uuid(next_spawn, "entity") == prior_paper_zombie
        or _tick(next_spawn) - _tick(previous_paper_death) != 600
        or "generation=2 " not in next_spawn
    ):
        raise D8TwoCycleRejected("first real S49 STOP/EAT or World 600tick source not closed")

    report["d8_stage"] = "GEN2_FRESH_WORLD_AND_INTENT"
    report["d8_previous_original_action_ids"] = sorted(owner._dispatched)
    report["d8_prior_rotten_after_gen1_eat"] = prior_rotten
    report["d8_first_completed_intent"] = owner.intent.current_intent.intent_id
    report["d8_second_generation_food_proven"] = False
    report["d8_last_real_world_zombie_uuid"] = _uuid(next_spawn, "entity")

    fresh = await _correlated_observe(session, "d8-gen2-fresh-rearm-source")
    zombies = [e.entity_id for e in fresh.snapshot.nearby_entities if e.name == "zombie"]
    if (
        fresh.session_id != sid or fresh.seq <= next_native["seq"]
        or zombies != [next_native["zombie_entity_id"]]
        or fresh.snapshot.health <= 15
        or fresh.snapshot.oxygen_level == 0
        or fresh.snapshot.nearby_entities_coverage.truncated
        or fresh.snapshot.nearby_entities_coverage.candidate_count
            != len(fresh.snapshot.nearby_entities)
    ):
        raise D8TwoCycleRejected("gen2 new native zombie/health source missing")
    old_intent = owner.intent.current_intent
    old_count = owner._count
    owner.intent.complete(
        old_intent.intent_id,
        reason="original real natural zombie killed, natural item moved and eaten",
        at_ns=owner.intent.last_at_ns + 1,
        provenance=Provenance("d8-original-s49", "end-real-food-generation-1"),
    )
    second_intent = owner.intent.commit(
        f"d8-natural-zombie-second-{sid}",
        objective="survive second actual World zombie and eat genuine natural food",
        at_ns=owner.intent.last_at_ns + 1,
        provenance=Provenance("d8-original-s49", "begin-natural-generation-2"),
    )
    rearm = owner.advance_intent_epoch(
        fresh, previous_zombie_entity_id=previous_id,
        verified_prior_d7_eat=prior,
    )
    if (
        rearm.next_epoch != 2
        or rearm.completed_action_count != old_count
        or rearm.next_intent_id != second_intent.intent_id
        or rearm.physically_issued or owner.supervisor is not previous_owner
        or owner._dispatched != set(report["d8_previous_original_action_ids"])
        or owner._post_move_settling_unqualified
        or owner._d7_dev_stop_consumed
    ):
        raise D8TwoCycleRejected("original S49 retained owner rearm failed")
    report["d8_intent_rearm"] = {
        "previous_intent": old_intent.intent_id,
        "next_intent": second_intent.intent_id,
        "previous_native_id": previous_id,
        "next_native_id": rearm.next_zombie_entity_id,
        "new_read_seq": fresh.seq, "previous_action_count": old_count,
        "same_supervisor": True, "no_physical_issue_for_rearm": True,
    }

    # Operator only stages the *new zombie* in this isolated DEV arena,
    # not meat, player inventory, or native food. Scope commands to
    # the player's World, not a server-global entity in another dimension.
    report["d8_stage"] = "GEN2_OPERATOR_TARGET_ONLY"
    commands = (
        "execute as RelaySelf at @s run tag "
        "@e[type=minecraft:zombie,sort=nearest,limit=1,distance=..16] "
        "add RelaySelfAttackTarget",
        "execute as RelaySelf at @s run tp "
        "@e[type=minecraft:zombie,tag=RelaySelfAttackTarget,limit=1] ^ ^ ^-2.2",
        "execute as RelaySelf at @s run data merge entity "
        "@e[type=minecraft:zombie,tag=RelaySelfAttackTarget,limit=1] "
        "{NoAI:1b,Silent:1b,Health:0.8f}",
        "execute as RelaySelf at @s run kill "
        "@e[type=minecraft:experience_orb,distance=..12]",
        "effect give RelaySelf minecraft:hunger 70 20 true",
    )
    for command in commands:
        _command(server, command)
    await server.stdin.drain()
    report["d8_operator_generation2_commands"] = list(commands)
    report["d8_operator_food_item_created"] = False
    report["d8_operator_hunger_effect"] = True
    await asyncio.sleep(0.7)

    report["d8_stage"] = "GEN2_NATIVE_FOOD_AND_THREAT"
    food_crossed = None
    report["d8_precombat_hunger_trace"] = []
    for attempt in range(80):
        source = await _correlated_observe(
            session, f"d8-gen2-hunger-{attempt:02d}",
        )
        report["d8_precombat_hunger_trace"].append({
            "seq": source.seq, "food": source.snapshot.food,
            "health": source.snapshot.health,
        })
        if qualified_native_precombat_hunger(source, sid):
            food_crossed = source
            break
        await asyncio.sleep(0.55)
    if food_crossed is None:
        raise D8TwoCycleRejected("real second-generation Hunger never reached S49 threshold")
    report["d8_precombat_hunger_qualified"] = True
    prev = await _correlated_observe(session, "d8-gen2-attack-prev")
    await asyncio.sleep(0.3)
    current = await _correlated_observe(session, "d8-gen2-attack-now")
    _target(prev, next_native["zombie_entity_id"])
    _target(current, next_native["zombie_entity_id"])
    decision = S49BasicPriorityL0(sid, max_decisions=4).decide(current)
    if (
        decision.selected != "DEFER"
        or decision.preferred != "MOVE_AWAY"
        or decision.fallback != "ATTACK"
    ):
        raise D8TwoCycleRejected("original L0 denied second zombie ATTACK fallback")
    action_id = f"d8-gen2-s49-attack-1-{sid}"
    grants = dict(
        intent_id=second_intent.intent_id, session_id=sid, action_id=action_id,
        probe_seq=current.seq, probe_request_id=current.request_id,
        target_entity_id=next_native["zombie_entity_id"], granted=True,
    )
    propose = NormalAttackingAuthorization(
        stage=NormalActionStage.PROPOSE, authority_id="d8-gen2-propose",
        provenance=Provenance("d8-operator-dev", "new-zombie-propose"),
        **grants,
    )
    issue = NormalAttackingAuthorization(
        stage=NormalActionStage.ISSUE, authority_id="d8-gen2-issue",
        provenance=Provenance("d8-operator-dev", "new-zombie-issue"),
        **grants,
    )
    report["d8_stage"] = "GEN2_REAL_S49_ATTACK"
    receipt = await owner.execute_attack(
        session, prev, current, next_native["zombie_entity_id"],
        propose, issue, allow_target_disappearance=True,
        physical_fence=physical_fence,
    )
    if (
        receipt.terminal.state is not ActionState.OUTCOME
        or receipt.effect.result != "applied"
        or owner._count != old_count + 1
        or owner._epoch_attack_count != 1
        or owner.supervisor is not previous_owner
        or owner.supervisor.open_actions
    ):
        raise D8TwoCycleRejected("gen2 physical ATTACK not original S49 outcome")
    report["d8_original_second_attack_action_id"] = action_id
    report["d8_original_second_attack_effect_seq"] = receipt.effect.seq
    second_paper_zombie = _uuid(next_spawn, "entity")
    death = await wait_paper(
        paper_log, "RSELF_RESPAWN_DEATH world=",
        token="generation=2 ", seconds=12,
    )
    natural = await wait_paper(
        paper_log, "RSELF_NATURAL_DROP_DEATH world=",
        token=f"zombie={second_paper_zombie} ", seconds=5,
    )
    if (
        _uuid(death, "entity") != second_paper_zombie
        or "killer_is_relay_self=true" not in natural
        or _uuid(death, "killer") != _uuid(natural, "killer")
        or _tick(death) != _tick(natural)
    ):
        raise D8TwoCycleRejected("gen2 Paper zombie true killer/death attestation absent")
    second_count = _rotten(natural)
    if second_count not in (0, 1, 2):
        raise D8TwoCycleRejected("vanilla source amount invalid")

    g2 = {
        "generation": 2, "paper_world_uuid": initial_world,
        "paper_zombie_uuid": second_paper_zombie,
        "paper_natural_death": natural,
        "paper_respawn_death": death,
        "death_tick": _tick(death),
        "real_rotten_flesh_count": second_count,
        "d4_natural_count": second_count,
        "d4_precombat_hunger_qualified": True,
        "d7f_operator_hunger_effect_dev": True,
        "self_attack_principal_attested": True,
        "d8_paper_current_zombie_uuid": second_paper_zombie,
        "d8_second_generation_dev": True,
    }
    report["d8_second_generation"] = g2
    if second_count == 0:
        report["d8_stage"] = "GEN2_TRUE_ZERO_NATURAL_DROP_NO_EAT"
        g2["classification"] = "D8_SECOND_TRUE_ZERO_DROP_EAT_NOT_EXERCISED"
        g2["original_eat_issued"] = False
        return

    report["d8_stage"] = "GEN2_NATURAL_ITEM_ORIGINAL_S49_MOVE"
    paper_spawn_item = await wait_paper(
        paper_log, "RSELF_NATURAL_DROP_SPAWN world=",
        token=f"zombie={second_paper_zombie} ", seconds=5,
    )
    if _rotten(paper_spawn_item) != second_count:
        raise D8TwoCycleRejected("gen2 Paper item spawn count differs from death")
    g2["d4_paper_item_spawn"] = paper_spawn_item
    g2["paper_loot_death"] = natural

    original_move = await source_qualified_natural_move(
        session, owner, g2, paper_log,
        motion_fence=motion_fence,
        d7f_live_eat_dev=True,
        d8_next_generation_dev=True,
        d8_prior_rotten_count=prior_rotten,
    )
    if (
        original_move is None or original_move[0] is not owner
        or not 1 <= len(g2.get("d6_original_s49_move_actions", ())) <= 4
    ):
        raise D8TwoCycleRejected("second native original S49 MOVE receipt absent")
    paper_pickup = await wait_paper(
        paper_log, "RSELF_NATURAL_DROP_PICKUP world=",
        token=f"zombie={second_paper_zombie} ", seconds=12,
    )
    if (
        _uuid(paper_pickup, "item") != _uuid(paper_spawn_item, "item")
        or _rotten(paper_pickup) != second_count
        or _tick(paper_pickup) <= _tick(paper_spawn_item)
    ):
        raise D8TwoCycleRejected("second Paper item genuine UUID pickup missing")
    g2["d4_paper_item_pickup"] = paper_pickup
    pickup = await _correlated_observe(session, "d8-gen2-native-after-real-pickup")
    actual_meat = sum(
        item.count for item in pickup.snapshot.inventory
        if item.name == "rotten_flesh"
    )
    if (
        pickup.session_id != sid
        or actual_meat != prior_rotten + second_count
        or owner.supervisor.open_actions
        or not owner._post_move_settling_unqualified
    ):
        raise D8TwoCycleRejected("second genuine Paper pickup did not raise native meat")
    g2["d4_native_after_pickup"] = _inventory(pickup)
    g2["d8_inventory_before_new_pickup"] = prior_rotten
    g2["d8_inventory_after_new_pickup"] = actual_meat
    report["d8_stage"] = "GEN2_CURRENT_WORLD_STOP_AND_ORIGINAL_S51_EAT"

    eaten = await after_real_natural_pickup_eat(
        session, server, owner, g2, paper_log,
        original_move=original_move, native_pickup=pickup,
        nonmotion_fence=physical_fence, s50_sidecar=s50_sidecar,
        d8_second_generation_dev=True,
        d8_prior_rotten_count=prior_rotten,
    )
    if (
        eaten is not True
        or g2.get("d7f_eat_terminal") != "outcome"
        or g2.get("d7f_natural_inventory_after")
            != prior_rotten + second_count - 1
        or len(physical_fence.actions) != owner._attack_count + 2
        or len(motion_fence.actions) != (
            owner._count - owner._attack_count - 2
        )
        or physical_fence.unresolved or motion_fence.unresolved
        or owner.supervisor.open_actions
        or any(
            owner.supervisor.get(action).state is not ActionState.OUTCOME
            for action in owner._dispatched
        )
    ):
        raise D8TwoCycleRejected("original second natural S49 EAT not closed")

    report["d8_original_same_supervisor"] = (
        owner.supervisor is previous_owner
    )
    report["d8_original_total_actions"] = owner._count
    report["d8_original_total_attacks"] = owner._attack_count
    report["d8_original_total_moves"] = len(motion_fence.actions)
    report["d8_original_total_eats"] = 2
    report["d8_final_rotten_inventory"] = (
        g2["d7f_natural_inventory_after"]
    )
    report["d8_second_generation_food_proven"] = True
    report["d8_stage"] = "TWO_GENUINE_NATURAL_FOOD_CYCLES_ONE_WORLD_DEV"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--nonmotion-fence", type=Path, required=True)
    p.add_argument("--motion-fence", type=Path, required=True)
    p.add_argument("--d7-passive-controls", type=Path, required=True)
    a = p.parse_args()
    if os.environ.get("D8_TWO_NATURAL_FOOD_CYCLES_WORLD_ONLY") != "1":
        raise SystemExit("D8 second natural zombie food trial not explicitly granted")
    raise SystemExit(asyncio.run(d4_world(
        a.report, a.server_log,
        nonmotion_fence_path=a.nonmotion_fence,
        motion_fence_path=a.motion_fence,
        post_death_loot_move_dev=source_qualified_natural_move,
        d7_native_controls_path=a.d7_passive_controls,
        d7f_natural_eat_dev=after_real_natural_pickup_eat,
        post_respawn_dev=continue_second_natural_food_cycle,
        d8_two_generation_food_dev=True,
    )))


if __name__ == "__main__":
    main()
