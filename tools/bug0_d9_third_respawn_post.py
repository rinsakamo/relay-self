"""Independent D9-A: audit D8 two meals AND passive survival until 3rd spawn.

Never promotes a new third-gen EAT or autonomous REST. Unchanged Paper log and
original nonmotion/C1 fences are the only physical provenance sources.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from tools.bug0_d6_multigen_world import _tick, _uuid, one_source_line
from tools.bug0_d8_two_natural_food_post import audit_two_natural_food_cycles
from tools.bug0_d9_third_respawn_world import d9_qualify_third_spawn


class D9SurvivalAuditRejected(ValueError):
    """Original native/Paper/fence evidence does not certify longer survival."""


def _field(line: str, key: str) -> str:
    try:
        return line.split(" " + key + "=", 1)[1].split()[0]
    except IndexError as exc:
        raise D9SurvivalAuditRejected("Paper tick missing " + key) from exc


def audit_paper_idle_before_third(log: str, third_tick: int) -> dict:
    """Read-only server-native controls, NOT an autonomous REST selection."""
    ticks: dict[int, tuple[float, float]] = {}
    for line in log.splitlines():
        if "RSELF_D7_PAPER_TICK source=PAPER_SERVER_MAIN_THREAD_V1 " not in line:
            continue
        tick = _tick(line)
        if not third_tick-16 <= tick < third_tick:
            continue
        for key in ("forward", "back", "left", "right", "jump",
                    "sprint", "sneak"):
            if _field(line, key) != "false":
                raise D9SurvivalAuditRejected("physical body still has active input")
        x, z = float(_field(line, "x")), float(_field(line, "z"))
        if not math.isfinite(x) or not math.isfinite(z) or tick in ticks:
            raise D9SurvivalAuditRejected("nonfinite or repeated Paper motion")
        ticks[tick] = (x, z)
    seq = sorted(ticks)
    if (
        len(seq) < 8
        or any(b != a+1 for a, b in zip(seq, seq[1:]))
        or max(p[0] for p in ticks.values())
            - min(p[0] for p in ticks.values()) > .06
        or max(p[1] for p in ticks.values())
            - min(p[1] for p in ticks.values()) > .06
    ):
        raise D9SurvivalAuditRejected("8+ consecutive source Paper idle ticks unproven")
    return {
        "paper_idle_tick_count": len(seq),
        "paper_idle_start": seq[0],
        "paper_idle_last": seq[-1],
        "all_native_input_off": True,
        "horizontal_stationary_0_06m": True,
        "autonomous_rest_selected": False,
    }


def audit_d9(
    report: dict, paper: str, *, nonmotion_path: Path,
    motion_path: Path, s50_jsonl: str,
) -> dict:
    if not isinstance(report, dict):
        raise D9SurvivalAuditRejected("report not dict")
    base = audit_two_natural_food_cycles(
        report, paper, nonmotion_path=nonmotion_path,
        motion_path=motion_path, s50_jsonl=s50_jsonl,
    )
    if base.get("status") == "NOT_EXERCISED":
        # A first-generation genuine zero never invokes the post-respawn
        # callback: no D9 fields exist. A second-generation zero invokes
        # it and explicitly records NOT_EXERCISED. Neither is a third pass.
        first_zero = report.get("d8_first_true_zero_food_not_exercised") is True
        if (
            (
                first_zero and (
                    report.get("d9_status") is not None
                    or report.get("d9_classification") is not None
                )
            )
            or (
                not first_zero and (
                    report.get("d9_status") != "NOT_EXERCISED"
                    or report.get("d9_classification")
                        != "D9_TWO_EATS_NOT_YET_PROVEN"
                )
            )
            or report.get("d9_third_paper_lineage") is not None
        ):
            raise D9SurvivalAuditRejected("zero natural drop cannot imply D9 survival")
        return {
            "status": "NOT_EXERCISED",
            "classification": "D9_NO_TWO_REAL_MEALS_NO_THIRD_SURVIVAL_CLAIM",
            "d8_prior_two_meals_proven": False,
            "third_gen_attack_issued": False,
            "qualification": "NO_GO", "science": "NOT_RUN",
        }
    if (
        base.get("status") != "PASS_DEV"
        or base.get("two_real_natural_food_cycles") is not True
        or report.get("d9_status") != "PASS_DEV"
        or report.get("d9_classification")
            != "D9_TWO_REAL_EATS_THIRD_RESPAWN_READ_ONLY_SURVIVAL_PASS"
        or report.get("d9_physical_action_issued_after_second_eat") is not False
        or report.get("d9_autonomous_rest_selected") is not False
        or report.get("d9_passive_wait_input_off_not_rest_authorized") is not True
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
        or report.get("cleanup_done") is not True
        or report.get("node_exit") != 0
        or report.get("java_exit") != 0
    ):
        raise D9SurvivalAuditRejected("D8 meal or D9 read-only boundary invalid")
    spawn = one_source_line(
        paper, "RSELF_RESPAWN_SPAWN world=", token="generation=3 ",
    )
    if (
        not spawn or report.get("d9_third_paper_spawn") != spawn
        or one_source_line(
            paper, "RSELF_RESPAWN_DEATH world=", token="generation=3 ",
        ) is not None
        or one_source_line(
            paper, "RSELF_NATURAL_DROP_SPAWN world=",
            token=f'zombie={_uuid(spawn, "entity")} ',
        ) is not None
        or "RSELF_NATURAL_DROP_FAULT" in paper
        or "RSELF_RESPAWN_FAULT" in paper
        or "RSELF_LOOT_STAGED " in paper
    ):
        raise D9SurvivalAuditRejected("third World entity was not passive and fresh")
    lineage = d9_qualify_third_spawn(
        report["initial_paper"], report["paper_respawn"],
        report["d8_second_generation"]["paper_respawn_death"], spawn,
    )
    if lineage != report.get("d9_third_paper_lineage"):
        raise D9SurvivalAuditRejected("third 600tick Paper lineage not original")
    sid = base["same_native_session_id"]
    third = report.get("d9_third_native")
    after = report.get("d9_final_native_body")
    records = report.get("d9_body_monitor_samples")
    l0 = report.get("d9_read_only_l0")
    if (
        not isinstance(third, dict) or not isinstance(after, dict)
        or not isinstance(records, list) or len(records) < 2
        or not isinstance(l0, dict)
        or l0.get("actually_dispatched") is not False
        or not isinstance(l0.get("selected"), str)
        or not isinstance(l0.get("reason"), str)
        or after.get("session_id") != sid
        or third.get("session_id") != sid
        or third.get("zombie_entity_id") in (
            report["native_initial"]["zombie_entity_id"],
            report["native_respawn"]["zombie_entity_id"],
        )
        or third.get("zombie_entity_id") not in after.get("zombie_ids", ())
        or report.get("d9_original_action_count")
            != report.get("d8_original_total_actions")
        or report.get("d9_original_action_ids")
            != sorted(base["original_S49_action_ids"])
        or report.get("d9_nonmotion_sha256")
            != base["original_nonmotion_ledger_sha256"]
        or report.get("d9_motion_sha256")
            != base["original_move_ledger_sha256"]
    ):
        raise D9SurvivalAuditRejected("third fresh native/owner continuity not witnessed")
    last_seq = -1
    ids: set[str] = set()
    for row in [*records, after]:
        if (
            not isinstance(row, dict)
            or row.get("session_id") != sid
            or type(row.get("native_seq")) is not int
            or row["native_seq"] <= last_seq
            or not isinstance(row.get("request_id"), str)
            or not row["request_id"]
            or row["request_id"] in ids
            or not isinstance(row.get("food"), (float, int))
            or not math.isfinite(row["food"]) or row["food"] <= 0
            or not isinstance(row.get("health"), (float, int))
            or not math.isfinite(row["health"]) or row["health"] <= 0
            or row.get("rotten_flesh") != base["second_inventory_after_eat"]
            or not isinstance(row.get("zombie_ids"), list)
        ):
            raise D9SurvivalAuditRejected("native survival record sequence/food invalid")
        last_seq = row["native_seq"]
        ids.add(row["request_id"])
    if (
        type(third.get("seq")) is not int
        or third["seq"] <= records[-1]["native_seq"]
        or third["seq"] >= after["native_seq"]
        or not l0.get("provenance")
    ):
        raise D9SurvivalAuditRejected("third native source not temporally after wait")
    idle = audit_paper_idle_before_third(paper, _tick(spawn))
    return {
        "status": "PASS_DEV",
        "classification": "D9_TWO_TRUE_MEALS_THIRD_WORLD_RESPAWN_SURVIVAL_READONLY_PASS",
        "same_paper_world_uuid": lineage["paper_world_uuid"],
        "same_native_session_id": sid,
        "three_distinct_world_zombie_uuids": True,
        "third_spawn_exact_server_ticks": 600,
        "two_real_natural_food_cycles": True,
        "third_zombie_real_killed": False,
        "third_real_natural_food_cycle": False,
        "same_original_s49_actions_before_after_third": True,
        "native_continuous_survival_samples": len(records) + 1,
        "native_food_after_third": after["food"],
        "native_health_after_third": after["health"],
        "original_nonmotion_sha256": base["original_nonmotion_ledger_sha256"],
        "original_move_sha256": base["original_move_ledger_sha256"],
        "passive_paper_body": idle,
        "autonomous_rest_or_long_run_proven": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    for name in ("report", "server-log", "nonmotion-fence",
                 "motion-fence", "s50-sidecar", "out"):
        p.add_argument("--" + name, required=True, type=Path)
    a = p.parse_args()
    result = audit_d9(
        json.loads(a.report.read_text(encoding="utf8")),
        a.server_log.read_text(encoding="utf8"),
        nonmotion_path=a.nonmotion_fence,
        motion_path=a.motion_fence,
        s50_jsonl=a.s50_sidecar.read_text(encoding="utf8"),
    )
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                     encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
