"""DEV D6-D3: zero natural drop is an experience, not a stop condition.

One real disposable World, original S49 ActionSupervisor, and fresh Intent
epochs when World-owned zombie generation changes. This driver bounds a CI
qualification SAMPLE to four generations; no product/self Goal policy or
World physics is capped, altered or granted extra authority here.

An actual positive natural drop authorizes a SOURCE candidate only. S49
physical MOVE is separately granted and fenced; post-MOVE EAT stays blocked.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import time
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
    _target, qualified_native_precombat_hunger, run,
)
from tools.bug0_d7f_natural_eat import after_real_natural_pickup_eat
from tools.bug0_d6_natural_move_world import source_qualified_natural_move
from tools.bug0_zombie_respawn_r1_world import _native_probe


class MultiGenerationDevRejected(RuntimeError):
    """No valid genuine next-generation source, original Action or World event."""


def one_source_line(text: str, marker: str, *, token: str = "") -> str | None:
    hits = [
        line for line in text.splitlines()
        if marker in line and (not token or token in line)
    ]
    if len(hits) > 1:
        raise MultiGenerationDevRejected(
            "ambiguous original Paper marker " + marker + " " + token
        )
    return hits[0] if hits else None


async def wait_paper(
    log_path: Path, marker: str, *, token: str = "", seconds: float = 12,
) -> str:
    started = time.monotonic()
    while time.monotonic() - started < seconds:
        if log_path.is_file():
            raw = log_path.read_text(encoding="utf8")
            if "RSELF_RESPAWN_FAULT" in raw or "RSELF_NATURAL_DROP_FAULT" in raw:
                raise MultiGenerationDevRejected("original Paper source fault")
            line = one_source_line(raw, marker, token=token)
            if line is not None:
                return line
        await asyncio.sleep(0.2)
    raise MultiGenerationDevRejected(
        "missing genuine Paper marker " + marker + " " + token
    )


def _tick(line: str) -> int:
    try:
        return int(line.split(" tick=")[1].split()[0])
    except (ValueError, IndexError) as exc:
        raise MultiGenerationDevRejected("original Paper tick absent") from exc


def _rotten(line: str) -> int:
    try:
        count = int(line.split(" rotten_count=")[1].split()[0])
    except (ValueError, IndexError) as exc:
        raise MultiGenerationDevRejected("natural Paper count absent") from exc
    if not 0 <= count <= 2:
        raise MultiGenerationDevRejected("vanilla zombie rotten count out of range")
    return count


def _uuid(line: str, key: str) -> str:
    try:
        word = line.split(f" {key}=")[1].split()[0]
    except IndexError as exc:
        raise MultiGenerationDevRejected("Paper UUID field absent: " + key) from exc
    if len(word) != 36:
        raise MultiGenerationDevRejected("unqualified Paper UUID field: " + key)
    return word


def _meat(read) -> int:
    return sum(item.count for item in read.snapshot.inventory
               if item.name == "rotten_flesh")


async def continue_after_first_respawn(
    session, server, owner: NormalSessionActionExecutor, report: dict,
    log_path: Path, *, physical_fence: OriginalS49NonMotionFence,
    motion_fence: OriginalS49PhysicalFence, baseline,
    d10_until_drop_dev: bool = False,
    d11_hunt_then_eat_dev: bool = False,
    s50_sidecar: Path | None = None,
) -> None:
    """DEV budget only. Every zero drop completes an Intent and waits World."""
    sid = owner.session_id
    preserved_supervisor = owner.supervisor
    previous_id = report["native_initial"]["zombie_entity_id"]
    next_info = report["native_respawn"]
    first_death = report["paper_respawn_death"]
    first_rotten = report["real_rotten_flesh_count"]
    first_uuid = _uuid(report["initial_paper"], "entity")
    old_ids = set(owner._dispatched)
    if (
        baseline.session_id != sid
        or not isinstance(physical_fence, OriginalS49NonMotionFence)
        or not isinstance(motion_fence, OriginalS49PhysicalFence)
        or report.get("real_world_started") is not True
        or owner.supervisor.open_actions
        or not owner._dispatched
        or len(physical_fence.actions) != owner._attack_count + (
            int(bool(report.get("self_eat"))) if d11_hunt_then_eat_dev else 0
        )
        or len(motion_fence.actions) != len(
            report.get("d6_original_s49_move_actions", ())
        )
        or _meat(baseline) != 0
        or not (0 <= first_rotten <= 2)
    ):
        raise MultiGenerationDevRejected("first original physical epoch source invalid")
    generations = [{
        "generation": 1,
        "paper_zombie_uuid": first_uuid,
        "native_zombie_id": previous_id,
        "intent_id": "escape-threat",
        "action_ids": [x["action_id"] for x in report["s49_actions"]],
        "death_tick": _tick(first_death),
        "real_rotten_count": first_rotten,
        "native_inventory_after": (
            first_rotten if report.get("d4_self_move_for_item") else 0
        ),
        "original_move_action_ids": [
            x["action_id"] for x in report.get("d6_original_s49_move_actions", ())
        ],
        "item_uuid": (
            _uuid(report["d4_paper_item_spawn"], "item")
            if first_rotten > 0 else None
        ),
        "item_spawn_tick": (
            _tick(report["d4_paper_item_spawn"])
            if first_rotten > 0 else None
        ),
        "item_pickup_tick": (
            _tick(report["d4_paper_item_pickup"])
            if first_rotten > 0 else None
        ),
        "respawn_tick": _tick(report["paper_respawn"]),
    }]
    report["d6_multigen_generations"] = generations
    generation_limit = 12 if d10_until_drop_dev else 4
    if d11_hunt_then_eat_dev and (
        not d10_until_drop_dev
        or report.get("d11_hunt_then_eat_dev") is not True
        or os.environ.get("D11_HUNT_THEN_S51_EAT_WORLD_ONLY") != "1"
        or not isinstance(s50_sidecar, Path)
        or not s50_sidecar.is_file()
        or s50_sidecar.is_symlink()
        or s50_sidecar.parent.resolve() != log_path.parent.resolve()
    ):
        raise MultiGenerationDevRejected("D11 original S50 natural EAT source absent")
    if d10_until_drop_dev and (
        os.environ.get("D10_HUNT_UNTIL_DROP_WORLD_ONLY") != "1"
        or getattr(owner, "_max_intent_epochs", None) != generation_limit
        or report.get("d10_until_drop_dev") is not True
        or report.get("d6_operator_forced_zero") is True
    ):
        raise MultiGenerationDevRejected("extended natural hunt DEV authority absent")
    report["d6_multigen_dev_world_trial_limit"] = generation_limit
    report["d10_hunt_trial_safety_limit_not_self_goal"] = (
        generation_limit if d10_until_drop_dev else None
    )
    report["d6_multigen_self_policy_epoch_limit_imposed"] = False
    report["d6_multigen_owner_session_id"] = sid
    operator_forced_zero = report.get("d6_operator_forced_zero") is True
    report["d6_multigen_source_natural_drop_rng_unchanged"] = (
        not operator_forced_zero
    )
    report["d6_multigen_operator_forced_zero"] = operator_forced_zero
    report["d6_multigen_no_physical_reissue"] = True
    report["d6_multigen_eat_after_move"] = False
    if d11_hunt_then_eat_dev:
        report["d11_source_eat_proven"] = False
    if (
        first_rotten > 0 and report.get("d4_self_move_for_item")
        and report.get("d4_native_after_pickup", {}).get("rotten_flesh") == first_rotten
    ):
        report["d6_multigen_classification"] = (
            "D6_MULTIGEN_FIRST_REAL_NATURAL_MOVE_PICKUP_EAT_FENCED_PASS"
        )
        report["d6_multigen_final_original_s49_action_count"] = owner._count
        report["d6_multigen_final_original_attack_count"] = owner._attack_count
        report["d6_multigen_final_original_move_count"] = owner._count - owner._attack_count
        report["d6_multigen_same_supervisor"] = owner.supervisor is preserved_supervisor
        report["d6_multigen_no_eat"] = not d11_hunt_then_eat_dev
        if d11_hunt_then_eat_dev:
            if (
                report.get("d7f_eat_terminal") != "outcome"
                or report.get("self_eat") is not True
                or report.get("d7f_original_eat_issued") is not True
                or len(physical_fence.actions) != owner._attack_count + 1
                or len(motion_fence.actions) != owner._count - owner._attack_count - 1
            ):
                raise MultiGenerationDevRejected("D11 first genuine drop EAT invalid")
            report["d6_multigen_eat_after_move"] = True
            report["d11_source_eat_proven"] = True
            report["d11_first_real_eat_generation"] = 1
            report["d11_eat_action_id"] = report["d7f_eat_action_id"]
            report["d11_eat_outcome"] = report["d7f_eat_outcome"]
        if d10_until_drop_dev:
            report["d10_first_natural_positive_generation"] = 1
            report["d10_hunt_stop_reason"] = "TRUE_NATURAL_DROP_AND_PICKUP"
            report["d10_hunt_goal_reached"] = True
            report["d10_natural_counts"] = [first_rotten]
            report["d10_original_kills"] = 1
            report["d10_all_prior_true_zero"] = True
        return
    if first_rotten != 0:
        raise MultiGenerationDevRejected("first positive natural drop was not picked")
    if operator_forced_zero and (
        report.get("d6_controlled_zero_set_before_first_attack") is not True
        or report.get("d6_controlled_zero_world_rule") != "doMobLoot=false"
    ):
        raise MultiGenerationDevRejected("controlled-zero fixture not source-qualified")

    for gen in range(2, generation_limit + 1):
        if owner._post_move_settling_unqualified:
            raise MultiGenerationDevRejected("physical MOVE without STOP cannot rearm")
        report["stage"] = f"D6_MULTIGEN_{gen}_FRESH_WORLD_RESPAWN"
        spawn = await wait_paper(
            log_path, "RSELF_RESPAWN_SPAWN world=",
            token=f"generation={gen} ",
            seconds=5,
        )
        previous_death_tick = generations[-1]["death_tick"]
        if (
            _tick(spawn) - previous_death_tick != 600
            or _tick(spawn) != generations[-1]["respawn_tick"]
        ):
            raise MultiGenerationDevRejected("next Paper generation not 600 ticks")
        if next_info["session_id"] != sid or next_info["zombie_entity_id"] == previous_id:
            raise MultiGenerationDevRejected("new native zombie identity not distinct")
        report["stage"] = f"D6_MULTIGEN_{gen}_ORIGINAL_INTENT_REARM"
        fresh = await _correlated_observe(
            session, f"d6-multigen-{gen}-rearm-source",
        )
        coverage = fresh.snapshot.nearby_entities_coverage
        ids = [e.entity_id for e in fresh.snapshot.nearby_entities
               if e.name == "zombie"]
        if (
            fresh.session_id != sid or fresh.seq <= next_info["seq"]
            or fresh.snapshot.health <= 0 or fresh.snapshot.oxygen_level == 0
            or coverage.truncated
            or coverage.candidate_count != len(fresh.snapshot.nearby_entities)
            or ids != [next_info["zombie_entity_id"]]
            or owner.supervisor.open_actions
            or any(owner.supervisor.get(a).state is not ActionState.OUTCOME
                   for a in owner._dispatched)
        ):
            raise MultiGenerationDevRejected("fresh genuine next zombie before Intent absent")
        current_old = owner.intent.current_intent
        if current_old is None:
            raise MultiGenerationDevRejected("current original Intent absent")
        current_count = owner._count
        owner.intent.complete(
            current_old.intent_id,
            reason=f"generation {gen-1} real zombie killed; natural drop 0; experience closed",
            at_ns=owner.intent.last_at_ns + 1,
            provenance=Provenance("d6-multigen-original-owner", f"end-{gen-1}"),
        )
        new_intent = owner.intent.commit(
            f"d6-multigen-zombie-{gen}",
            objective="defend and obtain food if true natural drop exists",
            at_ns=owner.intent.last_at_ns + 1,
            provenance=Provenance("d6-multigen-original-owner", f"begin-{gen}"),
        )
        rearm = owner.advance_intent_epoch(
            fresh, previous_zombie_entity_id=previous_id,
        )
        if (
            rearm.next_epoch != gen or rearm.completed_action_count != current_count
            or rearm.next_intent_id != new_intent.intent_id
            or rearm.physically_issued
            or owner.supervisor is not preserved_supervisor
            or set(owner._dispatched) != old_ids
        ):
            raise MultiGenerationDevRejected("Intent rearm changed original S49 history")
        report.setdefault("d6_multigen_rearms", []).append({
            "generation": gen,
            "previous_zombie_native_id": previous_id,
            "next_zombie_native_id": next_info["zombie_entity_id"],
            "previous_intent_id": rearm.completed_intent_id,
            "next_intent_id": rearm.next_intent_id,
            "read_seq": fresh.seq,
            "source": fresh.provenance.reference,
            "physical_issued": False,
            "same_supervisor": True,
        })

        # DEV-only positioning of the genuine NEW Paper zombie (not item).
        # Its genuine death is still exclusively from original S49 ATTACK.
        report["stage"] = f"D6_MULTIGEN_{gen}_OPERATOR_ZOMBIE_MELEE_STAGING"
        if operator_forced_zero:
            # Clear residual XP/orbs from the previous generation. This is an
            # operator DEV intervention and is explicitly preserved in report.
            cleanup_command = "kill @e[type=!minecraft:player,type=!minecraft:zombie]"
            _command(server, cleanup_command)
            await server.stdin.drain()
            await asyncio.sleep(0.3)
            report.setdefault("d6_multigen_operator_cleanup", []).append({
                "generation": gen, "command": cleanup_command,
                "operator_intervention": True,
            })
        commands = (
            "data merge entity @e[type=minecraft:zombie,limit=1] "
            "{NoAI:1b,Silent:1b,Health:0.8f}",
            "execute as RelaySelf at @s run tp "
            "@e[type=minecraft:zombie,limit=1] ^ ^ ^-2.2",
        ) if d10_until_drop_dev else (
            "execute as RelaySelf at @s run tp "
            "@e[type=minecraft:zombie,limit=1] ^ ^ ^-2.2",
            "data merge entity @e[type=minecraft:zombie,limit=1] "
            "{NoAI:1b,Silent:1b,Health:0.8f}",
        )
        for cmd in commands:
            _command(server, cmd)
        await server.stdin.drain()
        report.setdefault("d6_multigen_operator_staging", []).append({
            "generation": gen, "commands": list(commands),
            "staged_item": False,
            "unchanged_world_natural_loot": True,
        })
        await asyncio.sleep(0.85)
        if d11_hunt_then_eat_dev:
            # DEV World hunger is an environmental condition, never a
            # direct write to Food/Inventory. S49 still decides EAT later.
            _command(server, "effect give RelaySelf minecraft:hunger 70 20 true")
            await server.stdin.drain()
            qualified_hunger = False
            for attempt in range(80):
                body = await _correlated_observe(
                    session, f"d11-gen{gen}-precombat-hunger-{attempt:02d}",
                )
                if qualified_native_precombat_hunger(body, sid):
                    qualified_hunger = True
                    break
                await asyncio.sleep(0.55)
            if not qualified_hunger:
                raise MultiGenerationDevRejected("D11 real precombat Hunger not eligible")
            report.setdefault("d11_precombat_qualified_generations", []).append(gen)
        prev = await _correlated_observe(
            session, f"d6-multigen-{gen}-attack-prev",
        )
        await asyncio.sleep(0.25)
        curr = await _correlated_observe(
            session, f"d6-multigen-{gen}-attack-current",
        )
        target = next_info["zombie_entity_id"]
        _target(prev, target)
        _target(curr, target)
        decision = S49BasicPriorityL0(sid, max_decisions=3).decide(curr)
        if (
            decision.selected != "DEFER" or decision.preferred != "MOVE_AWAY"
            or decision.fallback != "ATTACK"
        ):
            raise MultiGenerationDevRejected("unchanged original L0 refused combat fallback")
        action_id = f"d6-multigen-gen-{gen}-attack-1-{sid}"
        fields = dict(
            intent_id=new_intent.intent_id, session_id=sid, action_id=action_id,
            probe_seq=curr.seq, probe_request_id=curr.request_id,
            target_entity_id=target, granted=True,
        )
        propose = NormalAttackingAuthorization(
            stage=NormalActionStage.PROPOSE,
            authority_id=f"operator-d6-multigen-{gen}-propose",
            provenance=Provenance("d6-multigen-real-dev-grant", f"propose-{gen}"),
            **fields,
        )
        issue = NormalAttackingAuthorization(
            stage=NormalActionStage.ISSUE,
            authority_id=f"operator-d6-multigen-{gen}-issue",
            provenance=Provenance("d6-multigen-real-dev-grant", f"issue-{gen}"),
            **fields,
        )
        owner.require_attack_authorizations(prev, curr, target, propose, issue)
        report["stage"] = f"D6_MULTIGEN_{gen}_ORIGINAL_S49_ATTACK"
        receipt = await owner.execute_attack(
            session, prev, curr, target, propose, issue,
            allow_target_disappearance=True, physical_fence=physical_fence,
        )
        if (
            receipt.terminal.state is not ActionState.OUTCOME
            or receipt.effect.result != "applied"
            or receipt.target_entity_id != target
            or receipt.after_probe.seq <= receipt.effect.seq
            or owner.supervisor is not preserved_supervisor
            or owner._count != current_count + 1
            or owner.supervisor.open_actions
        ):
            raise MultiGenerationDevRejected("new original S49 physical ATTACK unqualified")
        old_ids.add(action_id)
        if owner._dispatched != old_ids:
            raise MultiGenerationDevRejected("original S49 Action identity lost")
        report["stage"] = f"D6_MULTIGEN_{gen}_REAL_WORLD_DEATH"
        death = await wait_paper(
            log_path, "RSELF_RESPAWN_DEATH world=",
            token=f"generation={gen} ", seconds=12,
        )
        paper_uuid = _uuid(spawn, "entity")
        if _uuid(death, "entity") != paper_uuid:
            raise MultiGenerationDevRejected("Paper respawn/death zombie UUID mismatch")
        natural = await wait_paper(
            log_path, "RSELF_NATURAL_DROP_DEATH world=",
            token=f"zombie={paper_uuid} ", seconds=5,
        )
        if (
            "killer_is_relay_self=true" not in natural
            or _uuid(death, "killer") != _uuid(natural, "killer")
            or _tick(death) != _tick(natural)
        ):
            raise MultiGenerationDevRejected("genuine later kill principal unconfirmed")
        amount = _rotten(natural)
        if operator_forced_zero and amount != 0:
            raise MultiGenerationDevRejected(
                "operator-forced zero World yielded an unexpected item"
            )
        generation = {
            "generation": gen,
            "paper_zombie_uuid": paper_uuid,
            "native_zombie_id": target,
            "intent_id": new_intent.intent_id,
            "action_ids": [action_id],
            "attack_source_seq": curr.seq,
            "attack_effect_seq": receipt.effect.seq,
            "attack_after_seq": receipt.after_probe.seq,
            "death_tick": _tick(death),
            "real_rotten_count": amount,
            "native_inventory_after": 0,
            "original_move_action_ids": [],
            "respawn_tick": None,
        }
        generations.append(generation)
        report["d6_multigen_all_original_s49_action_ids"] = sorted(owner._dispatched)
        report["d6_multigen_generation_count"] = len(generations)

        if amount > 0:
            report["stage"] = f"D6_MULTIGEN_{gen}_NATURAL_MOVE_PICKUP"
            spawn_item = await wait_paper(
                log_path, "RSELF_NATURAL_DROP_SPAWN world=",
                token=f"zombie={paper_uuid} ", seconds=5,
            )
            if _rotten(spawn_item) != amount:
                raise MultiGenerationDevRejected("natural paper item amount mismatch")
            report["d6_multigen_active_natural_count"] = amount
            report["d6_multigen_paper_positive_item_uuid"] = _uuid(spawn_item, "item")
            report["d6_multigen_paper_positive_generation"] = gen
            if one_source_line(
                log_path.read_text(encoding="utf8"),
                "RSELF_NATURAL_DROP_PICKUP world=",
                token=f"zombie={paper_uuid} ",
            ):
                raise MultiGenerationDevRejected("positive natural item passively picked")
            original_move = await source_qualified_natural_move(
                session, owner, report, log_path, motion_fence=motion_fence,
                d7f_live_eat_dev=d11_hunt_then_eat_dev,
            )
            pickup = await wait_paper(
                log_path, "RSELF_NATURAL_DROP_PICKUP world=",
                token=f"zombie={paper_uuid} ", seconds=10,
            )
            if (
                _uuid(pickup, "item") != _uuid(spawn_item, "item")
                or _rotten(pickup) != amount
                or _tick(pickup) <= _tick(spawn_item)
            ):
                raise MultiGenerationDevRejected("Paper natural item UUID pickup mismatch")
            after = await _correlated_observe(
                session, f"d6-multigen-{gen}-native-inventory-after-move",
            )
            if (
                after.session_id != sid or after.seq <= receipt.after_probe.seq
                or _meat(after) != amount
                or owner.supervisor.open_actions
                or not owner._post_move_settling_unqualified
            ):
                raise MultiGenerationDevRejected("authentic native inventory gain absent")
            generation["native_inventory_after"] = _meat(after)
            generation["original_move_action_ids"] = [
                row["action_id"]
                for row in report["d6_original_s49_move_actions"]
            ]
            generation["item_uuid"] = _uuid(spawn_item, "item")
            generation["item_spawn_tick"] = _tick(spawn_item)
            generation["item_pickup_tick"] = _tick(pickup)
            report["d6_multigen_classification"] = (
                "D6_MULTIGEN_ZERO_DROP_CONTINUE_THEN_REAL_MOVE_PICKUP_PASS"
            )
            report["d6_multigen_postmove_eat_issued"] = False
            if d11_hunt_then_eat_dev:
                eat_source = {
                    "self_attack_principal_attested": True,
                    "real_rotten_flesh_count": amount,
                    "d4_natural_count": amount,
                    "d4_precombat_hunger_qualified": qualified_hunger,
                    "d7f_operator_hunger_effect_dev": True,
                    "d6_item_origin": report.get("d6_item_origin"),
                    "d6_d_same_attack_move_supervisor": report.get(
                        "d6_d_same_attack_move_supervisor"
                    ),
                    "d6_original_s49_move_actions": report[
                        "d6_original_s49_move_actions"
                    ],
                    "d4_paper_item_spawn": spawn_item,
                    "d4_paper_item_pickup": pickup,
                    "paper_loot_death": natural,
                }
                eaten = await after_real_natural_pickup_eat(
                    session, server, owner, eat_source, log_path,
                    original_move=original_move, native_pickup=after,
                    nonmotion_fence=physical_fence, s50_sidecar=s50_sidecar,
                    d11_hunt_generation=gen,
                )
                if (
                    eaten is not True
                    or eat_source.get("d7f_eat_terminal") != "outcome"
                    or eat_source.get("d7f_original_eat_issued") is not True
                    or owner.supervisor.open_actions
                    or len(physical_fence.actions) != owner._attack_count + 1
                    or len(motion_fence.actions)
                        != owner._count - owner._attack_count - 1
                ):
                    raise MultiGenerationDevRejected("D11 real original S51 EAT not closed")
                report["self_eat"] = True
                report["d6_multigen_eat_after_move"] = True
                report["d6_multigen_postmove_eat_issued"] = True
                report["d11_source_eat_proven"] = True
                report["d11_first_real_eat_generation"] = gen
                report["d11_eat_action_id"] = eat_source["d7f_eat_action_id"]
                report["d11_eat_outcome"] = eat_source["d7f_eat_outcome"]
                report["d11_native_after_eat"] = eat_source["d7f_native_after_eat"]
                report["d11_live_natural_stop"] = eat_source[
                    "d7f_live_natural_stop"
                ]
            if d10_until_drop_dev:
                report["d10_first_natural_positive_generation"] = gen
                report["d10_hunt_stop_reason"] = "TRUE_NATURAL_DROP_AND_PICKUP"
                report["d10_hunt_goal_reached"] = True
            break

        # No item: that Intent is an experience outcome, not a loop terminal.
        # Only Paper's actual next generation and fresh native entity can
        # rearm, never a guessed timer or synthetic Action.
        no_item = await _correlated_observe(
            session, f"d6-multigen-{gen}-no-food-inventory",
        )
        if no_item.session_id != sid or _meat(no_item) != 0:
            raise MultiGenerationDevRejected("zero natural drop contradicted native inventory")
        if gen == generation_limit:
            report["d6_multigen_classification"] = (
                "D10_SAFETY_BUDGET_EXHAUSTED_NO_DROP"
                if d10_until_drop_dev else (
                    "D6_MULTIGEN_FOUR_OPERATOR_FORCED_ZERO_KILLS_PASS"
                    if operator_forced_zero
                    else "D6_MULTIGEN_BOUNDED_FOUR_TRUE_ZERO_DROPS_PASS"
                )
            )
            report["d6_multigen_ci_limit_reached_not_self_goal_completed"] = True
            if d10_until_drop_dev:
                report["d10_hunt_stop_reason"] = "DEV_WORLD_GENERATION_SAFETY_LIMIT"
                report["d10_hunt_goal_reached"] = False
            break
        report["stage"] = f"D6_MULTIGEN_{gen}_WORLD_600TICK_RESPAWN"
        later = await wait_paper(
            log_path, "RSELF_RESPAWN_SPAWN world=",
            token=f"generation={gen+1} ", seconds=88,
        )
        if _tick(later) - _tick(death) != 600:
            raise MultiGenerationDevRejected("next respawn was not World600tick")
        generation["respawn_tick"] = _tick(later)
        next_info = await _native_probe(
            session, f"d6-multigen-new-world-generation-{gen+1}",
        )
        previous_id = target
    if (
        owner.supervisor is not preserved_supervisor
        or owner.supervisor.open_actions
        or any(owner.supervisor.get(a).state is not ActionState.OUTCOME
               for a in owner._dispatched)
        or len(physical_fence.actions) != owner._attack_count + int(
            d11_hunt_then_eat_dev and report.get("self_eat") is True
        )
        or len(motion_fence.actions) != (
            owner._count - owner._attack_count - int(
                d11_hunt_then_eat_dev and report.get("self_eat") is True
            )
        )
        or physical_fence.unresolved or motion_fence.unresolved
        or report.get("d6_multigen_classification") is None
    ):
        raise MultiGenerationDevRejected("original same-owner loop terminal unqualified")
    report["d6_multigen_final_original_s49_action_count"] = owner._count
    report["d6_multigen_final_original_attack_count"] = owner._attack_count
    report["d6_multigen_final_original_move_count"] = (
        owner._count - owner._attack_count - int(
            d11_hunt_then_eat_dev and report.get("self_eat") is True
        )
    )
    report["d6_multigen_same_supervisor"] = True
    report["d6_multigen_no_eat"] = not (
        d11_hunt_then_eat_dev and report.get("self_eat") is True
    )
    if d10_until_drop_dev:
        report["d10_natural_counts"] = [
            row["real_rotten_count"] for row in generations
        ]
        report["d10_original_kills"] = len(generations)
        report["d10_all_prior_true_zero"] = all(
            row["real_rotten_count"] == 0 for row in generations[:-1]
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--nonmotion-fence", type=Path, required=True)
    parser.add_argument("--motion-fence", type=Path, required=True)
    parser.add_argument("--d7-passive-controls", type=Path)
    args = parser.parse_args()
    if os.environ.get("D6_NATURAL_MULTIGEN_WORLD_ONLY") != "1":
        raise SystemExit("D6 multigen real World gate missing")
    raise SystemExit(asyncio.run(run(
        args.report, args.server_log,
        nonmotion_fence_path=args.nonmotion_fence,
        motion_fence_path=args.motion_fence,
        post_death_loot_move_dev=source_qualified_natural_move,
        post_respawn_dev=continue_after_first_respawn,
        d6_multigen_dev=True,
        d6_controlled_zero_dev=(
            os.environ.get("D6_CONTROLLED_ZERO_WORLD_ONLY") == "1"
        ),
        d7_native_controls_path=args.d7_passive_controls,
    )))


if __name__ == "__main__":
    main()
