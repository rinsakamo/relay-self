"""Retrospective independent DEV audit: fixed WorldBody, Self post-REST third S16.

Only here may the operator inspect Paper's hidden WorldBody server log;
the real S49 decision, SelfBody direct S16 observations and L0 cannot read it.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from tools.worldbody_fixed_physical_post import _rows


def audit_post_rest_retest(report: dict[str, Any], paper_log: str) -> dict[str, Any]:
    expected = "DEV_ONLY_WORLDBODY_ORIGINAL_S49_POST_REST_THIRD_MOTOR_OUTCOME"
    if (
        report.get("status") != "PASS"
        or report.get("classification") != expected
        or report.get("s49_dev_server") != "PINNED_PAPER_1_21_8"
        or report.get("worldbody_profile")
            != "SERVER_FIXED_WALK_SPEED_UNOBSERVED_FATIGUE"
        or report.get("worldbody_truth_exported_to_self") is not False
        or report.get("worldbody_rule_mutation_surface") is not False
        or report.get("worldbody_true_fatigue_received_by_self") is not False
        or report.get("worldbody_physics_write_from_self") is not False
        or report.get("worldbody_physics_verified_from_server_log") is not False
        or report.get("worldbody_rest_action_count") != 0
        or report.get("worldbody_rest_choice_is_not_physical_recovery_proof") is not True
        or report.get("worldbody_postmove_l0_choice", {}).get("selected") != "REST"
        or report.get("worldbody_postmove_l0_choice", {}).get("rest_action_issued")
            is not False
        or report.get("node_exit") != 0 or report.get("server_exit") != 0
        or "WORLDBODY_SOURCE_FAULT" in paper_log
    ):
        raise ValueError("fixed WorldBody and original S49 three-MOVE report invalid")

    decisions = report.get("decisions")
    actions = report.get("actual_native_actions")
    original = report.get("worldbody_direct_motor_observations")
    rest = report.get("worldbody_rest_native_observation")
    check = report.get("worldbody_post_rest_retest")
    if (
        not isinstance(decisions, list) or len(decisions) != 4
        or [x.get("selected") for x in decisions]
            != ["WAIT", "MOVE_AWAY", "MOVE_AWAY", "MOVE_AWAY"]
        or [x.get("issued") for x in decisions] != [False, True, True, True]
        or len({x.get("entity_id") for x in decisions}) != 4
        or not all(
            type(decisions[i].get("event_seq")) is int
            and (i == 0 or decisions[i]["event_seq"] > decisions[i-1]["event_seq"])
            for i in range(4)
        )
        or not isinstance(actions, list) or len(actions) != 3
        or [a.get("terminal") for a in actions] != ["outcome"] * 3
        or len({a.get("action") for a in actions}) != 3
        or [a.get("event_seq") for a in actions]
            != [d["event_seq"] for d in decisions[1:]]
        or not isinstance(original, list) or len(original) != 2
        or not isinstance(rest, dict) or rest.get("sample_count") != 9
        or not isinstance(rest.get("samples"), list)
        or len(rest["samples"]) != 9
        or not isinstance(check, dict)
        or check.get("regained_motor_output") is not True
        or check.get("worldbody_truth_accessed") is not False
        or check.get("server_internal_recovery_used_by_l0") is not False
        or check.get("three_separate_original_s16_move_outcomes") is not True
        or check.get("post_rest_world_rule_unchanged") is not True
    ):
        raise ValueError("four source choices / three original S16 outcomes absent")

    sess = report.get("session_id")
    if not isinstance(sess, str) or not sess:
        raise ValueError("original session ID absent")
    source_refs = check.get("source_refs")
    samples = rest["samples"]
    if (
        not isinstance(source_refs, list) or len(source_refs) != 3
        or not all(type(x.get("native_seq")) is int for x in samples)
        or not all(samples[i]["native_seq"] < samples[i+1]["native_seq"]
                   for i in range(8))
        or check.get("final_rest_probe_seq") != samples[-1]["native_seq"]
        or not all(x.get("session_id") == sess for x in (*original, *samples))
        or not all(x.get("worldbody_rate_accessed") is False
                   and x.get("hidden_worldbody_fatigue_accessed") is False
                   for x in original)
        or [x.get("source_ref") for x in original] != source_refs[:2]
        or not all(
            isinstance(ref, str) and ref.startswith(f"native-probe:{sess}:")
            for ref in source_refs
        )
        or [x.get("action_id") for x in original] != [
            a.get("action") for a in actions[:2]
        ]
        or check.get("post_rest_action") != actions[2].get("action")
        or check.get("pre_rest_first_action") != actions[0].get("action")
        or check.get("pre_rest_exhausted_action") != actions[1].get("action")
    ):
        raise ValueError("original correlation/provenance or REST boundary invalid")
    seqs = [int(ref.split(":")[2]) for ref in source_refs]
    if not seqs[0] < seqs[1] < samples[0]["native_seq"] <= (
        samples[-1]["native_seq"]
    ) < seqs[2]:
        raise ValueError("post-REST third MOVE source used future or stale probe")

    distances = [a.get("movement_m") for a in actions]
    if (
        any(type(d) not in (int, float) or not math.isfinite(d) or d <= 0
            for d in distances)
        or distances[0] != original[0].get("action_distance_m")
        or distances[1] != original[1].get("action_distance_m")
        or distances[0] != check.get("pre_rest_first_m")
        or distances[1] != check.get("pre_rest_exhausted_m")
        or distances[2] != check.get("post_rest_m")
        or distances[1] / distances[0] >= 0.8
        or distances[2] / distances[1] < 1.8
        or distances[2] / distances[0] < 0.7
        or not math.isclose(check.get("recovery_over_exhausted_ratio", float("nan")),
                            distances[2] / distances[1], rel_tol=0, abs_tol=1e-12)
        or not math.isclose(check.get("recovery_over_first_ratio", float("nan")),
                            distances[2] / distances[0], rel_tol=0, abs_tol=1e-12)
    ):
        raise ValueError("third original S16 MOVE did not regain motor output")

    attached = _rows(paper_log, "ATTACH")
    effects = _rows(paper_log, "EFFECT")
    restrict = _rows(paper_log, "RESTRICT")
    internal = _rows(paper_log, "INTERNAL")
    if (
        len(attached) != 1
        or len(effects) < 2
        or len(restrict) < 1
        or len(internal) < 20
    ):
        raise ValueError("server WorldBody physical source incomplete")
    identity = (attached[0].get("world"), attached[0].get("player"))
    if (
        any((row.get("world"), row.get("player")) != identity
            for row in (*effects, *restrict, *internal))
        or any(
            row.get("server_constraint") != "PLAYER_MOVE_DESTINATION"
            or not math.isclose(
                float(row["accepted_m"]) / float(row["requested_m"]),
                0.35, rel_tol=0, abs_tol=1e-12,
            )
            for row in restrict
        )
        or [int(e["tick"]) for e in effects]
            != sorted(int(e["tick"]) for e in effects)
        or not any(
            effects[i].get("change") == "DEGRADED"
            and effects[j].get("change") == "RECOVERED"
            and int(effects[j]["tick"]) > int(effects[i]["tick"])
            for i in range(len(effects))
            for j in range(i+1, len(effects))
        )
        or any(
            e.get("native_effect") != (
                "SLOWNESS_V" if e.get("change") == "DEGRADED" else "NONE"
            )
            for e in effects
        )
    ):
        raise ValueError("fixed Paper WorldBody server recovery not source-verified")

    return {
        "classification": "DEV_WORLDBODY_SAME_ORIGINAL_S49_THIRD_MOTOR_REGAIN",
        "original_s49_session_id": sess,
        "original_native_l0_decisions": [d["selected"] for d in decisions],
        "original_s16_move_action_ids": [a["action"] for a in actions],
        "original_three_move_distances_m": distances,
        "degraded_output_ratio": distances[1] / distances[0],
        "recovered_over_degraded_ratio": distances[2] / distances[1],
        "recovered_over_initial_ratio": distances[2] / distances[0],
        "rest_native_stationary_samples": 9,
        "post_rest_native_source_after_last_rest_probe": True,
        "original_l0_rest_action_issued": False,
        "worldbody_server_source_uuid": identity[0],
        "worldbody_server_physical_recovery_recorded": True,
        "worldbody_server_destination_restriction_records": len(restrict),
        "self_used_hidden_worldbody_fatigue_or_recovery_rate": False,
        "self_observed_regained_motor_output": True,
        "worldbody_rules_mutated_by_self": False,
        "sensation_or_emotion_compression": False,
        "learning_committed": False,
        "independent_full_tick_physical_rest_attested": False,
        "causal_survival_advantage_proven": False,
        "qualification_go": False,
        "science_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--paper-log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit_post_rest_retest(
        json.loads(args.report.read_text(encoding="utf-8")),
        args.paper_log.read_text(encoding="utf-8"),
    )
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n",
                        encoding="utf-8")
    print("DEV_SAME_S49_REST_THEN_THIRD_MOTOR_REGAIN_SOURCE_PASS")
    print("THREE_S16_METRES="+json.dumps(result["original_three_move_distances_m"]))


if __name__ == "__main__":
    main()
