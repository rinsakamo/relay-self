"""Independent post: 2 true Paper World zombie generations and original S49 food.

This is source verification after World shutdown, not an issuer and not a
learning/S14/QUAL/SCIENCE claim. No synthesis of missing second food outcome.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from adapters.mineflayer.d7_live_staged_stop import (
    CONTROL_KEYS,
    NATURAL_DEATH,
    NATURAL_PICKUP,
    NATURAL_SPAWN,
)
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d6_multigen_world import _tick, _uuid
from tools.bug0_d7_paper_server_tick_post import (
    SOURCE,
    TICK_MARK,
    _fields,
    _inputs_off,
    _integer,
    _number,
)
from tools.bug0_d7e_staged_move_eat_post import native_integral_food

NATURAL_DEATH_INCLUDING_ZERO = re.compile(
    NATURAL_DEATH.pattern.replace("(?P<count>[12])", "(?P<count>[012])")
)


class D8TwoCycleAuditRejected(ValueError):
    """Two actual S49/S51 natural food histories not independently proven."""


def _source(log: str, pattern) -> list[dict[str, str]]:
    return [
        match.groupdict()
        for line in log.splitlines()
        if (match := pattern.search(line))
    ]


def audit_first_true_zero_food(
    report: dict, paper_log: str, *,
    nonmotion_path: Path, motion_path: Path,
) -> dict:
    """Truthful first-generation zero: never issue second Action or claim food."""
    sid = report.get("session_id")
    attacks = report.get("s49_actions")
    zero = _source(paper_log, NATURAL_DEATH_INCLUDING_ZERO)
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification")
            != "D8_FIRST_TRUE_ZERO_DROP_TWO_FOOD_CYCLES_NOT_EXERCISED"
        or report.get("d8_two_generation_optin") is not True
        or report.get("d8_first_true_zero_food_not_exercised") is not True
        or report.get("d8_second_generation_food_proven") is not False
        or report.get("self_eat") is not False
        or report.get("d4_self_eat_issued") is not False
        or report.get("d4_eat_terminal") != "NOT_ISSUED"
        or report.get("d4_natural_food_pickup_eat_proven") is not False
        or report.get("real_rotten_flesh_count") != 0
        or report.get("d4_native_after_zero", {}).get("rotten_flesh") != 0
        or report.get("d4_precombat_hunger_qualified") is not True
        or report.get("original_action_issuer") != "S49"
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or report.get("real_world_started") is not True
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
        or "d7f_managed_world_witness=true" not in paper_log
        or "RSELF_LOOT_STAGED " in paper_log
        or "RSELF_NATURAL_DROP_FAULT" in paper_log
        or "RSELF_RESPAWN_FAULT" in paper_log
        or len(zero) != 1 or zero[0]["count"] != "0"
        or not isinstance(sid, str) or not sid
        or not isinstance(attacks, list) or len(attacks) != 1
        or report.get("attack_count") != 1
        or report.get("d4_final_action_count") != 1
        or report.get("d4_final_supervisor_open_count") != 0
        or report.get("d8_intent_rearm") is not None
        or report.get("d8_second_generation") is not None
        or any(("RSELF_NATURAL_DROP_SPAWN " in paper_log,
                "RSELF_NATURAL_DROP_PICKUP " in paper_log))
    ):
        raise D8TwoCycleAuditRejected(
            "first true zero World/owner/native food evidence invalid"
        )
    first = report["initial_paper"]
    death = report["paper_respawn_death"]
    reappear = report["paper_respawn"]
    if (
        first not in paper_log or death not in paper_log
        or reappear not in paper_log
        or report["paper_loot_death"] not in paper_log
        or zero[0]["world"] != _uuid(first, "world")
        or zero[0]["zombie"] != _uuid(first, "entity")
        or zero[0]["killer"] != _uuid(death, "killer")
        or _tick(death) != int(zero[0]["tick"])
        or _tick(reappear) - _tick(death) != 600
        or _uuid(reappear, "world") != _uuid(first, "world")
        or _uuid(reappear, "entity") == _uuid(first, "entity")
    ):
        raise D8TwoCycleAuditRejected(
            "first zero is not a real Paper managed Self-killed zombie"
        )
    nonmotion = OriginalS49NonMotionFence.restore(
        nonmotion_path, self_id="s49-original-self",
    )
    motion = OriginalS49PhysicalFence.restore(
        motion_path, self_id="s49-original-self",
    )
    nonmotion.require_clear()
    motion.require_clear()
    row = nonmotion.actions[0] if len(nonmotion.actions) == 1 else None
    if (
        motion.actions
        or row is None
        or row.get("kind") != "ATTACK"
        or row.get("status") != "S16_OUTCOME"
        or row.get("terminal") != "outcome"
        or row.get("session_id") != sid
        or row.get("action_id") != attacks[0].get("action_id")
        or attacks[0].get("ack") != "applied"
        or attacks[0].get("terminal") != "outcome"
        or report.get("nonmotion_fence", {}).get("sha256") != nonmotion.sha256
        or report.get("motion_fence", {}).get("sha256") != motion.sha256
    ):
        raise D8TwoCycleAuditRejected("first zero original S49 durable ATTACK invalid")
    return {
        "status": "NOT_EXERCISED",
        "classification": "D8_FIRST_TRUE_ZERO_NATURAL_DROP_NO_FOOD_CYCLE",
        "World_first_vanilla_rotten_count": 0,
        "first_attack_s49_terminal": "outcome",
        "second_generation_world_respawn_600ticks": True,
        "first_food_issued": False,
        "second_food_issued": False,
        "two_real_natural_food_cycles": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def audit_two_natural_food_cycles(
    report: dict, paper_log: str, *,
    nonmotion_path: Path, motion_path: Path,
    s50_jsonl: str = "",
) -> dict:
    if (
        isinstance(report, dict)
        and report.get("d8_first_true_zero_food_not_exercised") is True
    ):
        return audit_first_true_zero_food(
            report, paper_log,
            nonmotion_path=nonmotion_path, motion_path=motion_path,
        )
    if (
        not isinstance(report, dict) or not isinstance(paper_log, str)
        or report.get("status") != "PASS_DEV"
        or report.get("real_world_started") is not True
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or report.get("original_action_issuer") != "S49"
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
        or report.get("d8_two_generation_optin") is not True
        or report.get("d8_first_completed_intent") != "escape-threat"
        or report.get("self_eat") is not True
        or report.get("d4_natural_food_pickup_eat_proven") is not True
        or report.get("d7f_original_eat_issued") is not True
        or report.get("d7f_eat_terminal") != "outcome"
        or report.get("d8_operator_food_item_created") is not False
        or report.get("d8_operator_hunger_effect") is not True
        or report.get("d8_precombat_hunger_qualified") is not True
        or report.get("d8_intent_rearm", {}).get("same_supervisor") is not True
        or report["d8_intent_rearm"].get("no_physical_issue_for_rearm") is not True
        or report.get("d7f_operator_staged_item") is not False
        or "RSELF_LOOT_STAGED " in paper_log
        or "RSELF_NATURAL_DROP_FAULT" in paper_log
        or "RSELF_RESPAWN_FAULT" in paper_log
        or "d7f_managed_world_witness=true" not in paper_log
    ):
        raise D8TwoCycleAuditRejected("D8 real World, owner or fresh generation provenance missing")
    g2 = report.get("d8_second_generation")
    sid = report.get("session_id")
    if not isinstance(g2, dict) or not isinstance(sid, str) or not sid:
        raise D8TwoCycleAuditRejected("second original World generation missing")
    r1 = report.get("d7f_eat_outcome")
    r2 = g2.get("d7f_eat_outcome")
    first_count = report.get("real_rotten_flesh_count")
    second_count = g2.get("real_rotten_flesh_count")
    if (
        type(first_count) is not int or first_count not in (1, 2)
        or type(second_count) is not int or second_count not in (0, 1, 2)
        or not isinstance(r1, dict)
        or r1.get("session_id") != sid
        or r1.get("consumed_item") != "rotten_flesh"
        or r1.get("count_before") != first_count
        or r1.get("count_after") != first_count - 1
        or report.get("d8_prior_rotten_after_gen1_eat") != first_count - 1
        or g2.get("paper_world_uuid") != _uuid(report["initial_paper"], "world")
        or _uuid(report["paper_respawn"], "entity") == _uuid(report["initial_paper"], "entity")
        or _tick(report["paper_respawn"]) - _tick(report["paper_respawn_death"]) != 600
        or g2.get("paper_zombie_uuid") != _uuid(report["paper_respawn"], "entity")
    ):
        raise D8TwoCycleAuditRejected("genuine first food/next World identity inconsistent")
    first_before, first_after = (
        native_integral_food(r1.get("food_before")),
        native_integral_food(r1.get("food_after")),
    )
    if first_after <= first_before:
        raise D8TwoCycleAuditRejected("first real S51 Food did not increase")

    deaths = _source(paper_log, NATURAL_DEATH_INCLUDING_ZERO)
    spawns = _source(paper_log, NATURAL_SPAWN)
    pickups = _source(paper_log, NATURAL_PICKUP)
    if len(deaths) != 2 or len(deaths) != len(spawns) + (second_count == 0):
        raise D8TwoCycleAuditRejected("Paper two exact natural death/ItemSpawn count mismatch")
    if len(pickups) != len(spawns):
        raise D8TwoCycleAuditRejected("Paper actual item UUID pickup not proven")
    expected_world = deaths[0]["world"]
    if (
        deaths[0]["world"] != deaths[1]["world"]
        or deaths[0]["zombie"] == deaths[1]["zombie"]
        or deaths[0]["killer"] != deaths[1]["killer"]
        or deaths[0]["world"] != _uuid(report["initial_paper"], "world")
        or deaths[0]["zombie"] != _uuid(report["initial_paper"], "entity")
        or deaths[1]["zombie"] != g2["paper_zombie_uuid"]
        or deaths[0]["count"] != str(first_count)
        or deaths[1]["count"] != str(second_count)
        or int(deaths[1]["tick"]) < _tick(report["paper_respawn"])
        or int(deaths[0]["tick"]) != _tick(report["paper_respawn_death"])
        or int(deaths[1]["tick"]) != g2["death_tick"]
        or g2["paper_natural_death"] not in paper_log
        or report.get("paper_loot_death", "") not in paper_log
    ):
        raise D8TwoCycleAuditRejected("two true distinct managed zombie killers invalid")
    for i, (spawn, pickup) in enumerate(zip(spawns, pickups)):
        death = deaths[i]
        if (
            any(spawn[k] != death[k] for k in ("world", "zombie", "count"))
            or any(spawn[k] != pickup[k]
                   for k in ("world", "zombie", "item", "count"))
            or pickup["player"] != death["killer"]
            or not int(death["tick"]) <= int(spawn["tick"]) < int(pickup["tick"])
            or spawn["world"] != expected_world
        ):
            raise D8TwoCycleAuditRejected("natural generation drop and pickup UUID mismatch")
    if spawns and len(spawns) == 2 and spawns[0]["item"] == spawns[1]["item"]:
        raise D8TwoCycleAuditRejected("second-generation item identity reused")
    if (
        report.get("d4_paper_item_spawn", "") not in paper_log
        or report.get("d4_paper_item_pickup", "") not in paper_log
        or _uuid(report["d4_paper_item_spawn"], "item") != spawns[0]["item"]
        or _uuid(report["d4_paper_item_pickup"], "item") != pickups[0]["item"]
        or g2.get("paper_natural_death", "") not in paper_log
    ):
        raise D8TwoCycleAuditRejected("original first Paper food source missing")

    original_attacks = report.get("s49_actions")
    first_moves = report.get("d6_original_s49_move_actions")
    second_moves = g2.get("d6_original_s49_move_actions", [])
    if (
        not isinstance(original_attacks, list)
        or not 1 <= len(original_attacks) <= 8
        or not isinstance(first_moves, list)
        or not 1 <= len(first_moves) <= 4
        or not isinstance(second_moves, list)
        or g2.get("d8_second_generation_dev") is not True
        or g2.get("d7f_operator_hunger_effect_dev") is not True
        or g2.get("d4_precombat_hunger_qualified") is not True
        or report.get("d8_original_second_attack_action_id") is None
    ):
        raise D8TwoCycleAuditRejected("original attack and first MOVE owner history missing")
    nonmotion = OriginalS49NonMotionFence.restore(
        nonmotion_path, self_id="s49-original-self",
    )
    motion = OriginalS49PhysicalFence.restore(
        motion_path, self_id="s49-original-self",
    )
    nonmotion.require_clear()
    motion.require_clear()
    if len(nonmotion.actions) != (
        len(original_attacks) + 2 + int(second_count > 0)
    ):
        raise D8TwoCycleAuditRejected("two-generation original physical nonmotion ledger mismatch")
    if len(motion.actions) != len(first_moves) + len(second_moves):
        raise D8TwoCycleAuditRejected("two-generation original C1 MOVE ledger mismatch")

    all_original_ids = (
        [row["action_id"] for row in original_attacks]
        + [row["action_id"] for row in first_moves]
        + [r1["action_id"], report["d8_original_second_attack_action_id"]]
        + [row["action_id"] for row in second_moves]
        + ([r2["action_id"]] if isinstance(r2, dict) else [])
    )
    if len(set(all_original_ids)) != len(all_original_ids):
        raise D8TwoCycleAuditRejected("Action ID reused between generations")
    expected_nonmotion = [
        *[(row["action_id"], "ATTACK") for row in original_attacks],
        (r1["action_id"], "EAT"),
        (report["d8_original_second_attack_action_id"], "ATTACK"),
    ]
    if second_count > 0:
        expected_nonmotion.append((r2["action_id"], "EAT"))
    for row, (action_id, kind) in zip(nonmotion.actions, expected_nonmotion):
        if (
            row.get("session_id") != sid
            or row.get("action_id") != action_id
            or row.get("kind") != kind
            or row.get("status") != "S16_OUTCOME"
            or row.get("terminal") != "outcome"
        ):
            raise D8TwoCycleAuditRejected("original S49 ATTACK/EAT durable actions disagree")
    for row, source in zip(motion.actions, [*first_moves, *second_moves]):
        if (
            row.get("session_id") != sid
            or row.get("action_id") != source.get("action_id")
            or row.get("status") != "S16_OUTCOME"
            or row.get("action_ref") != "MOVE_BACKWARD"
            or row.get("cleanup_seq") != source.get("s15_clear_seq")
            or row.get("after_seq") != source.get("s15_after_seq")
            or source.get("terminal") != "outcome"
        ):
            raise D8TwoCycleAuditRejected("original S49 MOVE journal/clear mismatch")
    for row, outcome in (
        (nonmotion.actions[len(original_attacks)], r1),
        *(([(nonmotion.actions[-1], r2)] if second_count > 0 else [])),
    ):
        if (
            row.get("subject") != "rotten_flesh"
            or row.get("result") != {
                "food_before": native_integral_food(outcome["food_before"]),
                "food_after": native_integral_food(outcome["food_after"]),
                "item_count_before": outcome["count_before"],
                "item_count_after": outcome["count_after"],
            }
        ):
            raise D8TwoCycleAuditRejected("S51 native Food/inventory vs original durable ledger")
    if second_count == 0:
        if (
            report.get("d8_second_generation_food_proven") is not False
            or second_moves or r2 is not None
            or g2.get("original_eat_issued") is not False
        ):
            raise D8TwoCycleAuditRejected("true zero natural drop cannot claim second EAT")
        return {
            "status": "NOT_EXERCISED",
            "classification": "D8_TWO_GENERATION_SECOND_TRUE_ZERO_DROP_NO_EAT",
            "two_real_zombie_kills": True,
            "two_real_food_cycles": False,
            "second_natural_count": 0,
            "qualification": "NO_GO", "science": "NOT_RUN",
        }
    stop = g2.get("d7f_live_natural_stop")
    pickup_mode = g2.get("d8_natural_pickup_mode")
    passive_no_move = pickup_mode == "PASSIVE_NO_MOVE"
    if (
        pickup_mode not in ("PASSIVE_NO_MOVE", "ORIGINAL_S49_MOVE")
        or (
            passive_no_move
            and (
                second_moves != []
                or g2.get("d6_d_world_natural_loot_moved") is not False
            )
        )
        or (
            not passive_no_move
            and (
                not 1 <= len(second_moves) <= 4
                or g2.get("d6_d_world_natural_loot_moved") is not True
            )
        )
    ):
        raise D8TwoCycleAuditRejected("second generation MOVE provenance is forged")
    expected_stop_class = (
        "D8_DEV_LIVE_SECOND_NATURAL_PASSIVE_PICKUP_STEADY_SOURCE"
        if passive_no_move else "D8_DEV_LIVE_SECOND_NATURAL_BODY_STEADY_SOURCE"
    )
    anchor_action = (
        report["d8_original_second_attack_action_id"]
        if passive_no_move else second_moves[-1]["action_id"] + "-s15-clear"
    )
    anchor_seq = (
        report["d8_original_second_attack_effect_seq"]
        if passive_no_move else second_moves[-1]["s15_clear_seq"]
    )
    if (
        report.get("classification") != "D8_TWO_REAL_NATURAL_S49_FOOD_CYCLES_PASS"
        or report.get("d8_second_generation_food_proven") is not True
        or g2.get("d7f_original_eat_issued") is not True
        or g2.get("d7f_eat_terminal") != "outcome"
        or g2.get("d7f_stop_original_owner_admitted_dev") is not True
        or g2.get("d7f_server_effective_s15_clear_tick_attested") is not False
        or g2.get("d7f_natural_inventory_before") != first_count - 1 + second_count
        or g2.get("d7f_natural_inventory_after") != first_count - 2 + second_count
        or not isinstance(r2, dict) or not isinstance(stop, dict)
        or r2.get("session_id") != sid
        or r2.get("consumed_item") != "rotten_flesh"
        or r2.get("count_before") != first_count - 1 + second_count
        or r2.get("count_after") != first_count - 2 + second_count
        or g2.get("d7f_native_after_eat", {}).get("rotten_flesh")
            != first_count - 2 + second_count
        or report.get("d8_final_rotten_inventory") != first_count - 2 + second_count
        or report.get("d8_original_same_supervisor") is not True
        or report.get("d8_original_total_eats") != 2
        or report.get("d8_original_total_attacks") != len(original_attacks) + 1
        or report.get("d8_original_total_moves") != len(first_moves) + len(second_moves)
        or report.get("d8_original_total_actions") != len(all_original_ids)
        or stop.get("classification") != expected_stop_class
        or stop.get("session_id") != sid
        or stop.get("action_id") != (
            report["d8_original_second_attack_action_id"]
            if passive_no_move else second_moves[-1]["action_id"]
        )
        or stop.get("original_clear_seq") != (
            -1 if passive_no_move else second_moves[-1]["s15_clear_seq"]
        )
        or stop.get("original_attack_effect_seq") != (
            anchor_seq if passive_no_move else None
        )
        or stop.get("paper_world_uuid") != expected_world
        or stop.get("paper_item_uuid") != spawns[1]["item"]
        or stop.get("paper_pickup_tick") != int(pickups[1]["tick"])
        or stop.get("client_postclear_physics_ticks", 0) < 8
        or stop.get("paper_quiet_tail_ticks", 0) < 8
        or stop.get("server_effective_original_clear_tick") != (
            "NOT_APPLICABLE_NO_MOVE"
            if passive_no_move else "NOT_CAUSALLY_ATTESTED"
        )
        or g2.get("d7f_nonmotion_sha256") != nonmotion.sha256
    ):
        raise D8TwoCycleAuditRejected("second genuine original S51 Food/STOP not source-qualified")
    second_before = native_integral_food(r2.get("food_before"))
    second_after = native_integral_food(r2.get("food_after"))
    if second_after <= second_before:
        raise D8TwoCycleAuditRejected("second original S51 did not actually raise Food")

    # Read the immutable direct S50/Paper originals independently of the
    # current owner's stored STOP summary. The exact server-effective
    # original-clear tick remains unproven; no causal claim is inferred.
    if not isinstance(s50_jsonl, str) or not s50_jsonl:
        raise D8TwoCycleAuditRejected("immutable original S50 sidecar missing")
    records = []
    for line in s50_jsonl.splitlines():
        try:
            rec = json.loads(line)
        except (ValueError, TypeError) as exc:
            raise D8TwoCycleAuditRejected("native S50 original source malformed") from exc
        records.append(rec)
    if not records or records[0].get("kind") != "SESSION_START":
        raise D8TwoCycleAuditRejected("original native S50 session start missing")
    matched_clear = None
    verified_off_ticks = 0
    previous_client_tick = -1
    for ordinal, rec in enumerate(records, 1):
        if (
            not isinstance(rec, dict)
            or rec.get("source") != "S50_DEV_NATIVE_READBACK_V1"
            or rec.get("session_id") != sid
            or rec.get("ordinal") != ordinal
            or type(rec.get("client_physics_tick")) is not int
            or rec["client_physics_tick"] < previous_client_tick
        ):
            raise D8TwoCycleAuditRejected("S50 source session/ordinal drift")
        previous_client_tick = rec["client_physics_tick"]
        if (
            rec.get("kind") == "EFFECT_ACK"
            and rec.get("native_action_id")
                == anchor_action
            and rec.get("native_seq") == anchor_seq
        ):
            if matched_clear is not None:
                raise D8TwoCycleAuditRejected("duplicate second original S15 clear")
            matched_clear = ordinal
        if matched_clear is not None and ordinal >= matched_clear:
            if rec.get("kind") == "PHYSICS_TICK":
                controls = rec.get("controls")
                if (
                    not isinstance(controls, dict)
                    or set(controls) != set(CONTROL_KEYS)
                    or any(type(v) is not bool or v for v in controls.values())
                ):
                    raise D8TwoCycleAuditRejected("original S50 motor active after last clear")
                verified_off_ticks += 1
    if (
        matched_clear is None or verified_off_ticks < 8
        or verified_off_ticks < stop["client_postclear_physics_ticks"]
    ):
        raise D8TwoCycleAuditRejected("S50 independent last original MOVE clear not attested")
    ticks = [
        _fields(line, TICK_MARK)
        for line in paper_log.splitlines() if TICK_MARK in line
    ]
    if not ticks:
        raise D8TwoCycleAuditRejected("Paper tick source absent")
    old_tick = None
    old_xz = None
    quiet = 0
    current_stop = False
    for ordinal, row in enumerate(ticks, 1):
        t = _integer(row, "tick")
        if (
            row.get("source") != SOURCE
            or row.get("world") != expected_world
            or row.get("player") != deaths[1]["killer"]
            or _integer(row, "ordinal") != ordinal
            or (old_tick is not None and t != old_tick + 1)
        ):
            raise D8TwoCycleAuditRejected("Paper current-world tick source drift")
        old_tick = t
        pos = (_number(row, "x"), _number(row, "z"))
        quiet = quiet + 1 if (
            t > int(pickups[1]["tick"])
            and _inputs_off(row)
            and row.get("ground") == "true"
            and old_xz is not None
            and math.dist(pos, old_xz) <= 0.01
            and math.hypot(_number(row, "vx"), _number(row, "vz")) <= 0.01
        ) else 0
        old_xz = pos
        if t == stop.get("paper_last_tick"):
            current_stop = True
            if quiet < 8 or quiet != stop["paper_quiet_tail_ticks"]:
                raise D8TwoCycleAuditRejected("second Paper live STOP claim not true")
    if not current_stop:
        raise D8TwoCycleAuditRejected("second Paper live source tick not in actual log")
    return {
        "status": "PASS_DEV",
        "classification": "D8_TWO_GENUINE_PAPER_ZOMBIE_FOOD_CYCLES_S49_S51",
        "same_world_uuid": expected_world,
        "same_native_session_id": sid,
        "first_zombie_uuid": deaths[0]["zombie"],
        "second_zombie_uuid": deaths[1]["zombie"],
        "first_item_uuid": spawns[0]["item"],
        "second_item_uuid": spawns[1]["item"],
        "first_natural_count": first_count,
        "second_natural_count": second_count,
        "first_food_before": first_before, "first_food_after": first_after,
        "second_food_before": second_before, "second_food_after": second_after,
        "first_inventory_after_eat": first_count - 1,
        "second_inventory_after_eat": first_count - 2 + second_count,
        "original_S49_action_ids": all_original_ids,
        "original_nonmotion_ledger_sha256": nonmotion.sha256,
        "original_move_ledger_sha256": motion.sha256,
        "World_second_spawn_after_death_ticks": 600,
        "two_real_natural_food_cycles": True,
        "second_pickup_mode": pickup_mode,
        "second_real_MOVE_count": len(second_moves),
        "exact_server_effective_clear_tick_proven": False,
        "autonomous_long_run_proven": False,
        "learning_success_proven": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--nonmotion-fence", type=Path, required=True)
    p.add_argument("--motion-fence", type=Path, required=True)
    p.add_argument("--s50-sidecar", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = audit_two_natural_food_cycles(
        json.loads(a.report.read_text(encoding="utf8")),
        a.server_log.read_text(encoding="utf8"),
        nonmotion_path=a.nonmotion_fence,
        motion_path=a.motion_fence,
        s50_jsonl=a.s50_sidecar.read_text(encoding="utf8"),
    )
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",
                     encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
