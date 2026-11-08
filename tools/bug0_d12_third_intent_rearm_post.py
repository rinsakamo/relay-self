"""D12 independent post-audit: two native S51 meals -> third Paper/native rearm.

Original D8 post proves BOTH physical cycles with the unchanged S49/S51
durable fences. This adds the *read-only* third 600-tick World and Intent
lineage check. An unissued third ATTACK/EAT is not claimed as survival.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.bug0_d6_multigen_world import _tick, _uuid
from tools.bug0_d8_two_natural_food_post import audit_two_natural_food_cycles


class D12ThirdAuditRejected(ValueError):
    """Third World/new original Intent was not independently supportable."""


def require_third_rearm(report: dict, paper_log: str) -> dict:
    if not isinstance(report, dict) or not isinstance(paper_log, str):
        raise D12ThirdAuditRejected("typed real source required")
    record = report.get("d12_third_rearm")
    first = report.get("initial_paper")
    second = report.get("d8_second_generation")
    spawned = report.get("d12_third_paper_spawn")
    if (
        report.get("status") != "PASS_DEV"
        or report.get("d12_third_intent_rearm_optin") is not True
        or report.get("d8_second_generation_food_proven") is not True
        or report.get("d12_third_rearm_proven") is not True
        or report.get("d12_third_rearm_stage")
            != "THIRD_WORLD_NEW_INTENT_NO_ACTION_DEV_PASS"
        or not isinstance(first, str)
        or not isinstance(second, dict)
        or not isinstance(spawned, str)
        or not isinstance(record, dict)
        or "generation=3 " not in spawned
        or "RSELF_RESPAWN_SPAWN world=" not in spawned
    ):
        raise D12ThirdAuditRejected("two-food / third-rearm source absent")
    true_sources = [
        line for line in paper_log.splitlines()
        if "RSELF_RESPAWN_SPAWN world=" in line and "generation=3 " in line
    ]
    if len(true_sources) != 1 or true_sources[0] != spawned:
        raise D12ThirdAuditRejected("third Paper original source not unique")
    native_first = report.get("native_initial", {}).get("zombie_entity_id")
    native_second = report.get("native_respawn", {}).get("zombie_entity_id")
    second_death_tick = second.get("death_tick")
    first_uuid = _uuid(first, "entity")
    second_uuid = second.get("paper_zombie_uuid")
    third_uuid = _uuid(spawned, "entity")
    sid = report.get("session_id")
    if (
        not isinstance(sid, str) or not sid
        or type(native_first) is not int or type(native_second) is not int
        or native_first == native_second
        or not isinstance(second_uuid, str)
        or len({first_uuid, second_uuid, third_uuid}) != 3
        or _uuid(spawned, "world") != _uuid(first, "world")
        or type(second_death_tick) is not int
        or _tick(spawned) - second_death_tick != 600
    ):
        raise D12ThirdAuditRejected("third zombie World generation identity invalid")
    required_true = (
        "same_supervisor", "same_world", "prior_s51_receipt_consumed",
        "no_physical_reissue", "no_new_learning",
    )
    if (
        record.get("session_id") != sid
        or record.get("original_s49_epoch") != 3
        or any(record.get(key) is not True for key in required_true)
        or record.get("third_paper_zombie_uuid") != third_uuid
        or record.get("third_zombie_native_id") in (native_first, native_second)
        or type(record.get("third_zombie_native_id")) is not int
        or record.get("previous_zombie_native_id") != native_second
        or record.get("paper_spawn_tick") != _tick(spawned)
        or record.get("second_death_tick") != second_death_tick
        or type(record.get("native_source_seq")) is not int
        or not isinstance(record.get("native_request_id"), str)
        or not record["native_request_id"]
        or record.get("prior_original_action_count")
            != record.get("after_rearm_original_action_count")
        or type(record.get("prior_original_action_count")) is not int
        or record.get("third_physical_action_count") != 0
        or record.get("prior_second_s51_action_id")
            != second.get("d7f_eat_outcome", {}).get("action_id")
        or record.get("completed_intent_id")
            != report.get("d8_intent_rearm", {}).get("next_intent")
        or not isinstance(record.get("new_intent_id"), str)
        or record.get("new_intent_id") == record.get("completed_intent_id")
        or report.get("learning_updated") is not False
        or report.get("real_model_calls") != 0
    ):
        raise D12ThirdAuditRejected("original owner next Intent or receipt identity invalid")
    return {
        "status": "PASS_DEV",
        "classification": "D12_TWO_TRUE_MEALS_THIRD_REAL_WORLD_INTENT_REARM_PASS",
        "two_real_food_cycles": True,
        "third_paper_zombie_uuid": third_uuid,
        "third_world_spawn_tick": _tick(spawned),
        "previous_paper_death_tick": second_death_tick,
        "third_spawn_after_exactly_600_world_ticks": True,
        "same_original_s49_supervisor_reported": True,
        "original_s51_second_receipt_single_use": True,
        "additional_physical_actions": 0,
        "third_real_attack_or_eat": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def audit_d12(
    report: dict, paper_log: str, *, nonmotion_path: Path,
    motion_path: Path, s50_jsonl: str,
) -> dict:
    parent = audit_two_natural_food_cycles(
        report, paper_log,
        nonmotion_path=nonmotion_path,
        motion_path=motion_path,
        s50_jsonl=s50_jsonl,
    )
    if parent.get("status") == "NOT_EXERCISED":
        if report.get("d12_third_rearm_proven") is True:
            raise D12ThirdAuditRejected("cannot claim third rearm without two meals")
        return {
            "status": "NOT_EXERCISED",
            "classification": "D12_THIRD_REARM_NOT_EXERCISED_TRUE_ZERO_FOOD",
            "d8_parent_audit": parent,
            "third_rearm": False,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }
    if (
        parent.get("status") != "PASS_DEV"
        or parent.get("two_real_natural_food_cycles") is not True
    ):
        raise D12ThirdAuditRejected("two genuine D8 food cycles not independently proven")
    result = require_third_rearm(report, paper_log)
    result["d8_parent_audit"] = parent
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    for name in ("report", "server-log", "nonmotion-fence", "motion-fence",
                 "s50-sidecar", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    report = json.loads(a.report.read_text(encoding="utf8"))
    audit = audit_d12(
        report, a.server_log.read_text(encoding="utf8"),
        nonmotion_path=a.nonmotion_fence,
        motion_path=a.motion_fence,
        s50_jsonl=a.s50_sidecar.read_text(encoding="utf8"),
    )
    a.out.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    print(audit["classification"])


if __name__ == "__main__":
    main()
