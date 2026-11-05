"""Independent post-World audit of WorldBody server physics, never L0 input.

Private Paper plugin truth is permitted ONLY in this post-hoc operator audit.
SelfBody/S49 does not receive it, nor the World fatigue/recovery coefficients.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _rows(source: str, marker: str) -> list[dict[str, str]]:
    out = []
    needle = "WORLDBODY_" + marker + " "
    for raw in source.splitlines():
        if needle not in raw:
            continue
        pairs = [x.split("=", 1) for x in raw.split(needle, 1)[1].split()]
        if any(len(x) != 2 for x in pairs):
            raise ValueError("malformed authoritative server marker")
        row = dict(pairs)
        if len(row) != len(pairs):
            raise ValueError("duplicate authoritative server marker")
        out.append(row)
    return out


def compare_fixed_worldbody(report: dict[str, Any], paper_log: str) -> dict[str, Any]:
    if (
        report.get("status") != "PASS"
        or report.get("classification")
            != "DEV_ONLY_WORLDBODY_FIXED_PHYSICS_DIRECT_S16_REST"
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
        or not isinstance(report.get("actual_native_actions"), list)
        or len(report["actual_native_actions"]) != 2
        or [a.get("terminal") for a in report["actual_native_actions"]]
            != ["outcome", "outcome"]
        or [x.get("selected") for x in report.get("decisions", ())]
            != ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]
        or report.get("worldbody_postmove_l0_choice", {}).get("selected") != "REST"
        or report.get("worldbody_postmove_l0_choice", {}).get("rest_action_issued")
            is not False
        or report.get("worldbody_rest_native_observation", {}).get("sample_count")
            != 9
        or report.get("node_exit") != 0
        or report.get("server_exit") != 0
        or "WORLDBODY_SOURCE_FAULT" in paper_log
    ):
        raise ValueError("source-bound original S49 WorldBody report not qualified")

    experience = report.get("worldbody_direct_motor_observations")
    req = report.get("worldbody_direct_rest_request")
    if (
        not isinstance(experience, list) or len(experience) != 2
        or not isinstance(req, dict)
        or req.get("rest_requested") is not True
        or req.get("reason") != "OBSERVED_MOTOR_OUTPUT_LOSS"
        or req.get("worldbody_truth_accessed") is not False
        or any(item.get("hidden_worldbody_fatigue_accessed") is not False
               or item.get("worldbody_rate_accessed") is not False
               or item.get("session_id") != report.get("session_id")
               for item in experience)
        or not all(type(x.get("action_distance_m")) in (int, float)
                   and math.isfinite(x["action_distance_m"])
                   for x in experience)
        or req.get("output_ratio") != (
            experience[1]["action_distance_m"] / experience[0]["action_distance_m"]
        )
        or not 0 < req["output_ratio"] < 0.8
    ):
        raise ValueError("native SelfBody motor delta missing or server truth leaked")

    attached = _rows(paper_log, "ATTACH")
    effects = _rows(paper_log, "EFFECT")
    samples = _rows(paper_log, "INTERNAL")
    if len(attached) != 1 or len(effects) < 2 or len(samples) < 20:
        raise ValueError("WorldBody physical server truth transition absent")
    identity = (attached[0].get("world"), attached[0].get("player"))
    if any((x.get("world"), x.get("player")) != identity
           for x in [*effects, *samples]):
        raise ValueError("foreign WorldBody physical source")
    ticks = [int(e["tick"]) for e in effects]
    if ticks != sorted(ticks) or len(set(ticks)) != len(ticks):
        raise ValueError("repeated/retroactive physical effect")
    types = [e["change"] for e in effects]
    if types[0] != "DEGRADED" or types[-1] != "RECOVERED":
        raise ValueError("no initial physical degradation / final recovery")
    if not all(types[i] != types[i-1] for i in range(1, len(types))):
        raise ValueError("duplicate uncontrolled speed transition")
    if (
        effects[0].get("actual_walk_speed") not in ("0.08", "0.07999999821186066")
        or effects[0].get("native_effect") != "SLOWNESS_V"
        or effects[0].get("potion_active") != "true"
        or effects[-1].get("actual_walk_speed") not in ("0.2", "0.20000000298023224")
        or effects[-1].get("native_effect") != "NONE"
        or effects[-1].get("potion_active") != "false"
    ):
        # This is an exact DEV Paper rule, not a Self-observed fatigue value.
        raise ValueError("wrong actual Paper movement ability")
    last = max(int(x["tick"]) for x in samples)
    if last < ticks[-1]:
        raise ValueError("recovery claimed after source stopped")
    return {
        "classification": "DEV_ORIGINAL_S49_WORLDBODY_FIXED_PHYSICAL_EFFECT_AND_REST",
        "physical_source": "ORIGINAL_PAPER_PLUGIN_WALK_SPEED_AND_NATIVE_SLOWNESS_V",
        "server_world_uuid": identity[0],
        "server_player_uuid": identity[1],
        "worldbody_true_fatigue_and_rates_usable_by_self": False,
        "first_move_m": req["first_move_m"],
        "second_move_m": req["last_move_m"],
        "motor_output_ratio": req["output_ratio"],
        "first_speed_degradation_tick": ticks[0],
        "final_physical_speed_recovery_tick": ticks[-1],
        "physical_speed_transition_sequence": types,
        "server_native_slowness_on_degrade": True,
        "server_native_slowness_removed_on_recovery": True,
        "actual_walk_speed_restored": True,
        "original_l0_rest_intent": True,
        "original_rest_additional_native_actions": 0,
        "motor_recovery_observed_by_self_after_rest": False,
        "server_physical_recovery_attested_posthoc": True,
        "worldbody_rules_not_modified_by_self": True,
        "model_fatigue_read_into_self": False,
        "compressed_sensation_or_emotion": False,
        "physical_survival_advantage_proven": False,
        "qualification_go": False,
        "science_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--paper-log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = compare_fixed_worldbody(
        json.loads(args.report.read_text(encoding="utf-8")),
        args.paper_log.read_text(encoding="utf-8"),
    )
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("DEV_ORIGINAL_WORLDBODY_PHYSICAL_DEGRADE_AND_RECOVER_PASS")
    print(f"OBSERVED_MOTOR_RATIO={out['motor_output_ratio']}")


if __name__ == "__main__":
    main()
