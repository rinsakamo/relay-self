"""Independent read-only multi-generation Paper/native/S49/dual ledger audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relay_self.action import ActionState
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d6_multigen_world import _rotten, _tick, _uuid, one_source_line


class MultigenAuditRejected(ValueError):
    pass


def _one(raw: str, marker: str, token: str) -> str:
    line = one_source_line(raw, marker, token=token)
    if line is None:
        raise MultigenAuditRejected("missing genuine Paper source " + marker + " " + token)
    return line


def audit(
    original_log: str, report: dict, *, nonmotion_path: Path,
    motion_path: Path,
) -> dict:
    if (
        not isinstance(report, dict) or report.get("status") != "PASS_DEV"
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or report.get("real_world_started") is not True
        or report.get("d6_multigen_self_policy_epoch_limit_imposed") is not False
        or report.get("d6_multigen_source_natural_drop_rng_unchanged") is not True
        or report.get("d6_multigen_no_physical_reissue") is not True
        or report.get("d6_multigen_no_eat") is not True
        or report.get("d6_multigen_same_supervisor") is not True
        or report.get("d6_multigen_eat_after_move") is not False
        or report.get("self_eat") is not False
        or report.get("self_goal_selected_autonomously") is not False
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
        or report.get("d6_multigen_dev_world_trial_limit") != 4
        or "RSELF_RESPAWN_FAULT" in original_log
        or "RSELF_NATURAL_DROP_FAULT" in original_log
        or "RSELF_LOOT_STAGED" in original_log
        or "rselfstagefood" in original_log
        or "effect give RelaySelf minecraft:hunger" in original_log
    ):
        raise MultigenAuditRejected("DEV/World original physical loop source not qualified")
    epochs = report.get("d6_multigen_generations")
    rearm = report.get("d6_multigen_rearms", [])
    if (
        not isinstance(epochs, list)
        or not 1 <= len(epochs) <= 4
        or len(rearm) != len(epochs)-1
        or not isinstance(report.get("session_id"), str)
        or not report["session_id"]
    ):
        raise MultigenAuditRejected("continuous original S49 Intent epoch count invalid")
    nonmotion = OriginalS49NonMotionFence.restore(
        nonmotion_path, self_id="s49-original-self",
    )
    motion = OriginalS49PhysicalFence.restore(
        motion_path, self_id="s49-original-self",
    )
    nonmotion.require_clear()
    motion.require_clear()
    sid = report["session_id"]
    original_attacks = report.get("s49_actions")
    moves = report.get("d6_original_s49_move_actions", [])
    if (
        not isinstance(original_attacks, list)
        or not 1 <= len(original_attacks) <= 8
        or not isinstance(moves, list)
        or len(nonmotion.actions) != (
            len(original_attacks)
            + sum(len(e["action_ids"]) for e in epochs[1:])
        )
        or len(motion.actions) != len(moves)
        or report.get("d6_multigen_final_original_s49_action_count")
           != len(nonmotion.actions)+len(motion.actions)
        or report.get("d6_multigen_final_original_attack_count")
           != len(nonmotion.actions)
        or report.get("d6_multigen_final_original_move_count")
           != len(motion.actions)
        or report.get("nonmotion_fence", {}).get("sha256") != nonmotion.sha256
        or report.get("motion_fence", {}).get("sha256") != motion.sha256
        or report.get("nonmotion_fence", {}).get("unresolved") is not False
        or report.get("motion_fence", {}).get("unresolved") is not False
    ):
        raise MultigenAuditRejected("original journals or Action totals inconsistent")
    paper_world = _uuid(report["initial_paper"], "world")
    seen_zombies = set()
    seen_native = set()
    seen_actions = set()
    last_attack_seq = -1
    expected_attack_ids = []
    death_ticks = []
    positive = []
    for i, epoch in enumerate(epochs, 1):
        if epoch.get("generation") != i or (
            not isinstance(epoch.get("action_ids"), list)
            or len(epoch["action_ids"]) < 1
        ):
            raise MultigenAuditRejected("broken sequential genuine Intent experiences")
        paper_spawn = _one(
            original_log,
            "RSELF_RESPAWN_INITIAL world=" if i == 1
            else "RSELF_RESPAWN_SPAWN world=",
            "generation=1 " if i == 1 else f"generation={i} ",
        )
        paper_death = _one(
            original_log, "RSELF_RESPAWN_DEATH world=",
            f"generation={i} ",
        )
        zombie_uuid = _uuid(paper_spawn, "entity")
        native_id = epoch.get("native_zombie_id")
        if (
            zombie_uuid != epoch.get("paper_zombie_uuid")
            or zombie_uuid != _uuid(paper_death, "entity")
            or zombie_uuid in seen_zombies
            or native_id in seen_native
            or type(native_id) is not int
            or _uuid(paper_spawn, "world") != paper_world
            or _uuid(paper_death, "world") != paper_world
            or epoch.get("death_tick") != _tick(paper_death)
            or _tick(paper_death) < _tick(paper_spawn)
        ):
            raise MultigenAuditRejected("World-owned new zombie per generation invalid")
        seen_zombies.add(zombie_uuid)
        seen_native.add(native_id)
        death_ticks.append(_tick(paper_death))
        natural = _one(
            original_log,
            "RSELF_NATURAL_DROP_DEATH world=",
            f"zombie={zombie_uuid} ",
        )
        count = _rotten(natural)
        if (
            count != epoch.get("real_rotten_count")
            or _tick(natural) != _tick(paper_death)
            or _uuid(natural, "world") != paper_world
            or "killer_is_relay_self=true" not in natural
            or _uuid(natural, "killer") != _uuid(paper_death, "killer")
            or count != 0 and i != len(epochs)
        ):
            raise MultigenAuditRejected("natural vanilla source or Self killer invalid")
        if i > 1:
            rr = rearm[i-2]
            if (
                rr.get("generation") != i
                or rr.get("previous_zombie_native_id") != epochs[i-2]["native_zombie_id"]
                or rr.get("next_zombie_native_id") != native_id
                or rr.get("next_intent_id") != epoch["intent_id"]
                or rr.get("previous_intent_id") != epochs[i-2]["intent_id"]
                or rr.get("physical_issued") is not False
                or rr.get("same_supervisor") is not True
            ):
                raise MultigenAuditRejected("original retained Intent epoch rearm invalid")
        if i < len(epochs):
            next_spawn = _one(
                original_log, "RSELF_RESPAWN_SPAWN world=",
                f"generation={i+1} ",
            )
            if (
                _tick(next_spawn)-_tick(paper_death) != 600
                or epoch.get("respawn_tick") != _tick(next_spawn)
            ):
                raise MultigenAuditRejected("600 world tick respawn source wrong")
        expected_attack_ids.extend(epoch["action_ids"])
        if count > 0:
            positive.append((epoch,natural))
        else:
            if epoch.get("native_inventory_after") != 0:
                raise MultigenAuditRejected("zero-loot native inventory fabricated")
    if len(positive) > 1:
        raise MultigenAuditRejected("natural food should stop physical trial")
    if (
        expected_attack_ids
        != [a["action_id"] for a in nonmotion.actions]
        or len(seen_zombies) != len(epochs)
    ):
        raise MultigenAuditRejected("ATTACK ledger not ordered by true generations")
    for a in nonmotion.actions:
        if (
            a.get("kind") != "ATTACK"
            or a.get("session_id") != sid
            or a.get("status") != "S16_OUTCOME"
            or a.get("action_id") in seen_actions
            or type(a.get("probe_seq")) is not int
            or a.get("probe_seq") <= last_attack_seq
        ):
            raise MultigenAuditRejected("original prior ATTACK replay/UNKNOWN")
        seen_actions.add(a["action_id"])
        last_attack_seq = a["after_seq"]
    if (
        len(epochs) == 4 and not positive
        and (
            report.get("d6_multigen_classification")
            != "D6_MULTIGEN_BOUNDED_FOUR_TRUE_ZERO_DROPS_PASS"
            or report.get("d6_multigen_ci_limit_reached_not_self_goal_completed")
            is not True
            or moves
        )
    ):
        raise MultigenAuditRejected("bounded four true-zero experiences not closed")
    original_item = None
    if positive:
        epoch,_ = positive[0]
        zombie = epoch["paper_zombie_uuid"]
        source = _one(
            original_log, "RSELF_NATURAL_DROP_SPAWN world=",
            f"zombie={zombie} ",
        )
        pickup = _one(
            original_log, "RSELF_NATURAL_DROP_PICKUP world=",
            f"zombie={zombie} ",
        )
        original_item = _uuid(source,"item")
        if (
            _uuid(pickup,"item") != original_item
            or _uuid(source,"world") != paper_world
            or _uuid(pickup,"world") != paper_world
            or _rotten(source) != epoch["real_rotten_count"]
            or _rotten(pickup) != epoch["real_rotten_count"]
            or not _tick(source) < _tick(pickup)
            or epoch.get("item_uuid") != original_item
            or epoch.get("item_spawn_tick") != _tick(source)
            or epoch.get("item_pickup_tick") != _tick(pickup)
            or epoch.get("native_inventory_after") != epoch["real_rotten_count"]
            or report.get("d6_multigen_classification") not in (
                "D6_MULTIGEN_ZERO_DROP_CONTINUE_THEN_REAL_MOVE_PICKUP_PASS",
                "D6_MULTIGEN_FIRST_REAL_NATURAL_MOVE_PICKUP_EAT_FENCED_PASS",
            )
            or not moves
            or len(motion.actions) != len(moves)
            or epoch.get("original_move_action_ids")
                != [m["action_id"] for m in moves]
            or report.get("d6_post_move_eat_fenced") is not True
        ):
            raise MultigenAuditRejected("natural Paper item pickup / Self move not proven")
        first_move_seq = -1
        for m, persistence in zip(moves, motion.actions):
            if (
                persistence.get("status") != "S16_OUTCOME"
                or persistence.get("action_id") != m.get("action_id")
                or persistence.get("intent_id") != epoch["intent_id"]
                or persistence.get("session_id") != sid
                or persistence.get("action_ref") != "MOVE_BACKWARD"
                or persistence.get("before_seq") != m.get("s15_before_seq")
                or persistence.get("dispatch_seq") != m.get("s15_dispatch_seq")
                or persistence.get("cleanup_seq") != m.get("s15_clear_seq")
                or persistence.get("after_seq") != m.get("s15_after_seq")
                or m.get("target_distance_before_m", 0)
                   <= m.get("target_distance_after_m", -1) + .05
                or m.get("s15_after_seq", -1) <= first_move_seq
            ):
                raise MultigenAuditRejected("actual S15/S16 item directed original MOVE invalid")
            first_move_seq = m["s15_after_seq"]
    else:
        if (
            len(epochs) != 4
            or moves
            or motion.actions
            or report.get("d6_multigen_classification")
            != "D6_MULTIGEN_BOUNDED_FOUR_TRUE_ZERO_DROPS_PASS"
        ):
            raise MultigenAuditRejected("all zero should continue until CI trial cap")
    return {
        "classification": report["d6_multigen_classification"],
        "status": "PASS_DEV",
        "paper_world_uuid": paper_world,
        "session_id": sid,
        "completed_original_s49_kill_generations": len(epochs),
        "natural_counts": [e["real_rotten_count"] for e in epochs],
        "unique_zombies": len(seen_zombies),
        "death_ticks": death_ticks,
        "original_attack_count": len(nonmotion.actions),
        "original_move_count": len(motion.actions),
        "natural_item_uuid": original_item,
        "same_supervisor_retained": True,
        "all_real_respawns_world_600_ticks": True,
        "no_eat_after_move": True,
        "physical_exactly_once_proven": False,
        "dev_trial_limit_not_product_policy": True,
        "unresolved_nonmotion": nonmotion.unresolved,
        "unresolved_motion": motion.unresolved,
        "nonmotion_sha256": nonmotion.sha256,
        "motion_sha256": motion.sha256,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--server-log", required=True, type=Path)
    p.add_argument("--nonmotion-fence", required=True, type=Path)
    p.add_argument("--motion-fence", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a=p.parse_args()
    result=audit(
        a.server_log.read_text(encoding="utf8"),
        json.loads(a.report.read_text(encoding="utf8")),
        nonmotion_path=a.nonmotion_fence,
        motion_path=a.motion_fence,
    )
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print(result["classification"])


if __name__=="__main__":
    main()
